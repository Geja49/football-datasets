export const AXES_JOUEUR = [
  { cle: "buts", libelle: "Buts" },
  { cle: "xg", libelle: "xG" },
  { cle: "passes_decisives", libelle: "Passes D." },
  { cle: "xa", libelle: "xA" },
  { cle: "tirs", libelle: "Tirs" },
  { cle: "minutes", libelle: "Minutes" },
];

const PLAFOND_BUTS_MATCH = 3;
const PLAFOND_XG_MATCH = 2.5;
const PLAFOND_TIRS_MATCH = 18;
const PLAFOND_FORME = 15;

export function nombre(valeur) {
  const n = Number(valeur);
  return Number.isFinite(n) ? n : 0;
}

export function scoreRelatif(valeur, plafond) {
  if (!plafond || plafond <= 0) return 0;
  return Math.min(1, Math.max(0, nombre(valeur) / plafond));
}

function texteMesure(cle, valeur) {
  if (cle === "xg" || cle === "xa") return valeur.toFixed(1);
  if (cle.endsWith("_match") || cle === "xg_encaisse") return valeur.toFixed(2);
  return String(Math.round(valeur));
}

export const PLAFONDS_JOUEUR = {
  buts: 30,
  xg: 25,
  passes_decisives: 15,
  xa: 12,
  tirs: 120,
  minutes: 3420,
};

export function histogrammeLocal(valeurs, plafond, nb = 12) {
  const comptes = Array(nb).fill(0);
  if (!plafond || plafond <= 0) return comptes.map((n) => ({ n }));
  for (const v of valeurs) {
    const ratio = Math.min(Math.max(nombre(v) / plafond, 0), 0.9999);
    comptes[Math.floor(ratio * nb)] += 1;
  }
  return comptes.map((n) => ({ n }));
}

export function axesDepuisJoueur(ligne, reperes) {
  const parCle = {};
  for (const axe of reperes?.axes || []) parCle[axe.cle] = axe;
  return AXES_JOUEUR.map((def) => {
    const repere = parCle[def.cle];
    const valeur = nombre(ligne?.[def.cle]);
    const plafond = nombre(repere?.plafond) || PLAFONDS_JOUEUR[def.cle] || 1;
    return {
      libelle: def.libelle,
      cle: def.cle,
      valeur,
      texte: texteMesure(def.cle, valeur),
      score: scoreRelatif(valeur, plafond),
      histogramme: repere?.histogramme || [],
    };
  });
}

function coteMatch(match, noms) {
  const domicile = noms.has(match.domicile);
  const aXg = match.xg_domicile != null && match.xg_exterieur != null;
  const aTirs = match.tirs_domicile != null && match.tirs_exterieur != null;
  return {
    buts: nombre(domicile ? match.buts_domicile : match.buts_exterieur),
    contre: nombre(domicile ? match.buts_exterieur : match.buts_domicile),
    xg: aXg ? nombre(domicile ? match.xg_domicile : match.xg_exterieur) : null,
    xgContre: aXg ? nombre(domicile ? match.xg_exterieur : match.xg_domicile) : null,
    tirs: aTirs ? nombre(domicile ? match.tirs_domicile : match.tirs_exterieur) : null,
    victoire:
      nombre(domicile ? match.buts_domicile : match.buts_exterieur) >
      nombre(domicile ? match.buts_exterieur : match.buts_domicile),
    nul:
      nombre(domicile ? match.buts_domicile : match.buts_exterieur) ===
      nombre(domicile ? match.buts_exterieur : match.buts_domicile),
  };
}

export function axesDepuisEquipe(matchs, nomEquipe, aliasEquipe = []) {
  const noms = new Set([nomEquipe, ...(aliasEquipe || [])].filter(Boolean));
  const joues = (matchs || []).filter(
    (m) =>
      m.joue &&
      m.buts_domicile != null &&
      m.buts_exterieur != null &&
      (noms.has(m.domicile) || noms.has(m.exterieur)),
  );
  if (!joues.length) return [];

  const cotes = joues.map((m) => coteMatch(m, noms));
  const nb = cotes.length;
  const buts = cotes.reduce((s, c) => s + c.buts, 0) / nb;
  const contre = cotes.reduce((s, c) => s + c.contre, 0) / nb;
  const avecXg = cotes.filter((c) => c.xg != null);
  const avecTirs = cotes.filter((c) => c.tirs != null);
  const xg = avecXg.length ? avecXg.reduce((s, c) => s + c.xg, 0) / avecXg.length : 0;
  const xgContre = avecXg.length
    ? avecXg.reduce((s, c) => s + (c.xgContre || 0), 0) / avecXg.length
    : 0;
  const tirs = avecTirs.length ? avecTirs.reduce((s, c) => s + c.tirs, 0) / avecTirs.length : 0;

  const recents = [...joues].sort((a, b) => (b.date || "").localeCompare(a.date || "")).slice(0, 5);
  const pointsRecents = recents.map((m) => {
    const c = coteMatch(m, noms);
    if (c.victoire) return 3;
    if (c.nul) return 1;
    return 0;
  });
  const forme = pointsRecents.reduce((s, p) => s + p, 0);

  const series = [
    {
      libelle: "Buts",
      cle: "buts",
      valeur: buts,
      plafond: PLAFOND_BUTS_MATCH,
      brut: cotes.map((c) => c.buts),
      inverser: false,
    },
    {
      libelle: "xG",
      cle: "xg_match",
      valeur: xg,
      plafond: PLAFOND_XG_MATCH,
      brut: avecXg.map((c) => c.xg),
      inverser: false,
      masquer: !avecXg.length,
    },
    {
      libelle: "Tirs",
      cle: "tirs",
      valeur: tirs,
      plafond: PLAFOND_TIRS_MATCH,
      brut: avecTirs.map((c) => c.tirs),
      inverser: false,
      masquer: !avecTirs.length,
    },
    {
      libelle: "Forme",
      cle: "forme",
      valeur: forme,
      plafond: PLAFOND_FORME,
      brut: pointsRecents,
      plafondHisto: 3,
      inverser: false,
    },
    {
      libelle: "Solidité",
      cle: "defense",
      valeur: contre,
      plafond: PLAFOND_BUTS_MATCH,
      brut: cotes.map((c) => c.contre),
      inverser: true,
    },
    {
      libelle: "xG encaissés",
      cle: "xg_encaisse",
      valeur: xgContre,
      plafond: PLAFOND_XG_MATCH,
      brut: avecXg.map((c) => c.xgContre || 0),
      inverser: true,
      masquer: !avecXg.length,
    },
  ];

  return series
    .filter((axe) => !axe.masquer)
    .map((axe) => {
      const brut = axe.brut.length ? axe.brut : [0];
      const scoreDirect = scoreRelatif(axe.valeur, axe.plafond);
      const plafondHisto = axe.plafondHisto || axe.plafond;
      return {
        libelle: axe.libelle,
        cle: axe.cle,
        valeur: axe.valeur,
        texte: axe.cle === "forme" ? `${Math.round(axe.valeur)} pts` : axe.valeur.toFixed(2),
        score: axe.inverser ? 1 - scoreDirect : scoreDirect,
        histogramme: histogrammeLocal(
          axe.inverser ? brut.map((v) => plafondHisto - Math.min(v, plafondHisto)) : brut,
          plafondHisto,
        ),
      };
    });
}
