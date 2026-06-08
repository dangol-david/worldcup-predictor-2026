"""
database.py
-----------
SQLite persistence layer for the Predict and Win World Cup app.

Tables
------
- users        : registered players
- matches      : tournament fixtures across QF / SF / Final
- predictions  : per-user predictions for each match
                 (scored automatically when a match is marked completed)
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

DB_PATH = Path(__file__).parent / "worldcup.db"

VALID_STAGES = (
    "Group Stage", "Round of 32", "Round of 16",
    "Quarter-Final", "Semi-Final", "Third Place", "Final",
)
VALID_STATUS = ("upcoming", "completed")

STAGE_ORDER = {s: i for i, s in enumerate(VALID_STAGES, start=1)}

MAX_DAILY_PARTICIPANTS = 10

# Predictions for a match freeze this many hours before its scheduled kickoff.
LOCK_LEAD_HOURS = 3


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------
@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Yield a SQLite connection with foreign keys + Row factory enabled."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT UNIQUE NOT NULL COLLATE NOCASE,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS matches (
    match_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    match_number INTEGER UNIQUE,
    stage        TEXT NOT NULL CHECK(stage IN (
                    'Group Stage','Round of 32','Round of 16',
                    'Quarter-Final','Semi-Final','Third Place','Final')),
    group_name   TEXT,
    team_a       TEXT NOT NULL,
    team_b       TEXT NOT NULL,
    match_date   TIMESTAMP NOT NULL,
    venue        TEXT,
    city         TEXT,
    country      TEXT,
    score_a      INTEGER,
    score_b      INTEGER,
    winner       TEXT,
    mom_player   TEXT,
    first_scorer TEXT,
    highlights   TEXT,
    status       TEXT NOT NULL DEFAULT 'upcoming'
                 CHECK(status IN ('upcoming','completed')),
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS predictions (
    prediction_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL,
    match_id          INTEGER NOT NULL,
    predicted_winner       TEXT    NOT NULL,
    predicted_score_a      INTEGER NOT NULL,
    predicted_score_b      INTEGER NOT NULL,
    predicted_mom          TEXT,
    predicted_first_scorer TEXT,
    is_banker         INTEGER NOT NULL DEFAULT 0,
    winner_points     INTEGER NOT NULL DEFAULT 0,
    score_points      INTEGER NOT NULL DEFAULT 0,
    mom_points        INTEGER NOT NULL DEFAULT 0,
    scorer_points     INTEGER NOT NULL DEFAULT 0,
    bonus_points      INTEGER NOT NULL DEFAULT 0,
    total_points      INTEGER NOT NULL DEFAULT 0,
    is_evaluated      INTEGER NOT NULL DEFAULT 0,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)  REFERENCES users(user_id)   ON DELETE CASCADE,
    FOREIGN KEY (match_id) REFERENCES matches(match_id) ON DELETE CASCADE,
    UNIQUE(user_id, match_id)
);

CREATE TABLE IF NOT EXISTS daily_participants (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    day         TEXT NOT NULL,
    user_id     INTEGER NOT NULL,
    joined_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(day, user_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS squads (
    team       TEXT PRIMARY KEY COLLATE NOCASE,
    coach      TEXT,
    players    TEXT,                       -- one player name per line
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_matches_stage  ON matches(stage);
CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
CREATE INDEX IF NOT EXISTS idx_matches_group  ON matches(group_name);
CREATE INDEX IF NOT EXISTS idx_matches_number ON matches(match_number);
CREATE INDEX IF NOT EXISTS idx_pred_user      ON predictions(user_id);
CREATE INDEX IF NOT EXISTS idx_pred_match     ON predictions(match_id);
CREATE INDEX IF NOT EXISTS idx_daily_day      ON daily_participants(day);
"""


