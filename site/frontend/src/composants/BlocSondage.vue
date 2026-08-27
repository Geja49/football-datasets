<script setup>
defineProps({
  question: { type: String, required: true },
  options: { type: Array, default: () => [] },
  aVote: { type: Boolean, default: false },
  monCle: { type: [Number, String, null], default: null },
  nbVotesTotal: { type: Number, default: null },
  connecte: { type: Boolean, default: false },
  cleOption: { type: String, default: "id" },
  envoi: { type: Boolean, default: false },
  peutSupprimer: { type: Boolean, default: false },
  disclaimer: { type: String, default: "" },
});

const emit = defineEmits(["voter", "supprimer"]);

function pourcentage(option) {
  if (typeof option.pourcentage === "number") return option.pourcentage;
  return 0;
}

function libelleVotes(total) {
  if (total == null) return "";
  return total <= 1 ? `${total} vote` : `${total} votes`;
}
</script>

<template>
  <div class="bloc-sondage">
    <header class="entete-sondage">
      <p class="tag-sondage">Sondage</p>
      <h3 class="question-sondage">{{ question }}</h3>
      <p v-if="aVote && nbVotesTotal != null" class="meta-sondage doux">
        {{ libelleVotes(nbVotesTotal) }}
      </p>
    </header>

    <ul class="liste-options-sondage" role="list">
      <li v-for="option in options" :key="option[cleOption]">
        <button
          v-if="!aVote"
          type="button"
          class="bouton-option-sondage"
          :disabled="!connecte || envoi"
          @click="emit('voter', option[cleOption])"
        >
          {{ option.libelle }}
        </button>
        <div
          v-else
          class="barre-resultat-sondage"
          :class="{ choisie: option[cleOption] === monCle }"
        >
          <div class="rangee-resultat-sondage">
            <span class="libelle-option-sondage">{{ option.libelle }}</span>
            <span class="pct-option-sondage">{{ pourcentage(option) }}&nbsp;%</span>
          </div>
          <div class="piste-barre-sondage" aria-hidden="true">
            <div
              class="remplissage-barre-sondage"
              :style="{ width: `${pourcentage(option)}%` }"
            />
          </div>
        </div>
      </li>
    </ul>

    <p v-if="!connecte && !aVote" class="doux petit-sondage">
      Connectez-vous pour voter (1 vote par compte).
    </p>
    <p v-else-if="connecte && !aVote" class="doux petit-sondage">
      Un seul vote, non modifiable.
    </p>
    <p v-if="disclaimer" class="disclaimer-sondage doux">{{ disclaimer }}</p>

    <button
      v-if="peutSupprimer"
      type="button"
      class="bouton-supprimer-sondage"
      :disabled="envoi"
      @click="emit('supprimer')"
    >
      Supprimer le sondage
    </button>
  </div>
</template>
