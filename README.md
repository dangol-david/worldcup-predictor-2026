# 🏆 Predict & Win — 2026 FIFA World Cup

A Streamlit + SQLite prediction game for the **2026 FIFA World Cup**
(Canada · Mexico · USA, June 11 – July 19). Players predict winners, scores,
and Man-of-the-Match for all **104 official fixtures** across 7 tournament
stages. Points multiply as the rounds get bigger, and a live dashboard tracks
group standings, the knockout bracket, and the leaderboard.

## What's inside

```
worldcup_predictor/
├── app.py            # Streamlit dashboard (sports-broadcast theme)
├── database.py       # SQLite schema + CRUD + group-standings logic
├── game_logic.py     # Pure scoring rules + batch evaluator
├── seed_data.py      # All 104 official fixtures (teams, dates, venues)
├── teams.py          # Country flag emoji lookup
├── requirements.txt
└── README.md
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python seed_data.py                # populates 104 matches (one-time)
python game_logic.py               # quick scoring self-test (optional)
streamlit run app.py
```

App opens at <http://localhost:8501>.

To wipe and reseed (e.g. after editing fixtures):
```bash
python seed_data.py --reset
```

## The dashboard — 10 tabs

| Tab | What you see |
|---|---|
| 🏁 **Dashboard** | Hero header with kickoff countdown, KPI strip, today's daily-mode banner, recent daily winners strip, next 6 fixtures **with your submitted pick + lock countdown**, top 5 leaderboard, latest results |
| 📅 **Fixtures** | All 104 matches — filter by stage, status, group, or team |
| 🅰️ **Groups** | Auto-computed standings for all 12 groups (P / W / D / L / GF / GA / GD / Pts) with qualification stripes |
| 🏆 **Bracket** | Knockout bracket from Round of 16 through the Final, plus champion banner when the Final is done |
| 📆 **Daily Mode** | Pick a tournament day · up to **10 players** can join · predict that day's matches · daily leaderboard · daily winner crowned when all matches complete |
| 🎯 **Predict** | Pick winner, scoreline, MOM, First Scorer + ⭐ Banker for every upcoming fixture. Predictions lock **3 hours before kickoff** |
| 📊 **My Picks** | Player KPIs (totals, exact/MOM/first-scorer hits, bonus, correct-winner %) + full pick history |
| 🏅 **Leaderboard** | Podium for top 3 + full ranked table broken down by stage and by category (incl. 1st-scorer & bonus) |
| 👥 **Squads** | Browse each team's coach + roster (read-only; admins add them in the Admin tab) |
| ⚙️ **Admin** | Password-protected (`admin123` — change in `app.py`). Submit results (score + MOM + first scorer + highlights), **manage squads & coaches**, or edit highlights on completed matches. Everyone's predictions score instantly |

## Run it for your league (same Wi-Fi / LAN)

`.streamlit/config.toml` pins the dark theme and binds the server to your whole
network, so all 10 players can open it from their own phones/laptops:

```bash
streamlit run app.py
```

Streamlit prints a **Network URL** like `http://192.168.0.100:8501` — share that
with players on the same Wi-Fi. (On first run, allow Python through the Windows
Firewall when prompted, for Private networks.) Everyone shares one `worldcup.db`,
so scores update live for all of them. Keep this one machine running as the host.

## Daily Mode

A self-contained daily mini-game that runs *alongside* the season-long predictor:

1. Pick any tournament day (defaults to today, or the next match day).
2. The first **10 players** to tap "Join today's game" lock in a roster for that day.
3. Roster members predict only that day's matches (the same prediction is also counted in the season-long game).
4. Once every match on that day is completed, the **highest scorer** is crowned the **Daily Winner** — visible on the Dashboard and the Daily Mode tab.
5. Past daily winners scroll in a strip on the Dashboard so you can see who took each day.

A player who joined but didn't get the highest points still appears on the daily leaderboard with their stats; only those who join can be the daily winner.

## Highlights

When an admin submits a result they can include 1–3 sentences of recap (e.g. "Vinicius brace caps Brazil's commanding win"). Highlights render directly on the match card and persist across all tabs. Admins can also edit highlights on already-completed matches via the "Add / edit highlights" mode in the Admin tab.

