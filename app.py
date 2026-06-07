"""
app.py
------
Predict and Win — 2026 FIFA World Cup
Editorial sports-broadcast dashboard built on Streamlit + SQLite.

Run: streamlit run app.py
"""

from __future__ import annotations

from datetime import datetime, timedelta
from html import escape

import pandas as pd
import streamlit as st

import database as db
from game_logic import STAGE_MULTIPLIER
from teams import FLAGS, flag

# =============================================================================
# Page config + base CSS
# =============================================================================
st.set_page_config(
    page_title="Predict & Win · World Cup 2026",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
)

db.init_db()

# Tournament constants
KICKOFF_ISO       = "2026-06-11 15:00"     # Mexico vs South Africa, ET
TOURNAMENT_START  = datetime.fromisoformat(KICKOFF_ISO)
FINAL_ISO         = "2026-07-19 15:00"
TOURNAMENT_END    = datetime.fromisoformat(FINAL_ISO)

# Stage palette (must match CSS class names below)
STAGE_CLASS = {
    "Group Stage":   "s-group",
    "Round of 32":   "s-r32",
    "Round of 16":   "s-r16",
    "Quarter-Final": "s-qf",
    "Semi-Final":    "s-sf",
    "Third Place":   "s-tp",
    "Final":         "s-final",
}

