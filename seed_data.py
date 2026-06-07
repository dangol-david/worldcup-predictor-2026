"""
seed_data.py
------------
Loads the official 2026 FIFA World Cup fixture list (Canada / Mexico / USA)
into the database: 104 matches across 7 stages.

  72 Group Stage (Groups A–L)
  16 Round of 32  (matches 73–88)
   8 Round of 16  (matches 89–96)
   4 Quarter-Final (matches 97–100)
   2 Semi-Final   (matches 101–102)
   1 Third Place  (match 103)
   1 Final        (match 104)

Knockout-stage teams are stored as placeholder labels ("Winner Group A",
"3rd A/B/C/D/F", "Winner Match 73", …) and should be updated by an admin
as the tournament progresses.

Run:  python seed_data.py            # only seeds if DB is empty
      python seed_data.py --reset    # wipes DB and reseeds
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from database import DB_PATH, create_match, get_connection, init_db

# Tuple shape: (match_number, group, team_a, team_b, "YYYY-MM-DD HH:MM ET",
#               venue, city, country)
# Knockout placeholders use "—" as the group.

GROUP_STAGE = [
    # ---- Group A
    (1,  "A", "Mexico", "South Africa",      "2026-06-11 15:00", "Estadio Azteca",       "Mexico City",         "MEX"),
    (2,  "A", "South Korea", "Czechia",      "2026-06-11 22:00", "Estadio Akron",        "Guadalajara",         "MEX"),
    (17, "A", "Czechia", "South Africa",     "2026-06-18 12:00", "Mercedes-Benz Stadium","Atlanta",             "USA"),
    (18, "A", "Mexico", "South Korea",       "2026-06-18 21:00", "Estadio Akron",        "Guadalajara",         "MEX"),
    (33, "A", "Czechia", "Mexico",           "2026-06-24 21:00", "Estadio Azteca",       "Mexico City",         "MEX"),
    (34, "A", "South Africa", "South Korea", "2026-06-24 21:00", "Estadio BBVA",         "Monterrey",           "MEX"),

    # ---- Group B
    (3,  "B", "Canada", "Bosnia and Herzegovina", "2026-06-12 15:00", "BMO Field",          "Toronto",        "CAN"),
    (4,  "B", "Qatar", "Switzerland",              "2026-06-13 15:00", "Levi's Stadium",     "San Francisco",  "USA"),
    (19, "B", "Switzerland", "Bosnia and Herzegovina","2026-06-18 15:00","SoFi Stadium",     "Los Angeles",    "USA"),
    (20, "B", "Canada", "Qatar",                   "2026-06-18 18:00", "BC Place",           "Vancouver",      "CAN"),
    (35, "B", "Switzerland", "Canada",             "2026-06-24 15:00", "BC Place",           "Vancouver",      "CAN"),
    (36, "B", "Bosnia and Herzegovina", "Qatar",   "2026-06-24 15:00", "Lumen Field",        "Seattle",        "USA"),

    # ---- Group C
    (5,  "C", "Brazil", "Morocco",      "2026-06-13 18:00", "MetLife Stadium",       "New York/New Jersey","USA"),
    (6,  "C", "Haiti", "Scotland",      "2026-06-13 21:00", "Gillette Stadium",      "Boston",             "USA"),
    (21, "C", "Scotland", "Morocco",    "2026-06-19 18:00", "Gillette Stadium",      "Boston",             "USA"),
    (22, "C", "Brazil", "Haiti",        "2026-06-19 21:00", "Lincoln Financial Field","Philadelphia",      "USA"),
    (37, "C", "Scotland", "Brazil",     "2026-06-24 18:00", "Hard Rock Stadium",     "Miami",              "USA"),
    (38, "C", "Morocco", "Haiti",       "2026-06-24 18:00", "Mercedes-Benz Stadium", "Atlanta",            "USA"),

    # ---- Group D
    (7,  "D", "USA", "Paraguay",        "2026-06-12 21:00", "SoFi Stadium",          "Los Angeles",      "USA"),
    (8,  "D", "Australia", "Turkiye",   "2026-06-14 00:00", "BC Place",              "Vancouver",        "CAN"),
    (23, "D", "USA", "Australia",       "2026-06-19 15:00", "Lumen Field",           "Seattle",          "USA"),
    (24, "D", "Turkiye", "Paraguay",    "2026-06-20 00:00", "Levi's Stadium",        "San Francisco",    "USA"),
    (39, "D", "Turkiye", "USA",         "2026-06-25 22:00", "SoFi Stadium",          "Los Angeles",      "USA"),
    (40, "D", "Paraguay", "Australia",  "2026-06-25 22:00", "Levi's Stadium",        "San Francisco",    "USA"),

    # ---- Group E
    (9,  "E", "Germany", "Curacao",         "2026-06-14 13:00", "NRG Stadium",            "Houston",      "USA"),
    (10, "E", "Ivory Coast", "Ecuador",     "2026-06-14 19:00", "Lincoln Financial Field","Philadelphia","USA"),
    (25, "E", "Germany", "Ivory Coast",     "2026-06-20 16:00", "BMO Field",              "Toronto",      "CAN"),
    (26, "E", "Ecuador", "Curacao",         "2026-06-20 20:00", "Arrowhead Stadium",      "Kansas City",  "USA"),
    (41, "E", "Ecuador", "Germany",         "2026-06-25 16:00", "MetLife Stadium",        "New York/New Jersey","USA"),
    (42, "E", "Curacao", "Ivory Coast",     "2026-06-25 16:00", "Lincoln Financial Field","Philadelphia","USA"),

    # ---- Group F
    (11, "F", "Netherlands", "Japan",       "2026-06-14 16:00", "AT&T Stadium",     "Dallas",       "USA"),
    (12, "F", "Sweden", "Tunisia",          "2026-06-14 22:00", "Estadio BBVA",     "Monterrey",    "MEX"),
    (27, "F", "Netherlands", "Sweden",      "2026-06-20 13:00", "NRG Stadium",      "Houston",      "USA"),
    (28, "F", "Tunisia", "Japan",           "2026-06-21 00:00", "Estadio BBVA",     "Monterrey",    "MEX"),
    (43, "F", "Japan", "Sweden",            "2026-06-25 19:00", "AT&T Stadium",     "Dallas",       "USA"),
    (44, "F", "Tunisia", "Netherlands",     "2026-06-25 19:00", "Arrowhead Stadium","Kansas City",  "USA"),

    # ---- Group G
    (13, "G", "Belgium", "Egypt",           "2026-06-15 15:00", "Lumen Field",      "Seattle",      "USA"),
    (14, "G", "Iran", "New Zealand",        "2026-06-15 21:00", "SoFi Stadium",     "Los Angeles",  "USA"),
    (29, "G", "Belgium", "Iran",            "2026-06-21 15:00", "SoFi Stadium",     "Los Angeles",  "USA"),
    (30, "G", "New Zealand", "Egypt",       "2026-06-21 21:00", "BC Place",         "Vancouver",    "CAN"),
    (45, "G", "Egypt", "Iran",              "2026-06-26 23:00", "Lumen Field",      "Seattle",      "USA"),
    (46, "G", "New Zealand", "Belgium",     "2026-06-26 23:00", "BC Place",         "Vancouver",    "CAN"),

    # ---- Group H
    (15, "H", "Spain", "Cape Verde",        "2026-06-15 12:00", "Mercedes-Benz Stadium","Atlanta",      "USA"),
    (16, "H", "Saudi Arabia", "Uruguay",    "2026-06-15 18:00", "Hard Rock Stadium",     "Miami",        "USA"),
    (31, "H", "Spain", "Saudi Arabia",      "2026-06-21 12:00", "Mercedes-Benz Stadium","Atlanta",      "USA"),
    (32, "H", "Uruguay", "Cape Verde",      "2026-06-21 18:00", "Hard Rock Stadium",     "Miami",        "USA"),
    (47, "H", "Cape Verde", "Saudi Arabia", "2026-06-26 20:00", "NRG Stadium",          "Houston",       "USA"),
    (48, "H", "Uruguay", "Spain",           "2026-06-26 20:00", "Estadio Akron",        "Guadalajara",   "MEX"),

    # ---- Group I
    (49, "I", "France", "Senegal",          "2026-06-16 15:00", "MetLife Stadium",        "New York/New Jersey","USA"),
    (50, "I", "Iraq", "Norway",             "2026-06-16 18:00", "Gillette Stadium",       "Boston",       "USA"),
    (51, "I", "France", "Iraq",             "2026-06-22 17:00", "Lincoln Financial Field","Philadelphia", "USA"),
    (52, "I", "Norway", "Senegal",          "2026-06-22 20:00", "MetLife Stadium",        "New York/New Jersey","USA"),
    (53, "I", "Norway", "France",           "2026-06-26 15:00", "Gillette Stadium",       "Boston",       "USA"),
    (54, "I", "Senegal", "Iraq",            "2026-06-26 15:00", "BMO Field",              "Toronto",      "CAN"),

    # ---- Group J
    (55, "J", "Argentina", "Algeria",       "2026-06-16 21:00", "Arrowhead Stadium","Kansas City",   "USA"),
    (56, "J", "Austria", "Jordan",          "2026-06-17 00:00", "Levi's Stadium",   "San Francisco", "USA"),
    (57, "J", "Argentina", "Austria",       "2026-06-22 13:00", "AT&T Stadium",     "Dallas",        "USA"),
    (58, "J", "Jordan", "Algeria",          "2026-06-22 23:00", "Levi's Stadium",   "San Francisco", "USA"),
    (59, "J", "Algeria", "Austria",         "2026-06-27 22:00", "Arrowhead Stadium","Kansas City",   "USA"),
    (60, "J", "Jordan", "Argentina",        "2026-06-27 22:00", "AT&T Stadium",     "Dallas",        "USA"),

    # ---- Group K
    (61, "K", "Portugal", "Democratic Republic of Congo", "2026-06-17 13:00", "NRG Stadium",          "Houston",     "USA"),
    (62, "K", "Uzbekistan", "Colombia",                   "2026-06-17 22:00", "Estadio Azteca",       "Mexico City", "MEX"),
    (63, "K", "Portugal", "Uzbekistan",                   "2026-06-23 13:00", "NRG Stadium",          "Houston",     "USA"),
    (64, "K", "Colombia", "Democratic Republic of Congo", "2026-06-23 22:00", "Estadio Akron",        "Guadalajara", "MEX"),
    (65, "K", "Colombia", "Portugal",                     "2026-06-27 19:30", "Hard Rock Stadium",    "Miami",       "USA"),
    (66, "K", "Democratic Republic of Congo", "Uzbekistan","2026-06-27 19:30","Mercedes-Benz Stadium","Atlanta",     "USA"),

    # ---- Group L
    (67, "L", "England", "Croatia",         "2026-06-17 16:00", "AT&T Stadium",           "Dallas",      "USA"),
    (68, "L", "Ghana", "Panama",            "2026-06-17 19:00", "BMO Field",              "Toronto",     "CAN"),
    (69, "L", "England", "Ghana",           "2026-06-23 16:00", "Gillette Stadium",       "Boston",      "USA"),
    (70, "L", "Panama", "Croatia",          "2026-06-23 19:00", "BMO Field",              "Toronto",     "CAN"),
    (71, "L", "Panama", "England",          "2026-06-27 17:00", "MetLife Stadium",        "New York/New Jersey","USA"),
    (72, "L", "Croatia", "Ghana",           "2026-06-27 17:00", "Lincoln Financial Field","Philadelphia","USA"),
]

# Knockout placeholders (teams determined after the prior stage finishes)
ROUND_OF_32 = [
    (73, "Runner-up A",  "Runner-up B",       "2026-06-28 15:00", "SoFi Stadium",          "Los Angeles",        "USA"),
    (74, "Winner E",     "3rd A/B/C/D/F",     "2026-06-29 16:30", "Gillette Stadium",      "Boston",             "USA"),
    (75, "Winner F",     "Runner-up C",       "2026-06-29 21:00", "Estadio BBVA",          "Monterrey",          "MEX"),
    (76, "Winner C",     "Runner-up F",       "2026-06-29 13:00", "NRG Stadium",           "Houston",            "USA"),
    (77, "Winner I",     "3rd C/D/F/G/H",     "2026-06-30 17:00", "MetLife Stadium",       "New York/New Jersey","USA"),
    (78, "Runner-up E",  "Runner-up I",       "2026-06-30 13:00", "AT&T Stadium",          "Dallas",             "USA"),
    (79, "Winner A",     "3rd C/E/F/H/I",     "2026-06-30 21:00", "Estadio Azteca",        "Mexico City",        "MEX"),
    (80, "Winner L",     "3rd E/H/I/J/K",     "2026-07-01 12:00", "Mercedes-Benz Stadium", "Atlanta",            "USA"),
    (81, "Winner D",     "3rd B/E/F/I/J",     "2026-07-01 20:00", "Levi's Stadium",        "San Francisco",      "USA"),
    (82, "Winner G",     "3rd A/E/H/I/J",     "2026-07-01 16:00", "Lumen Field",           "Seattle",            "USA"),
    (83, "Runner-up K",  "Runner-up L",       "2026-07-02 19:00", "BMO Field",             "Toronto",            "CAN"),
    (84, "Winner H",     "Runner-up J",       "2026-07-02 15:00", "SoFi Stadium",          "Los Angeles",        "USA"),
    (85, "Winner B",     "3rd E/F/G/I/J",     "2026-07-02 23:00", "BC Place",              "Vancouver",          "CAN"),
    (86, "Winner J",     "Runner-up H",       "2026-07-03 18:00", "Hard Rock Stadium",     "Miami",              "USA"),
    (87, "Winner K",     "3rd D/E/I/J/L",     "2026-07-03 21:30", "Arrowhead Stadium",     "Kansas City",        "USA"),
    (88, "Runner-up D",  "Runner-up G",       "2026-07-03 14:00", "AT&T Stadium",          "Dallas",             "USA"),
]

# Round of 16 — pairings follow the official bracket (winners of R32 matches).
# Source: FIFA bracket as published; exact pairings tied to match numbers.
ROUND_OF_16 = [
    (89, "Winner Match 74", "Winner Match 76", "2026-07-04 16:00", "Lincoln Financial Field","Philadelphia","USA"),
    (90, "Winner Match 73", "Winner Match 75", "2026-07-04 13:00", "NRG Stadium",            "Houston",     "USA"),
    (91, "Winner Match 77", "Winner Match 78", "2026-07-05 16:00", "Mercedes-Benz Stadium",  "Atlanta",     "USA"),
    (92, "Winner Match 79", "Winner Match 81", "2026-07-05 20:00", "Levi's Stadium",         "San Francisco","USA"),
    (93, "Winner Match 80", "Winner Match 82", "2026-07-06 16:00", "Lumen Field",            "Seattle",     "USA"),
    (94, "Winner Match 83", "Winner Match 84", "2026-07-06 20:00", "SoFi Stadium",           "Los Angeles", "USA"),
    (95, "Winner Match 86", "Winner Match 88", "2026-07-07 12:00", "Hard Rock Stadium",      "Miami",       "USA"),
    (96, "Winner Match 85", "Winner Match 87", "2026-07-07 21:00", "BC Place",               "Vancouver",   "CAN"),
]

QUARTER_FINALS = [
    (97,  "Winner Match 89", "Winner Match 90", "2026-07-09 16:00", "Gillette Stadium",   "Boston",      "USA"),
    (98,  "Winner Match 93", "Winner Match 94", "2026-07-10 20:00", "SoFi Stadium",       "Los Angeles", "USA"),
    (99,  "Winner Match 91", "Winner Match 92", "2026-07-11 18:00", "Hard Rock Stadium",  "Miami",       "USA"),
    (100, "Winner Match 95", "Winner Match 96", "2026-07-11 21:00", "Arrowhead Stadium",  "Kansas City", "USA"),
]

SEMI_FINALS = [
    (101, "Winner Match 97", "Winner Match 98",  "2026-07-14 20:00", "AT&T Stadium",          "Dallas",  "USA"),
    (102, "Winner Match 99", "Winner Match 100", "2026-07-15 20:00", "Mercedes-Benz Stadium", "Atlanta", "USA"),
]

THIRD_PLACE = [
    (103, "Loser Match 101", "Loser Match 102",  "2026-07-18 16:00", "Hard Rock Stadium", "Miami", "USA"),
]

FINAL = [
    (104, "Winner Match 101", "Winner Match 102","2026-07-19 15:00", "MetLife Stadium", "New York/New Jersey", "USA"),
]


def _seed_stage(rows, stage: str) -> None:
    for r in rows:
        if stage == "Group Stage":
            num, grp, a, b, when, venue, city, country = r
        else:
            num, a, b, when, venue, city, country = r
            grp = None
        create_match(
            stage=stage, team_a=a, team_b=b, match_date=when,
            venue=venue, city=city, country=country,
            match_number=num, group_name=grp,
        )


def _match_count() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) AS c FROM matches").fetchone()["c"]


def seed(force_reset: bool = False) -> None:
    if force_reset and Path(DB_PATH).exists():
        Path(DB_PATH).unlink()
        print(f"Wiped {DB_PATH}.")

    init_db()

    if _match_count() > 0:
        print(f"Database already contains {_match_count()} matches. "
              "Use `python seed_data.py --reset` to wipe and reseed.")
        return

    _seed_stage(GROUP_STAGE,   "Group Stage")
    _seed_stage(ROUND_OF_32,   "Round of 32")
    _seed_stage(ROUND_OF_16,   "Round of 16")
    _seed_stage(QUARTER_FINALS,"Quarter-Final")
    _seed_stage(SEMI_FINALS,   "Semi-Final")
    _seed_stage(THIRD_PLACE,   "Third Place")
    _seed_stage(FINAL,         "Final")

    total = _match_count()
    print(f"Seeded {total} matches "
          f"({len(GROUP_STAGE)} Group, {len(ROUND_OF_32)} R32, "
          f"{len(ROUND_OF_16)} R16, {len(QUARTER_FINALS)} QF, "
          f"{len(SEMI_FINALS)} SF, {len(THIRD_PLACE)} 3rd, {len(FINAL)} Final).")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Seed the World Cup database.")
    p.add_argument("--reset", action="store_true",
                   help="Delete worldcup.db before seeding (destructive).")
    args = p.parse_args()
    seed(force_reset=args.reset)
