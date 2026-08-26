<script setup>
import { computed, ref, watch } from "vue";

const props = defineProps({
  /** Texte suivi par la tête (identifiant, e-mail ou pseudo). */
  texteSuivi: { type: String, default: "" },
  suiviActif: { type: Boolean, default: false },
  masqueMotDePasse: { type: Boolean, default: false },
  motDePasseVisible: { type: Boolean, default: false },
});

const visageRef = ref(null);

const rotationTete = computed(() => {
  if (!props.suiviActif) return "0deg";
  const longueur = Math.min(props.texteSuivi.length - 16, 19);
  return `${-longueur}deg`;
});

const classePattes = computed(() => {
  if (props.masqueMotDePasse && props.motDePasseVisible) return "apercu";
  if (props.masqueMotDePasse) return "cache";
  return "";
});

watch(
  rotationTete,
  (valeur) => {
    if (visageRef.value) {
      visageRef.value.style.setProperty("--rotation-tete", valeur);
    }
  },
  { immediate: true },
);
</script>

<template>
  <div class="avatar-chien" aria-hidden="true">
    <div class="oreille oreille-gauche"></div>
    <div class="oreille oreille-droite"></div>

    <div ref="visageRef" class="visage">
      <div class="yeux">
        <div class="oeil oeil-gauche"><div class="reflet"></div></div>
        <div class="oeil oeil-droit"><div class="reflet"></div></div>
      </div>
      <div class="nez">
        <svg width="38.161" height="22.03">
          <path
            class="nez-forme"
            d="M2.017 10.987Q-.563 7.513.157 4.754C.877 1.994 2.976.135 6.164.093 16.4-.04 22.293-.022 32.048.093c3.501.042 5.48 2.081 6.02 4.661q.54 2.579-2.051 6.233-8.612 10.979-16.664 11.043-8.053.063-17.336-11.043z"
          />
        </svg>
        <div class="reflet-nez"></div>
      </div>
      <div class="bouche">
        <svg class="sourire" viewBox="-2 -2 84 23" width="84" height="23">
          <path
            d="M0 0c3.76 9.279 9.69 18.98 26.712 19.238 17.022.258 10.72.258 28 0S75.959 9.182 79.987.161"
            fill="none"
            stroke-width="3"
            stroke-linecap="square"
            stroke-miterlimit="3"
          />
        </svg>
        <div class="trou-bouche"></div>
        <div class="langue" :class="{ respiration: !masqueMotDePasse }">
          <div class="langue-haut"></div>
          <div class="ligne-langue"></div>
          <div class="median-langue"></div>
        </div>
      </div>
    </div>

    <div class="zone-pattes">
      <div class="pattes">
        <div class="patte patte-gauche" :class="classePattes">
          <div class="doigt"><div class="os"></div><div class="ongle"></div></div>
          <div class="doigt"><div class="os"></div><div class="ongle"></div></div>
          <div class="doigt"><div class="os"></div><div class="ongle"></div></div>
        </div>
        <div class="patte patte-droite" :class="classePattes">
          <div class="doigt"><div class="os"></div><div class="ongle"></div></div>
          <div class="doigt"><div class="os"></div><div class="ongle"></div></div>
          <div class="doigt"><div class="os"></div><div class="ongle"></div></div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Animation d’origine ; couleurs Stats Foot (lisible sur carte sombre) */
