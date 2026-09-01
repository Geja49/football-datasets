<template>
  <div class="scene-animation" aria-hidden="true">
    <video
      ref="videoRef"
      class="video-but"
      src="/animations/but-football.mp4"
      autoplay
      loop
      muted
      playsinline
      preload="auto"
    />
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from "vue";

const videoRef = ref(null);
let mediaQuery = null;

function surMouvementReduit(evenement) {
  const video = videoRef.value;
  if (!video) return;
  if (evenement.matches) {
    video.pause();
  } else {
    video.play().catch(() => {});
  }
}

onMounted(() => {
  const video = videoRef.value;
  if (!video) return;

  video.play().catch(() => {});

  mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  surMouvementReduit(mediaQuery);
  mediaQuery.addEventListener("change", surMouvementReduit);
});

onUnmounted(() => {
  mediaQuery?.removeEventListener("change", surMouvementReduit);
});
</script>

<style scoped>
.scene-animation {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: min(260px, 74vw);
  line-height: 0;
  background: transparent;
  isolation: isolate;
}

.video-but {
  width: 100%;
  height: auto;
  display: block;
  object-fit: contain;
  /* Fond blanc encodé dans le MP4 : le multiply le fond sur le thème sombre. */
  mix-blend-mode: multiply;
  background: transparent;
  filter: contrast(1.1) saturate(1.06);
  -webkit-mask-image: radial-gradient(
    ellipse 94% 90% at 50% 48%,
    #000 78%,
    transparent 100%
  );
  mask-image: radial-gradient(
    ellipse 94% 90% at 50% 48%,
    #000 78%,
    transparent 100%
  );
}

@supports not (mix-blend-mode: multiply) {
  .video-but {
    mix-blend-mode: normal;
    filter: none;
  }
}

@media (max-width: 420px) {
  .scene-animation {
    width: min(200px, 68vw);
  }
}
</style>