## Scoring rules

| Outcome | Base points |
|---|---|
| Correct winner (or correct Draw) | **+1** |
| Correct goal difference (winner correct, not exact) | **+2** *(stacks with winner → 3 total)* |
| Exact score | **+5** *(replaces winner + diff bonuses)* |
| Correct Man of the Match (case-insensitive) | **+3** |
| Correct First Goal Scorer (case-insensitive) | **+4** |

**Stage multipliers** apply to every point above:

| Stage | × |
|---|---|
| Group Stage | 1 |
| Round of 32 | 2 |
| Round of 16 | 3 |
| Quarter-Final | 4 |
| Semi-Final | 5 |
| Third Place | 2 |
| **Final** | **6** |

**Bonus mechanics** (applied on top of the base points):

- **⭐ Banker / double-down** — each player flags one match per calendar day as
  their Banker; that match's whole haul (base + underdog) is doubled (×2).
- **🐺 Underdog upset** — correctly call a winner that fewer than half of the
  predictors backed (not a Draw) for **+3 base × stage**.

Example: predicting the exact Final scoreline + MOM + First Goal Scorer is
`(5 + 3 + 4) × 6 = 72 points` in a single match — `144` if it's your Banker.

> ⏰ **Predictions lock 3 hours before each kickoff** (`db.LOCK_LEAD_HOURS`),
> enforced in the data layer. See **[GAME_RULES.md](GAME_RULES.md)** for the full
> rulebook, onboarding steps, and the daily-play process.

## Architecture

```
                ┌──────────────────────────┐
                │         app.py           │  ← Streamlit dashboard
                │  (8 tabs, custom CSS)    │
                └────────────┬─────────────┘
                             │
       ┌─────────────────────┼─────────────────────┐
       ▼                     ▼                     ▼
 ┌─────────────┐    ┌───────────────┐    ┌────────────────┐
 │ database.py │    │ game_logic.py │    │  seed_data.py  │
 │  (sqlite3)  │◄───┤ pure scoring  │    │ 104 fixtures   │
 └──────┬──────┘    └───────────────┘    └───────┬────────┘
        │                                        │
        └──────────► worldcup.db ◄───────────────┘
        ▲
        │
   ┌────┴─────┐
   │ teams.py │  ← 48 country flags + placeholder helper
   └──────────┘
```

**Key design decisions**

1. **One source of truth.** `database.py` is the only module that touches
   SQLite. `game_logic.py` is pure Python and easy to unit test. `app.py` only
   does presentation.
2. **Stages mirror the real bracket.** The schema accepts the 7 official
   stages (Group Stage → Round of 32 → Round of 16 → Quarter-Final →
   Semi-Final → Third Place → Final). Match numbers 1–104 match FIFA's
   official numbering.
3. **Atomic scoring.** When an admin submits a result, `update_match_result`
   atomically updates the match and re-scores every prediction in a single
   `executemany` batch. Re-submitting a result safely re-scores.
4. **Group standings are computed, not stored.** `compute_group_standings()`
   builds standings from completed matches on demand — no risk of stale data.
5. **Validation at the data layer.** The DB rejects negative scores, scores
   >20, contradictory winner/score combos (e.g. "Brazil to win 1–1"), invalid
   stages, and edits to a locked match.
6. **Knockout placeholders.** R32 → Final teams start as labels like
   "Winner Group A", "3rd A/B/C/D/F", "Winner Match 73". Admins update the
   `matches` table (or extend the admin tab) as the bracket fills in.

## Customising

- **Edit fixtures**: tweak the `GROUP_STAGE`, `ROUND_OF_32`, etc. lists in
  `seed_data.py`, then `python seed_data.py --reset`.
- **Change the admin password**: search `admin123` in `app.py`.
- **Adjust scoring**: edit the `POINTS_*` constants or `STAGE_MULTIPLIER` in
  `game_logic.py`. The next admin result submission re-scores everything.
- **Add a team flag**: add it to the `FLAGS` dict in `teams.py`.

## Run the tests

```bash
python game_logic.py     # 5 scoring assertions
```

Want full end-to-end coverage? Add a `tests/` directory and use `pytest` —
all three modules are designed for it.
