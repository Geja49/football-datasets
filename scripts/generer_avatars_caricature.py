"""Génère des avatars SVG originaux style caricature cartoon joueur de foot.

Inspiré du style « Cartoon caricature » (Sanggi Design, Dribbble) —
créations originales Stats Foot, sans copie des assets protégés.
Référence visuelle : https://dribbble.com/shots/20956054-Cartoon-caricature-of-Eeling-Haaland
"""

from __future__ import annotations

from pathlib import Path

DOSSIER_SORTIE = Path(__file__).resolve().parents[1] / "site" / "frontend" / "public" / "avatars"

# (id, libelle, fond, peau, cheveux, style_cheveux, maillot, accent, expression, extras)
CONFIGS: list[tuple[str, str, str, str, str, str, str, str, str, str]] = [
    (
        "caricature-foot-01",
        "Caricature blond",
        "#38bdf8",
        "#f5d0a9",
        "#f5e6a3",
        "blond_nordique",
        "#6ee7f9",
        "#1e3a5f",
        "determine",
        "",
    ),
    (
        "caricature-foot-02",
        "Joueur cartoon 2",
        "#dc2626",
        "#8d5524",
        "#1a1a1a",
        "afro",
        "#ef4444",
        "#fbbf24",
        "sourire",
        "",
    ),
    (
        "caricature-foot-03",
        "Joueur cartoon 3",
        "#15803d",
        "#c68642",
        "#4a3728",
        "boucles",
        "#22c55e",
        "#ffffff",
        "confiant",
        "barbe",
    ),
    (
        "caricature-foot-04",
        "Joueur cartoon 4",
        "#475569",
        "#ffdbac",
        "#2c1810",
        "court",
        "#f8fafc",
        "#dc2626",
        "sourire",
        "brassard",
    ),
    (
        "caricature-foot-05",
        "Joueur cartoon 5",
        "#7c3aed",
        "#e0ac69",
        "#b45309",
        "mohawk",
        "#a855f7",
        "#ffffff",
        "feu",
        "",
    ),
    (
        "caricature-foot-06",
        "Joueur cartoon 6",
        "#ea580c",
        "#6b4423",
        "#1a1a1a",
        "bandeau",
        "#fb923c",
        "#1e293b",
        "determine",
        "",
    ),
    (
        "caricature-foot-07",
        "Joueur cartoon 7",
        "#ca8a04",
        "#5c3317",
        "#1a1a1a",
        "rase",
        "#facc15",
        "#1e293b",
        "sourire",
        "",
    ),
    (
        "caricature-foot-08",
        "Joueur cartoon 8",
        "#1d4ed8",
        "#f1c27d",
        "#8b4513",
        "long",
        "#3b82f6",
        "#ffffff",
        "confiant",
        "",
    ),
    (
        "caricature-foot-09",
        "Joueur cartoon 9",
        "#be185d",
        "#ffdbac",
        "#d4a017",
        "meches",
        "#ec4899",
        "#831843",
        "sourire",
        "",
    ),
    (
        "caricature-foot-10",
        "Joueur cartoon 10",
        "#0f766e",
        "#8d5524",
        "#6b6b6b",
        "calvitie",
        "#14b8a6",
        "#facc15",
        "determine",
        "barbe",
    ),
]

CONTOUR = "#1a1a1a"
EPAISSEUR = "2.5"


