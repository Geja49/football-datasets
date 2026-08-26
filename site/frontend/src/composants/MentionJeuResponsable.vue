<script setup>
defineProps({
  compact: { type: Boolean, default: false },
});
</script>

<template>
  <p
    class="mention-jeu-responsable"
    :class="{ 'mention-jeu-responsable-compact': compact }"
  >
    <template v-if="compact">
      18+ · aide jeu :
      <a
        href="https://www.joueurs-info-service.fr/"
        target="_blank"
        rel="noopener noreferrer"
      >
        Joueurs Info Service
      </a>
      ·
      <a href="https://connexions.ca/" target="_blank" rel="noopener noreferrer">
        Connexions.ca
      </a>
      ·
      <a
        href="https://www.jeu-aidereference.qc.ca/"
        target="_blank"
        rel="noopener noreferrer"
      >
        Québec
      </a>
    </template>
    <template v-else>
      <span class="mention-jeu-responsable-intro">
        Besoin d'aide face au jeu ?
      </span>
      <span class="mention-jeu-responsable-ressources">
        <span class="mention-jeu-responsable-item">
          <a
            href="https://www.joueurs-info-service.fr/"
            target="_blank"
            rel="noopener noreferrer"
          >
            Joueurs Info Service
          </a>
          (France)
        </span>
        <span class="pied-site-sep" aria-hidden="true">·</span>
        <span class="mention-jeu-responsable-item">
          <a
            href="https://connexions.ca/"
            target="_blank"
            rel="noopener noreferrer"
          >
            Connexions.ca
          </a>
          (Canada)
        </span>
        <span class="pied-site-sep" aria-hidden="true">·</span>
        <span class="mention-jeu-responsable-item">
          Québec :
          <a
            href="https://www.jeu-aidereference.qc.ca/"
            target="_blank"
            rel="noopener noreferrer"
          >
            jeu-aidereference.qc.ca
          </a>
          <span class="mention-jeu-responsable-tel">(1-800-461-0140)</span>
        </span>
      </span>
    </template>
  </p>
</template>
