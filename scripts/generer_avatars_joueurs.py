"""Génère des avatars SVG originaux style joueur de foot (illustration flat).

Inspiré du style « Football player Avatars » (nikibd, Dribbble) — créations
originales Stats Foot, sans copie des assets protégés.
"""

from __future__ import annotations

from pathlib import Path

DOSSIER_SORTIE = Path(__file__).resolve().parents[1] / "site" / "frontend" / "public" / "avatars"

# (id, libelle, fond, peau, cheveux, style_cheveux, maillot, accent_maillot, extras)
CONFIGS: list[tuple[str, str, str, str, str, str, str, str, str]] = [
    ("joueur-foot-01", "Attaquant rouge", "#dc2626", "#c68642", "#1a1a1a", "court", "#ef4444", "#ffffff", ""),
    ("joueur-foot-02", "Milieu bleu", "#1d4ed8", "#8d5524", "#2c1810", "frisé", "#2563eb", "#fbbf24", ""),
    ("joueur-foot-03", "Défenseur vert", "#15803d", "#e0ac69", "#4a3728", "court", "#22c55e", "#ffffff", "barbe"),
    ("joueur-foot-04", "Gardien jaune", "#ca8a04", "#f1c27d", "#1a1a1a", "rasé", "#eab308", "#1e293b", "gants"),
    ("joueur-foot-05", "Capitaine blanc", "#475569", "#c68642", "#1a1a1a", "bandeau", "#f8fafc", "#dc2626", "brassard"),
    ("joueur-foot-06", "Ailier violet", "#7c3aed", "#6b4423", "#1a1a1a", "afro", "#8b5cf6", "#ffffff", ""),
    ("joueur-foot-07", "Polyvalent orange", "#ea580c", "#ffdbac", "#d4a017", "mèches", "#f97316", "#1e293b", ""),
    ("joueur-foot-08", "Stopper noir", "#0f172a", "#5c3317", "#1a1a1a", "court", "#334155", "#22d3ee", ""),
    ("joueur-foot-09", "Meneur rose", "#db2777", "#e0ac69", "#8b4513", "long", "#ec4899", "#ffffff", ""),
    ("joueur-foot-10", "Jeune prodige", "#0891b2", "#ffdbac", "#2c1810", "court", "#06b6d4", "#facc15", ""),
    ("joueur-foot-11", "Vétéran", "#78716c", "#c68642", "#6b6b6b", "calvitie", "#a8a29e", "#1e40af", "barbe"),
    ("joueur-foot-12", "Star dorée", "#b45309", "#8d5524", "#1a1a1a", "mohawk", "#f59e0b", "#ffffff", "bandeau"),
]


def _cheveux(style: str, couleur: str) -> str:
    if style == "court":
        return f'<ellipse cx="64" cy="38" rx="28" ry="14" fill="{couleur}"/>'
    if style == "frisé":
        return (
            f'<circle cx="48" cy="36" r="8" fill="{couleur}"/>'
            f'<circle cx="64" cy="32" r="9" fill="{couleur}"/>'
            f'<circle cx="80" cy="36" r="8" fill="{couleur}"/>'
            f'<ellipse cx="64" cy="40" rx="26" ry="12" fill="{couleur}"/>'
        )
    if style == "rasé":
        return f'<ellipse cx="64" cy="40" rx="26" ry="8" fill="{couleur}" opacity="0.3"/>'
    if style == "bandeau":
        return (
            f'<ellipse cx="64" cy="38" rx="28" ry="14" fill="{couleur}"/>'
            f'<rect x="36" y="34" width="56" height="8" rx="2" fill="#ef4444"/>'
        )
    if style == "afro":
        return (
            f'<circle cx="50" cy="34" r="10" fill="{couleur}"/>'
            f'<circle cx="64" cy="30" r="12" fill="{couleur}"/>'
            f'<circle cx="78" cy="34" r="10" fill="{couleur}"/>'
            f'<circle cx="56" cy="42" r="9" fill="{couleur}"/>'
            f'<circle cx="72" cy="42" r="9" fill="{couleur}"/>'
        )
    if style == "mèches":
        return (
            f'<ellipse cx="64" cy="36" rx="28" ry="14" fill="{couleur}"/>'
            f'<path d="M44 38 Q48 24 52 36" fill="{couleur}"/>'
            f'<path d="M56 34 Q60 22 64 34" fill="{couleur}"/>'
            f'<path d="M68 34 Q72 22 76 34" fill="{couleur}"/>'
        )
    if style == "long":
        return (
            f'<ellipse cx="64" cy="36" rx="28" ry="14" fill="{couleur}"/>'
            f'<path d="M38 40 Q36 58 42 68 Q64 72 86 68 Q92 58 90 40" fill="{couleur}"/>'
        )
    if style == "calvitie":
        return f'<ellipse cx="64" cy="42" rx="24" ry="10" fill="{couleur}" opacity="0.25"/>'
    if style == "mohawk":
        return (
            f'<ellipse cx="64" cy="40" rx="26" ry="10" fill="{couleur}" opacity="0.4"/>'
            f'<path d="M58 28 L64 14 L70 28 Z" fill="{couleur}"/>'
            f'<rect x="61" y="14" width="6" height="18" fill="{couleur}"/>'
        )
    return f'<ellipse cx="64" cy="38" rx="28" ry="14" fill="{couleur}"/>'


