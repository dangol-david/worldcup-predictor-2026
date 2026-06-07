"""
game_logic.py
-------------
Pure scoring + evaluation logic for the prediction game.

Scoring rubric (per match)
--------------------------
Winner / score prediction:
    +1  correct winner OR correct "Draw"
    +2  correct goal difference (stacks with the +1 winner point => 3 total)
    +5  exact score (replaces the +1 and +2 above)
Man of the Match:
    +3  correct MOM player (case-insensitive match)
First Goal Scorer:
    +4  correct first goal scorer (case-insensitive match)

The four components above are summed and multiplied by the stage multiplier
(see STAGE_MULTIPLIER) to give the match's *base* points.

Bonus mechanics (applied on top of the base, in evaluate_predictions_for_match)
-------------------------------------------------------------------------------
Underdog upset (+3 base, multiplied by stage):
    Awarded when you correctly pick the winner AND that winner was the
    "minority" call — fewer than half of all players who predicted the match
    backed them (and it wasn't a Draw). Most lucrative in late knockout rounds.
Banker / double-down (x2):
    Each player may flag ONE match per calendar day as their "Banker". That
    match's entire haul (base + any underdog bonus) is doubled. High risk —
    a wrong banker simply doubles zero.

Stage multipliers
-----------------
Group Stage  : 1x   Round of 32 : 2x   Round of 16 : 3x
Quarter-Final: 4x   Semi-Final  : 5x   Third Place : 2x   Final : 6x
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from database import (
    get_connection,
    get_match,
    list_predictions_for_match,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STAGE_MULTIPLIER: dict[str, int] = {
    "Group Stage":    1,
    "Round of 32":    2,
    "Round of 16":    3,
    "Quarter-Final":  4,
    "Semi-Final":     5,
    "Third Place":    2,
    "Final":          6,
}

POINTS_WINNER        = 1
POINTS_EXACT_SCORE   = 5   # supersedes POINTS_WINNER when both qualify
POINTS_GOAL_DIFF     = 2
POINTS_MOM           = 3
POINTS_FIRST_SCORER  = 4

# Bonus mechanics
UNDERDOG_BONUS       = 3     # base points, multiplied by stage
UNDERDOG_THRESHOLD   = 0.5   # winner is an "upset" if backed by < this share
BANKER_MULTIPLIER    = 2     # a Banker pick doubles its match haul


# ---------------------------------------------------------------------------
# Data class for scoring results
# ---------------------------------------------------------------------------
@dataclass
class ScoreBreakdown:
    winner_points: int
    score_points:  int
    mom_points:    int
    scorer_points: int
    multiplier:    int

    @property
    def total(self) -> int:
        """Base match points: rubric components summed, times the multiplier."""
        return (
            self.winner_points + self.score_points
            + self.mom_points + self.scorer_points
        ) * self.multiplier

    def as_dict(self) -> dict[str, int]:
        return {
            "winner_points": self.winner_points * self.multiplier,
            "score_points":  self.score_points  * self.multiplier,
            "mom_points":    self.mom_points    * self.multiplier,
            "scorer_points": self.scorer_points * self.multiplier,
            "total_points":  self.total,
        }


# ---------------------------------------------------------------------------
# Pure scoring function (easy to unit test)
# ---------------------------------------------------------------------------
def _name_match(a: str | None, b: str | None) -> bool:
    """Case-insensitive, whitespace-trimmed equality for player names."""
    return bool(a and b and a.strip().lower() == b.strip().lower())


def score_prediction(
    *,
    actual_winner: str,
    actual_score_a: int,
    actual_score_b: int,
    actual_mom: str | None,
    pred_winner: str,
    pred_score_a: int,
    pred_score_b: int,
    pred_mom: str | None,
    stage: str,
    actual_first_scorer: str | None = None,
    pred_first_scorer: str | None = None,
) -> ScoreBreakdown:
    """Compute a ScoreBreakdown for a single prediction vs. actual result."""
    multiplier = STAGE_MULTIPLIER.get(stage, 1)

    # --- Winner / score component --------------------------------------------------
    winner_pts = 0
    score_pts = 0

    exact_score = (
        pred_score_a == actual_score_a and pred_score_b == actual_score_b
    )
    correct_winner = (pred_winner == actual_winner)

    if exact_score:
        # Exact score is the top tier; replaces the winner point.
        score_pts = POINTS_EXACT_SCORE
    elif correct_winner:
        winner_pts = POINTS_WINNER
        # Bonus if goal difference also matches (and winner is correct, not draw)
        if actual_winner != "Draw":
            actual_diff = actual_score_a - actual_score_b
            pred_diff   = pred_score_a   - pred_score_b
            if actual_diff == pred_diff:
                score_pts = POINTS_GOAL_DIFF

    # --- Man of the Match component ------------------------------------------------
    mom_pts = POINTS_MOM if _name_match(actual_mom, pred_mom) else 0

    # --- First Goal Scorer component -----------------------------------------------
    scorer_pts = (
        POINTS_FIRST_SCORER if _name_match(actual_first_scorer, pred_first_scorer) else 0
    )

    return ScoreBreakdown(
        winner_points=winner_pts,
        score_points=score_pts,
        mom_points=mom_pts,
        scorer_points=scorer_pts,
        multiplier=multiplier,
    )


# ---------------------------------------------------------------------------
# Batch evaluation for a completed match
# ---------------------------------------------------------------------------
def evaluate_predictions_for_match(match_id: int) -> int:
    """
    Re-score every prediction for the given (completed) match.
    Returns the number of predictions updated.
    """
    match = get_match(match_id)
    if not match or match["status"] != "completed":
        return 0

    predictions = list_predictions_for_match(match_id)
    if not predictions:
        return 0

    multiplier     = STAGE_MULTIPLIER.get(match["stage"], 1)
    actual_winner  = match["winner"]

    # --- Underdog detection: was the actual winner a minority call? ----------------
    # Predictions are locked by the time a match completes, so the consensus is
    # stable and re-scoring is deterministic.
    winner_counts = Counter(p["predicted_winner"] for p in predictions)
    total_preds   = len(predictions)
    winner_share  = winner_counts.get(actual_winner, 0) / total_preds
    is_upset      = actual_winner != "Draw" and winner_share < UNDERDOG_THRESHOLD

    updates: list[tuple] = []
    for p in predictions:
        breakdown = score_prediction(
            actual_winner       = actual_winner,
            actual_score_a      = match["score_a"],
            actual_score_b      = match["score_b"],
            actual_mom          = match["mom_player"],
            actual_first_scorer = match["first_scorer"],
            pred_winner         = p["predicted_winner"],
            pred_score_a        = p["predicted_score_a"],
            pred_score_b        = p["predicted_score_b"],
            pred_mom            = p["predicted_mom"],
            pred_first_scorer   = p["predicted_first_scorer"],
            stage               = match["stage"],
        )
        d    = breakdown.as_dict()
        base = d["total_points"]

        # Underdog upset bonus — only if this player backed the upset winner.
        underdog = (
            UNDERDOG_BONUS * multiplier
            if is_upset and p["predicted_winner"] == actual_winner
            else 0
        )

        # Banker doubles the entire match haul (base + underdog).
        match_haul = base + underdog
        total = match_haul * BANKER_MULTIPLIER if p["is_banker"] else match_haul
        bonus = total - base   # everything beyond the standard rubric

        updates.append(
            (
                d["winner_points"],
                d["score_points"],
                d["mom_points"],
                d["scorer_points"],
                bonus,
                total,
                p["prediction_id"],
            )
        )

    with get_connection() as conn:
        conn.executemany(
            """
            UPDATE predictions
               SET winner_points = ?,
                   score_points  = ?,
                   mom_points    = ?,
                   scorer_points = ?,
                   bonus_points  = ?,
                   total_points  = ?,
                   is_evaluated  = 1,
                   updated_at    = CURRENT_TIMESTAMP
             WHERE prediction_id = ?
            """,
            updates,
        )

    return len(updates)


# ---------------------------------------------------------------------------
# Small self-test (run `python game_logic.py`)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    cases = [
        # (description, kwargs, expected_total)
        ("Exact score + MOM + first scorer in Final",
            dict(actual_winner="Brazil", actual_score_a=3, actual_score_b=1,
                 actual_mom="Neymar", actual_first_scorer="Vinicius",
                 pred_winner="Brazil",  pred_score_a=3,   pred_score_b=1,
                 pred_mom="neymar",     pred_first_scorer="VINICIUS",
                 stage="Final"),
            (5 + 3 + 4) * 6),                          # 72
        ("Correct first scorer only in Group Stage",
            dict(actual_winner="Spain", actual_score_a=2, actual_score_b=0,
                 actual_mom="Pedri", actual_first_scorer="Yamal",
                 pred_winner="Draw", pred_score_a=1, pred_score_b=1,
                 pred_mom="Rodri", pred_first_scorer="Yamal",
                 stage="Group Stage"),
            4 * 1),                                    # 4
        ("Correct winner + diff in SF",
            dict(actual_winner="Spain", actual_score_a=2, actual_score_b=0,
                 actual_mom="Pedri",
                 pred_winner="Spain",   pred_score_a=3,   pred_score_b=1,
                 pred_mom="Rodri",      stage="Semi-Final"),
            (1 + 2 + 0) * 5),                          # 15
        ("Only winner correct in Group Stage",
            dict(actual_winner="Argentina", actual_score_a=2, actual_score_b=1,
                 actual_mom="Messi",
                 pred_winner="Argentina",   pred_score_a=4, pred_score_b=0,
                 pred_mom="Di Maria",       stage="Group Stage"),
            (1 + 0 + 0) * 1),                          # 1
        ("Wrong winner in Final",
            dict(actual_winner="France", actual_score_a=1, actual_score_b=0,
                 actual_mom="Mbappe",
                 pred_winner="England",   pred_score_a=2, pred_score_b=0,
                 pred_mom="Kane",         stage="Final"),
            0),
        ("Correct Draw in Group Stage",
            dict(actual_winner="Draw", actual_score_a=1, actual_score_b=1,
                 actual_mom=None,
                 pred_winner="Draw", pred_score_a=2, pred_score_b=2,
                 pred_mom=None, stage="Group Stage"),
            1 * 1),                                    # 1
    ]
    for desc, kwargs, expected in cases:
        got = score_prediction(**kwargs).total
        status = "OK" if got == expected else "FAIL"
        print(f"[{status}] {desc}: got {got}, expected {expected}")
