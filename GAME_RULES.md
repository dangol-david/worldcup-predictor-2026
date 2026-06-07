# 📖 Predict & Win — Game Rules, Points & How to Play

The complete rulebook for **Predict & Win — 2026 FIFA World Cup**
(Canada · Mexico · USA · June 11 – July 19, 2026). 104 official fixtures,
7 stages, one trophy. Pick winners, scorelines, Man of the Match and the
First Goal Scorer — points multiply as the rounds get bigger.

---

## 1. Getting on the platform (player onboarding)

There is no password or email sign-up — a player is just a **unique username**.

1. Open the app (`streamlit run app.py` → <http://localhost:8501>).
2. In the **left sidebar**, expand **➕ Create new profile**.
3. Type a username (max 30 characters, must be unique — names are
   case-insensitive, so `Sam` and `sam` are the same player) and hit **Register**.
4. From then on, anyone returning picks their name from the **Active profile**
   dropdown at the top of the sidebar to "sign in". The active player is shown
   under **PLAYING AS**.

> 💡 This is built for a small private league. Anyone with the link can pick any
> profile, so use it with people you trust. Each person should register once and
> always select their own name.

---

## 2. The prediction deadline — picks lock 3 hours before kickoff

This is the headline rule for "on time" play:

- Every match has a scheduled kickoff. **Predictions for that match freeze
  exactly 3 hours before kickoff** (`LOCK_LEAD_HOURS = 3`).
- Before the lock you can edit your pick as many times as you like.
- Once locked you can no longer create or change a pick (or move your Banker) for
  that match — the form is replaced by a read-only summary of your entry.
- The lock is enforced **server-side** in the database, not just hidden in the
  UI, so there is no way to sneak a late pick in.

Where you see the deadline:
- **Dashboard → Next Fixtures**: each upcoming match shows `🔓 Locks in 2d 4h`
  (counting down) or `🔒 PICKS LOCKED`, with your submitted pick underneath.
- **Predict tab**: each match is prefixed `🔒` when locked, `⭐` when it's your
  Banker, `✅` when you've picked, `⚪` when you haven't.

> ⏰ **Timezone note:** kickoff times are stored in US Eastern Time (ET). The lock
> compares against the server clock, so run the app in ET (or adjust
> `LOCK_LEAD_HOURS`) if your league is elsewhere.

---

## 3. Making a prediction

For each upcoming match you submit, in a single form:

| Field | Required? | Notes |
|---|---|---|
| **Team A goals** & **Team B goals** | ✅ | 0–20 each |
| **Predicted winner** | ✅ | Team A, Team B, or Draw — must agree with your scoreline |
| **Man of the Match** | optional | Free-text player name (case-insensitive) |
| **First goal scorer** | optional | Free-text player name (case-insensitive) |
| **⭐ Make this my Banker** | optional | Doubles this match (see §5) — one per day |

Your scoreline and winner must be consistent: a 2–1 scoreline can't be saved as a
"Draw", and equal scores must be predicted as a Draw.

---

## 4. Points — the scoring rubric

Base points per match:

| Outcome | Base points |
|---|---|
| Correct winner (or correct Draw) | **+1** |
| Correct goal difference (winner right, score not exact) | **+2** *(stacks with winner → 3 total)* |
| Exact score | **+5** *(replaces the winner + goal-diff points)* |
| Correct Man of the Match (case-insensitive) | **+3** |
| Correct First Goal Scorer (case-insensitive) | **+4** |

These four components are **summed**, then multiplied by the stage multiplier.

### Stage multipliers

| Stage | × |
|---|---|
| Group Stage | 1 |
| Round of 32 | 2 |
| Round of 16 | 3 |
| Quarter-Final | 4 |
| Semi-Final | 5 |
| Third Place | 2 |
| **Final** | **6** |

**Worked example.** Nail the exact Final scoreline (5) + Man of the Match (3) +
First Goal Scorer (4) = 12 base × 6 = **72 points** from one match — before any
bonus.

---

## 5. Bonus mechanics (the fun stuff)

Both bonuses are applied automatically when a match is scored, *on top of* the
base points above.

### ⭐ Banker / double-down
- Each player may flag **one match per calendar day** as their **Banker**.
- That match's **entire haul** (base points **plus** any underdog bonus) is
  **doubled (×2)**.
- Setting a Banker on a new match automatically clears your Banker on any other
  match the same day — you always have at most one per day.
- A Banker can be set or moved any time before that match locks (3h pre-kickoff).
- High risk: doubling a wrong pick just doubles zero.

### 🐺 Underdog upset bonus
- Awarded when you **correctly pick the winner** of a match **and** that winner
  was the *minority* call — **fewer than half** of all players who predicted that
  match backed them (and the result wasn't a Draw).
- Worth **+3 base**, multiplied by the stage — so a called upset in the Final is
  worth **+18**, and doubled to **+36** if it's also your Banker.
- It's crowd-based, so it rewards going against the grain when you're right.
  (With predictions locked before kickoff, the "crowd" is fixed and scoring is
  deterministic.)

---

## 6. Daily Mode (the day-by-day mini-game)

Runs alongside the season-long game so people can "predict the game for each day".

1. Open the **📆 Daily Mode** tab and pick a tournament day (defaults to today or
   the next match day).
2. The first **10 players** to tap **🎯 Join today's game** lock in that day's
   roster (`MAX_DAILY_PARTICIPANTS = 10`).
3. Roster members predict **only that day's matches** — the same picks also count
   in the season-long game and on the main leaderboard.
4. Standard lock applies: each match still freezes 3h before its kickoff, so join
   and predict early.
5. When **every match that day is complete**, the **highest scorer** is crowned
   the **Daily Winner**, shown on the Daily Mode tab and the Dashboard.
6. You can leave a day's roster only before any of that day's matches has started.

Players who join but don't top the table still appear on the daily leaderboard
with their stats; only roster members are eligible to be the Daily Winner.

---

## 7. Where predictions are shown

- **Dashboard** — your pick (winner · score · 1st scorer · ⭐ Banker) appears
  under each of the next fixtures, with a live lock countdown.
- **My Picks** — full pick history plus KPIs: total points, correct-winner %,
  exact/MOM/first-scorer hits, and total bonus points.
- **Leaderboard** — ranked table broken down by stage and by category, including
  the new **1ST** (first-scorer) and **BONUS** columns.
- **Daily Mode** — the per-day leaderboard for everyone on that day's roster.

---

## 8. How a result gets posted (admin)

1. Open the **⚙️ Admin** tab and enter the admin password (`admin123` — change it
   in `app.py`).
2. Choose **📥 Submit a result**, pick the match, and enter: final score, **Man
   of the Match**, **First goal scorer**, and an optional 1–3 sentence highlight.
3. Tick the confirmation box and submit. This **locks the match and instantly
   re-scores every prediction**, including underdog and Banker bonuses.
4. Re-submitting a result safely re-scores everything (idempotent).

---

### Quick reference card

```
WINNER +1 · GOAL DIFF +2 · EXACT SCORE +5 · MOM +3 · FIRST SCORER +4
STAGE × :  Group 1 · R32 2 · R16 3 · QF 4 · SF 5 · 3rd 2 · FINAL 6
⭐ BANKER ×2 (one match/day)   🐺 UNDERDOG +3 (minority correct pick)
⏰ PICKS LOCK 3 HOURS BEFORE KICKOFF
```
