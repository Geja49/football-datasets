<script setup>
import { computed } from "vue";

const props = defineProps({
  lignes: { type: Array, default: () => [] },
});

const largeur = 280;
const margeHaut = 16;
const hauteur = 48;
const margeGauche = 4;
const piste = largeur - 8;
const yAxe = margeHaut + hauteur;
const hauteurSvg = yAxe + 6;

function pointsDensite(histogramme) {
  const bins = histogramme || [];
  if (!bins.length) return [];
  const maxN = Math.max(1, ...bins.map((b) => b.n || 0));
  const pas = piste / Math.max(bins.length - 1, 1);
  return bins.map((b, i) => ({
    x: margeGauche + i * pas,
    y: yAxe - ((b.n || 0) / maxN) * (hauteur - 10),
  }));
}

function lisser(points) {
  let d = "";
  for (let i = 1; i < points.length; i += 1) {
    const prec = points[i - 1];
    const cur = points[i];
    const cx = (prec.x + cur.x) / 2;
    d += ` C ${cx} ${prec.y}, ${cx} ${cur.y}, ${cur.x} ${cur.y}`;
  }
  return d;
}

function cheminAire(points) {
  if (!points.length) {
    return `M ${margeGauche} ${yAxe} L ${margeGauche + piste} ${yAxe}`;
  }
  return `M ${margeGauche} ${yAxe} L ${points[0].x} ${points[0].y}${lisser(points)} L ${margeGauche + piste} ${yAxe} Z`;
}

function cheminCrete(points) {
  if (!points.length) return "";
  return `M ${points[0].x} ${points[0].y}${lisser(points)}`;
}

function ySurCourbe(points, xMarqueur) {
  if (!points.length) return yAxe;
  if (xMarqueur <= points[0].x) return points[0].y;
  if (xMarqueur >= points[points.length - 1].x) return points[points.length - 1].y;
  let i = 0;
  while (i < points.length - 2 && points[i + 1].x < xMarqueur) i += 1;
  const prec = points[i];
  const cur = points[i + 1];
  const t = (xMarqueur - prec.x) / (cur.x - prec.x || 1);
  const u = 1 - t;
  return u * u * (1 + 2 * t) * prec.y + t * t * (3 - 2 * t) * cur.y;
}

const rangees = computed(() =>
  props.lignes.map((ligne, i) => {
    const score = Math.max(0, Math.min(1, ligne.score || 0));
    const points = pointsDensite(ligne.histogramme);
    const xMarqueur = margeGauche + score * piste;
    const yMarqueur = ySurCourbe(points, xMarqueur);
    const etiquetteADroite = xMarqueur < largeur - 56;
    return {
      i,
      libelle: ligne.libelle,
      texte: ligne.texte,
      score,
      xMarqueur,
      yMarqueur,
      chemin: cheminAire(points),
      crete: cheminCrete(points),
      xEtiquette: etiquetteADroite ? xMarqueur + 10 : xMarqueur - 10,
      ancreEtiquette: etiquetteADroite ? "start" : "end",
    };
  }),
);
</script>

<template>
  <div class="diagramme-densites" v-if="rangees.length">
    <p class="legende-densite">Gauche = plus faible, droite = plus fort dans la ligue</p>
    <div v-for="rangee in rangees" :key="rangee.libelle" class="rangee-densite">
      <div class="entete-densite">
        <span>{{ rangee.libelle }}</span>
        <strong>{{ rangee.texte }}</strong>
      </div>
      <svg :viewBox="`0 0 ${largeur} ${hauteurSvg}`" role="img" :aria-label="rangee.libelle">
        <path class="aire-densite" :d="rangee.chemin" />
        <path class="crete-densite" :d="rangee.crete" />
        <line
          class="axe-densite"
          :x1="margeGauche"
          :y1="yAxe"
          :x2="margeGauche + piste"
          :y2="yAxe"
        />
        <line
          class="tige-densite"
          :x1="rangee.xMarqueur"
          :y1="yAxe"
          :x2="rangee.xMarqueur"
          :y2="rangee.yMarqueur"
        />
        <circle
          class="marqueur-densite"
          :cx="rangee.xMarqueur"
          :cy="rangee.yMarqueur"
          r="6.5"
        />
        <text
          class="valeur-densite"
          :x="rangee.xEtiquette"
          :y="rangee.yMarqueur + 4"
          :text-anchor="rangee.ancreEtiquette"
        >
          {{ rangee.texte }}
        </text>
      </svg>
    </div>
  </div>
</template>