def _extras(extras: str) -> str:
    if extras == "barbe":
        return (
            '<path d="M48 58 Q64 72 80 58 Q78 66 64 70 Q50 66 48 58" fill="#3d2314" opacity="0.7"/>'
        )
    if extras == "gants":
        return (
            '<rect x="28" y="88" width="14" height="18" rx="4" fill="#facc15" stroke="#1e293b" stroke-width="1.5"/>'
            '<rect x="86" y="88" width="14" height="18" rx="4" fill="#facc15" stroke="#1e293b" stroke-width="1.5"/>'
        )
    if extras == "brassard":
        return '<rect x="82" y="78" width="10" height="14" rx="2" fill="#dc2626" stroke="#ffffff" stroke-width="1"/>'
    return ""


def generer_svg(
    libelle: str,
    fond: str,
    peau: str,
    cheveux: str,
    style_cheveux: str,
    maillot: str,
    accent: str,
    extras: str,
) -> str:
    ombre = "rgba(0,0,0,0.12)"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" role="img" aria-label="{libelle}">
  <defs>
    <clipPath id="cercle"><circle cx="64" cy="64" r="62"/></clipPath>
  </defs>
  <circle cx="64" cy="64" r="62" fill="{fond}"/>
  <g clip-path="url(#cercle)">
    <ellipse cx="64" cy="118" rx="40" ry="12" fill="{ombre}"/>
    <path d="M32 128 L96 128 L88 92 Q64 84 40 92 Z" fill="{maillot}"/>
    <path d="M52 92 L76 92 L74 128 L54 128 Z" fill="{accent}" opacity="0.35"/>
    <path d="M58 92 Q64 88 70 92" fill="none" stroke="{accent}" stroke-width="2"/>
    <circle cx="64" cy="56" r="24" fill="{peau}"/>
    <ellipse cx="64" cy="62" rx="20" ry="16" fill="{peau}"/>
    {_cheveux(style_cheveux, cheveux)}
    <ellipse cx="54" cy="54" rx="3" ry="4" fill="#1e293b"/>
    <ellipse cx="74" cy="54" rx="3" ry="4" fill="#1e293b"/>
    <circle cx="55" cy="53" r="1" fill="#ffffff"/>
    <circle cx="75" cy="53" r="1" fill="#ffffff"/>
    <path d="M58 64 Q64 68 70 64" fill="none" stroke="#b45309" stroke-width="1.5" stroke-linecap="round"/>
    <ellipse cx="48" cy="60" rx="4" ry="2.5" fill="#e11d48" opacity="0.25"/>
    <ellipse cx="80" cy="60" rx="4" ry="2.5" fill="#e11d48" opacity="0.25"/>
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
