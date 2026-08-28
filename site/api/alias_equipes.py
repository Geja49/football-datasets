"""Alias noms calendrier -> noms football-data (table matchs)."""

from __future__ import annotations

from correspondances import nom_depuis_openfootball

# Cas connus : openfootball / fixtures vs football-data.co.uk
ALIAS_CALENDRIER_VERS_MATCHS: dict[str, str] = {
    "Stade Rennais FC 1901": "Rennes",
    "Stade Rennais FC": "Rennes",
    "SC Paderborn 07": "Paderborn",
    "SV 07 Elversberg": "Elversberg",
    "1. FC Union Berlin": "Union Berlin",
    "FC Bayern München": "Bayern Munich",
    "FC Bayern Munich": "Bayern Munich",
    "FC Bayern Munchen": "Bayern Munich",
    "TSG Hoffenheim": "Hoffenheim",
    "TSG 1899 Hoffenheim": "Hoffenheim",
    "VfL Wolfsburg": "Wolfsburg",
    "FC Augsburg": "Augsburg",
    "1. FC Köln": "FC Koln",
    "1. FC Koeln": "FC Koln",
    "Borussia Mönchengladbach": "M'gladbach",
    "Borussia Monchengladbach": "M'gladbach",
    "Bayer 04 Leverkusen": "Leverkusen",
    "Eintracht Frankfurt": "Ein Frankfurt",
    "VfB Stuttgart": "Stuttgart",
    "SV Werder Bremen": "Werder Bremen",
    "FC Schalke 04": "Schalke 04",
    "Hamburger SV": "Hamburg",
    "RB Leipzig": "RB Leipzig",
    "RasenBallsport Leipzig": "RB Leipzig",
    "Borussia Dortmund": "Dortmund",
    "SC Freiburg": "Freiburg",
    "1. FSV Mainz 05": "Mainz",
    "FSV Mainz 05": "Mainz",
    # Super Lig (fixtures.csv / openfootball)
    "Galatasaray SK": "Galatasaray",
    "Fenerbahçe SK": "Fenerbahce",
    "Fenerbahce SK": "Fenerbahce",
    "Beşiktaş JK": "Besiktas",
    "Besiktas JK": "Besiktas",
    "Trabzonspor Kulübü": "Trabzonspor",
    "Trabzonspor Kulubu": "Trabzonspor",
    "İstanbul Başakşehir FK": "Istanbul Basaksehir",
    "Istanbul Basaksehir FK": "Istanbul Basaksehir",
    # LDC (noms longs openfootball sans code pays)
    "FC Barcelona": "Barcelona",
    "Real Madrid CF": "Real Madrid",
    "Manchester City FC": "Man City",
    "Manchester United FC": "Man United",
    "Newcastle United FC": "Newcastle",
    "Tottenham Hotspur FC": "Tottenham",
    "Chelsea FC": "Chelsea",
    "Arsenal FC": "Arsenal",
    "Liverpool FC": "Liverpool",
    "Paris Saint-Germain FC": "Paris SG",
    "Paris Saint Germain FC": "Paris SG",
    "Club Atlético de Madrid": "Ath Madrid",
    "Club Atletico de Madrid": "Ath Madrid",
    "Atletico de Madrid": "Ath Madrid",
    "Athletic Club": "Ath Bilbao",
    "FC Internazionale Milano": "Inter",
    "AC Milan": "Milan",
    "Juventus FC": "Juventus",
    "SSC Napoli": "Napoli",
    "AS Monaco FC": "Monaco",
    "Sport Lisboa e Benfica": "Benfica",
    "SL Benfica": "Benfica",
    "Sporting Clube de Portugal": "Sporting",
    "Sporting CP": "Sporting",
    "PSV Eindhoven": "PSV",
    "AFC Ajax": "Ajax",
    "SK Slavia Praha": "Slavia Prague",
    "FK Bodø/Glimt": "Bodo/Glimt",
    "FK Bodo/Glimt": "Bodo/Glimt",
    "PAE Olympiakos SFP": "Olympiacos",
    "Royale Union Saint-Gilloise": "Union SG",
}


def normaliser_nom_calendrier(nom: str | None, noms_matchs: set[str] | list[str] | None = None) -> str:
    """Retourne le nom utilisé dans matchs pour un club du calendrier."""
    texte = (nom or "").strip()
    if not texte:
        return texte
    if texte in ALIAS_CALENDRIER_VERS_MATCHS:
        return ALIAS_CALENDRIER_VERS_MATCHS[texte]
    via_openfootball = nom_depuis_openfootball(texte, noms_matchs)
    if via_openfootball != texte:
        return via_openfootball
    return ALIAS_CALENDRIER_VERS_MATCHS.get(texte, texte)