def _cheveux(style: str, couleur: str) -> str:
    s = f'stroke="{CONTOUR}" stroke-width="{EPAISSEUR}"'
    if style == "blond_nordique":
        return (
            f'<path d="M34 52 Q32 28 64 22 Q96 28 94 52 Q90 38 64 34 Q38 38 34 52" fill="{couleur}" {s}/>'
            f'<path d="M36 48 Q40 30 52 36 M76 36 Q88 30 92 48" fill="none" stroke="{couleur}" stroke-width="4" stroke-linecap="round"/>'
            f'<ellipse cx="64" cy="38" rx="30" ry="16" fill="{couleur}" {s}/>'
        )
    if style == "afro":
        return (
            f'<circle cx="50" cy="36" r="12" fill="{couleur}" {s}/>'
            f'<circle cx="64" cy="28" r="14" fill="{couleur}" {s}/>'
            f'<circle cx="78" cy="36" r="12" fill="{couleur}" {s}/>'
            f'<circle cx="54" cy="46" r="10" fill="{couleur}" {s}/>'
            f'<circle cx="74" cy="46" r="10" fill="{couleur}" {s}/>'
        )
    if style == "boucles":
        return (
            f'<ellipse cx="64" cy="36" rx="32" ry="16" fill="{couleur}" {s}/>'
            f'<circle cx="44" cy="42" r="7" fill="{couleur}" {s}/>'
            f'<circle cx="54" cy="36" r="7" fill="{couleur}" {s}/>'
            f'<circle cx="74" cy="36" r="7" fill="{couleur}" {s}/>'
            f'<circle cx="84" cy="42" r="7" fill="{couleur}" {s}/>'
        )
    if style == "court":
        return f'<ellipse cx="64" cy="36" rx="32" ry="18" fill="{couleur}" {s}/>'
    if style == "mohawk":
        return (
            f'<ellipse cx="64" cy="40" rx="28" ry="12" fill="{couleur}" opacity="0.35" {s}/>'
            f'<path d="M58 26 L64 8 L70 26 Z" fill="{couleur}" {s}/>'
            f'<rect x="60" y="8" width="8" height="22" rx="2" fill="{couleur}" {s}/>'
        )
    if style == "bandeau":
        return (
            f'<ellipse cx="64" cy="36" rx="32" ry="18" fill="{couleur}" {s}/>'
            f'<rect x="32" y="32" width="64" height="10" rx="3" fill="#ef4444" {s}/>'
        )
    if style == "rase":
        return f'<ellipse cx="64" cy="40" rx="28" ry="10" fill="{couleur}" opacity="0.2" {s}/>'
    if style == "long":
        return (
            f'<ellipse cx="64" cy="34" rx="32" ry="16" fill="{couleur}" {s}/>'
            f'<path d="M34 44 Q30 72 38 88 Q64 94 90 88 Q98 72 94 44" fill="{couleur}" {s}/>'
        )
    if style == "meches":
        return (
            f'<ellipse cx="64" cy="34" rx="32" ry="16" fill="{couleur}" {s}/>'
            f'<path d="M42 40 Q46 18 52 38" fill="{couleur}" {s}/>'
            f'<path d="M54 32 Q60 14 66 34" fill="{couleur}" {s}/>'
            f'<path d="M66 34 Q72 14 78 32" fill="{couleur}" {s}/>'
            f'<path d="M82 38 Q88 18 90 42" fill="{couleur}" {s}/>'
        )
    if style == "calvitie":
        return f'<ellipse cx="64" cy="42" rx="26" ry="12" fill="{couleur}" opacity="0.25" {s}/>'
    return f'<ellipse cx="64" cy="36" rx="32" ry="18" fill="{couleur}" {s}/>'


def _yeux(expression: str) -> str:
    s = f'stroke="{CONTOUR}" stroke-width="{EPAISSEUR}"'
    base = (
        f'<ellipse cx="50" cy="58" rx="7" ry="9" fill="#ffffff" {s}/>'
        f'<ellipse cx="78" cy="58" rx="7" ry="9" fill="#ffffff" {s}/>'
        f'<circle cx="52" cy="60" r="4" fill="#1e293b"/>'
        f'<circle cx="80" cy="60" r="4" fill="#1e293b"/>'
        f'<circle cx="53" cy="58" r="1.5" fill="#ffffff"/>'
        f'<circle cx="81" cy="58" r="1.5" fill="#ffffff"/>'
    )
    if expression == "feu":
        base += (
            f'<path d="M44 52 L50 56 L46 60 Z" fill="#ef4444" {s}/>'
            f'<path d="M84 52 L78 56 L82 60 Z" fill="#ef4444" {s}/>'
        )
    elif expression == "confiant":
        base += (
            f'<path d="M43 52 L50 54" fill="none" stroke="{CONTOUR}" stroke-width="2" stroke-linecap="round"/>'
            f'<path d="M85 52 L78 54" fill="none" stroke="{CONTOUR}" stroke-width="2" stroke-linecap="round"/>'
        )
    return base


