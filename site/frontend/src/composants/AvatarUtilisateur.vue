<script setup>
import { computed } from "vue";
import { formaterPseudoAffichage } from "../formaterPseudo.js";
import {
  couleurInitiales,
  initialesDepuisPseudo,
  urlAvatar,
} from "../catalogueAvatars.js";

const props = defineProps({
  pseudo: { type: String, default: "" },
  avatarId: { type: String, default: "" },
  taille: { type: Number, default: 36 },
  titre: { type: String, default: "" },
});

const pseudoAffiche = computed(() => formaterPseudoAffichage(props.pseudo));
const srcAvatar = computed(() => urlAvatar(props.avatarId));
const initiales = computed(() => initialesDepuisPseudo(pseudoAffiche.value));
const couleurFond = computed(() => couleurInitiales(props.pseudo));
const libelle = computed(
  () => props.titre || `Avatar de ${pseudoAffiche.value || "utilisateur"}`,
);
const styleTaille = computed(() => ({
  width: `${props.taille}px`,
  height: `${props.taille}px`,
  fontSize: `${Math.max(10, Math.round(props.taille * 0.38))}px`,
}));
</script>

<template>
  <span
    class="avatar-utilisateur"
    :class="{ 'avatar-initiales': !srcAvatar }"
    :style="[styleTaille, !srcAvatar ? { backgroundColor: couleurFond } : null]"
    role="img"
    :aria-label="libelle"
  >
    <img v-if="srcAvatar" :src="srcAvatar" alt="" class="avatar-image" />
    <span v-else class="avatar-lettres">{{ initiales }}</span>
  </span>
</template>
