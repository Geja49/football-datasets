<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";

/**
 * Petite palette d'emojis unicode (pas de HTML), orientée football.
 * Émet l'emoji choisi ; le parent l'insère dans le champ de saisie.
 */
const EMOJIS_COURANTS = [
  "⚽",
  "🏆",
  "🥇",
  "🥈",
  "🥉",
  "🥅",
  "🏟️",
  "🎽",
  "👟",
  "🧤",
  "⏱️",
  "📊",
  "💪",
  "🔥",
  "👏",
  "🙌",
  "🎯",
  "⭐",
  "🎊",
  "🎉",
  "👑",
  "🦁",
  "🦅",
  "❤️",
  "👍",
  "👎",
  "😂",
  "😮",
];

const props = defineProps({
  /** id du textarea / input cible (focus après insertion) */
  cibleId: {
    type: String,
    default: "",
  },
  disabled: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["inserer"]);

const ouvert = ref(false);
const racine = ref(null);

function basculer() {
  if (props.disabled) return;
  ouvert.value = !ouvert.value;
}

function fermer() {
  ouvert.value = false;
}

async function choisirEmoji(emoji) {
  emit("inserer", emoji);
  fermer();
  if (!props.cibleId) return;
  await nextTick();
  const champ = document.getElementById(props.cibleId);
  if (champ && typeof champ.focus === "function") {
    champ.focus();
  }
}

function surClicDocument(event) {
  if (!ouvert.value || !racine.value) return;
  if (!racine.value.contains(event.target)) {
    fermer();
  }
}

function surTouche(event) {
  if (event.key === "Escape" && ouvert.value) {
    fermer();
  }
}

onMounted(() => {
  document.addEventListener("click", surClicDocument, true);
  document.addEventListener("keydown", surTouche);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", surClicDocument, true);
  document.removeEventListener("keydown", surTouche);
});
</script>

<template>
  <div ref="racine" class="selecteur-emoji">
    <button
      type="button"
      class="bouton-selecteur-emoji"
      :disabled="disabled"
      :aria-expanded="ouvert"
      aria-haspopup="dialog"
      title="Insérer un emoji"
      @mousedown.prevent
      @click="basculer"
    >
      <span aria-hidden="true">😊</span>
      <span class="visuellement-cache">Insérer un emoji</span>
    </button>
    <div
      v-if="ouvert"
      class="palette-emoji"
      role="dialog"
      aria-label="Choisir un emoji"
    >
      <button
        v-for="emoji in EMOJIS_COURANTS"
        :key="emoji"
        type="button"
        class="bouton-emoji-palette"
        :title="`Insérer ${emoji}`"
        @mousedown.prevent
        @click="choisirEmoji(emoji)"
      >
        {{ emoji }}
      </button>
    </div>
  </div>
</template>
