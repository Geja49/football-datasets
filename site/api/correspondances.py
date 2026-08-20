"""Noms football-data.co.uk -> noms Understat."""

CORRESPONDANCES = {
    "Man City": "Manchester City",
    "Man United": "Manchester United",
    "Newcastle": "Newcastle United",
    "Nott'm Forest": "Nottingham Forest",
    "Wolves": "Wolverhampton Wanderers",
    "Paris SG": "Paris Saint Germain",
    "Ath Bilbao": "Athletic Club",
    "Ath Madrid": "Atletico Madrid",
    "Betis": "Real Betis",
    "Celta": "Celta Vigo",
    "Espanol": "Espanyol",
    "Oviedo": "Real Oviedo",
    "Sociedad": "Real Sociedad",
    "Vallecano": "Rayo Vallecano",
    "Santander": "Racing Santander",
    "Dep. A Coruna": "Deportivo La Coruna",
    "Dortmund": "Borussia Dortmund",
    "Ein Frankfurt": "Eintracht Frankfurt",
    "FC Koln": "FC Cologne",
    "Hamburg": "Hamburger SV",
    "Heidenheim": "FC Heidenheim",
    "Leverkusen": "Bayer Leverkusen",
    "M'gladbach": "Borussia M.Gladbach",
    "Mainz": "Mainz 05",
    "RB Leipzig": "RasenBallsport Leipzig",
    "St Pauli": "St. Pauli",
    "Stuttgart": "VfB Stuttgart",
    "Milan": "AC Milan",
    "Parma": "Parma Calcio 1913",
}


NOMS_VERS_CALENDRIER = {nom_understat: nom_matchs for nom_matchs, nom_understat in CORRESPONDANCES.items()}
# Variantes fixtures.csv (noms un peu differents des CSV de saison).
NOMS_VERS_CALENDRIER.update(
    {
        "Atl. Madrid": "Ath Madrid",
        "Atletico": "Ath Madrid",
        "Atlético": "Ath Madrid",
        "Atlético Madrid": "Ath Madrid",
    }
)


def normaliser(nom):
    texte = (nom or "").lower()
    for mot in ("fc ", " fc", "real ", "borussia ", "ac ", "the "):
        texte = texte.replace(mot, "")
    return "".join(car for car in texte if car.isalnum())


def nom_pour_calendrier(nom_understat, noms_matchs=None):
    """Nom Understat -> nom football-data, pour fusionner le calendrier."""
    if nom_understat in NOMS_VERS_CALENDRIER:
        return NOMS_VERS_CALENDRIER[nom_understat]
    if not noms_matchs or nom_understat in noms_matchs:
        return nom_understat
    cible = normaliser(nom_understat)
    if len(cible) < 4:
        return nom_understat
    for nom in noms_matchs:
        if cible == normaliser(nom):
            return nom
    return nom_understat


def nom_pour_joueurs(nom_matchs, noms_understat):
    if nom_matchs in CORRESPONDANCES and CORRESPONDANCES[nom_matchs] in noms_understat:
        return CORRESPONDANCES[nom_matchs]
    if nom_matchs in noms_understat:
        return nom_matchs
    cible = normaliser(nom_matchs)
    if len(cible) < 4:
        return nom_matchs
    for nom in noms_understat:
        autre = normaliser(nom)
        if cible == autre or cible in autre or autre in cible:
            return nom
    return nom_matchs


