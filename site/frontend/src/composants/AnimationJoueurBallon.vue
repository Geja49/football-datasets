<template>
  <div class="scene-ballon" aria-hidden="true">
    <svg class="scene" viewBox="0 0 100 72" xmlns="http://www.w3.org/2000/svg" fill="none">
      <defs>
        <!-- Sphère : lumière haut-gauche, ombre bas-droite -->
        <radialGradient id="degrade-sphere" cx="34%" cy="28%" r="72%" fx="30%" fy="24%">
          <stop offset="0%" stop-color="#ffffff" />
          <stop offset="42%" stop-color="#f4f4f4" />
          <stop offset="78%" stop-color="#c8c8c8" />
          <stop offset="100%" stop-color="#8f8f8f" />
        </radialGradient>

        <!-- Assombrissement périphérique pour le volume -->
        <radialGradient id="ombre-volume" cx="50%" cy="48%" r="50%">
          <stop offset="55%" stop-color="#000000" stop-opacity="0" />
          <stop offset="100%" stop-color="#000000" stop-opacity="0.28" />
        </radialGradient>

        <!-- Lueur teal ambiante très légère -->
        <radialGradient id="reflet-teal" cx="48%" cy="42%" r="58%">
          <stop offset="0%" stop-color="#14b8a6" stop-opacity="0.14" />
          <stop offset="70%" stop-color="#14b8a6" stop-opacity="0.04" />
          <stop offset="100%" stop-color="#14b8a6" stop-opacity="0" />
        </radialGradient>

        <!-- Reflet spéculaire -->
        <radialGradient id="degrade-reflet" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#ffffff" stop-opacity="0.75" />
          <stop offset="55%" stop-color="#ffffff" stop-opacity="0.22" />
          <stop offset="100%" stop-color="#ffffff" stop-opacity="0" />
        </radialGradient>

        <filter id="lueur-ballon" x="-50%" y="-50%" width="200%" height="200%">
          <feDropShadow
            dx="0"
            dy="1.2"
            stdDeviation="2.2"
            flood-color="#14b8a6"
            flood-opacity="0.22"
          />
          <feDropShadow
            dx="0.4"
            dy="1.8"
            stdDeviation="1.1"
            flood-color="#000000"
            flood-opacity="0.35"
          />
        </filter>

        <radialGradient id="degrade-ombre-sol" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#000000" stop-opacity="0.55" />
          <stop offset="70%" stop-color="#000000" stop-opacity="0.22" />
          <stop offset="100%" stop-color="#000000" stop-opacity="0" />
        </radialGradient>

        <clipPath id="clip-sphere">
          <circle cx="50" cy="28" r="16" />
        </clipPath>
      </defs>

      <ellipse class="ombre-sol" cx="50" cy="60" rx="14" ry="3.2" fill="url(#degrade-ombre-sol)" />

      <g class="ballon-rebond">
        <g class="ballon-rotation">
          <g filter="url(#lueur-ballon)">
            <g clip-path="url(#clip-sphere)">
              <circle cx="50" cy="28" r="16" fill="url(#degrade-sphere)" />

              <!-- Pentagone central -->
              <path
                class="panneau-noir"
                d="M50 16.2 L56.1 20.6 L53.9 28 L46.1 28 L43.9 20.6 Z"
              />
              <!-- Hexagones / panneaux latéraux -->
              <path
                class="panneau-noir"
                d="M34.4 26.2 L38.4 21.4 L43.9 23.8 L42.4 30.4 L36.6 32.6 Z"
              />
              <path
                class="panneau-noir"
                d="M65.6 26.2 L61.6 21.4 L56.1 23.8 L57.6 30.4 L63.4 32.6 Z"
              />
              <path
                class="panneau-noir"
                d="M38.8 40.2 L44 37.6 L48.6 40.8 L46.6 45.6 L41.2 45.8 Z"
              />
              <path
                class="panneau-noir"
                d="M61.2 40.2 L56 37.6 L51.4 40.8 L53.4 45.6 L58.8 45.8 Z"
              />
              <path
                class="panneau-noir"
                d="M50 43.8 L45.8 40.8 L47.6 37 L52.4 37 L54.2 40.8 Z"
              />

              <path
                class="couture"
                d="M50 22.4 L50 12
                   M56.1 20.6 L64.2 17.6
                   M53.9 28 L58.8 35.2
                   M46.1 28 L41.2 35.2
                   M43.9 20.6 L35.8 17.6
                   M38.8 40.2 L30.6 41.8
                   M61.2 40.2 L69.4 41.8
                   M50 42.8 L50 44.2"
              />

              <circle cx="50" cy="28" r="16" fill="url(#ombre-volume)" />
              <circle cx="50" cy="28" r="16" fill="url(#reflet-teal)" />
            </g>

            <!-- Contour fin pour détacher du fond sombre -->
            <circle
              cx="50"
              cy="28"
              r="16"
              class="contour-ballon"
            />

            <ellipse class="reflet" cx="42.5" cy="20.5" rx="4.6" ry="2.6" fill="url(#degrade-reflet)" />
          </g>
        </g>
      </g>
    </svg>
  </div>
</template>

<style scoped>
.scene-ballon {
  width: min(128px, 42vw);
  line-height: 0;
}

.scene {
  display: block;
  width: 100%;
  height: auto;
  overflow: visible;
}

.ombre-sol {
  transform-origin: 50px 60px;
  animation: ombre-rebond 0.95s infinite;
  animation-timing-function: cubic-bezier(0.45, 0.05, 0.55, 0.95);
}

.ballon-rebond {
  transform-origin: 50px 60px;
  animation: rebond-ballon 0.95s infinite;
}

.ballon-rotation {
  transform-origin: 50px 28px;
  animation: rotation-ballon 2.4s linear infinite;
}

.panneau-noir {
  fill: #0d0d0d;
}

.couture {
  stroke: #d4d4d4;
  stroke-width: 0.4;
  stroke-linecap: round;
  stroke-linejoin: round;
  opacity: 0.5;
}

.contour-ballon {
  fill: none;
  stroke: rgba(255, 255, 255, 0.12);
  stroke-width: 0.55;
}

.reflet {
  pointer-events: none;
}

@keyframes rebond-ballon {
  0% {
    transform: translateY(0);
    animation-timing-function: cubic-bezier(0.55, 0.08, 0.68, 0.5);
  }
  50% {
    transform: translateY(20px);
    animation-timing-function: cubic-bezier(0.22, 0.61, 0.36, 1);
  }
  100% {
    transform: translateY(0);
  }
}

@keyframes ombre-rebond {
  0%,
  100% {
    transform: scale(0.52, 0.7);
    opacity: 0.28;
  }
  50% {
    transform: scale(1, 1);
    opacity: 0.7;
  }
}

@keyframes rotation-ballon {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 420px) {
  .scene-ballon {
    width: min(112px, 40vw);
  }
}

@media (prefers-reduced-motion: reduce) {
  .ombre-sol,
  .ballon-rebond,
  .ballon-rotation {
    animation: none;
  }

  .ombre-sol {
    opacity: 0.5;
    transform: scale(0.85, 0.9);
  }

  .ballon-rebond {
    transform: translateY(12px);
  }
}
</style>