def _bouche(expression: str) -> str:
    s = f'stroke="{CONTOUR}" stroke-width="{EPAISSEUR}" fill="none" stroke-linecap="round"'
    if expression == "sourire":
        return f'<path d="M52 78 Q64 90 76 78" {s}/>'
    if expression == "feu":
        return (
            f'<path d="M54 76 Q64 86 74 76" {s}/>'
            f'<path d="M60 80 L64 88 L68 80" fill="#ef4444" stroke="{CONTOUR}" stroke-width="1.5"/>'
        )
    if expression == "confiant":
        return f'<path d="M56 78 L72 78" {s}/>'
    return f'<path d="M54 78 Q64 84 74 78" {s}/>'


def _extras(extras: str) -> str:
    s = f'stroke="{CONTOUR}" stroke-width="{EPAISSEUR}"'
    if extras == "barbe":
        return (
            f'<path d="M44 72 Q64 98 84 72 Q80 88 64 92 Q48 88 44 72" fill="#3d2314" opacity="0.85" {s}/>'
        )
    if extras == "brassard":
        return f'<rect x="86" y="96" width="12" height="16" rx="2" fill="#dc2626" {s}/>'
    return ""


def generer_svg(
    libelle: str,
    fond: str,
    peau: str,
    cheveux: str,
    style_cheveux: str,
    maillot: str,
    accent: str,
    expression: str,
    extras: str,
) -> str:
    s = f'stroke="{CONTOUR}" stroke-width="{EPAISSEUR}"'
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" role="img" aria-label="{libelle}">
  <defs>
    <clipPath id="cercle"><circle cx="64" cy="64" r="62"/></clipPath>
  </defs>
  <circle cx="64" cy="64" r="62" fill="{fond}"/>
  <g clip-path="url(#cercle)">
    <ellipse cx="64" cy="122" rx="36" ry="8" fill="rgba(0,0,0,0.15)"/>
    <path d="M28 128 L100 128 L92 98 Q64 88 36 98 Z" fill="{maillot}" {s}/>
    <path d="M54 98 L74 98 L72 128 L56 128 Z" fill="{accent}" opacity="0.4"/>
    <path d="M56 98 Q64 92 72 98" fill="none" stroke="{accent}" stroke-width="2.5"/>
    <circle cx="64" cy="64" r="34" fill="{peau}" {s}/>
    <ellipse cx="64" cy="72" rx="28" ry="24" fill="{peau}" {s}/>
    <path d="M38 68 Q64 88 90 68" fill="none" stroke="{CONTOUR}" stroke-width="1.5" opacity="0.15"/>
    {_cheveux(style_cheveux, cheveux)}
    <ellipse cx="42" cy="70" rx="6" ry="4" fill="#e11d48" opacity="0.3"/>
    <ellipse cx="86" cy="70" rx="6" ry="4" fill="#e11d48" opacity="0.3"/>
    <ellipse cx="64" cy="68" rx="5" ry="4" fill="#d4a574" opacity="0.5"/>
    {_yeux(expression)}
    {_bouche(expression)}
    {_extras(extras)}
  </g>
</svg>
"""


def main() -> None:
    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)
    for cfg in CONFIGS:
        ident, libelle, *params = cfg
        svg = generer_svg(libelle, *params)
        chemin = DOSSIER_SORTIE / f"{ident}.svg"
        chemin.write_text(svg, encoding="utf-8")
        print(f"Écrit {chemin.name}")


if __name__ == "__main__":
    main()
