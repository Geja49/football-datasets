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

export function moyenneListe(valeurs) {
  const liste = (valeurs || []).map(nombre).filter((n) => Number.isFinite(n));
  if (!liste.length) return 0;
  return liste.reduce((s, v) => s + v, 0) / liste.length;
}

export function medianeListe(valeurs) {
  const liste = (valeurs || []).map(nombre).filter((n) => Number.isFinite(n)).sort((a, b) => a - b);
  if (!liste.length) return 0;
  const milieu = Math.floor(liste.length / 2);
  if (liste.length % 2) return liste[milieu];
  return (liste[milieu - 1] + liste[milieu]) / 2;
}

function texteMesure(cle, valeur) {
  if (cle === "forme") return `${Math.round(valeur)} pts`;
  if (cle === "xg" || cle === "xa") return valeur.toFixed(1);
  if (cle === "xg_match" || cle === "xg_encaisse" || cle === "defense") {
    return valeur.toFixed(2);
  }
  if (cle === "buts" || cle === "tirs") {
    if (Math.abs(valeur - Math.round(valeur)) > 0.001) return valeur.toFixed(2);
    return String(Math.round(valeur));
  }
  return String(Math.round(valeur));
}

function texteMesureLigue(cle, valeur) {
  if (cle === "forme") return valeur.toFixed(1);
  if (cle === "xg" || cle === "xa") return valeur.toFixed(1);
  if (
    cle === "xg_match" ||
    cle === "xg_encaisse" ||
    cle === "defense" ||
    cle === "buts" ||
    cle === "tirs"
  ) {
    return valeur.toFixed(2);
  }
  return String(Math.round(valeur * 10) / 10);
}

/**
 * Écart simple vs référence ligue (moyenne).
 * Pour les métriques inversées, le jugement « au-dessus » suit le score (meilleur).
 */
