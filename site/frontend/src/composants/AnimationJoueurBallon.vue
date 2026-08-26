<script setup>
defineProps({
  /** Message affiché sous l’animation. */
  message: { type: String, default: "Calcul du scénario…" },
});
</script>

<template>
  <div class="chargement-scenario" role="status" aria-live="polite" aria-busy="true">
    <div class="piste" aria-hidden="true">
      <svg class="scene" viewBox="0 0 200 90" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="degrade-maillot" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stop-color="var(--marque, #14b8a6)" stop-opacity="0.95" />
            <stop offset="100%" stop-color="var(--marque, #14b8a6)" stop-opacity="0.55" />
          </linearGradient>
        </defs>

        <!-- Ligne de terrain -->
        <line class="ligne-terrain" x1="12" y1="78" x2="188" y2="78" />

        <g class="groupe-joueur">
          <!-- Ombre -->
          <ellipse class="ombre" cx="72" cy="78" rx="22" ry="3.5" />

          <!-- Corps -->
          <g class="corps">
            <circle class="tete" cx="58" cy="22" r="8" />
            <path
              class="torse"
              d="M50 32 Q58 30 66 32 L70 52 Q58 56 46 52 Z"
            />
            <!-- Bras (poussée) -->
            <path class="bras bras-arriere" d="M52 36 Q40 42 36 50" />
            <path class="bras bras-avant" d="M64 36 Q78 40 86 48" />
            <!-- Jambes (course) -->
            <path class="jambe jambe-arriere" d="M52 52 Q46 64 42 74" />
            <path class="jambe jambe-avant" d="M62 52 Q70 62 78 72" />
          </g>

          <!-- Ballon -->
          <g class="ballon">
            <circle class="ballon-corps" cx="98" cy="70" r="9" />
            <path
              class="ballon-motif"
              d="M98 61 Q102 70 98 79 M91 66 Q98 70 105 66 M91 74 Q98 70 105 74"
            />
          </g>
        </g>
      </svg>
    </div>
    <p class="message-chargement">{{ message }}</p>
  </div>
</template>

<style scoped>
.chargement-scenario {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  margin: 28px 0 36px;
  padding: 28px 20px 24px;
  border-radius: 12px;
  border: 1px solid color-mix(in srgb, var(--marque, #14b8a6) 28%, var(--ligne, #243044));
  background:
    radial-gradient(
      ellipse 70% 80% at 50% 100%,
      color-mix(in srgb, var(--marque, #14b8a6) 12%, transparent),
      transparent 70%
    ),
    var(--fond-carte, #121a28);
}

.piste {
  width: min(280px, 100%);
  overflow: hidden;
}

.scene {
  display: block;
  width: 100%;
  height: auto;
}

.ligne-terrain {
  stroke: color-mix(in srgb, var(--marque, #14b8a6) 35%, var(--ligne, #243044));
  stroke-width: 1.5;
  stroke-dasharray: 6 5;
  animation: defilement-ligne 1.1s linear infinite;
}

.groupe-joueur {
  animation: avance-dribble 1.4s ease-in-out infinite;
  transform-origin: 72px 78px;
}

.ombre {
  fill: rgba(0, 0, 0, 0.35);
  animation: ombre-pulse 1.4s ease-in-out infinite;
}

.tete {
  fill: color-mix(in srgb, var(--texte, #f4f7fb) 88%, var(--marque, #14b8a6));
}

.torse {
  fill: url(#degrade-maillot);
}

.bras,
.jambe {
  fill: none;
  stroke: color-mix(in srgb, var(--texte, #f4f7fb) 75%, var(--marque, #14b8a6));
  stroke-width: 3.2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.bras-avant {
  animation: bras-poussee 0.7s ease-in-out infinite;
  transform-origin: 64px 36px;
}

.jambe-avant {
  animation: jambe-pas 0.7s ease-in-out infinite;
  transform-origin: 62px 52px;
}

.jambe-arriere {
  animation: jambe-pas 0.7s ease-in-out infinite reverse;
  transform-origin: 52px 52px;
}

.ballon {
  animation: ballon-dribble 0.7s ease-in-out infinite;
  transform-origin: 98px 70px;
}

.ballon-corps {
  fill: color-mix(in srgb, var(--marque, #14b8a6) 70%, #e8fff8);
  stroke: var(--marque, #14b8a6);
  stroke-width: 1.5;
}

.ballon-motif {
  fill: none;
  stroke: color-mix(in srgb, var(--fond, #070b12) 55%, var(--marque, #14b8a6));
  stroke-width: 1.2;
  stroke-linecap: round;
}

.message-chargement {
  margin: 0;
  font-size: 0.95rem;
  color: var(--texte-doux, #9aa8bc);
  letter-spacing: 0.02em;
}

@keyframes avance-dribble {
  0%,
  100% {
    transform: translateX(-10px);
  }
  50% {
    transform: translateX(14px);
  }
}

@keyframes ombre-pulse {
  0%,
  100% {
    transform: scaleX(1);
    opacity: 0.55;
  }
  50% {
    transform: scaleX(1.15);
    opacity: 0.35;
  }
}

@keyframes bras-poussee {
  0%,
  100% {
    transform: rotate(-8deg);
  }
  50% {
    transform: rotate(12deg);
  }
}

@keyframes jambe-pas {
  0%,
  100% {
    transform: rotate(-14deg);
  }
  50% {
    transform: rotate(16deg);
  }
}

@keyframes ballon-dribble {
  0%,
  100% {
    transform: translate(0, 0) rotate(0deg);
  }
  35% {
    transform: translate(6px, -10px) rotate(90deg);
  }
  70% {
    transform: translate(10px, 0) rotate(180deg);
  }
}

@keyframes defilement-ligne {
  to {
    stroke-dashoffset: -22;
  }
}

@media (prefers-reduced-motion: reduce) {
  .ligne-terrain,
  .groupe-joueur,
  .ombre,
  .bras-avant,
  .jambe-avant,
  .jambe-arriere,
  .ballon {
    animation: none;
  }

  .groupe-joueur {
    transform: translateX(0);
  }
}
</style>
