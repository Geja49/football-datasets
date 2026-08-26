<script setup>
import { computed } from "vue";

const props = defineProps({
  axes: { type: Array, default: () => [] },
  comparaison: { type: Array, default: () => [] },
  libelleSujet: { type: String, default: "Valeur" },
  libelleComparaison: { type: String, default: "Moyenne ligue" },
});

const taille = 420;
const centre = 210;
const rayon = 118;
const niveaux = [0.25, 0.5, 0.75, 1];

function point(index, score, n, horsLimite = false) {
  const angle = -Math.PI / 2 + (index * 2 * Math.PI) / n;
  const facteur = horsLimite ? score : Math.max(0, Math.min(1, score));
  const r = facteur * rayon;
  return {
    x: centre + r * Math.cos(angle),
    y: centre + r * Math.sin(angle),
    angle,
  };
}

const anneaux = computed(() =>
  niveaux.map((p) => ({
    r: p * rayon,
    etiquette: Math.round(p * 100),
  })),
);

const rayons = computed(() => {
  const n = props.axes.length || 1;
  return props.axes.map((_, i) => {
    const bout = point(i, 1, n);
    return { x2: bout.x, y2: bout.y };
  });
});

function polygone(liste) {
  const n = liste.length;
  if (!n) return "";
  return liste
    .map((axe, i) => {
      const p = point(i, axe.score || 0, n);
      return `${p.x},${p.y}`;
    })
    .join(" ");
}

const forme = computed(() => polygone(props.axes));
const aComparaison = computed(
  () => props.comparaison.length === props.axes.length && props.axes.length > 0,
);
const formeComparaison = computed(() =>
  aComparaison.value ? polygone(props.comparaison) : "",
);

const noeudsComparaison = computed(() => {
  if (!aComparaison.value) return [];
  const n = props.comparaison.length;
  return props.comparaison.map((axe, i) => {
    const p = point(i, axe.score || 0, n);
    return { i, x: p.x, y: p.y };
  });
});

/** Étiquettes d’échelle sur l’axe du haut (0–100). */
const etiquettesEchelle = computed(() =>
  [0.5, 1].map((p) => ({
    y: centre - p * rayon,
    texte: String(Math.round(p * 100)),
  })),
);

const etiquettes = computed(() => {
  const n = props.axes.length;
  return props.axes.map((axe, i) => {
    const p = point(i, 1.38, n, true);
    const sommet = point(i, axe.score || 0, n);
    const cos = Math.cos(p.angle);
    const sin = Math.sin(p.angle);
    let ancre = "middle";
    if (cos > 0.4) ancre = "start";
    if (cos < -0.4) ancre = "end";
    let dyLibelle = 0;
    if (sin > 0.55) dyLibelle = 4;
    if (sin < -0.55) dyLibelle = -2;
    return {
      i,
      x: p.x,
      y: p.y + dyLibelle,
      px: sommet.x,
      py: sommet.y,
      ancre,
      libelle: axe.libelle,
      texte: axe.texte,
      textePosition: axe.textePosition || "",
      texteEcart: axe.texteEcart || "",
    };
  });
});
</script>

<template>
  <div class="conteneur-radar" v-if="axes.length">
    <p class="legende-radar">
      Échelle 0–100 (relatif au plafond) · valeur sous chaque axe
    </p>
    <div v-if="aComparaison" class="puces-legende" aria-hidden="true">
      <span class="puce-sujet">{{ libelleSujet }}</span>
      <span class="puce-ligue">{{ libelleComparaison }}</span>
    </div>
    <svg
      class="diagramme-radar"
      :viewBox="`0 0 ${taille} ${taille}`"
      role="img"
      aria-label="Radar des statistiques"
    >
      <g class="fond-radar">
        <circle
          v-for="anneau in anneaux"
          :key="anneau.r"
          class="anneau"
          :cx="centre"
          :cy="centre"
          :r="anneau.r"
        />
        <line
          v-for="(rayonLigne, i) in rayons"
          :key="'r' + i"
          class="rayon"
          :x1="centre"
          :y1="centre"
          :x2="rayonLigne.x2"
          :y2="rayonLigne.y2"
        />
        <text
          v-for="tick in etiquettesEchelle"
          :key="'ech' + tick.texte"
          class="echelle-radar"
          :x="centre + 4"
          :y="tick.y + 3"
        >
          {{ tick.texte }}
        </text>
      </g>
      <polygon v-if="formeComparaison" class="polygone-comparaison" :points="formeComparaison" />
      <circle
        v-for="noeud in noeudsComparaison"
        :key="'cl' + noeud.i"
        class="noeud-comparaison"
        :cx="noeud.x"
        :cy="noeud.y"
        r="3.5"
      />
      <polygon class="polygone" :points="forme" />
      <circle
        v-for="noeud in etiquettes"
        :key="'p' + noeud.i"
        class="noeud"
        :cx="noeud.px"
        :cy="noeud.py"
        r="4.5"
      />
      <text
        v-for="etiquette in etiquettes"
        :key="'e' + etiquette.i"
        class="etiquette-axe"
        :x="etiquette.x"
        :y="etiquette.y"
        :text-anchor="etiquette.ancre"
      >
        <tspan :x="etiquette.x" dy="0">{{ etiquette.libelle }}</tspan>
        <tspan class="valeur-axe" :x="etiquette.x" dy="13">{{ etiquette.texte }}</tspan>
        <tspan
          v-if="etiquette.textePosition"
          class="position-axe"
          :x="etiquette.x"
          dy="12"
        >
          {{ etiquette.textePosition }}
        </tspan>
      </text>
    </svg>
  </div>
</template>