STAGE_LABEL = {
    "Group Stage":   "GROUP",
    "Round of 32":   "ROUND OF 32",
    "Round of 16":   "ROUND OF 16",
    "Quarter-Final": "QUARTER-FINAL",
    "Semi-Final":    "SEMI-FINAL",
    "Third Place":   "THIRD PLACE",
    "Final":         "FINAL",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Anton&family=Space+Mono:wght@400;700&family=Manrope:wght@400;600;700;800&display=swap');

:root {
    --bg:        #0B1421;
    --surface:   #152238;
    --surface-2: #1C2A45;
    --border:    #243046;
    --text:      #FAFAFA;
    --muted:     #8A95B0;
    --coral:     #FF3366;
    --lime:      #C3FF3E;
    --gold:      #FFB800;
    --cyan:      #00D9FF;
    --violet:    #B47AFF;
}

/* --- Streamlit overrides --- */
.stApp { background: var(--bg); color: var(--text); }
section.main > div { padding-top: 1rem; }
[data-testid="stSidebar"] { background: #08101C; border-right: 1px solid var(--border); }
[data-testid="stSidebar"] * { color: var(--text); }
.stTabs [data-baseweb="tab-list"] {
    gap: 4px; border-bottom: 1px solid var(--border); padding-bottom: 0;
}
.stTabs [data-baseweb="tab"] {
    background: transparent; color: var(--muted);
    font-family: 'Manrope', sans-serif; font-weight: 700;
    letter-spacing: 0.08em; text-transform: uppercase; font-size: 0.78rem;
    padding: 10px 18px; border-radius: 6px 6px 0 0;
}
.stTabs [aria-selected="true"] {
    background: var(--surface); color: var(--lime);
    border-bottom: 2px solid var(--lime);
}
.stMetric { background: var(--surface); padding: 14px 18px; border-radius: 8px;
            border: 1px solid var(--border); }
.stMetric label { color: var(--muted) !important;
                  font-family: 'Manrope', sans-serif;
                  text-transform: uppercase; letter-spacing: 0.1em;
                  font-size: 0.7rem !important; font-weight: 700 !important; }
.stMetric [data-testid="stMetricValue"] {
    font-family: 'Anton', sans-serif; font-size: 2.4rem !important;
    color: var(--text) !important; letter-spacing: 0.02em;
}
[data-testid="stExpander"] {
    background: var(--surface); border: 1px solid var(--border) !important;
    border-radius: 8px;
}
hr { border-color: var(--border); }
.stDataFrame { background: var(--surface); border-radius: 8px;
               border: 1px solid var(--border); }
.stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div {
    background: var(--surface-2) !important; color: var(--text) !important;
    border-color: var(--border) !important; font-family: 'Manrope', sans-serif;
}
button[kind="primary"], .stButton button {
    background: var(--lime) !important; color: #0B1421 !important;
    border: none !important; font-family: 'Manrope', sans-serif;
    font-weight: 800 !important; letter-spacing: 0.05em; text-transform: uppercase;
}
.stForm { background: var(--surface); border: 1px solid var(--border);
          border-radius: 10px; padding: 16px; }
h1, h2, h3, h4 { color: var(--text); font-family: 'Manrope', sans-serif; }

/* --- Hero --- */
.hero {
    background: linear-gradient(135deg, #0B1421 0%, #152238 60%, #1C2A45 100%);
    border: 1px solid var(--border); border-radius: 14px;
    padding: 28px 32px; margin-bottom: 22px; position: relative; overflow: hidden;
}
.hero::before {
    content: ''; position: absolute; top: -50%; right: -10%;
    width: 600px; height: 600px;
    background: radial-gradient(circle, rgba(255,51,102,0.15) 0%, transparent 60%);
    pointer-events: none;
}
.hero-grid { display: grid; grid-template-columns: 1fr auto; gap: 28px;
             align-items: end; position: relative; }
.hero-eyebrow {
    font-family: 'Space Mono', monospace; color: var(--lime);
    font-size: 0.72rem; letter-spacing: 0.3em; text-transform: uppercase;
    margin-bottom: 8px;
}
.hero-title {
    font-family: 'Anton', sans-serif; font-size: 4rem; line-height: 0.95;
    letter-spacing: 0.01em; text-transform: uppercase; color: var(--text);
    margin: 0;
}
.hero-title .accent { color: var(--coral); }
.hero-sub {
    color: var(--muted); font-family: 'Manrope', sans-serif;
    margin-top: 10px; max-width: 520px;
}
.hero-countdown { text-align: right; }
.hero-countdown .num {
    font-family: 'Anton', sans-serif; font-size: 4.5rem; line-height: 1;
    color: var(--gold); letter-spacing: 0.02em;
}
.hero-countdown .label {
    font-family: 'Space Mono', monospace; color: var(--muted);
    font-size: 0.7rem; letter-spacing: 0.3em; text-transform: uppercase;
}

/* --- Stage badges --- */
.stage-badge {
    display: inline-block; padding: 4px 10px; border-radius: 4px;
    font-family: 'Space Mono', monospace; font-size: 0.65rem;
    font-weight: 700; letter-spacing: 0.15em; text-transform: uppercase;
}
.s-group  { background: rgba(0,217,255,0.15);   color: var(--cyan); }
.s-r32    { background: rgba(180,122,255,0.15); color: var(--violet); }
.s-r16    { background: rgba(195,255,62,0.15);  color: var(--lime); }
.s-qf     { background: rgba(255,184,0,0.15);   color: var(--gold); }
.s-sf     { background: rgba(255,124,0,0.18);   color: #FF9F40; }
.s-tp     { background: rgba(138,149,176,0.18); color: var(--muted); }
.s-final  { background: rgba(255,51,102,0.18);  color: var(--coral); }

.mult { color: var(--muted); font-family: 'Space Mono', monospace;
        font-size: 0.7rem; letter-spacing: 0.1em; }
.mult b { color: var(--gold); }

/* --- Match card --- */
.match-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; padding: 16px 18px; margin-bottom: 12px;
    transition: border-color 0.15s;
}
.match-card:hover { border-color: var(--lime); }
.match-card.completed { background: linear-gradient(180deg, var(--surface), #131D2F); }
.match-card .head {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 12px;
}
.match-card .teams {
    display: grid; grid-template-columns: 1fr auto 1fr; align-items: center;
    gap: 12px; margin: 8px 0;
}
.match-card .team { display: flex; align-items: center; gap: 10px; min-width: 0; }
.match-card .team.right { justify-content: flex-end; text-align: right; }
.match-card .team .flag { font-size: 1.8rem; line-height: 1; flex-shrink: 0; }
.match-card .team .name {
    font-family: 'Manrope', sans-serif; font-weight: 800;
    font-size: 1.02rem; color: var(--text);
    text-transform: uppercase; letter-spacing: 0.03em;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.match-card .team .name.placeholder { font-weight: 600; color: var(--muted);
                                       text-transform: none; letter-spacing: 0; }
.match-card .score {
    font-family: 'Space Mono', monospace; font-weight: 700;
    font-size: 1.6rem; color: var(--gold); padding: 0 16px;
    border-left: 1px solid var(--border); border-right: 1px solid var(--border);
}
.match-card .score.vs { color: var(--muted); font-size: 0.9rem;
                         font-family: 'Space Mono', monospace; }
.match-card .winner-mark { color: var(--lime); font-weight: 800; }
.match-card .loser-mark  { color: var(--muted); }
.match-card .foot {
    display: flex; justify-content: space-between; align-items: center;
    margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--border);
    color: var(--muted); font-family: 'Space Mono', monospace; font-size: 0.72rem;
}
.match-card .mom {
    margin-top: 8px; padding: 6px 10px; background: rgba(255,184,0,0.1);
    border-left: 3px solid var(--gold); border-radius: 4px;
    color: var(--gold); font-family: 'Manrope', sans-serif;
    font-size: 0.82rem; font-weight: 600;
}
.match-card .scorer {
    margin-top: 8px; padding: 6px 10px; background: rgba(195,255,62,0.1);
    border-left: 3px solid var(--lime); border-radius: 4px;
    color: var(--lime); font-family: 'Manrope', sans-serif;
    font-size: 0.82rem; font-weight: 600;
}
.match-card .highlights {
    margin-top: 8px; padding: 8px 12px;
    background: rgba(0,217,255,0.08);
    border-left: 3px solid var(--cyan); border-radius: 4px;
    color: #DDE9F0; font-family: 'Manrope', sans-serif;
    font-size: 0.85rem; line-height: 1.45;
}

/* --- Daily mode --- */
.daily-banner {
    background: linear-gradient(135deg, #1C2A45 0%, #243046 100%);
    border: 1px solid var(--gold); border-radius: 12px;
    padding: 18px 22px; margin-bottom: 18px;
    display: grid; grid-template-columns: 1fr auto; gap: 18px;
    align-items: center;
}
.daily-banner .eyebrow {
    font-family: 'Space Mono', monospace; color: var(--gold);
    font-size: 0.68rem; letter-spacing: 0.3em; text-transform: uppercase;
}
.daily-banner .day {
    font-family: 'Anton', sans-serif; font-size: 2rem;
    color: var(--text); letter-spacing: 0.02em; margin: 4px 0 6px;
    text-transform: uppercase;
}
.daily-banner .meta {
    color: var(--muted); font-family: 'Space Mono', monospace;
    font-size: 0.75rem; letter-spacing: 0.05em;
}
.daily-banner .spots {
    text-align: right; font-family: 'Anton', sans-serif;
    font-size: 3.5rem; color: var(--lime); line-height: 1;
}
.daily-banner .spots .total {
    color: var(--muted); font-size: 1.8rem;
}
.daily-banner .spots .label {
    display: block; font-family: 'Space Mono', monospace;
    font-size: 0.65rem; color: var(--muted); letter-spacing: 0.25em;
    text-align: right;
}
.daily-banner.full { border-color: var(--coral); }
.daily-banner.full .spots { color: var(--coral); }

.daily-winner {
    background: linear-gradient(135deg, #FFB800 0%, #FF3366 100%);
    border-radius: 14px; padding: 24px 28px; margin: 20px 0;
    color: #0B1421; position: relative; overflow: hidden;
}
.daily-winner::before {
    content: '🏆'; position: absolute; right: 20px; top: 50%;
    transform: translateY(-50%); font-size: 5rem; opacity: 0.25;
}
.daily-winner .eyebrow {
    font-family: 'Space Mono', monospace; font-size: 0.7rem;
    letter-spacing: 0.3em; text-transform: uppercase; font-weight: 700;
}
.daily-winner .name {
    font-family: 'Anton', sans-serif; font-size: 2.8rem; line-height: 1;
    margin: 6px 0; letter-spacing: 0.02em; text-transform: uppercase;
}
.daily-winner .pts {
    font-family: 'Space Mono', monospace; font-size: 1.05rem; font-weight: 700;
}
.daily-winner .pts span { opacity: 0.7; font-size: 0.75rem; }

.dw-strip {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 10px;
}
.dw-tile {
    background: var(--surface); border: 1px solid var(--border);
    border-left: 3px solid var(--gold); border-radius: 8px;
    padding: 12px 14px;
}
.dw-tile .when {
    font-family: 'Space Mono', monospace; color: var(--muted);
    font-size: 0.65rem; letter-spacing: 0.15em; text-transform: uppercase;
}
.dw-tile .who {
    font-family: 'Manrope', sans-serif; font-weight: 800; color: var(--text);
    font-size: 1rem; margin-top: 4px;
}
.dw-tile .num {
    font-family: 'Space Mono', monospace; color: var(--lime);
    font-size: 0.85rem; font-weight: 700; margin-top: 2px;
}

.participant-chip {
    display: inline-block; background: var(--surface-2);
    border: 1px solid var(--border); border-radius: 999px;
    padding: 4px 10px; margin: 2px; font-family: 'Manrope', sans-serif;
    font-size: 0.78rem; color: var(--text);
}
.participant-chip.empty { color: var(--muted); border-style: dashed; }

/* --- Compact "next up" tile --- */
.tile {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; padding: 14px; margin-bottom: 10px;
}
.tile .row { display: flex; justify-content: space-between; align-items: center; }
.tile .matchup { font-family: 'Manrope', sans-serif; font-weight: 800;
                  color: var(--text); font-size: 0.95rem; }
.tile .when { color: var(--muted); font-family: 'Space Mono', monospace;
              font-size: 0.7rem; margin-top: 4px; }

/* --- Podium --- */
.podium {
    display: grid; grid-template-columns: 1fr 1.15fr 1fr;
    gap: 14px; align-items: end; margin: 22px 0;
}
.pod {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 12px; padding: 18px 14px; text-align: center;
    position: relative;
}
.pod.rank-1 { border-color: var(--gold); }
.pod.rank-1::before {
    content: '🏆'; position: absolute; top: -22px; left: 50%;
    transform: translateX(-50%); font-size: 2.5rem;
}
.pod .rank {
    font-family: 'Anton', sans-serif; font-size: 2.6rem; color: var(--muted);
    line-height: 1;
}
.pod.rank-1 .rank { color: var(--gold); }
.pod.rank-2 .rank { color: #CCD2E0; }
.pod.rank-3 .rank { color: #C57A3E; }
.pod .name {
    font-family: 'Manrope', sans-serif; font-weight: 800;
    margin: 6px 0; font-size: 1.05rem; color: var(--text);
    text-transform: uppercase; letter-spacing: 0.05em;
}
.pod .pts {
    font-family: 'Space Mono', monospace; color: var(--lime);
    font-size: 1.4rem; font-weight: 700;
}
.pod .pts span { color: var(--muted); font-size: 0.7rem; margin-left: 4px; }

/* --- Bracket --- */
.bracket-cols { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.bracket-col h4 {
    font-family: 'Anton', sans-serif; letter-spacing: 0.05em;
    color: var(--gold); margin-bottom: 12px; text-transform: uppercase;
    font-size: 1rem;
}
.bk-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 8px; padding: 10px 12px; margin-bottom: 10px;
    font-family: 'Manrope', sans-serif;
}
.bk-card.completed { border-color: var(--lime); }
.bk-team { display: flex; justify-content: space-between; align-items: center;
            padding: 4px 0; font-size: 0.88rem; color: var(--text); }
.bk-team .nm { display: flex; gap: 8px; align-items: center; }
.bk-team.lose { color: var(--muted); }
.bk-team .sc { font-family: 'Space Mono', monospace; font-weight: 700;
               color: var(--gold); }
.bk-meta { color: var(--muted); font-family: 'Space Mono', monospace;
            font-size: 0.65rem; margin-top: 6px; padding-top: 6px;
            border-top: 1px solid var(--border); letter-spacing: 0.1em; }

/* --- Group standings table --- */
.gst-wrap { display: grid; grid-template-columns: repeat(2, 1fr); gap: 18px; }
.gst-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; padding: 14px 16px;
}
.gst-card h4 {
    font-family: 'Anton', sans-serif; color: var(--gold);
    letter-spacing: 0.05em; margin-bottom: 10px;
    text-transform: uppercase; font-size: 1.1rem;
}
.gst-table { width: 100%; border-collapse: collapse;
              font-family: 'Manrope', sans-serif; }
.gst-table th { text-align: left; color: var(--muted); font-size: 0.65rem;
                 letter-spacing: 0.15em; text-transform: uppercase;
                 padding: 4px 6px; border-bottom: 1px solid var(--border); }
.gst-table th.r, .gst-table td.r { text-align: right; }
.gst-table td { padding: 6px; color: var(--text); font-size: 0.88rem;
                 border-bottom: 1px solid var(--border); }
.gst-table td.pts { font-family: 'Space Mono', monospace;
                      color: var(--lime); font-weight: 700; }
.gst-table tr.q-win td:first-child { border-left: 3px solid var(--lime); }
.gst-table tr.q-run td:first-child { border-left: 3px solid var(--cyan); }
.gst-table tr.q-3rd td:first-child { border-left: 3px solid var(--gold); }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# =============================================================================
# Render helpers
# =============================================================================
def days_to_kickoff() -> int:
    return max(0, (TOURNAMENT_START - datetime.now()).days)


def fmt_date(iso_str: str) -> str:
    dt = datetime.fromisoformat(iso_str)
    return dt.strftime("%a %b %d · %H:%M ET")


def _fmt_countdown(delta: timedelta) -> str:
    """Human 'Nd Nh' / 'Nh Nm' string for a positive timedelta."""
    mins = int(delta.total_seconds() // 60)
    days, rem = divmod(mins, 60 * 24)
    hours, minutes = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def lock_status(m: dict) -> tuple[bool, str]:
    """
    Return (is_locked, human label) for a match's prediction window.
    Predictions close db.LOCK_LEAD_HOURS before kickoff.
    """
    if m["status"] == "completed":
        return True, "FINAL"
    lock_at = db.lock_time(m)
    if lock_at is None:
        return False, ""
    now = datetime.now()
    if now >= lock_at:
        return True, "🔒 PICKS LOCKED"
    return False, f"🔓 Locks in {_fmt_countdown(lock_at - now)}"


def render_hero() -> None:
    days = days_to_kickoff()
    if days > 0:
        cd_num, cd_label = days, "DAYS TO KICKOFF"
    elif datetime.now() < TOURNAMENT_END:
        cd_num, cd_label = "LIVE", "TOURNAMENT ACTIVE"
    else:
        cd_num, cd_label = "DONE", "TOURNAMENT COMPLETE"

    st.markdown(f"""
<div class="hero">
  <div class="hero-grid">
    <div>
      <div class="hero-eyebrow">FIFA WORLD CUP · CANADA · MEXICO · USA</div>
      <h1 class="hero-title">PREDICT &amp;<br><span class="accent">WIN.</span> 2026</h1>
      <p class="hero-sub">104 matches across 16 stadiums. 48 nations. One trophy.
      Pick winners, scores, and Man of the Match — points multiply as the rounds get bigger.</p>
    </div>
    <div class="hero-countdown">
      <div class="num">{cd_num}</div>
      <div class="label">{cd_label}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


def _team_html(name: str, score: int | None, is_winner: bool, side: str) -> str:
    is_placeholder = name not in FLAGS
    name_class = "name placeholder" if is_placeholder else "name"
    mark = ""
    if is_winner and score is not None:
        mark = " winner-mark"
    elif score is not None and not is_winner:
        mark = " loser-mark"
    flag_html = f'<span class="flag">{flag(name)}</span>'
    name_html = f'<span class="{name_class}{mark}">{escape(name)}</span>'
    if side == "left":
        return f'<div class="team">{flag_html}{name_html}</div>'
    return f'<div class="team right">{name_html}{flag_html}</div>'


def render_match_card(m: dict) -> str:
    """Return the HTML for a match card."""
    stage_cls = STAGE_CLASS[m["stage"]]
    badge_label = STAGE_LABEL[m["stage"]]
    if m["group_name"]:
        badge_label += f" · {m['group_name']}"
    mult = STAGE_MULTIPLIER[m["stage"]]
    completed = m["status"] == "completed"

    if completed:
        sa, sb = m["score_a"], m["score_b"]
        score_html = f'<div class="score">{sa} — {sb}</div>'
        win_a = m["winner"] == m["team_a"]
        win_b = m["winner"] == m["team_b"]
    else:
        score_html = '<div class="score vs">VS</div>'
        win_a = win_b = False
        sa = sb = None

    left  = _team_html(m["team_a"], sa, win_a, "left")
    right = _team_html(m["team_b"], sb, win_b, "right")

    mom_html = ""
    if completed and m.get("mom_player"):
        mom_html = f'<div class="mom">⭐ MAN OF THE MATCH · {escape(m["mom_player"])}</div>'

    scorer_html = ""
    if completed and m.get("first_scorer"):
        scorer_html = f'<div class="scorer">⚽ FIRST GOAL · {escape(m["first_scorer"])}</div>'

    highlights_html = ""
    if completed and m.get("highlights"):
        highlights_html = (
            f'<div class="highlights">📝 {escape(m["highlights"])}</div>'
        )

    venue_line = ""
    if m.get("venue"):
        venue = escape(m["venue"])
        city  = escape(m.get("city") or "")
        venue_line = f'📍 {venue}{" · " + city if city else ""}'

    match_no = f'#{m["match_number"]}' if m.get("match_number") else ''

    return f"""
<div class="match-card {'completed' if completed else ''}">
  <div class="head">
    <span class="stage-badge {stage_cls}">{badge_label}</span>
    <span class="mult">{match_no} &nbsp; MULTIPLIER <b>×{mult}</b></span>
  </div>
  <div class="teams">{left}{score_html}{right}</div>
  {mom_html}
  {scorer_html}
  {highlights_html}
  <div class="foot">
    <span>📅 {fmt_date(m['match_date'])}</span>
    <span>{venue_line}</span>
  </div>
</div>
"""


def render_match_grid(matches: list[dict], cols: int = 2) -> None:
    """Lay out a list of match cards in N columns."""
    if not matches:
        st.info("No matches to display.")
        return
    columns = st.columns(cols)
    for i, m in enumerate(matches):
        with columns[i % cols]:
            st.markdown(render_match_card(m), unsafe_allow_html=True)


def render_prediction_summary(pred: dict | None) -> str:
    """One-line read-only summary of a player's pick (used when locked / on dash)."""
    if not pred:
        return ('<span style="color:#8A95B0;font-family:Space Mono,monospace;'
                'font-size:0.78rem;">— no pick submitted —</span>')
    banker = (' <span style="color:#FFB800;font-weight:700;">⭐ BANKER ×2</span>'
              if pred.get("is_banker") else "")
    scorer = (f' · 1st: {escape(pred["predicted_first_scorer"])}'
              if pred.get("predicted_first_scorer") else "")
    return (
        f'<span style="font-family:Space Mono,monospace;font-size:0.82rem;'
        f'color:#FAFAFA;">{escape(pred["predicted_winner"])} '
        f'({pred["predicted_score_a"]}–{pred["predicted_score_b"]}){scorer}</span>{banker}'
    )


def _render_prediction_form(user: dict, m: dict, key_prefix: str = "pred") -> None:
    """Reusable prediction form for one match. Used by Predict + Daily Mode tabs."""
    existing = db.get_user_prediction(user["user_id"], m["match_id"])
    locked, label = lock_status(m)

    if locked:
        st.markdown(
            f'<div style="padding:8px 12px;background:rgba(255,51,102,0.1);'
            f'border-left:3px solid #FF3366;border-radius:4px;color:#FF7A99;'
            f'font-family:Space Mono,monospace;font-size:0.8rem;">'
            f'🔒 Picks are locked for this match. '
            f'Your entry: {render_prediction_summary(existing)}</div>',
            unsafe_allow_html=True,
        )
        return

    st.caption(label)  # e.g. "🔓 Locks in 2d 4h"
    with st.form(f"{key_prefix}_form_{m['match_id']}"):
        col1, col2 = st.columns(2)
        pa = col1.number_input(
            f"{m['team_a']} goals", min_value=0, max_value=20, step=1,
            value=int(existing["predicted_score_a"]) if existing else 0,
            key=f"{key_prefix}_sa_{m['match_id']}",
        )
        pb = col2.number_input(
            f"{m['team_b']} goals", min_value=0, max_value=20, step=1,
            value=int(existing["predicted_score_b"]) if existing else 0,
            key=f"{key_prefix}_sb_{m['match_id']}",
        )
        winner_options = [m["team_a"], m["team_b"], "Draw"]
        idx = 0
        if existing and existing["predicted_winner"] in winner_options:
            idx = winner_options.index(existing["predicted_winner"])
        pred_winner = st.selectbox(
            "Predicted winner", winner_options, index=idx,
            key=f"{key_prefix}_w_{m['match_id']}",
        )
        col3, col4 = st.columns(2)
        pred_mom = col3.text_input(
            "Man of the Match (+3, optional)",
            value=existing["predicted_mom"] if existing and existing["predicted_mom"] else "",
            key=f"{key_prefix}_mom_{m['match_id']}",
        )
        pred_scorer = col4.text_input(
            "First goal scorer (+4, optional)",
            value=(existing["predicted_first_scorer"]
                   if existing and existing["predicted_first_scorer"] else ""),
            key=f"{key_prefix}_scorer_{m['match_id']}",
        )
        make_banker = st.checkbox(
            "⭐ Make this my Banker for the day (doubles this match's points)",
            value=bool(existing and existing["is_banker"]),
            key=f"{key_prefix}_bank_{m['match_id']}",
        )
        label = "Update prediction" if existing else "Save prediction"
        if st.form_submit_button(label):
            try:
                db.upsert_prediction(
                    user_id=user["user_id"], match_id=m["match_id"],
                    predicted_winner=pred_winner,
                    predicted_score_a=int(pa), predicted_score_b=int(pb),
                    predicted_mom=pred_mom,
                    predicted_first_scorer=pred_scorer,
                )
                db.set_banker(user["user_id"], m["match_id"], on=make_banker)
                msg = "Prediction saved."
                if make_banker:
                    msg += " ⭐ Banker set — any other banker you held today was cleared."
                st.success(msg)
            except ValueError as e:
                st.error(str(e))


# =============================================================================
# Sidebar (player login)
# =============================================================================
def sidebar_user_panel() -> dict | None:
    st.sidebar.markdown(
        '<div style="font-family:Anton,sans-serif; font-size:1.6rem; '
        'color:#FF3366; letter-spacing:0.05em; margin-bottom:6px;">PLAYER</div>'
        '<div style="font-family:Space Mono,monospace; font-size:0.65rem; '
        'color:#8A95B0; letter-spacing:0.2em; margin-bottom:18px;">SIGN IN OR REGISTER</div>',
        unsafe_allow_html=True,
    )
    users = db.list_users()
    options = ["— Select player —"] + [u["username"] for u in users]
    selected = st.sidebar.selectbox("Active profile", options, label_visibility="collapsed")

    with st.sidebar.expander("➕ Create new profile"):
        with st.form("new_user_form", clear_on_submit=True):
            new_name = st.text_input("Username", max_chars=30)
            if st.form_submit_button("Register"):
                try:
                    db.create_user(new_name)
                    st.success(f"Welcome, {new_name}!")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    user = None
    if selected != "— Select player —":
        user = db.get_user(selected)

    st.sidebar.markdown("---")
    if user:
        st.sidebar.markdown(
            f'<div style="padding:10px; background:#152238; border-radius:8px;'
            f'border:1px solid #243046;">'
            f'<div style="color:#8A95B0; font-size:0.65rem; letter-spacing:0.2em;">'
            f'PLAYING AS</div>'
            f'<div style="font-family:Anton,sans-serif; font-size:1.4rem;'
            f'color:#C3FF3E; margin-top:4px;">{escape(user["username"]).upper()}</div>'
            f'</div>', unsafe_allow_html=True,
        )
    else:
        st.sidebar.info("Pick or create a profile to play.")

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "💡 **Scoring** · Winner +1 · Goal diff +2 · Exact score +5 · "
        "MOM +3 · First scorer +4\n\n"
        "⭐ **Banker:** double one match per day · "
        "🐺 **Underdog:** +3 for calling a minority-pick upset\n\n"
        f"Stage multipliers: Group ×1 → Final ×6 · "
        f"Picks lock {db.LOCK_LEAD_HOURS}h before kickoff"
    )
    return user


# =============================================================================
# Tab: Dashboard
# =============================================================================
def tab_dashboard(user: dict | None) -> None:
    render_hero()

    all_m  = db.list_matches()
    played = [m for m in all_m if m["status"] == "completed"]
    upcoming = [m for m in all_m if m["status"] == "upcoming"]
    board  = db.get_leaderboard()
    leader = board[0] if board and board[0]["total_points"] > 0 else None

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Matches played",   f"{len(played)} / 104")
    c2.metric("Upcoming",         len(upcoming))
    c3.metric("Players",          len(db.list_users()))
    c4.metric("Top score",        leader["total_points"] if leader else 0,
              delta=leader["username"] if leader else None)

    # --- Today's daily mode banner (if today has matches) ---
    today_iso = datetime.now().date().isoformat()
    today_matches = db.get_matches_for_day(today_iso)
    if today_matches:
        _render_daily_banner(today_iso, today_matches, user)
        winner = db.get_daily_winner(today_iso)
        if winner:
            st.markdown(f"""
<div class="daily-winner">
  <div class="eyebrow">DAILY WINNER · {today_iso}</div>
  <div class="name">{escape(winner['username'])}</div>
  <div class="pts">{winner['day_points']} <span>PTS · {winner['correct_winners']} correct picks across {today_matches and len(today_matches)} matches</span></div>
</div>
""", unsafe_allow_html=True)

    # --- Recent daily winners strip ---
    recent_winners = db.get_all_daily_winners()[:6]
    if recent_winners:
        st.markdown(
            '<h3 style="font-family:Anton,sans-serif;letter-spacing:0.05em;'
            'color:#FFB800;margin-top:10px;">🏆 RECENT DAILY WINNERS</h3>',
            unsafe_allow_html=True)
        tiles_html = '<div class="dw-strip">'
        for w in recent_winners:
            tiles_html += (
                f'<div class="dw-tile">'
                f'<div class="when">{w["day"]} · {w["matches"]} matches</div>'
                f'<div class="who">🏆 {escape(w["username"])}</div>'
                f'<div class="num">{w["day_points"]} PTS</div>'
                f'</div>'
            )
        tiles_html += '</div>'
        st.markdown(tiles_html, unsafe_allow_html=True)

    st.markdown("### ")
    col_a, col_b = st.columns([3, 2])

    with col_a:
        heading = "⏭ NEXT FIXTURES" + (" · YOUR PICKS" if user else "")
        st.markdown(
            f'<h3 style="font-family:Anton,sans-serif;letter-spacing:0.05em;'
            f'color:#FFB800;">{heading}</h3>', unsafe_allow_html=True)
        if user:
            st.caption("Sign-in active — your submitted pick shows under each match. "
                       f"Picks lock {db.LOCK_LEAD_HOURS}h before kickoff.")
        next_six = upcoming[:6]
        if next_six:
            for m in next_six:
                st.markdown(render_match_card(m), unsafe_allow_html=True)
                if user:
                    pred = db.get_user_prediction(user["user_id"], m["match_id"])
                    _, lbl = lock_status(m)
                    st.markdown(
                        f'<div style="margin:-6px 0 14px 0;padding:6px 12px;'
                        f'background:#11192B;border:1px solid #243046;'
                        f'border-radius:0 0 8px 8px;display:flex;'
                        f'justify-content:space-between;align-items:center;">'
                        f'<span>{render_prediction_summary(pred)}</span>'
                        f'<span style="color:#8A95B0;font-family:Space Mono,monospace;'
                        f'font-size:0.7rem;">{lbl}</span></div>',
                        unsafe_allow_html=True,
                    )
        else:
            st.info("No upcoming matches.")

    with col_b:
        st.markdown(
            '<h3 style="font-family:Anton,sans-serif;letter-spacing:0.05em;'
            'color:#C3FF3E;">🏅 LEADERBOARD TOP 5</h3>', unsafe_allow_html=True)
        if board:
            for i, p in enumerate(board[:5], 1):
                rank_color = ["#FFB800", "#CCD2E0", "#C57A3E", "#8A95B0", "#8A95B0"][i-1]
                st.markdown(f"""
<div class="tile">
  <div class="row">
    <div>
      <span style="font-family:Anton,sans-serif;font-size:1.6rem;color:{rank_color};">
        {i:02d}</span>
      <span class="matchup" style="margin-left:8px;">{escape(p['username'])}</span>
    </div>
    <div style="font-family:'Space Mono',monospace;font-weight:700;color:#C3FF3E;font-size:1.1rem;">
      {p['total_points']} <span style="color:#8A95B0;font-size:0.7rem;">PTS</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
        else:
            st.info("No players yet.")

        st.markdown(
            '<h3 style="font-family:Anton,sans-serif;letter-spacing:0.05em;'
            'color:#FF3366;margin-top:18px;">⚡ LATEST RESULTS</h3>',
            unsafe_allow_html=True)
        recent = sorted(played, key=lambda x: x["match_date"], reverse=True)[:3]
        if recent:
            for m in recent:
                st.markdown(render_match_card(m), unsafe_allow_html=True)
        else:
            st.info("No results posted yet.")


# =============================================================================
# Tab: Fixtures (all 104 matches, filterable)
# =============================================================================
def tab_fixtures() -> None:
    st.markdown('<h2 style="font-family:Anton,sans-serif;letter-spacing:0.05em;'
                'color:#FFB800;">📅 ALL FIXTURES</h2>', unsafe_allow_html=True)

    all_m = db.list_matches()

    c1, c2, c3, c4 = st.columns([2, 2, 2, 3])
    stages = ["All stages"] + list(db.VALID_STAGES)
    pick_stage = c1.selectbox("Stage", stages)
    status_pick = c2.selectbox("Status", ["All", "Upcoming", "Completed"])
    groups = ["All groups"] + db.list_groups()
    pick_group = c3.selectbox("Group", groups)
    all_teams = sorted({t for m in all_m for t in (m["team_a"], m["team_b"]) if t in FLAGS})
    pick_team  = c4.selectbox("Team", ["All teams"] + all_teams)

    filtered = all_m
    if pick_stage  != "All stages":  filtered = [m for m in filtered if m["stage"] == pick_stage]
    if status_pick == "Upcoming":    filtered = [m for m in filtered if m["status"] == "upcoming"]
    if status_pick == "Completed":   filtered = [m for m in filtered if m["status"] == "completed"]
    if pick_group  != "All groups":  filtered = [m for m in filtered if m["group_name"] == pick_group]
    if pick_team   != "All teams":
        filtered = [m for m in filtered if pick_team in (m["team_a"], m["team_b"])]

    st.caption(f"Showing **{len(filtered)}** of {len(all_m)} matches")
    render_match_grid(filtered, cols=2)


# =============================================================================
# Tab: Groups
# =============================================================================
def tab_groups() -> None:
    st.markdown('<h2 style="font-family:Anton,sans-serif;letter-spacing:0.05em;'
                'color:#00D9FF;">🅰️ GROUP STAGE STANDINGS</h2>',
                unsafe_allow_html=True)
    st.caption("Top 2 from each group + 8 best 3rd-placed teams advance to the Round of 32.")

    groups = db.list_groups()
    if not groups:
        st.info("No groups in the database.")
        return

    # Render two groups per row
    for i in range(0, len(groups), 2):
        cols = st.columns(2)
        for j, grp in enumerate(groups[i:i+2]):
            standings = db.compute_group_standings(grp)
            rows_html = ""
            for rank, t in enumerate(standings, 1):
                cls = "q-win" if rank == 1 else ("q-run" if rank == 2 else
                       ("q-3rd" if rank == 3 else ""))
                rows_html += (
                    f'<tr class="{cls}">'
                    f'<td>{flag(t["team"])} {escape(t["team"])}</td>'
                    f'<td class="r">{t["P"]}</td>'
                    f'<td class="r">{t["W"]}</td>'
                    f'<td class="r">{t["D"]}</td>'
                    f'<td class="r">{t["L"]}</td>'
                    f'<td class="r">{t["GF"]}</td>'
                    f'<td class="r">{t["GA"]}</td>'
                    f'<td class="r">{t["GD"]:+d}</td>'
                    f'<td class="r pts">{t["Pts"]}</td>'
                    f'</tr>'
                )
            with cols[j]:
                st.markdown(f"""
<div class="gst-card">
  <h4>GROUP {grp}</h4>
  <table class="gst-table">
    <thead><tr>
      <th>TEAM</th><th class="r">P</th><th class="r">W</th><th class="r">D</th>
      <th class="r">L</th><th class="r">GF</th><th class="r">GA</th>
      <th class="r">GD</th><th class="r">PTS</th>
    </tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</div>
""", unsafe_allow_html=True)


# =============================================================================
# Tab: Bracket (knockout visualization)
# =============================================================================
def tab_bracket() -> None:
    st.markdown('<h2 style="font-family:Anton,sans-serif;letter-spacing:0.05em;'
                'color:#FF3366;">🏆 KNOCKOUT BRACKET</h2>',
                unsafe_allow_html=True)
    st.caption("Round of 16 onwards. Cards turn green when results are posted.")

    stages_order = ["Round of 16", "Quarter-Final", "Semi-Final", "Final"]
    cols = st.columns(4)

    for i, stage in enumerate(stages_order):
        matches = db.list_matches(stage=stage)
        with cols[i]:
            cards_html = f'<div class="bracket-col"><h4>{STAGE_LABEL[stage]}</h4>'
            for m in matches:
                completed = m["status"] == "completed"
                def team_row(team_name, score, is_winner):
                    cls = "bk-team" + ("" if not score or is_winner else " lose")
                    sc = f'<span class="sc">{score}</span>' if score is not None else ''
                    return (f'<div class="{cls}"><span class="nm">'
                            f'{flag(team_name)} {escape(team_name)}</span>{sc}</div>')

                row_a = team_row(m["team_a"], m.get("score_a"),
                                  m.get("winner") == m["team_a"])
                row_b = team_row(m["team_b"], m.get("score_b"),
                                  m.get("winner") == m["team_b"])
                date_str = fmt_date(m["match_date"]).split(" · ")[0]
                cards_html += (
                    f'<div class="bk-card {"completed" if completed else ""}">'
                    f'{row_a}{row_b}'
                    f'<div class="bk-meta">#{m["match_number"]} · {date_str} · '
                    f'{escape(m.get("city") or "")}</div>'
                    f'</div>'
                )
            cards_html += '</div>'
            st.markdown(cards_html, unsafe_allow_html=True)

    champ = db.get_tournament_winner()
    if champ:
        st.markdown(f"""
<div style="margin-top:24px;padding:24px;text-align:center;
            background:linear-gradient(135deg,#FF3366,#FFB800);
            border-radius:14px;">
  <div style="font-family:'Space Mono',monospace;letter-spacing:0.3em;
              font-size:0.75rem;color:#0B1421;">CHAMPION</div>
  <div style="font-family:Anton,sans-serif;font-size:4rem;color:#0B1421;
              margin-top:6px;">{flag(champ["winner"])} {escape(champ["winner"]).upper()}</div>
</div>
""", unsafe_allow_html=True)


# =============================================================================
# Tab: Predict
# =============================================================================
def tab_predict(user: dict) -> None:
    st.markdown('<h2 style="font-family:Anton,sans-serif;letter-spacing:0.05em;'
                'color:#C3FF3E;">🎯 MAKE PREDICTIONS</h2>',
                unsafe_allow_html=True)

    upcoming = db.list_matches(status="upcoming")
    if not upcoming:
        st.info("No upcoming matches available.")
        return

    stages = ["All stages"] + sorted({m["stage"] for m in upcoming},
                                       key=lambda s: db.STAGE_ORDER[s])
    pick = st.selectbox("Filter by stage", stages, key="pred_stage")
    if pick != "All stages":
        upcoming = [m for m in upcoming if m["stage"] == pick]

    st.caption(f"**{len(upcoming)}** matches available · Predictions lock when a result is posted.")

    st.caption(f"Picks lock {db.LOCK_LEAD_HOURS} hours before each kickoff. "
               "⭐ Banker doubles one match per day · 🐺 underdog upset bonus is automatic.")

    for m in upcoming:
        existing = db.get_user_prediction(user["user_id"], m["match_id"])
        locked, _ = lock_status(m)
        if locked:
            status_emoji = "🔒"
        elif existing and existing["is_banker"]:
            status_emoji = "⭐"
        elif existing:
            status_emoji = "✅"
        else:
            status_emoji = "⚪"
        title = (f"{status_emoji}  #{m['match_number']}  "
                 f"{flag(m['team_a'])} {m['team_a']}  vs  "
                 f"{flag(m['team_b'])} {m['team_b']}   ·   "
                 f"{STAGE_LABEL[m['stage']]} (×{STAGE_MULTIPLIER[m['stage']]})   ·   "
                 f"{fmt_date(m['match_date'])}")

        with st.expander(title, expanded=False):
            _render_prediction_form(user, m, key_prefix="pred")


# =============================================================================
# Tab: My Picks
# =============================================================================
def tab_my_predictions(user: dict) -> None:
    st.markdown(
        f'<h2 style="font-family:Anton,sans-serif;letter-spacing:0.05em;'
        f'color:#FFB800;">📊 {escape(user["username"]).upper()} · PICKS</h2>',
        unsafe_allow_html=True,
    )
    rows = db.list_user_predictions(user["user_id"])
    if not rows:
        st.info("You haven't made any predictions yet. Head to the **Predict** tab.")
        return

    scored = [r for r in rows if r["is_evaluated"]]
    total = sum(r["total_points"] for r in scored)
    correct_w = sum(1 for r in scored if r["winner_points"] + r["score_points"] > 0)
    exact = sum(1 for r in scored if r["score_points"] >= 5)
    mom_hit = sum(1 for r in scored if r["mom_points"] > 0)
    scorer_hit = sum(1 for r in scored if r["scorer_points"] > 0)
    bonus_total = sum(r["bonus_points"] for r in scored)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total points", total)
    c2.metric("Picks made", f"{len(rows)} / 104")
    c3.metric("Correct winners", f"{correct_w} / {len(scored)}" if scored else "0 / 0")
    c4.metric("Exact · MOM · 1st", f"{exact} · {mom_hit} · {scorer_hit}")
    c5.metric("Bonus points", bonus_total)

    df = pd.DataFrame([
        {
            "Stage":    r["stage"],
            "Match":    f"{flag(r['team_a'])} {r['team_a']} vs {flag(r['team_b'])} {r['team_b']}",
            "Your pick": f"{r['predicted_winner']} ({r['predicted_score_a']}-{r['predicted_score_b']})",
            "⭐":        "⭐" if r["is_banker"] else "",
            "Your MOM":  r["predicted_mom"] or "—",
            "Your 1st":  r["predicted_first_scorer"] or "—",
            "Actual":    (f"{r['actual_winner']} ({r['actual_score_a']}-{r['actual_score_b']})"
                          if r["status"] == "completed" else "TBD"),
            "Actual MOM": r["actual_mom"] or ("—" if r["status"] == "completed" else "TBD"),
            "Actual 1st": r["actual_first_scorer"] or ("—" if r["status"] == "completed" else "TBD"),
            "Bonus":     r["bonus_points"] if r["is_evaluated"] else "—",
            "Pts":       r["total_points"] if r["is_evaluated"] else "—",
        }
        for r in rows
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)


# =============================================================================
# Tab: Leaderboard
# =============================================================================
def tab_leaderboard() -> None:
    st.markdown('<h2 style="font-family:Anton,sans-serif;letter-spacing:0.05em;'
                'color:#FFB800;">🏅 LEADERBOARD</h2>', unsafe_allow_html=True)

    board = db.get_leaderboard()
    if not board:
        st.info("No players registered yet.")
        return

    # Podium for top 3
    top3 = board[:3]
    if len(top3) >= 3 and top3[0]["total_points"] > 0:
        # Order: 2nd, 1st, 3rd for visual podium
        order = [top3[1], top3[0], top3[2]]
        ranks = [2, 1, 3]
        cells = ""
        for r, p in zip(ranks, order):
            cells += f"""
<div class="pod rank-{r}">
  <div class="rank">{r:02d}</div>
  <div class="name">{escape(p['username'])}</div>
  <div class="pts">{p['total_points']}<span>PTS</span></div>
</div>"""
        st.markdown(f'<div class="podium">{cells}</div>', unsafe_allow_html=True)

    # Full table
    df = pd.DataFrame(board)
    df.insert(0, "#", range(1, len(df) + 1))
    display = df[[
        "#", "username", "total_points",
        "group_points", "r32_points", "r16_points",
        "qf_points", "sf_points", "final_points",
        "winner_points", "score_points", "mom_points", "scorer_points",
        "bonus_points", "predictions_made", "correct_winners",
    ]].rename(columns={
        "username":         "PLAYER",
        "total_points":     "TOTAL",
        "group_points":     "GRP",
        "r32_points":       "R32",
        "r16_points":       "R16",
        "qf_points":        "QF",
        "sf_points":        "SF",
        "final_points":     "FINAL",
        "winner_points":    "WIN",
        "score_points":     "SCORE",
        "mom_points":       "MOM",
        "scorer_points":    "1ST",
        "bonus_points":     "BONUS",
        "predictions_made": "PICKS",
        "correct_winners":  "CORRECT",
    })
    st.dataframe(display, use_container_width=True, hide_index=True)

    champ = db.get_tournament_winner()
    if champ and board[0]["total_points"] > 0:
        st.success(
            f"🥇 **GAME WINNER:** {board[0]['username']} — "
            f"{board[0]['total_points']} pts · "
            f"Tournament champion: {flag(champ['winner'])} {champ['winner']}"
        )


# =============================================================================
# Daily Mode helpers and tab
# =============================================================================
def _render_daily_banner(day_iso: str, day_matches: list[dict],
                          user: dict | None) -> None:
    """Compact info banner for a tournament day — used on Dashboard + Daily Mode."""
    participants = db.list_daily_participants(day_iso)
    filled = len(participants)
    is_full = filled >= db.MAX_DAILY_PARTICIPANTS
    completed = sum(1 for m in day_matches if m["status"] == "completed")
    pretty_day = datetime.fromisoformat(day_iso).strftime("%A · %b %d, %Y")
    css_class = "daily-banner full" if is_full else "daily-banner"
    st.markdown(f"""
<div class="{css_class}">
  <div>
    <div class="eyebrow">DAILY MODE</div>
    <div class="day">{pretty_day}</div>
    <div class="meta">{len(day_matches)} matches · {completed} completed · max {db.MAX_DAILY_PARTICIPANTS} players</div>
  </div>
  <div class="spots">
    {filled}<span class="total">/{db.MAX_DAILY_PARTICIPANTS}</span>
    <span class="label">SPOTS FILLED</span>
  </div>
</div>
""", unsafe_allow_html=True)


def _pick_default_day() -> str:
    """Default day for the date picker: today if matches exist, else next match day."""
    today = datetime.now().date().isoformat()
    if db.get_matches_for_day(today):
        return today
    upcoming = [d["day"] for d in db.list_tournament_dates() if d["day"] >= today]
    if upcoming:
        return upcoming[0]
    dates = [d["day"] for d in db.list_tournament_dates()]
    return dates[-1] if dates else today


def tab_daily(user: dict | None) -> None:
    st.markdown('<h2 style="font-family:Anton,sans-serif;letter-spacing:0.05em;'
                'color:#FFB800;">📆 DAILY MODE</h2>', unsafe_allow_html=True)
    st.caption(f"Up to **{db.MAX_DAILY_PARTICIPANTS}** players join each tournament day. "
               "Highest scorer across that day's matches takes the daily title.")

    all_dates = db.list_tournament_dates()
    if not all_dates:
        st.info("No matches in the database. Run `python seed_data.py`.")
        return

    # Date picker
    date_options = [d["day"] for d in all_dates]
    default = _pick_default_day()
    default_idx = date_options.index(default) if default in date_options else 0

    pretty_labels = []
    for d in all_dates:
        nice = datetime.fromisoformat(d["day"]).strftime("%a · %b %d")
        status = "✓" if d["completed"] == d["total"] else "○"
        pretty_labels.append(f"{nice}  ({d['total']} matches) {status}")

    chosen_idx = st.selectbox("Tournament day", range(len(date_options)),
                                index=default_idx,
                                format_func=lambda i: pretty_labels[i])
    day_iso = date_options[chosen_idx]
    day_matches = db.get_matches_for_day(day_iso)

    _render_daily_banner(day_iso, day_matches, user)

    # Daily winner banner if available
    winner = db.get_daily_winner(day_iso)
    if winner:
        st.markdown(f"""
<div class="daily-winner">
  <div class="eyebrow">DAILY WINNER · {day_iso}</div>
  <div class="name">{escape(winner['username'])}</div>
  <div class="pts">{winner['day_points']} <span>PTS · {winner['correct_winners']}/{winner['picks_made']} correct picks · {len(day_matches)} matches today</span></div>
</div>
""", unsafe_allow_html=True)
    elif day_matches and all(m["status"] == "completed" for m in day_matches):
        st.info("All matches complete but no participant scored any points.")
    elif day_matches:
        n_done = sum(1 for m in day_matches if m["status"] == "completed")
        st.info(f"⏳ Daily winner pending — {n_done} of {len(day_matches)} matches completed.")

    # Participants
    participants = db.list_daily_participants(day_iso)
    if participants or user:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown("**Today's roster:**")
            chips = ""
            for p in participants:
                chips += f'<span class="participant-chip">👤 {escape(p["username"])}</span>'
            for _ in range(db.MAX_DAILY_PARTICIPANTS - len(participants)):
                chips += '<span class="participant-chip empty">empty</span>'
            st.markdown(chips, unsafe_allow_html=True)
        with c2:
            if user:
                in_game = db.is_daily_participant(user["user_id"], day_iso)
                if in_game:
                    st.success(f"✅ You're in")
                    any_done = any(m["status"] == "completed" for m in day_matches)
                    if not any_done and st.button("Leave today's game",
                                                   key=f"leave_{day_iso}"):
                        try:
                            db.leave_daily_game(user["user_id"], day_iso)
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))
                elif len(participants) >= db.MAX_DAILY_PARTICIPANTS:
                    st.error("❌ Day is full")
                else:
                    if st.button("🎯 Join today's game", key=f"join_{day_iso}",
                                  use_container_width=True):
                        try:
                            db.join_daily_game(user["user_id"], day_iso)
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))
            else:
                st.info("Sign in to join.")

    st.markdown("---")

    # Matches & predictions
    if not day_matches:
        st.info("No matches on this date.")
        return

    user_in_game = user and db.is_daily_participant(user["user_id"], day_iso)
    upcoming_today = [m for m in day_matches if m["status"] == "upcoming"]
    completed_today = [m for m in day_matches if m["status"] == "completed"]

    if upcoming_today:
        st.markdown(
            f'<h3 style="font-family:Anton,sans-serif;letter-spacing:0.05em;'
            f'color:#C3FF3E;">⏭ TODAY\'S FIXTURES ({len(upcoming_today)})</h3>',
            unsafe_allow_html=True)
        for m in upcoming_today:
            st.markdown(render_match_card(m), unsafe_allow_html=True)
            if user_in_game:
                with st.expander("✏️ Make / update your prediction", expanded=False):
                    _render_prediction_form(user, m, key_prefix=f"daily_{day_iso}")
            elif user and not user_in_game:
                st.caption("Join the daily game above to predict this match.")

    if completed_today:
        st.markdown(
            f'<h3 style="font-family:Anton,sans-serif;letter-spacing:0.05em;'
            f'color:#FF3366;margin-top:18px;">⚡ RESULTS ({len(completed_today)})</h3>',
            unsafe_allow_html=True)
        for m in completed_today:
            st.markdown(render_match_card(m), unsafe_allow_html=True)

    # Daily leaderboard
    st.markdown("---")
    st.markdown(
        '<h3 style="font-family:Anton,sans-serif;letter-spacing:0.05em;'
        'color:#FFB800;">🏅 DAILY LEADERBOARD</h3>', unsafe_allow_html=True)
    board = db.get_daily_leaderboard(day_iso)
    if not board:
        st.info("No participants yet for this day.")
    else:
        df = pd.DataFrame([
            {
                "#":        i,
                "Player":   r["username"],
                "Day pts":  r["day_points"],
                "Picks":    r["picks_made"],
                "Scored":   r["picks_scored"],
                "Correct":  r["correct_winners"],
                "Joined":   r["joined_at"][:16],
            }
            for i, r in enumerate(board, 1)
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)


# =============================================================================
# Tab: Admin
# =============================================================================
def tab_admin() -> None:
    st.markdown('<h2 style="font-family:Anton,sans-serif;letter-spacing:0.05em;'
                'color:#B47AFF;">⚙️ ADMIN · MATCH RESULTS</h2>',
                unsafe_allow_html=True)
    st.caption("Submit official results + highlights. Change the admin password in `app.py`.")

    pwd = st.text_input("Admin password", type="password", key="adm_pwd")
    if pwd != "admin123":
        st.warning("Enter admin password to unlock.")
        return

    sub = st.radio("Action", ["📥 Submit a result",
                                "📝 Add / edit highlights for a completed match"],
                    horizontal=True, label_visibility="collapsed")

    if sub == "📥 Submit a result":
        upcoming = db.list_matches(status="upcoming")
        if not upcoming:
            st.info("All matches are completed.")
            return
        labels = [
            f"#{m['match_number']}  ·  {STAGE_LABEL[m['stage']]}  ·  "
            f"{m['team_a']} vs {m['team_b']}  ·  {fmt_date(m['match_date'])}"
            for m in upcoming
        ]
        idx = st.selectbox("Match", range(len(upcoming)),
                            format_func=lambda i: labels[i], key="adm_match_idx")
        m = upcoming[idx]
        st.markdown(render_match_card(m), unsafe_allow_html=True)
        with st.form(f"result_form_{m['match_id']}"):
            c1, c2 = st.columns(2)
            sa = c1.number_input(f"{m['team_a']} goals", 0, 20, 0)
            sb = c2.number_input(f"{m['team_b']} goals", 0, 20, 0)
            c3, c4 = st.columns(2)
            mom = c3.text_input("Man of the Match (player name)")
            first_scorer = c4.text_input("First goal scorer (player name)")
            highlights = st.text_area(
                "Highlights / recap (optional, 1–3 sentences)",
                placeholder="Brace from Vinicius caps a clinical Brazil performance...",
                max_chars=400, height=80,
            )
            confirm = st.checkbox(
                "Confirm — this locks predictions and scores all entries.")
            if st.form_submit_button("Submit result"):
                if not confirm:
                    st.error("Please tick the confirmation box.")
                else:
                    try:
                        db.update_match_result(
                            m["match_id"], int(sa), int(sb), mom, first_scorer)
                        if highlights.strip():
                            db.set_match_highlights(m["match_id"], highlights)
                        st.success(f"Result saved for {m['team_a']} vs {m['team_b']}.")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))

    else:
        completed = db.list_matches(status="completed")
        if not completed:
            st.info("No completed matches yet.")
            return
        labels = [
            f"#{m['match_number']}  ·  {m['team_a']} {m['score_a']}–"
            f"{m['score_b']} {m['team_b']}"
            for m in completed
        ]
        idx = st.selectbox("Completed match", range(len(completed)),
                            format_func=lambda i: labels[i], key="adm_hl_idx")
        m = completed[idx]
        st.markdown(render_match_card(m), unsafe_allow_html=True)
        with st.form(f"highlights_form_{m['match_id']}"):
            new_hl = st.text_area(
                "Highlights / recap",
                value=m.get("highlights") or "",
                max_chars=400, height=100,
            )
            if st.form_submit_button("Save highlights"):
                db.set_match_highlights(m["match_id"], new_hl)
                st.success("Highlights updated.")
                st.rerun()


# =============================================================================
# Main
# =============================================================================
def main() -> None:
    user = sidebar_user_panel()

    tabs = st.tabs([
        "🏁 Dashboard", "📅 Fixtures", "🅰️ Groups", "🏆 Bracket",
        "📆 Daily Mode",
        "🎯 Predict", "📊 My Picks", "🏅 Leaderboard", "⚙️ Admin",
    ])

    with tabs[0]: tab_dashboard(user)
    with tabs[1]: tab_fixtures()
    with tabs[2]: tab_groups()
    with tabs[3]: tab_bracket()
    with tabs[4]: tab_daily(user)
    with tabs[5]:
        if user: tab_predict(user)
        else: st.info("👈 Pick a player in the sidebar to make predictions.")
    with tabs[6]:
        if user: tab_my_predictions(user)
        else: st.info("👈 Pick a player to view your picks.")
    with tabs[7]: tab_leaderboard()
    with tabs[8]: tab_admin()


if __name__ == "__main__":
    main()