# Noms openfootball (sans code pays) -> noms football-data des 5 ligues,
# ou un libelle court pour les clubs hors ligues.
NOMS_LDC = {
    "athletic club": "Ath Bilbao",
    "arsenal fc": "Arsenal",
    "arsenal": "Arsenal",
    "psv": "PSV",
    "psv eindhoven": "PSV",
    "royale union saint-gilloise": "Union SG",
    "union saint-gilloise": "Union SG",
    "union sg": "Union SG",
    "juventus fc": "Juventus",
    "juventus": "Juventus",
    "borussia dortmund": "Dortmund",
    "sport lisboa e benfica": "Benfica",
    "sl benfica": "Benfica",
    "benfica": "Benfica",
    "qarabag agdam fk": "Qarabag",
    "qarabag fk": "Qarabag",
    "qarabag": "Qarabag",
    "tottenham hotspur fc": "Tottenham",
    "tottenham hotspur": "Tottenham",
    "villarreal cf": "Villarreal",
    "real madrid cf": "Real Madrid",
    "real madrid": "Real Madrid",
    "olympique de marseille": "Marseille",
    "sk slavia praha": "Slavia Prague",
    "slavia praha": "Slavia Prague",
    "slavia prague": "Slavia Prague",
    "fk bodo/glimt": "Bodo/Glimt",
    "bodo/glimt": "Bodo/Glimt",
    "pae olympiakos sfp": "Olympiacos",
    "olympiakos": "Olympiacos",
    "olympiacos": "Olympiacos",
    "paphos fc": "Paphos",
    "afc ajax": "Ajax",
    "ajax": "Ajax",
    "fc internazionale milano": "Inter",
    "internazionale": "Inter",
    "inter milan": "Inter",
    "liverpool fc": "Liverpool",
    "club atletico de madrid": "Ath Madrid",
    "atletico de madrid": "Ath Madrid",
    "atletico madrid": "Ath Madrid",
    "paris saint-germain fc": "Paris SG",
    "paris saint germain fc": "Paris SG",
    "paris saint-germain": "Paris SG",
    "paris saint germain": "Paris SG",
    "atalanta bc": "Atalanta",
    "fc bayern munchen": "Bayern Munich",
    "bayern munchen": "Bayern Munich",
    "bayern munich": "Bayern Munich",
    "chelsea fc": "Chelsea",
    "fc kobenhavn": "Copenhagen",
    "kobenhavn": "Copenhagen",
    "fc copenhagen": "Copenhagen",
    "bayer 04 leverkusen": "Leverkusen",
    "bayer leverkusen": "Leverkusen",
    "club brugge kv": "Club Brugge",
    "club brugge": "Club Brugge",
    "as monaco fc": "Monaco",
    "as monaco": "Monaco",
    "newcastle united fc": "Newcastle",
    "newcastle united": "Newcastle",
    "fc barcelona": "Barcelona",
    "barcelona": "Barcelona",
    "manchester city fc": "Man City",
    "manchester city": "Man City",
    "ssc napoli": "Napoli",
    "napoli": "Napoli",
    "eintracht frankfurt": "Ein Frankfurt",
    "galatasaray sk": "Galatasaray",
    "galatasaray": "Galatasaray",
    "sporting clube de portugal": "Sporting",
    "sporting cp": "Sporting",
    "fk kairat": "Kairat",
    "kairat almaty": "Kairat",
    "ac milan": "Milan",
    "manchester united fc": "Man United",
    "manchester united": "Man United",
    "rb leipzig": "RB Leipzig",
    "rasenballsport leipzig": "RB Leipzig",
    "as roma": "Roma",
    "ogc nice": "Nice",
    "lille osc": "Lille",
    "stade brestois 29": "Brest",
    "girona fc": "Girona",
    "sevilla fc": "Sevilla",
    "real sociedad": "Sociedad",
    "celta de vigo": "Celta",
    "rc celta": "Celta",
    "atalanta": "Atalanta",
}


def cle_nom(nom):
    texte = (nom or "").lower().replace("saint-germain", "saint germain")
    texte = texte.replace("á", "a").replace("à", "a").replace("ä", "a")
    texte = texte.replace("é", "e").replace("è", "e").replace("ë", "e")
    texte = texte.replace("í", "i").replace("ó", "o").replace("ö", "o")
    texte = texte.replace("ú", "u").replace("ü", "u").replace("ø", "o")
    texte = texte.replace("å", "a").replace("ğ", "g").replace("ç", "c")
    texte = texte.replace("ñ", "n").replace("ş", "s").replace("ø", "o")
    return " ".join(texte.split())


def retirer_code_pays(nom):
    texte = (nom or "").strip()
    if len(texte) >= 5 and texte[-1] == ")" and texte[-5] == "(":
        return texte[:-5].strip()
    return texte


def nom_depuis_openfootball(nom_brut, noms_ligues=None):
    """FC Barcelona (ESP) -> Barcelona si le club est deja dans nos ligues."""
    propre = retirer_code_pays(nom_brut)
    alias = NOMS_LDC.get(cle_nom(propre))
    if alias:
        return alias
    if noms_ligues:
        return nom_pour_calendrier(propre, noms_ligues)
    return propre
