<script setup>
import { computed, ref, watch } from "vue";

const props = defineProps({
  nom: { type: String, default: "" },
  urlPhoto: { type: String, default: "" },
  /** "mini" (listes) ou "grand" (fiche joueur) */
  taille: { type: String, default: "mini" },
  classeCss: { type: String, default: "" },
});

const cassee = ref(false);

watch(
  () => [props.nom, props.urlPhoto],
  () => {
    cassee.value = false;
  },
);

const initiale = computed(() => {
  const texte = (props.nom || "?").trim();
  return texte ? texte.slice(0, 1).toUpperCase() : "?";
});

const afficherImage = computed(
  () => Boolean(props.urlPhoto) && !cassee.value,
);

const classesImage = computed(() =>
  props.taille === "grand"
    ? ["portrait-joueur", props.classeCss].filter(Boolean)
    : ["portrait-mini", props.classeCss].filter(Boolean),
);

const classesVide = computed(() =>
  props.taille === "grand"
    ? ["portrait-joueur", "portrait-vide", props.classeCss].filter(Boolean)
    : ["portrait-mini", "portrait-mini-vide", props.classeCss].filter(Boolean),
);

function marquerCassee() {
  cassee.value = true;
}
</script>

<template>
  <img
    v-if="afficherImage"
    :src="urlPhoto"
    :alt="nom"
    :class="classesImage"
    loading="lazy"
    decoding="async"
    @error="marquerCassee"
  />
  <span
    v-else
    :class="classesVide"
    aria-hidden="true"
  >{{ initiale }}</span>
</template>
