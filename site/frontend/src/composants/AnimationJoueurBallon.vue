<template>
  <div class="scene-ballon" aria-hidden="true">
    <svg class="scene" viewBox="0 0 100 68" xmlns="http://www.w3.org/2000/svg" fill="none">
      <defs>
        <radialGradient id="degrade-sphere" cx="38%" cy="32%" r="68%" fx="32%" fy="26%">
          <stop offset="0%" stop-color="#ffffff" />
          <stop offset="55%" stop-color="#f2f2f2" />
          <stop offset="100%" stop-color="#b8b8b8" />
        </radialGradient>

        <radialGradient id="reflet-teal" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#14b8a6" stop-opacity="0.18" />
          <stop offset="100%" stop-color="#14b8a6" stop-opacity="0" />
        </radialGradient>

        <filter id="lueur-ballon" x="-40%" y="-40%" width="180%" height="180%">
          <feDropShadow
            dx="0"
            dy="1.5"
            stdDeviation="2.5"
            flood-color="#14b8a6"
            flood-opacity="0.35"
          />
        </filter>

        <clipPath id="clip-sphere">
          <circle cx="50" cy="30" r="15" />
        </clipPath>
      </defs>

      <ellipse class="ombre-sol" cx="50" cy="56" rx="13" ry="3" />

      <g class="ballon-rebond">
        <g class="ballon-rotation">
          <g filter="url(#lueur-ballon)">
            <g clip-path="url(#clip-sphere)">
              <circle cx="50" cy="30" r="15" fill="url(#degrade-sphere)" />

              <path
                class="panneau-noir"
                d="M50 18.8 L55.4 22.8 L53.5 29.6 L46.5 29.6 L44.6 22.8 Z"
              />
              <path
                class="panneau-noir"
                d="M35.2 28.5 L38.8 24.2 L43.8 26.2 L42.5 32.2 L37.2 34.2 Z"
              />
              <path
                class="panneau-noir"
                d="M64.8 28.5 L61.2 24.2 L56.2 26.2 L57.5 32.2 L62.8 34.2 Z"
              />
              <path
                class="panneau-noir"
                d="M39.5 40.8 L44.2 38.5 L48.5 41.2 L46.8 45.5 L42 45.8 Z"
              />
              <path
                class="panneau-noir"
                d="M60.5 40.8 L55.8 38.5 L51.5 41.2 L53.2 45.5 L58 45.8 Z"
              />
              <path
                class="panneau-noir"
                d="M50 44.2 L46.2 41.6 L47.8 38.2 L52.2 38.2 L53.8 41.6 Z"
              />

              <path
                class="couture"
                d="M50 24.2 L50 15 M55.4 22.8 L63 20 M53.5 29.6 L58 36
                   M46.5 29.6 L42 36 M44.6 22.8 L37 20 M39.5 40.8 L32 42
                   M60.5 40.8 L68 42 M50 43.5 L50 45"
              />

              <circle cx="50" cy="30" r="15" fill="url(#reflet-teal)" />
            </g>

            <ellipse class="reflet" cx="43" cy="23" rx="4.2" ry="2.4" />
          </g>
        </g>
      </g>
    </svg>
  </div>
</template>

<style scoped>
.scene-ballon {
  width: min(160px, 52vw);
}

.scene {
  display: block;
  width: 100%;
  height: auto;
}

.ombre-sol {
  fill: rgba(0, 0, 0, 0.5);
  transform-origin: 50px 56px;
  animation: ombre-rebond 0.85s ease-in infinite;
}

.ballon-rebond {
  transform-origin: 50px 56px;
  animation: rebond-ballon 0.85s ease-in infinite;
}

.ballon-rotation {
  transform-origin: 50px 30px;
  animation: rotation-ballon 2s linear infinite;
}

.panneau-noir {
  fill: #111111;
}

.couture {
  stroke: #cccccc;
  stroke-width: 0.45;
  stroke-linecap: round;
  opacity: 0.55;
}

.reflet {
  fill: #ffffff;
  opacity: 0.42;
}

@keyframes rebond-ballon {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(22px);
  }
}

@keyframes ombre-rebond {
  0%,
  100% {
    transform: scaleX(0.5);
    opacity: 0.2;
  }
  50% {
    transform: scaleX(1);
    opacity: 0.55;
  }
}

@keyframes rotation-ballon {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 420px) {
  .scene-ballon {
    width: min(140px, 48vw);
  }
}

@media (prefers-reduced-motion: reduce) {
  .ombre-sol,
  .ballon-rebond,
  .ballon-rotation {
    animation: none;
  }

  .ombre-sol {
    opacity: 0.45;
    transform: scaleX(0.85);
  }

  .ballon-rebond {
    transform: translateY(14px);
  }
}
</style>