def init_db() -> None:
    """Create tables/indexes if missing. Also run lightweight migrations."""
    # Columns added after the original schema shipped. Each is applied with a
    # plain ALTER for databases created before the column existed; CREATE TABLE
    # above already includes them for fresh installs.
    migrations = [
        ("matches",     "first_scorer",           "TEXT"),
        ("matches",     "highlights",             "TEXT"),
        ("predictions", "predicted_first_scorer", "TEXT"),
        ("predictions", "is_banker",              "INTEGER NOT NULL DEFAULT 0"),
        ("predictions", "scorer_points",          "INTEGER NOT NULL DEFAULT 0"),
        ("predictions", "bonus_points",           "INTEGER NOT NULL DEFAULT 0"),
    ]
    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)
        for table, column, decl in migrations:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
            except sqlite3.OperationalError:
                pass  # column already exists


# ---------------------------------------------------------------------------
# Prediction lock (time-based)
# ---------------------------------------------------------------------------
def lock_time(match: dict[str, Any]) -> datetime | None:
    """The instant predictions freeze for a match (kickoff − LOCK_LEAD_HOURS)."""
    try:
        kickoff = datetime.fromisoformat(match["match_date"])
    except (ValueError, TypeError, KeyError):
        return None
    return kickoff - timedelta(hours=LOCK_LEAD_HOURS)


def is_match_locked(match: dict[str, Any]) -> bool:
    """True if predictions are frozen: match completed OR within the lock window."""
    if match.get("status") == "completed":
        return True
    lock_at = lock_time(match)
    if lock_at is None:
        return False
    return datetime.now() >= lock_at


# ---------------------------------------------------------------------------
# User operations
# ---------------------------------------------------------------------------
def create_user(username: str) -> int:
    """Insert a new user. Returns user_id. Raises ValueError if name taken/empty."""
    username = (username or "").strip()
    if not username:
        raise ValueError("Username cannot be empty.")
    if len(username) > 30:
        raise ValueError("Username must be 30 characters or fewer.")

    with get_connection() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users (username) VALUES (?)", (username,)
            )
            return cur.lastrowid
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Username '{username}' is already taken.") from exc


def get_user(username: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username.strip(),)
        ).fetchone()
        return dict(row) if row else None


def list_users() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM users ORDER BY username COLLATE NOCASE"
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Match operations
# ---------------------------------------------------------------------------
def create_match(
    stage: str,
    team_a: str,
    team_b: str,
    match_date: str,
    venue: str | None = None,
    city: str | None = None,
    country: str | None = None,
    match_number: int | None = None,
    group_name: str | None = None,
) -> int:
    if stage not in VALID_STAGES:
        raise ValueError(f"Invalid stage. Must be one of {VALID_STAGES}.")
    if not team_a or not team_b:
        raise ValueError("Both teams are required.")
    if team_a.strip().lower() == team_b.strip().lower():
        raise ValueError("A team cannot play itself.")

    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO matches (
                match_number, stage, group_name,
                team_a, team_b, match_date,
                venue, city, country
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (match_number, stage, group_name,
             team_a.strip(), team_b.strip(), match_date,
             venue, city, country),
        )
        return cur.lastrowid


def get_match(match_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM matches WHERE match_id = ?", (match_id,)
        ).fetchone()
        return dict(row) if row else None