.avatar-chien {
  --couleur-chien: var(--accent, #14b8a6);
  --couleur-chien-doux: color-mix(in srgb, var(--accent, #14b8a6) 55%, #0b1220);
  --couleur-patte: color-mix(in srgb, var(--accent, #14b8a6) 35%, #f4f7fb);
  position: relative;
  width: 100%;
  overflow: visible;
}

.oreille {
  position: absolute;
  top: -110px;
  width: 200px;
  height: 200px;
  border-radius: 50%;
  background-color: var(--couleur-chien);
  pointer-events: none;
}

.oreille-gauche {
  left: -135px;
}

.oreille-droite {
  right: -135px;
}

.visage {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 200px;
  height: 150px;
  margin: 80px auto 10px;
  --rotation-tete: 0deg;
  transform: rotate(var(--rotation-tete));
  transition: transform 0.2s;
  transform-origin: center 20px;
}

.oeil {
  display: inline-block;
  width: 25px;
  height: 25px;
  border-radius: 50%;
  background-color: var(--couleur-chien);
}

.oeil-gauche {
  margin-right: 40px;
}

.oeil-droit {
  margin-left: 40px;
}

.reflet {
  position: relative;
  top: 3px;
  right: -12px;
  width: 12px;
  height: 6px;
  border-radius: 50%;
  background-color: #fff;
  transform: rotate(38deg);
}

.nez {
  position: relative;
  top: 30px;
  transform: scale(1.1);
}

.nez-forme {
  fill: var(--couleur-chien);
}

.reflet-nez {
  position: absolute;
  top: 3px;
  left: 32%;
  width: 15px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--couleur-chien-doux);
}

.bouche {
  position: relative;
  margin-top: 45px;
}

.sourire {
  position: absolute;
  left: -28px;
  top: -19px;
  transform: scaleX(1.1);
  stroke: var(--couleur-chien);
}

.trou-bouche {
  position: absolute;
  top: 0;
  left: -50%;
  width: 60px;
  height: 15px;
  border-radius: 50% / 100% 100% 0% 0;
  transform: rotate(180deg);
  background-color: var(--couleur-chien);
  z-index: -1;
}

.langue {
  position: relative;
  top: 5px;
  width: 30px;
  height: 20px;
  background-color: #ffd7dd;
  transform-origin: top;
  transform: rotateX(60deg);
}

.langue.respiration {
  animation: respiration-langue 0.3s infinite linear;
}

.langue-haut {
  position: absolute;
  bottom: -15px;
  width: 30px;
  height: 30px;
  border-radius: 15px;
  background-color: #ffd7dd;
}

.ligne-langue {
  position: absolute;
  top: 0;
  width: 30px;
  height: 5px;
  background-color: #fcb7bf;
}

.median-langue {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 4px;
  height: 25px;
  border-radius: 5px;
  background-color: #fcb7bf;
}

.zone-pattes {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 0;
}

.pattes {
  position: relative;
}

.patte {
  position: absolute;
  top: -3px;
  display: flex;
  transition: transform 0.5s ease-in-out;
  z-index: 1;
}

.patte-gauche {
  left: -85px;
}

.patte-gauche.cache {
  transform: translate(2px, -155px) rotate(-160deg);
}

.patte-gauche.apercu {
  transform: translate(0px, -120px) rotate(-160deg);
}

.patte-droite {
  left: 30px;
}

.patte-droite.cache {
  transform: translate(-6px, -155px) rotate(160deg);
}

.patte-droite.apercu {
  transform: translate(-4px, -120px) rotate(160deg);
}

.doigt {
  position: relative;
  z-index: 0;
}

.doigt .os {
  width: 20px;
  height: 20px;
  border: 2px solid var(--couleur-chien);
  border-bottom: none;
  border-top: none;
  background-color: var(--couleur-patte);
}

.doigt .ongle {
  position: absolute;
  left: 0;
  top: 10px;
  width: 20px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid var(--couleur-chien);
  background-color: var(--couleur-patte);
  z-index: -1;
}

.doigt:nth-child(1),
.doigt:nth-child(3) {
  left: 4px;
  z-index: 1;
}

.doigt:nth-child(1) .os,
.doigt:nth-child(3) .os {
  height: 10px;
}

.doigt:nth-child(3) {
  left: -4px;
}

.doigt:nth-child(2) {
  top: -5px;
  z-index: 2;
}

.doigt:nth-child(1) .ongle,
.doigt:nth-child(3) .ongle {
  top: 0;
}

@keyframes respiration-langue {
  0%,
  100% {
    transform: rotateX(0deg);
  }
  50% {
    transform: rotateX(60deg);
  }
}

@media (max-width: 480px) {
  .oreille {
    width: 160px;
    height: 160px;
    top: -88px;
  }

  .oreille-gauche {
    left: -108px;
  }

  .oreille-droite {
    right: -108px;
  }

  .visage {
    margin-top: 64px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .langue.respiration {
    animation: none;
  }
}
</style>
