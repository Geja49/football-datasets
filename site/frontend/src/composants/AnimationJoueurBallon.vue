<template>
  <div class="scene-ballon" aria-hidden="true">
    <svg class="scene" viewBox="0 0 100 76" xmlns="http://www.w3.org/2000/svg" fill="none">
      <defs>
        <!-- Sphère : lumière haut-gauche -->
        <radialGradient id="degrade-sphere" cx="32%" cy="26%" r="78%" fx="28%" fy="22%">
          <stop offset="0%" stop-color="#ffffff" />
          <stop offset="38%" stop-color="#f7f7f7" />
          <stop offset="72%" stop-color="#d8d8d8" />
          <stop offset="100%" stop-color="#9a9a9a" />
        </radialGradient>

        <!-- Panneaux blancs légèrement ombrés -->
        <linearGradient id="degrade-panneau-blanc" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#ffffff" />
          <stop offset="100%" stop-color="#e8e8e8" />
        </linearGradient>

        <!-- Pentagones noirs avec léger relief -->
        <linearGradient id="degrade-panneau-noir" x1="20%" y1="10%" x2="80%" y2="90%">
          <stop offset="0%" stop-color="#1a1a1a" />
          <stop offset="55%" stop-color="#0a0a0a" />
          <stop offset="100%" stop-color="#000000" />
        </linearGradient>

        <!-- Assombrissement périphérique -->
        <radialGradient id="ombre-volume" cx="52%" cy="50%" r="50%">
          <stop offset="50%" stop-color="#000000" stop-opacity="0" />
          <stop offset="100%" stop-color="#000000" stop-opacity="0.32" />
        </radialGradient>

        <!-- Lueur teal ambiante (thème site) -->
        <radialGradient id="reflet-teal" cx="50%" cy="44%" r="62%">
          <stop offset="0%" stop-color="#14b8a6" stop-opacity="0.18" />
          <stop offset="65%" stop-color="#14b8a6" stop-opacity="0.05" />
          <stop offset="100%" stop-color="#14b8a6" stop-opacity="0" />
        </radialGradient>

        <!-- Reflet spéculaire principal -->
        <radialGradient id="degrade-reflet" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#ffffff" stop-opacity="0.92" />
          <stop offset="45%" stop-color="#ffffff" stop-opacity="0.28" />
          <stop offset="100%" stop-color="#ffffff" stop-opacity="0" />
        </radialGradient>

        <!-- Second reflet discret -->
        <radialGradient id="degrade-reflet-secondaire" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#ffffff" stop-opacity="0.35" />
          <stop offset="100%" stop-color="#ffffff" stop-opacity="0" />
        </radialGradient>

        <filter id="lueur-ballon" x="-60%" y="-60%" width="220%" height="220%">
          <feDropShadow
            dx="0"
            dy="1.4"
            stdDeviation="2.8"
            flood-color="#14b8a6"
            flood-opacity="0.28"
          />
          <feDropShadow
            dx="0.5"
            dy="2.2"
            stdDeviation="1.4"
            flood-color="#000000"
            flood-opacity="0.4"
          />
        </filter>

        <radialGradient id="degrade-ombre-sol" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#000000" stop-opacity="0.62" />
          <stop offset="65%" stop-color="#000000" stop-opacity="0.24" />
          <stop offset="100%" stop-color="#000000" stop-opacity="0" />
        </radialGradient>

        <clipPath id="clip-sphere">
          <circle cx="50" cy="30" r="17" />
        </clipPath>
      </defs>

      <ellipse class="ombre-sol" cx="50" cy="63" rx="15" ry="3.4" fill="url(#degrade-ombre-sol)" />

      <g class="ballon-rebond">
        <g class="ballon-rotation">
          <g class="ballon-corps" filter="url(#lueur-ballon)">
            <g clip-path="url(#clip-sphere)">
              <circle cx="50" cy="30" r="17" fill="url(#degrade-sphere)" />

              <!-- Motif classique : pentagones + hexagones (projection frontale) -->
              <!-- Pentagone central -->
              <path
                class="panneau-noir"
                d="M50 15.8 L56.4 20.5 L54.1 28.2 L45.9 28.2 L43.6 20.5 Z"
              />
              <!-- Hexagones autour du pentagone central -->
              <path
                class="panneau-blanc"
                d="M43.6 20.5 L38.2 17.2 L38.8 11.2 L45.2 11.8 L48.8 16.2 Z"
              />
              <path
                class="panneau-blanc"
                d="M56.4 20.5 L61.8 17.2 L61.2 11.2 L54.8 11.8 L51.2 16.2 Z"
              />
              <path
                class="panneau-blanc"
                d="M38.4 26.8 L43.6 28.2 L42.8 34.2 L37.2 36.2 L33.6 31.8 Z"
              />
              <path
                class="panneau-blanc"
                d="M61.6 26.8 L56.4 28.2 L57.2 34.2 L62.8 36.2 L66.4 31.8 Z"
              />
              <path
                class="panneau-blanc"
                d="M45.9 28.2 L42.8 34.2 L46.2 39.2 L53.8 39.2 L57.2 34.2 L54.1 28.2 Z"
              />
              <!-- Pentagones périphériques -->
              <path
                class="panneau-noir"
                d="M38.8 11.2 L45.2 11.8 L48.8 16.2 L45.6 20.8 L39.8 18.6 Z"
              />
              <path
                class="panneau-noir"
                d="M61.2 11.2 L54.8 11.8 L51.2 16.2 L54.4 20.8 L60.2 18.6 Z"
              />
              <path
                class="panneau-noir"
                d="M33.6 31.8 L37.2 36.2 L35.4 42.2 L29.2 42.8 L27.2 36.8 Z"
              />
              <path
                class="panneau-noir"
                d="M66.4 31.8 L62.8 36.2 L64.6 42.2 L70.8 42.8 L72.8 36.8 Z"
              />
              <path
                class="panneau-noir"
                d="M46.2 39.2 L42.4 44.2 L46.8 47.2 L53.2 47.2 L57.6 44.2 L53.8 39.2 Z"
              />

              <!-- Coutures entre panneaux -->
              <path
                class="couture"
                d="M50 15.8 L50 11.2
                   M43.6 20.5 L38.2 17.2
                   M56.4 20.5 L61.8 17.2
                   M45.9 28.2 L38.4 26.8
                   M54.1 28.2 L61.6 26.8
                   M45.9 28.2 L46.2 39.2
                   M54.1 28.2 L53.8 39.2
                   M38.8 11.2 L45.2 11.8 L48.8 16.2 L45.6 20.8
                   M61.2 11.2 L54.8 11.8 L51.2 16.2 L54.4 20.8
                   M33.6 31.8 L37.2 36.2 L35.4 42.2
                   M66.4 31.8 L62.8 36.2 L64.6 42.2
                   M46.2 39.2 L42.4 44.2 L46.8 47.2
                   M53.8 39.2 L57.6 44.2 L53.2 47.2"
              />

              <circle cx="50" cy="30" r="17" fill="url(#ombre-volume)" />
              <circle cx="50" cy="30" r="17" fill="url(#reflet-teal)" />
            </g>

            <circle cx="50" cy="30" r="17" class="contour-ballon" />

            <ellipse
              class="reflet reflet-principal"
              cx="41.5"
              cy="21"
              rx="5.2"
              ry="3"
              fill="url(#degrade-reflet)"
            />
            <ellipse
              class="reflet reflet-secondaire"
              cx="58"
              cy="36"
              rx="2.4"
              ry="1.4"
              fill="url(#degrade-reflet-secondaire)"
            />
          </g>
        </g>
      </g>
    </svg>
  </div>