def list_matches(
    stage: str | None = None,
    status: str | None = None,
    group_name: str | None = None,
) -> list[dict[str, Any]]:
    """Return matches optionally filtered, ordered by date then match_number."""
    query = "SELECT * FROM matches WHERE 1=1"
    params: list[Any] = []
    if stage:
        query += " AND stage = ?"
        params.append(stage)
    if status:
        query += " AND status = ?"
        params.append(status)
    if group_name:
        query += " AND group_name = ?"
        params.append(group_name)
    query += " ORDER BY match_date ASC, match_number ASC, match_id ASC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def update_match_result(
    match_id: int,
    score_a: int,
    score_b: int,
    mom_player: str | None,
    first_scorer: str | None = None,
) -> None:
    """Mark a match completed with final score, MOM & first scorer, then score."""
    if score_a < 0 or score_b < 0:
        raise ValueError("Scores cannot be negative.")

    match = get_match(match_id)
    if not match:
        raise ValueError(f"Match {match_id} does not exist.")

    # Determine winner. Knockout games can't be a tie in real life, but for
    # group-stage-like flexibility we allow 'Draw' to be recorded.
    if score_a > score_b:
        winner = match["team_a"]
    elif score_b > score_a:
        winner = match["team_b"]
    else:
        winner = "Draw"

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE matches
               SET score_a      = ?,
                   score_b      = ?,
                   mom_player   = ?,
                   first_scorer = ?,
                   winner       = ?,
                   status       = 'completed'
             WHERE match_id     = ?
            """,
            (
                score_a, score_b,
                (mom_player or "").strip() or None,
                (first_scorer or "").strip() or None,
                winner, match_id,
            ),
        )

    # Score all predictions for this match.
    # Imported here to avoid a circular import at module load time.
    from game_logic import evaluate_predictions_for_match
    evaluate_predictions_for_match(match_id)


# ---------------------------------------------------------------------------
# Prediction operations
# ---------------------------------------------------------------------------
def upsert_prediction(
    user_id: int,
    match_id: int,
    predicted_winner: str,
    predicted_score_a: int,
    predicted_score_b: int,
    predicted_mom: str | None,
    predicted_first_scorer: str | None = None,
) -> None:
    """Insert or update a user's prediction. Locked LOCK_LEAD_HOURS before kickoff."""
    if predicted_score_a < 0 or predicted_score_b < 0:
        raise ValueError("Predicted scores cannot be negative.")
    if predicted_score_a > 20 or predicted_score_b > 20:
        raise ValueError("Predicted scores look unrealistic (max 20).")

    match = get_match(match_id)
    if not match:
        raise ValueError("Match not found.")
    if is_match_locked(match):
        raise ValueError(
            f"Predictions for this match are locked "
            f"(they close {LOCK_LEAD_HOURS}h before kickoff)."
        )

    valid_winners = {match["team_a"], match["team_b"], "Draw"}
    if predicted_winner not in valid_winners:
        raise ValueError(
            f"Predicted winner must be one of: {', '.join(sorted(valid_winners))}."
        )

    # Consistency check: predicted score should agree with predicted winner.
    if predicted_score_a > predicted_score_b and predicted_winner != match["team_a"]:
        raise ValueError("Your predicted score implies a different winner.")
    if predicted_score_b > predicted_score_a and predicted_winner != match["team_b"]:
        raise ValueError("Your predicted score implies a different winner.")
    if predicted_score_a == predicted_score_b and predicted_winner != "Draw":
        raise ValueError("Equal scores must be predicted as a Draw.")

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO predictions (
                user_id, match_id,
                predicted_winner, predicted_score_a, predicted_score_b,
                predicted_mom, predicted_first_scorer
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, match_id) DO UPDATE SET
                predicted_winner       = excluded.predicted_winner,
                predicted_score_a      = excluded.predicted_score_a,
                predicted_score_b      = excluded.predicted_score_b,
                predicted_mom          = excluded.predicted_mom,
                predicted_first_scorer = excluded.predicted_first_scorer,
                updated_at             = CURRENT_TIMESTAMP
            """,
            (
                user_id, match_id,
                predicted_winner, predicted_score_a, predicted_score_b,
                (predicted_mom or "").strip() or None,
                (predicted_first_scorer or "").strip() or None,
            ),
        )


# ---------------------------------------------------------------------------
# Banker (double-down) — one per user per calendar day
# ---------------------------------------------------------------------------
def set_banker(user_id: int, match_id: int, on: bool = True) -> None:
    """
    Flag (or clear) a prediction as the player's Banker for that match's day.
    Setting a banker clears any other banker the user holds on the SAME day,
    so each player has at most one banker per calendar day. Locked once the
    match's prediction window closes.
    """
    match = get_match(match_id)
    if not match:
        raise ValueError("Match not found.")
    if is_match_locked(match):
        raise ValueError("This match is locked — banker can no longer be changed.")

    pred = get_user_prediction(user_id, match_id)
    if not pred:
        raise ValueError("Make a prediction for this match before setting it as Banker.")

    day = (match["match_date"] or "")[:10]
    with get_connection() as conn:
        if on:
            # Clear any existing banker the user holds on the same day.
            conn.execute(
                """
                UPDATE predictions
                   SET is_banker = 0
                 WHERE user_id = ?
                   AND match_id IN (
                       SELECT match_id FROM matches WHERE date(match_date) = ?
                   )
                """,
                (user_id, day),
            )
        conn.execute(
            "UPDATE predictions SET is_banker = ? WHERE user_id = ? AND match_id = ?",
            (1 if on else 0, user_id, match_id),
        )


def get_banker_for_day(user_id: int, day: str) -> dict[str, Any] | None:
    """Return the user's banker prediction (joined with match) for a day, if any."""
    if not user_id:
        return None
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT p.*, m.team_a, m.team_b, m.match_number, m.stage
              FROM predictions p
              JOIN matches m ON m.match_id = p.match_id
             WHERE p.user_id = ? AND p.is_banker = 1
               AND date(m.match_date) = ?
             LIMIT 1
            """,
            (user_id, day),
        ).fetchone()
        return dict(row) if row else None


def get_user_prediction(user_id: int, match_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM predictions WHERE user_id = ? AND match_id = ?",
            (user_id, match_id),
        ).fetchone()
        return dict(row) if row else None


def list_user_predictions(user_id: int) -> list[dict[str, Any]]:
    """Predictions joined with match info, ordered by stage and date."""
    stage_order = (
        "CASE stage "
        "WHEN 'Group Stage'    THEN 1 "
        "WHEN 'Round of 32'    THEN 2 "
        "WHEN 'Round of 16'    THEN 3 "
        "WHEN 'Quarter-Final'  THEN 4 "
        "WHEN 'Semi-Final'     THEN 5 "
        "WHEN 'Third Place'    THEN 6 "
        "WHEN 'Final'          THEN 7 END"
    )
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT p.*, m.stage, m.team_a, m.team_b, m.match_date,
                   m.match_number, m.group_name, m.venue, m.city,
                   m.score_a AS actual_score_a,
                   m.score_b AS actual_score_b,
                   m.winner  AS actual_winner,
                   m.mom_player   AS actual_mom,
                   m.first_scorer AS actual_first_scorer,
                   m.status
              FROM predictions p
              JOIN matches m ON m.match_id = p.match_id
             WHERE p.user_id = ?
             ORDER BY {stage_order}, m.match_date ASC
            """,
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def list_predictions_for_match(match_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT p.*, u.username
              FROM predictions p
              JOIN users u ON u.user_id = p.user_id
             WHERE p.match_id = ?
            """,
            (match_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------
def get_leaderboard() -> list[dict[str, Any]]:
    """
    Aggregate total + stage-wise + category-wise points per user.
    Users with zero predictions still appear (LEFT JOIN) for transparency.
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                u.user_id,
                u.username,
                COALESCE(SUM(p.total_points), 0)   AS total_points,
                COALESCE(SUM(p.winner_points), 0)  AS winner_points,
                COALESCE(SUM(p.score_points), 0)   AS score_points,
                COALESCE(SUM(p.mom_points), 0)     AS mom_points,
                COALESCE(SUM(p.scorer_points), 0)  AS scorer_points,
                COALESCE(SUM(p.bonus_points), 0)   AS bonus_points,
                COALESCE(SUM(CASE WHEN m.stage='Group Stage'
                                  THEN p.total_points END), 0) AS group_points,
                COALESCE(SUM(CASE WHEN m.stage='Round of 32'
                                  THEN p.total_points END), 0) AS r32_points,
                COALESCE(SUM(CASE WHEN m.stage='Round of 16'
                                  THEN p.total_points END), 0) AS r16_points,
                COALESCE(SUM(CASE WHEN m.stage='Quarter-Final'
                                  THEN p.total_points END), 0) AS qf_points,
                COALESCE(SUM(CASE WHEN m.stage='Semi-Final'
                                  THEN p.total_points END), 0) AS sf_points,
                COALESCE(SUM(CASE WHEN m.stage='Final'
                                  THEN p.total_points END), 0) AS final_points,
                COUNT(p.prediction_id)                          AS predictions_made,
                COUNT(CASE WHEN p.is_evaluated = 1 THEN 1 END)  AS matches_scored,
                COUNT(CASE WHEN p.is_evaluated = 1
                            AND p.winner_points + p.score_points > 0
                           THEN 1 END)                          AS correct_winners
              FROM users u
              LEFT JOIN predictions p ON p.user_id = u.user_id
              LEFT JOIN matches m     ON m.match_id = p.match_id
             GROUP BY u.user_id, u.username
             ORDER BY total_points DESC, u.username COLLATE NOCASE ASC
            """
        ).fetchall()
        return [dict(r) for r in rows]


def compute_group_standings(group_name: str) -> list[dict[str, Any]]:
    """
    Compute standings for a group from its completed Group Stage matches.
    Standard FIFA rules: 3pts win, 1 draw, 0 loss; ordered by Pts, GD, GF.
    """
    matches = list_matches(stage="Group Stage", group_name=group_name)
    teams: dict[str, dict[str, Any]] = {}

    for m in matches:
        for t in (m["team_a"], m["team_b"]):
            teams.setdefault(t, {
                "team": t, "P": 0, "W": 0, "D": 0, "L": 0,
                "GF": 0, "GA": 0, "GD": 0, "Pts": 0,
            })
        if m["status"] != "completed":
            continue
        a, b = m["team_a"], m["team_b"]
        sa, sb = m["score_a"], m["score_b"]
        teams[a]["P"] += 1; teams[b]["P"] += 1
        teams[a]["GF"] += sa; teams[a]["GA"] += sb
        teams[b]["GF"] += sb; teams[b]["GA"] += sa
        if sa > sb:
            teams[a]["W"] += 1; teams[b]["L"] += 1; teams[a]["Pts"] += 3
        elif sb > sa:
            teams[b]["W"] += 1; teams[a]["L"] += 1; teams[b]["Pts"] += 3
        else:
            teams[a]["D"] += 1; teams[b]["D"] += 1
            teams[a]["Pts"] += 1; teams[b]["Pts"] += 1

    for t in teams.values():
        t["GD"] = t["GF"] - t["GA"]

    return sorted(
        teams.values(),
        key=lambda r: (-r["Pts"], -r["GD"], -r["GF"], r["team"]),
    )


def list_groups() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT group_name FROM matches "
            "WHERE group_name IS NOT NULL ORDER BY group_name"
        ).fetchall()
    return [r["group_name"] for r in rows]


def get_tournament_winner() -> dict[str, Any] | None:
    """The single team that won the Final, if it has been played."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT winner, team_a, team_b, score_a, score_b, mom_player, match_date
              FROM matches
             WHERE stage = 'Final' AND status = 'completed'
             ORDER BY match_date DESC
             LIMIT 1
            """
        ).fetchone()
        return dict(row) if row else None


# =============================================================================
# Daily Mode
# =============================================================================
def get_matches_for_day(day: str) -> list[dict[str, Any]]:
    """Matches whose match_date falls on the given calendar day (YYYY-MM-DD, ET)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM matches "
            "WHERE date(match_date) = ? "
            "ORDER BY match_date ASC, match_number ASC",
            (day,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_tournament_dates() -> list[dict[str, Any]]:
    """Distinct match dates with completion counts, in chronological order."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT date(match_date) AS day,
                   COUNT(*)         AS total,
                   SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) AS completed
              FROM matches
             GROUP BY date(match_date)
             ORDER BY day
            """
        ).fetchall()
    return [dict(r) for r in rows]


def join_daily_game(user_id: int, day: str) -> None:
    """Register user for a day's daily mode. Enforces 10-player cap."""
    if not user_id:
        raise ValueError("Sign in to join daily mode.")
    with get_connection() as conn:
        already = conn.execute(
            "SELECT 1 FROM daily_participants WHERE day = ? AND user_id = ?",
            (day, user_id),
        ).fetchone()
        if already:
            return  # idempotent
        count = conn.execute(
            "SELECT COUNT(*) AS c FROM daily_participants WHERE day = ?",
            (day,),
        ).fetchone()["c"]
        if count >= MAX_DAILY_PARTICIPANTS:
            raise ValueError(
                f"Daily mode is full — {MAX_DAILY_PARTICIPANTS} players "
                f"have already joined for {day}."
            )
        conn.execute(
            "INSERT INTO daily_participants (day, user_id) VALUES (?, ?)",
            (day, user_id),
        )


def leave_daily_game(user_id: int, day: str) -> None:
    """Allow a user to leave a day's roster (only before any match starts)."""
    matches = get_matches_for_day(day)
    if matches and any(m["status"] == "completed" for m in matches):
        raise ValueError("Can't leave — at least one match on this day is already completed.")
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM daily_participants WHERE user_id = ? AND day = ?",
            (user_id, day),
        )


