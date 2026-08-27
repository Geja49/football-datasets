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
  gap: 10px;
  margin: 28px 0 36px;
  padding: 28px 20px 22px;
  border-radius: 14px;
  border: 1px solid color-mix(in srgb, #14b8a6 28%, #1a1a1a);
  background:
    radial-gradient(
      ellipse 55% 42% at 50% 38%,
      color-mix(in srgb, #14b8a6 10%, transparent),
      transparent 68%
    ),
    #050505;
  box-shadow: inset 0 1px 0 color-mix(in srgb, #14b8a6 10%, transparent);
}

.message-chargement {
  display: inline-flex;
  align-items: baseline;
  gap: 1px;
  margin: 0;
  font-size: clamp(0.9rem, 2.8vw, 1rem);
  font-weight: 500;
  letter-spacing: 0.04em;
}

.message-texte {
  color: #ffffff;
}

.points span {
  display: inline-block;
  color: #14b8a6;
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
    margin: 20px 0 28px;
    padding: 22px 14px 18px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .points span {
    animation: none;
    opacity: 0.7;
  }
}
</style>
