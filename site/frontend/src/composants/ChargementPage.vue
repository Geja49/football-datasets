<script setup>
import AnimationJoueurBallon from "./AnimationJoueurBallon.vue";

defineProps({
  /** Message sous l’animation (les points animés sont ajoutés ici). */
  message: { type: String, default: "Chargement" },
});
</script>

<template>
  <div class="chargement-scenario" role="status" aria-live="polite" aria-busy="true">
    <AnimationJoueurBallon />

    <p class="message-chargement">
      <span class="message-texte">{{ message }}</span>
      <span class="points" aria-hidden="true"><span>.</span><span>.</span><span>.</span></span>
    </p>
  </div>
</template>

<style scoped>
.chargement-scenario {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  width: 100%;
  margin: 24px 0 32px;
  padding: 0 16px;
  background: transparent;
}

.message-chargement {
  display: inline-flex;
  align-items: baseline;
  gap: 1px;
  margin: 0;
  font-size: clamp(0.9rem, 2.8vw, 1rem);
  font-weight: 600;
  letter-spacing: 0.03em;
}

.message-texte {
  color: var(--texte);
}

.points span {
  display: inline-block;
  color: var(--accent);
  animation: point-clignote 1.2s ease-in-out infinite;
  opacity: 0.25;
}

.points span:nth-child(2) {
  animation-delay: 0.2s;
}

.points span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes point-clignote {
  0%,
  100% {
    opacity: 0.2;
  }
  40% {
    opacity: 1;
  }
}

@media (max-width: 420px) {
  .chargement-scenario {
    margin: 18px 0 24px;
    padding: 0 12px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .points span {
    animation: none;
    opacity: 0.7;
  }
}
</style>