export function texteEcart(valeur, reference, { inverser = false, cle = "" } = {}) {
  if (reference == null || !Number.isFinite(Number(reference))) return "";
  const v = nombre(valeur);
  const r = nombre(reference);
  const delta = v - r;
  const abs = Math.abs(delta);
  let chiffre;
  if (cle === "forme") chiffre = (delta >= 0 ? "+" : "") + Math.round(delta);
  else if (cle === "minutes" || (Number.isInteger(v) && Number.isInteger(r) && abs >= 1)) {
    chiffre = (delta >= 0 ? "+" : "") + Math.round(delta);
  } else if (abs >= 10) chiffre = (delta >= 0 ? "+" : "") + Math.round(delta);
  else chiffre = (delta >= 0 ? "+" : "") + delta.toFixed(1);

  const meilleur = inverser ? delta < 0 : delta > 0;
  const neutre = Math.abs(delta) < 0.05 || (cle === "forme" && Math.abs(delta) < 0.5);
  const jugement = neutre ? "proche de la moyenne" : meilleur ? "au-dessus" : "en-dessous";
  return `${chiffre} vs moyenne · ${jugement}`;
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

export function totalHistogramme(histogramme) {
  return (histogramme || []).reduce((s, b) => s + (b.n || 0), 0);
}

/** Position médiane sur l’échelle 0–1 (classe au milieu du massif). */
export function scoreMedianHistogramme(histogramme) {
  const bins = histogramme || [];
  const total = totalHistogramme(bins);
  if (!total || !bins.length) return 0.5;
  let cumul = 0;
  const cible = total / 2;
  for (let i = 0; i < bins.length; i += 1) {
    cumul += bins[i].n || 0;
    if (cumul >= cible) return (i + 0.5) / bins.length;
  }
  return 0.5;
}

/** Percentile approximatif (0–100) : part de la distribution à gauche du score. */
export function percentileDepuisScore(score, histogramme) {
  const s = Math.max(0, Math.min(1, score || 0));
  const bins = histogramme || [];
  const total = totalHistogramme(bins);
  if (!total || !bins.length) return Math.round(s * 100);
  const idx = Math.min(bins.length - 1, Math.floor(s * bins.length));
  let sous = 0;
  for (let i = 0; i < idx; i += 1) sous += bins[i].n || 0;
  sous += (bins[idx].n || 0) * 0.5;
  return Math.round((sous / total) * 100);
}

/** Rang approximatif (1 = meilleur) à partir de l’histogramme. */
export function rangDepuisScore(score, histogramme) {
  const bins = histogramme || [];
  const total = totalHistogramme(bins);
  if (!total || !bins.length) return null;
  const s = Math.max(0, Math.min(1, score || 0));
  const idx = Math.min(bins.length - 1, Math.floor(s * bins.length));
  let meilleurs = 0;
  for (let i = idx + 1; i < bins.length; i += 1) meilleurs += bins[i].n || 0;
  meilleurs += Math.floor((bins[idx].n || 0) / 2);
  return { rang: Math.max(1, meilleurs + 1), total };
}

/**
 * Texte de lecture type analytics foot : « Top 20 % » ou « 8e / 20 ».
 * Une seule info claire pour compléter la courbe.
 */
export function textePosition(score, histogramme) {
  const pct = percentileDepuisScore(score, histogramme);
  const detail = rangDepuisScore(score, histogramme);
  if (pct >= 80) {
    const top = Math.max(1, 100 - pct);
    return `Top ${top} %`;
  }
  if (detail && detail.total >= 4) {
    return `${detail.rang}e / ${detail.total}`;
  }
  if (pct <= 20) return `Bas ${pct} %`;
  return `${pct}e centile`;
}

function valeurReferenceLigue(repere) {
  if (!repere) return null;
  if (repere.moyenne != null && Number.isFinite(Number(repere.moyenne))) {
    return nombre(repere.moyenne);
  }
  if (repere.mediane != null && Number.isFinite(Number(repere.mediane))) {
    return nombre(repere.mediane);
  }
  return null;
}

function enrichirAxe(axe) {
  const score = Math.max(0, Math.min(1, axe.score || 0));
  const histogramme = axe.histogramme || [];
  const inverser = !!axe.inverser;
  const valeurLigue = axe.valeurLigue;
  let scoreLigue = axe.scoreLigue;
  if (scoreLigue == null && valeurLigue != null && axe.plafond) {
    const direct = scoreRelatif(valeurLigue, axe.plafond);
    scoreLigue = inverser ? 1 - direct : direct;
  }
  // Trait « médiane ligue » aligné sur la valeur de référence (pas seulement le bin).
  const scoreMedian =
    scoreLigue != null ? scoreLigue : scoreMedianHistogramme(histogramme);
  const texteEcartLigne =
    valeurLigue != null
      ? texteEcart(axe.valeur, valeurLigue, { inverser, cle: axe.cle })
      : "";
  return {
    ...axe,
    score,
    scoreMedian,
    scoreLigue: scoreLigue != null ? Math.max(0, Math.min(1, scoreLigue)) : null,
    valeurLigue: valeurLigue != null ? valeurLigue : null,
    texteLigue:
      valeurLigue != null
        ? axe.texteLigue || texteMesureLigue(axe.cle, valeurLigue)
        : "",
    texteEcart: texteEcartLigne,
    percentile: percentileDepuisScore(score, histogramme),
    textePosition: textePosition(score, histogramme),
  };
}

/** Polygone radar de référence (moyenne ligue). */
export function axesComparaisonLigue(axes) {
  const liste = axes || [];
  if (!liste.length) return [];
  // Au moins une vraie moyenne ligue ; sinon pas de second polygone.
  if (!liste.some((a) => a.scoreLigue != null)) return [];
  return liste.map((a) => ({
    score: a.scoreLigue != null ? a.scoreLigue : a.scoreMedian ?? 0.5,
    libelle: a.libelle,
    texte: a.texteLigue || "",
  }));
}

/**
 * Fusionne deux profils (même axes) : A reste le sujet, B devient la référence
 * (polygone pointillé + losange densités), comme vs moyenne ligue.
 */
export function fusionnerComparaisonDirecte(axesSujet, axesAutre) {
  const parCle = {};
  for (const axe of axesAutre || []) {
    if (axe?.cle) parCle[axe.cle] = axe;
  }
  return (axesSujet || []).map((axe) => {
    const autre = parCle[axe.cle];
    if (!autre) {
      return enrichirAxe({ ...axe, valeurLigue: null, scoreLigue: null, texteLigue: "" });
    }
    const enrichi = enrichirAxe({
      ...axe,
      valeurLigue: autre.valeur,
      scoreLigue: autre.score,
      texteLigue: autre.texte,
    });
    if (enrichi.texteEcart) {
      enrichi.texteEcart = enrichi.texteEcart.replace("vs moyenne", "écart");
    }
    return enrichi;
  });
}

export function axesDepuisJoueur(ligne, reperes) {
  const parCle = {};
  for (const axe of reperes?.axes || []) parCle[axe.cle] = axe;
  return AXES_JOUEUR.map((def) => {
    const repere = parCle[def.cle];
    const valeur = nombre(ligne?.[def.cle]);
    const plafond = nombre(repere?.plafond) || PLAFONDS_JOUEUR[def.cle] || 1;
    const valeurLigue = valeurReferenceLigue(repere);
    return enrichirAxe({
      libelle: def.libelle,
      cle: def.cle,
      valeur,
      texte: texteMesure(def.cle, valeur),
      score: scoreRelatif(valeur, plafond),
      plafond,
      valeurLigue,
      histogramme: repere?.histogramme || [],
    });
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

export function axesDepuisEquipe(matchs, nomEquipe, aliasEquipe = [], reperes = null) {
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

  const parCle = {};
  for (const axe of reperes?.axes || []) parCle[axe.cle] = axe;
  const aLigue = Object.keys(parCle).length > 0;

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
      const repere = parCle[axe.cle];
      const valeurLigue = valeurReferenceLigue(repere);
      const plafond = nombre(repere?.plafond) || axe.plafond;
      const scoreDirect = scoreRelatif(axe.valeur, plafond);
      const plafondHisto = axe.plafondHisto || axe.plafond;

      if (aLigue && repere?.histogramme?.length) {
        return enrichirAxe({
          libelle: axe.libelle,
          cle: axe.cle,
          valeur: axe.valeur,
          texte: axe.cle === "forme" ? `${Math.round(axe.valeur)} pts` : axe.valeur.toFixed(2),
          score: axe.inverser ? 1 - scoreDirect : scoreDirect,
          plafond,
          inverser: axe.inverser,
          valeurLigue,
          histogramme: repere.histogramme,
        });
      }

      const brut = axe.brut.length ? axe.brut : [0];
      return enrichirAxe({
        libelle: axe.libelle,
        cle: axe.cle,
        valeur: axe.valeur,
        texte: axe.cle === "forme" ? `${Math.round(axe.valeur)} pts` : axe.valeur.toFixed(2),
        score: axe.inverser ? 1 - scoreDirect : scoreDirect,
        plafond,
        inverser: axe.inverser,
        histogramme: histogrammeLocal(
          axe.inverser ? brut.map((v) => plafondHisto - Math.min(v, plafondHisto)) : brut,
          plafondHisto,
        ),
      });
    });
}
