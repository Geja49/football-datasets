<script setup>
import { computed } from "vue";

const props = defineProps({
  axes: { type: Array, default: () => [] },
  comparaison: { type: Array, default: () => [] },
});

const taille = 400;
const centre = 200;
const rayon = 125;
const niveaux = [0.2, 0.4, 0.6, 0.8, 1];

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
const formeComparaison = computed(() =>
  props.comparaison.length === props.axes.length ? polygone(props.comparaison) : "",
);

const etiquettes = computed(() => {
  const n = props.axes.length;
  return props.axes.map((axe, i) => {
    const p = point(i, 1.32, n, true);
    const sommet = point(i, axe.score || 0, n);
    const cos = Math.cos(p.angle);
    let ancre = "middle";
    if (cos > 0.35) ancre = "start";
    if (cos < -0.35) ancre = "end";
    return {
      i,
      x: p.x,
      y: p.y,
      px: sommet.x,
      py: sommet.y,
      ancre,
      libelle: axe.libelle,
      texte: axe.texte,
    };
  });
});
</script>

<template>
  <svg
    v-if="axes.length"
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
    </g>
    <polygon v-if="formeComparaison" class="polygone-comparaison" :points="formeComparaison" />
    <polygon class="polygone" :points="forme" />
    <circle
      v-for="noeud in etiquettes"
      :key="'p' + noeud.i"
      class="noeud"
      :cx="noeud.px"
      :cy="noeud.py"
      r="4"
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
      <tspan :x="etiquette.x" dy="14">{{ etiquette.texte }}</tspan>
    </text>
  </svg>
</template>