</template>

<style scoped>
.scene-ballon {
  width: min(132px, 44vw);
  line-height: 0;
}

.scene {
  display: block;
  width: 100%;
  height: auto;
  overflow: visible;
}

.ombre-sol {
  transform-origin: 50px 63px;
  animation: ombre-rebond 1.05s infinite;
  animation-timing-function: cubic-bezier(0.42, 0, 0.58, 1);
}

.ballon-rebond {
  transform-origin: 50px 63px;
  animation: rebond-ballon 1.05s infinite;
}

.ballon-rotation {
  transform-origin: 50px 30px;
  animation: rotation-ballon 3s linear infinite;
}

.ballon-corps {
  transform-origin: 50px 30px;
  animation: pulse-lueur 1.05s ease-in-out infinite;
}

.panneau-noir {
  fill: url(#degrade-panneau-noir);
}

.panneau-blanc {
  fill: url(#degrade-panneau-blanc);
  opacity: 0.92;
}

.couture {
  stroke: #c8c8c8;
  stroke-width: 0.38;
  stroke-linecap: round;
  stroke-linejoin: round;
  opacity: 0.55;
  fill: none;
}

.contour-ballon {
  fill: none;
  stroke: rgba(255, 255, 255, 0.14);
  stroke-width: 0.5;
}

.reflet {
  pointer-events: none;
}

.reflet-principal {
  transform-origin: 41.5px 21px;
  animation: scintillement-reflet 1.05s ease-in-out infinite;
}

@keyframes rebond-ballon {
  0%,
  100% {
    transform: translateY(0) scale(1, 1);
    animation-timing-function: cubic-bezier(0.33, 0, 0.2, 1);
  }
  18% {
    transform: translateY(0) scale(1.04, 0.94);
    animation-timing-function: cubic-bezier(0.55, 0.08, 0.68, 0.45);
  }
  48% {
    transform: translateY(22px) scale(0.96, 1.06);
    animation-timing-function: cubic-bezier(0.22, 0.61, 0.36, 1);
  }
  72% {
    transform: translateY(6px) scale(1.02, 0.98);
    animation-timing-function: cubic-bezier(0.33, 0, 0.2, 1);
  }
}

@keyframes ombre-rebond {
  0%,
  100% {
    transform: scale(0.48, 0.65);
    opacity: 0.22;
  }
  18% {
    transform: scale(1.08, 1.12);
    opacity: 0.78;
  }
  48% {
    transform: scale(0.92, 0.95);
    opacity: 0.55;
  }
  72% {
    transform: scale(1.02, 1.05);
    opacity: 0.68;
  }
}

@keyframes rotation-ballon {
  to {
    transform: rotate(360deg);
  }
}

@keyframes pulse-lueur {
  0%,
  100% {
    opacity: 1;
  }
  18% {
    opacity: 1.03;
  }
  48% {
    opacity: 0.94;
  }
}

@keyframes scintillement-reflet {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  48% {
    opacity: 0.75;
    transform: scale(0.88);
  }
}

@media (max-width: 420px) {
  .scene-ballon {
    width: min(116px, 42vw);
  }
}

@media (prefers-reduced-motion: reduce) {
  .ombre-sol,
  .ballon-rebond,
  .ballon-rotation,
  .ballon-corps,
  .reflet-principal {
    animation: none;
  }

  .ombre-sol {
    opacity: 0.5;
    transform: scale(0.85, 0.9);
  }

  .ballon-rebond {
    transform: translateY(14px);
  }
}
</style>
