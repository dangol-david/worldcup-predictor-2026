# GEMINI.md — Project context for the Antigravity agent

You are the AI coding agent for **Predict & Win — 2026 FIFA World Cup**, a Streamlit + SQLite prediction game for the official 2026 FIFA World Cup (Canada · Mexico · USA, June 11 – July 19, 2026).

## Project identity

- **Stack**: Python 3.10+, Streamlit (UI), SQLite (persistence) — no external services.
- **Theme**: editorial sports-broadcast — dark navy (`#0B1421`), electric coral / lime / gold accents, Anton display font + Space Mono numerals. Don't drift to generic AI aesthetics.
- **Tournament data**: all 104 official fixtures are pre-seeded across 7 stages (Group Stage 1–72, Round of 32 73–88, Round of 16 89–96, Quarter-Finals 97–100, Semi-Finals 101–102, Third Place 103, Final 104).

## File map (read these before changing anything)

| File | Purpose |
|---|---|
| `app.py` | Streamlit dashboard. 10 tabs (Dashboard, Fixtures, Groups, Bracket, Daily Mode, Predict, My Picks, Leaderboard, Squads, Admin). Heavy use of injected CSS via `st.markdown(..., unsafe_allow_html=True)`. |
| `.streamlit/config.toml` | Pins the dark theme (so text is readable in any browser) and binds the server to the LAN (`address=0.0.0.0`) so all players can connect. |
| `database.py` | The *only* module that touches SQLite. Schema + all CRUD + group-standings + daily-mode functions. |
| `game_logic.py` | Pure scoring functions. Easy to unit-test. `STAGE_MULTIPLIER` maps each stage to its point multiplier. |
| `seed_data.py` | All 104 fixtures with teams, dates, venues. Run with `--reset` to wipe and reseed. |
| `teams.py` | Country flag emoji lookup (48 nations + knockout placeholders). |

## Hard rules

1. **All SQLite I/O lives in `database.py`.** Never put `sqlite3.connect` calls in `app.py` or `game_logic.py`.
2. **Use the `get_connection()` context manager** for every DB read/write. It handles commit/rollback and foreign-key enforcement.
3. **`game_logic.py` must stay pure.** No DB imports inside `score_prediction()`. The only DB-touching function in that file is `evaluate_predictions_for_match`, which uses the connection helper.
4. **Match-number column (1–104) mirrors FIFA's official numbering.** Don't re-number on reseed.
5. **Predictions are locked** once a match's status is `completed`. The DB enforces this — don't add UI-side bypasses.
6. **Daily Mode cap is 10 players per calendar day.** Defined as `db.MAX_DAILY_PARTICIPANTS`. Don't hard-code `10` elsewhere; reference the constant.
7. **Streamlit forms only** for prediction input. Never write to the DB from a button outside a form, or you'll get duplicate writes on rerun.

## Scoring rubric (mirror this exactly when explaining or modifying)

Base points per match:
- Correct winner (or correct Draw): **+1**
- Correct goal difference (winner correct, not exact score): **+2** *(stacks with winner → 3 total)*
- Exact score: **+5** *(replaces winner + diff)*
- Correct Man of the Match (case-insensitive): **+3**
- Correct First Goal Scorer (case-insensitive): **+4**

Stage multipliers applied to the sum of the above:
| Stage | × |
|---|---|
| Group Stage | 1 |
| Round of 32 | 2 |
| Round of 16 | 3 |
| Quarter-Final | 4 |
| Semi-Final | 5 |
| Third Place | 2 |
| Final | 6 |

Bonus mechanics (applied in `evaluate_predictions_for_match`, on top of the base):
- **Banker (×2)** — `predictions.is_banker`. One per user per calendar day
  (`db.set_banker` clears same-day bankers). Doubles base + underdog.
- **Underdog (+3 × stage)** — `UNDERDOG_BONUS`. Awarded when a player's correct
  winner was backed by `< UNDERDOG_THRESHOLD` (0.5) of that match's predictors
  and it wasn't a Draw. Consensus is computed from locked predictions.

## Prediction lock (time-based)

- Predictions freeze **`db.LOCK_LEAD_HOURS` (3) hours before kickoff**, enforced
  in `db.is_match_locked()` and re-checked inside `upsert_prediction` /
  `set_banker` — never bypass it in the UI.
- `db.lock_time(match)` returns the freeze instant; `app.lock_status(m)` returns
  `(is_locked, human_label)` for display.
- Don't ask the admin to "lock" matches manually anymore; completion still locks
  too, but time is the primary gate.

## Common tasks

- **Run the app**: `streamlit run app.py`
- **Reseed the DB**: `python seed_data.py --reset` (destructive — deletes `worldcup.db`)
- **Run scoring tests**: `python game_logic.py` (5 built-in assertions)
- **Reset just one player's picks**: `DELETE FROM predictions WHERE user_id = ?` then they can re-predict any upcoming match.
- **Admin password**: `admin123` — defined in `app.py` (search for it). Change there.
- **Update knockout-stage teams** as the tournament progresses: edit the rows in the `matches` table where `team_a` or `team_b` starts with "Winner Match" / "Runner-up" / "3rd". Predictions made against placeholder names will need to be cleared if the team changes.

## Style preferences

- Type hints on every function signature.
- Docstrings on public functions in `database.py` and `game_logic.py`.
- No `print` statements in `app.py` — use `st.write`, `st.info`, `st.success`, `st.error`.
- Keep CSS in the single `CSS` string at the top of `app.py`. Don't sprinkle `<style>` tags throughout.
- Tab labels use the existing emoji prefixes (🏁 📅 🅰️ 🏆 📆 🎯 📊 🏅 ⚙️) — keep this convention.

## Things to ask the user before doing

- Adding new external dependencies (anything beyond `streamlit` and `pandas`).
- Changing the scoring rubric or stage multipliers.
- Restructuring the database schema (writing migrations).
- Switching from SQLite to anything else.

## Known limitations / future ideas

- Knockout placeholder teams ("Winner Group A", "Runner-up B", "Winner Match 73", …) require manual updates as the bracket fills.
- No user authentication beyond a username selector — fine for a small private league, not for public deployment.
- Kickoff lockout is time-based (3h before kickoff) and compares against the
  server clock. Match times are stored naive in **Nepal time (NPT, UTC+5:45)**;
  `seed_data._to_nepal` converts the official ET schedule (+9h45m) on seed, so
  run the app on a Nepali clock (or adjust the offset / `LOCK_LEAD_HOURS`).
- The `worldcup.db` file is local; sharing requires file transfer or a hosted DB.