def list_daily_participants(day: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT dp.user_id, u.username, dp.joined_at
              FROM daily_participants dp
              JOIN users u ON u.user_id = dp.user_id
             WHERE dp.day = ?
             ORDER BY dp.joined_at ASC
            """,
            (day,),
        ).fetchall()
    return [dict(r) for r in rows]


def is_daily_participant(user_id: int, day: str) -> bool:
    if not user_id:
        return False
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM daily_participants WHERE user_id = ? AND day = ?",
            (user_id, day),
        ).fetchone()
    return row is not None


def get_daily_leaderboard(day: str) -> list[dict[str, Any]]:
    """
    Points each participant scored on the given day.
    Players who joined but didn't predict appear with 0 points.
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT u.user_id, u.username, dp.joined_at,
                   COALESCE(SUM(p.total_points), 0)              AS day_points,
                   COUNT(p.prediction_id)                        AS picks_made,
                   COUNT(CASE WHEN p.is_evaluated=1 THEN 1 END)  AS picks_scored,
                   COUNT(CASE WHEN p.is_evaluated=1
                               AND p.winner_points + p.score_points > 0
                              THEN 1 END)                        AS correct_winners
              FROM daily_participants dp
              JOIN users u  ON u.user_id  = dp.user_id
              LEFT JOIN predictions p
                ON p.user_id  = u.user_id
               AND p.match_id IN (
                   SELECT match_id FROM matches WHERE date(match_date) = ?
               )
             WHERE dp.day = ?
             GROUP BY u.user_id, u.username, dp.joined_at
             ORDER BY day_points DESC, u.username COLLATE NOCASE ASC
            """,
            (day, day),
        ).fetchall()
    return [dict(r) for r in rows]


def get_daily_winner(day: str) -> dict[str, Any] | None:
    """
    Return the day's winner only when:
      - the day has at least one match,
      - every match on that day is completed,
      - at least one participant scored > 0.
    """
    matches = get_matches_for_day(day)
    if not matches:
        return None
    if not all(m["status"] == "completed" for m in matches):
        return None
    board = get_daily_leaderboard(day)
    if not board:
        return None
    top = board[0]
    if top["day_points"] <= 0:
        return None
    return top


def get_all_daily_winners() -> list[dict[str, Any]]:
    """List of every completed day with its declared winner, newest first."""
    out: list[dict[str, Any]] = []
    for d in list_tournament_dates():
        w = get_daily_winner(d["day"])
        if w:
            out.append({
                "day":         d["day"],
                "username":    w["username"],
                "day_points":  w["day_points"],
                "picks_made":  w["picks_made"],
                "matches":     d["total"],
                "correct_winners": w["correct_winners"],
            })
    return list(reversed(out))


def set_match_highlights(match_id: int, highlights: str) -> None:
    """Admin can attach a short recap / highlight note to any match."""
    cleaned = (highlights or "").strip() or None
    with get_connection() as conn:
        conn.execute(
            "UPDATE matches SET highlights = ? WHERE match_id = ?",
            (cleaned, match_id),
        )


# =============================================================================
# Squads (admin-managed: coach + roster per team)
# =============================================================================
def _clean_players(players_text: str | None) -> str:
    """Normalise a pasted roster into one trimmed player name per line."""
    if not players_text:
        return ""
    lines = [ln.strip() for ln in players_text.replace("\r", "").split("\n")]
    return "\n".join(ln for ln in lines if ln)


def upsert_squad(team: str, coach: str | None, players_text: str | None) -> None:
    """Insert or update a team's coach + roster (one player per line)."""
    team = (team or "").strip()
    if not team:
        raise ValueError("Team is required.")
    coach = (coach or "").strip() or None
    players = _clean_players(players_text)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO squads (team, coach, players, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(team) DO UPDATE SET
                coach      = excluded.coach,
                players    = excluded.players,
                updated_at = CURRENT_TIMESTAMP
            """,
            (team, coach, players),
        )


def get_squad(team: str) -> dict[str, Any] | None:
    """Return {team, coach, players, updated_at} for a team, or None."""
    if not team:
        return None
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM squads WHERE team = ?", (team.strip(),)
        ).fetchone()
        return dict(row) if row else None


POSITIONS = ("GK", "DF", "MF", "FW")


def parse_roster(players_text: str | None) -> list[dict[str, str]]:
    """
    Parse stored roster text into [{'pos': 'GK', 'name': 'Ronwen Williams'}, ...].
    Each line is either 'POS|Name' (new format) or a bare 'Name' (legacy);
    a bare name yields an empty position. Order is preserved.
    """
    roster: list[dict[str, str]] = []
    for ln in (players_text or "").replace("\r", "").split("\n"):
        ln = ln.strip()
        if not ln:
            continue
        if "|" in ln:
            pos, name = ln.split("|", 1)
            pos, name = pos.strip().upper(), name.strip()
        else:
            pos, name = "", ln
        if name:
            roster.append({"pos": pos, "name": name})
    return roster


def get_squad_roster(team: str) -> list[dict[str, str]]:
    """Return a team's roster as [{'pos', 'name'}, ...] (empty if none saved)."""
    sq = get_squad(team)
    if not sq:
        return []
    return parse_roster(sq.get("players"))


def get_squad_players(team: str) -> list[str]:
    """Return just the player names for a team (empty if no squad saved)."""
    return [r["name"] for r in get_squad_roster(team)]


def players_for_match(match: dict[str, Any]) -> list[dict[str, str]]:
    """
    Combined roster of both teams in a match, each entry tagged with its team
    and position: [{'team', 'pos', 'name'}, ...]. Team A first, then Team B,
    each in saved (GK→FW) order — ready to group/segregate in a dropdown.
    """
    out: list[dict[str, str]] = []
    for team in (match.get("team_a"), match.get("team_b")):
        for r in get_squad_roster(team or ""):
            out.append({"team": team, "pos": r["pos"], "name": r["name"]})
    return out


def list_squads() -> list[dict[str, Any]]:
    """All saved squads, alphabetical by team."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM squads ORDER BY team COLLATE NOCASE"
        ).fetchall()
        return [dict(r) for r in rows]


def squad_team_names() -> set[str]:
    """Set of team names that have a squad saved (for quick 'has squad?' checks)."""
    with get_connection() as conn:
        rows = conn.execute("SELECT team FROM squads").fetchall()
        return {r["team"] for r in rows}
