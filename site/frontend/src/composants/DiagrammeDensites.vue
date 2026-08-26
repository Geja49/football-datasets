<script setup>
import { computed } from "vue";

const props = defineProps({
  lignes: { type: Array, default: () => [] },
  /** « Club » ou « Joueur » — légende du marqueur plein. */
  libelleSujet: { type: String, default: "Valeur" },
  /** Légende du losange (moyenne ligue ou adversaire). */
  libelleComparaison: { type: String, default: "Moyenne ligue" },
});

const largeur = 320;
const margeGauche = 8;
const margeDroite = 8;
const piste = largeur - margeGauche - margeDroite;
const margeHaut = 8;
const hauteur = 36;
const yAxe = margeHaut + hauteur;
const hauteurLabels = 14;
const hauteurSvg = yAxe + hauteurLabels;

function pointsDensite(histogramme) {
  const bins = histogramme || [];
  if (!bins.length) return [];
  const maxN = Math.max(1, ...bins.map((b) => b.n || 0));
  const pas = piste / Math.max(bins.length - 1, 1);
  return bins.map((b, i) => ({
    x: margeGauche + i * pas,
    y: yAxe - ((b.n || 0) / maxN) * (hauteur - 6),
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
  if (!points.length) return yAxe - 4;
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

const aReferenceLigue = computed(() =>
  props.lignes.some((l) => l.scoreLigue != null || l.valeurLigue != null),
);

const rangees = computed(() =>
  props.lignes.map((ligne) => {
    const score = Math.max(0, Math.min(1, ligne.score || 0));
    const scoreLigue =
      ligne.scoreLigue != null
        ? Math.max(0, Math.min(1, ligne.scoreLigue))
        : Math.max(0, Math.min(1, ligne.scoreMedian ?? 0.5));
    const points = pointsDensite(ligne.histogramme);
    const xMarqueur = margeGauche + score * piste;
    const xLigue = margeGauche + scoreLigue * piste;
    const yMarqueur = ySurCourbe(points, xMarqueur);
    const yLigue = ySurCourbe(points, xLigue);
    return {
      libelle: ligne.libelle,
      texte: ligne.texte,
      texteLigue: ligne.texteLigue || "",
      texteEcart: ligne.texteEcart || "",
      textePosition: ligne.textePosition || "",
      score,
      scoreLigue,
      xMarqueur,
      xLigue,
      yMarqueur,
      yLigue,
      chemin: cheminAire(points),
      crete: cheminCrete(points),
      aLigue: ligne.scoreLigue != null || ligne.valeurLigue != null,
    };
  }),
);
</script>

<template>
  <div class="diagramme-densites" v-if="rangees.length">
    <p class="legende-densite">
        Courbe = répartition dans le championnat.
      <template v-if="aReferenceLigue">
        Trait pointillé + losange = {{ libelleComparaison.toLowerCase() }} · point = {{ libelleSujet.toLowerCase() }}.
      </template>
      <template v-else>
        Trait pointillé = médiane · point = {{ libelleSujet.toLowerCase() }}.
      </template>
    </p>
    <div v-if="aReferenceLigue" class="puces-legende" aria-hidden="true">
      <span class="puce-sujet">{{ libelleSujet }}</span>
      <span class="puce-ligue">{{ libelleComparaison }}</span>
    </div>
    <div class="echelle-densite" aria-hidden="true">
      <span>Faible</span>
      <span>{{ aReferenceLigue ? libelleComparaison : "Médiane" }}</span>
      <span>Fort</span>
    </div>
    <div v-for="rangee in rangees" :key="rangee.libelle" class="rangee-densite">
      <div class="entete-densite">
        <span class="libelle-densite">{{ rangee.libelle }}</span>
        <div class="infos-densite">
          <strong class="valeur-ligne">{{ rangee.texte }}</strong>
          <span v-if="rangee.texteLigue" class="ligue-ligne">{{ libelleComparaison.toLowerCase().startsWith('moy') ? 'moy.' : 'vs' }} {{ rangee.texteLigue }}</span>
          <span v-if="rangee.textePosition" class="position-ligne">{{ rangee.textePosition }}</span>
        </div>
      </div>
      <p v-if="rangee.texteEcart" class="ecart-densite">{{ rangee.texteEcart }}</p>
      <svg
        :viewBox="`0 0 ${largeur} ${hauteurSvg}`"
        role="img"
        :aria-label="`${rangee.libelle} : ${rangee.texte}${rangee.texteEcart ? ', ' + rangee.texteEcart : ''}${rangee.textePosition ? ', ' + rangee.textePosition : ''}`"
      >
        <line
          class="median-densite"
          :x1="rangee.xLigue"
          :y1="margeHaut"
          :x2="rangee.xLigue"
          :y2="yAxe"
        />
        <path class="aire-densite" :d="rangee.chemin" />
        <path class="crete-densite" :d="rangee.crete" />
        <line
          class="axe-densite"
          :x1="margeGauche"
          :y1="yAxe"
          :x2="margeGauche + piste"
          :y2="yAxe"
        />
        <!-- Repère moyenne ligue (losange) -->
        <line
          v-if="rangee.aLigue"
          class="tige-ligue"
          :x1="rangee.xLigue"
          :y1="yAxe"
          :x2="rangee.xLigue"
          :y2="rangee.yLigue"
        />
        <polygon
          v-if="rangee.aLigue"
          class="marqueur-ligue"
          :points="`${rangee.xLigue},${rangee.yLigue - 5.5} ${rangee.xLigue + 5.5},${rangee.yLigue} ${rangee.xLigue},${rangee.yLigue + 5.5} ${rangee.xLigue - 5.5},${rangee.yLigue}`"
        />
        <!-- Repère club / joueur (point) -->
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
          r="5.5"
        />
        <text class="label-axe-densite" :x="margeGauche" :y="yAxe + 11" text-anchor="start">faible</text>
        <text
          class="label-axe-densite"
          :x="margeGauche + piste"
          :y="yAxe + 11"
          text-anchor="end"
        >
          fort
        </text>
      </svg>
    </div>
  </div>
</template>
