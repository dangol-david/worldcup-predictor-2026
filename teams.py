"""Country flag emoji lookup for the 48 qualified nations + placeholders."""

FLAGS: dict[str, str] = {
    # AFC
    "Australia": "🇦🇺", "Iran": "🇮🇷", "Iraq": "🇮🇶", "Japan": "🇯🇵",
    "Jordan": "🇯🇴", "Qatar": "🇶🇦", "Saudi Arabia": "🇸🇦",
    "South Korea": "🇰🇷", "Uzbekistan": "🇺🇿",
    # CAF
    "Algeria": "🇩🇿", "Cape Verde": "🇨🇻", "Egypt": "🇪🇬",
    "Ghana": "🇬🇭", "Ivory Coast": "🇨🇮", "Morocco": "🇲🇦",
    "Senegal": "🇸🇳", "South Africa": "🇿🇦", "Tunisia": "🇹🇳",
    # CONCACAF
    "Canada": "🇨🇦", "Curacao": "🇨🇼", "Haiti": "🇭🇹",
    "Mexico": "🇲🇽", "Panama": "🇵🇦", "USA": "🇺🇸",
    # CONMEBOL
    "Argentina": "🇦🇷", "Brazil": "🇧🇷", "Colombia": "🇨🇴",
    "Ecuador": "🇪🇨", "Paraguay": "🇵🇾", "Uruguay": "🇺🇾",
    # OFC
    "New Zealand": "🇳🇿",
    # UEFA
    "Austria": "🇦🇹", "Belgium": "🇧🇪",
    "Bosnia and Herzegovina": "🇧🇦", "Croatia": "🇭🇷",
    "Czechia": "🇨🇿", "Democratic Republic of Congo": "🇨🇩",
    "England": "🏴\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F",
    "France": "🇫🇷", "Germany": "🇩🇪", "Italy": "🇮🇹",
    "Netherlands": "🇳🇱", "Norway": "🇳🇴", "Portugal": "🇵🇹",
    "Scotland": "🏴\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F",
    "Spain": "🇪🇸", "Sweden": "🇸🇪", "Switzerland": "🇨🇭",
    "Turkiye": "🇹🇷",
}

def flag(team: str) -> str:
    """Flag emoji for a team. Returns 🏆 for knockout placeholders."""
    if team in FLAGS:
        return FLAGS[team]
    # Placeholder labels like "Winner Group A", "3rd A/B/C/D/F", "Winner Match 73"
    return "🏆"

def team_label(team: str) -> str:
    """`🇧🇷 Brazil` for known teams, `🏆 Winner Group A` for placeholders."""
    return f"{flag(team)} {team}"
