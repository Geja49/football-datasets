<script setup>
defineProps({
  /** Message affiché sous l’animation. */
  message: { type: String, default: "Calcul du scénario…" },
});
</script>

<template>
  <div class="chargement-scenario" role="status" aria-live="polite" aria-busy="true">
    <div class="piste" aria-hidden="true">
      <svg
        class="scene"
        viewBox="0 0 240 110"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
      >
        <defs>
          <!-- Courbe teal du logo (soulignement) -->
          <linearGradient id="degrade-arc" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#14b8a6" stop-opacity="0" />
            <stop offset="20%" stop-color="#14b8a6" stop-opacity="0.85" />
            <stop offset="80%" stop-color="#14b8a6" stop-opacity="0.85" />
            <stop offset="100%" stop-color="#14b8a6" stop-opacity="0" />
          </linearGradient>
          <!-- Trace stats (flèche / sparkline du « a ») -->
          <linearGradient id="degrade-stats" x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#14b8a6" stop-opacity="0.15" />
            <stop offset="100%" stop-color="#14b8a6" stop-opacity="0.95" />
          </linearGradient>
        </defs>

        <!-- Sparkline stats en fond (esprit logo) -->
        <path
          class="courbe-stats"
          d="M18 78 L38 70 L52 74 L72 52 L88 58 L108 38 L128 46 L148 28 L168 34 L188 18 L208 24 L222 12"
        />

        <!-- Arc teal sous la scène (= soulignement logo) -->
        <path
          class="arc-marque"
          d="M24 96 Q120 108 216 96"
        />

        <g class="groupe-course">
          <!-- Ombre discrète -->
          <ellipse class="ombre" cx="100" cy="88" rx="28" ry="3.2" />

          <!-- Silhouette style logo : trait blanc épais, pas de maillot rempli -->
          <g class="joueur">
            <circle class="tete" cx="78" cy="28" r="8.5" />
            <!-- Corps : ligne centrale comme stick-figure logo -->
            <path class="corps" d="M78 37 L78 58" />
            <!-- Bras -->
            <path class="membre bras bras-arriere" d="M78 42 Q62 48 54 58" />
            <path class="membre bras bras-avant" d="M78 42 Q96 46 108 54" />
            <!-- Jambes course / poussée -->
            <path class="membre jambe jambe-arriere" d="M78 58 Q66 72 58 86" />
            <path class="membre jambe jambe-avant" d="M78 58 Q94 70 108 84" />
          </g>

          <!-- Ballon : disque blanc simple comme le logo -->
          <circle class="ballon" cx="128" cy="82" r="9" />
        </g>
      </svg>
    </div>

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
  gap: 12px;
  margin: 28px 0 36px;
  padding: 30px 20px 24px;
  border-radius: 14px;
  /* Fond proche du logo (noir profond) + halo teal */
  border: 1px solid color-mix(in srgb, #14b8a6 28%, #1a1a1a);
  background:
    radial-gradient(
      ellipse 80% 65% at 50% 90%,
      color-mix(in srgb, #14b8a6 14%, transparent),
      transparent 70%
    ),
    #050505;
  box-shadow: inset 0 1px 0 color-mix(in srgb, #14b8a6 10%, transparent);
}

.piste {
  width: min(300px, 90vw);
  overflow: hidden;
}

.scene {
  display: block;
  width: 100%;
  height: auto;
}

/* Sparkline teal animée (calcul en cours) */
.courbe-stats {
  stroke: url(#degrade-stats);
  stroke-width: 2.2;
  stroke-linecap: round;
  stroke-linejoin: round;
  fill: none;
  stroke-dasharray: 280;
  stroke-dashoffset: 280;
  animation: trace-stats 1.8s ease-in-out infinite;
  opacity: 0.85;
}

.arc-marque {
  stroke: url(#degrade-arc);
  stroke-width: 2.4;
  stroke-linecap: round;
  fill: none;
  animation: pulse-arc 1.6s ease-in-out infinite;
}

.groupe-course {
  animation: avance-dribble 1.45s ease-in-out infinite;
  transform-origin: 100px 88px;
}

.ombre {
  fill: rgba(0, 0, 0, 0.55);
  animation: ombre-pulse 0.72s ease-in-out infinite;
  transform-origin: 100px 88px;
}

/* Silhouette blanche = logo Stats Foot */
.tete {
  fill: #ffffff;
}

.corps,
.membre {
  stroke: #ffffff;
  stroke-width: 5.5;
  stroke-linecap: round;
  stroke-linejoin: round;
  fill: none;
}

.bras-avant {
  animation: bras-poussee 0.72s ease-in-out infinite;
  transform-origin: 78px 42px;
}

.bras-arriere {
  animation: bras-arriere 0.72s ease-in-out infinite;
  transform-origin: 78px 42px;
}

.jambe-avant {
  animation: jambe-pas 0.72s ease-in-out infinite;
  transform-origin: 78px 58px;
}

.jambe-arriere {
  animation: jambe-pas 0.72s ease-in-out infinite reverse;
  transform-origin: 78px 58px;
}

/* Ballon blanc plein + léger halo teal */
.ballon {
  fill: #ffffff;
  filter: drop-shadow(0 0 4px color-mix(in srgb, #14b8a6 55%, transparent));
  animation: ballon-dribble 0.72s cubic-bezier(0.4, 0.05, 0.55, 0.95) infinite;
  transform-origin: 128px 82px;
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

@keyframes avance-dribble {
  0%,
  100% {
    transform: translateX(-14px) translateY(0);
  }
  25% {
    transform: translateX(-2px) translateY(-1.5px);
  }
  50% {
    transform: translateX(18px) translateY(0);
  }
  75% {
    transform: translateX(6px) translateY(-1.5px);
  }
}

@keyframes ombre-pulse {
  0%,
  100% {
    transform: scaleX(1);
    opacity: 0.55;
  }
  50% {
    transform: scaleX(1.18);
    opacity: 0.32;
  }
}

@keyframes bras-poussee {
  0%,
  100% {
    transform: rotate(-12deg);
  }
  50% {
    transform: rotate(16deg);
  }
}

@keyframes bras-arriere {
  0%,
  100% {
    transform: rotate(10deg);
  }
  50% {
    transform: rotate(-16deg);
  }
}

@keyframes jambe-pas {
  0%,
  100% {
    transform: rotate(-20deg);
  }
  50% {
    transform: rotate(22deg);
  }
}

@keyframes ballon-dribble {
  0% {
    transform: translate(0, 0);
  }
  28% {
    transform: translate(10px, -12px);
  }
  55% {
    transform: translate(16px, -1px);
  }
  78% {
    transform: translate(8px, 0);
  }
  100% {
    transform: translate(0, 0);
  }
}

@keyframes trace-stats {
  0% {
    stroke-dashoffset: 280;
    opacity: 0.35;
  }
  45% {
    stroke-dashoffset: 0;
    opacity: 0.9;
  }
  70% {
    stroke-dashoffset: 0;
    opacity: 0.75;
  }
  100% {
    stroke-dashoffset: -40;
    opacity: 0.2;
  }
}

@keyframes pulse-arc {
  0%,
  100% {
    opacity: 0.55;
  }
  50% {
    opacity: 1;
  }
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

  .piste {
    width: min(250px, 88vw);
  }
}

@media (prefers-reduced-motion: reduce) {
  .courbe-stats,
  .arc-marque,
  .groupe-course,
  .ombre,
  .bras-avant,
  .bras-arriere,
  .jambe-avant,
  .jambe-arriere,
  .ballon,
  .points span {
    animation: none;
  }

  .courbe-stats {
    stroke-dashoffset: 0;
    opacity: 0.7;
  }

  .groupe-course {
    transform: none;
  }

  .points span {
    opacity: 0.7;
  }
}
</style>
