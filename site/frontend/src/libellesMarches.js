/** Types cartons exclus du bilan (aligné sur TYPES_MARCHES_CARTONS_BD côté API). */
export const TYPES_MARCHES_CARTONS = new Set([
  "cartons",
  "cartons_15",
  "cartons_15_dom",
  "cartons_15_ext",
  "cartons_jaunes",
  "cartons_over_1_5",
  "cartons_over_1_5_domicile",
  "cartons_over_1_5_exterieur",
]);

/** Libellés français pour les clés techniques (BD ou API). */
export const LIBELLES_TYPES_MARCHE = {
  victoire_1: "Victoire domicile",
  victoire_domicile: "Victoire domicile",
  victoire_2: "Victoire extérieur",
  victoire_exterieur: "Victoire extérieur",
  btts: "Les deux équipes marquent",
  over_15: "+1,5 buts",
  over_1_5: "+1,5 buts",
  over_15_dom: "Domicile +1,5 buts",
  over_1_5_domicile: "Domicile +1,5 buts",
  over_15_ext: "Extérieur +1,5 buts",
  over_1_5_exterieur: "Extérieur +1,5 buts",
  over_25: "+2,5 buts",
  over_2_5: "+2,5 buts",
  corners_over_95: "Corners +9,5",
};

/** Ordre d’affichage des marchés dans le bilan. */
export const ORDRE_TYPES_MARCHE = [
  "victoire_1",
  "victoire_domicile",
  "victoire_2",
  "victoire_exterieur",
  "btts",
  "over_25",
  "over_2_5",
  "over_15",
  "over_1_5",
  "over_15_dom",
  "over_1_5_domicile",
  "over_15_ext",
  "over_1_5_exterieur",
  "corners_over_95",
];

export function estMarcheCarton(type) {
  return TYPES_MARCHES_CARTONS.has(type);
}

export function libelleTypeMarche(type, libelleApi) {
  if (libelleApi) return libelleApi;
  return LIBELLES_TYPES_MARCHE[type] || type;
}

/** Paliers visuels pour le hit-rate (vert / orange / rouge). */
export function palierHitRate(taux, seuilHaute = 70) {
  if (taux == null) return "neutre";
  if (taux >= seuilHaute) return "haute";
  if (taux >= 50) return "moyenne";
  return "basse";
}

export function indiceTriMarche(type) {
  const idx = ORDRE_TYPES_MARCHE.indexOf(type);
  return idx >= 0 ? idx : 999;
}
