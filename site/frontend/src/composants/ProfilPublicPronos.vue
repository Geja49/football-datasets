<script setup>
import { onMounted, ref, watch } from "vue";
import { chargerProfilPublic } from "../services/api.js";

const props = defineProps({
  pseudo: { type: String, required: true },
});

const profil = ref(null);
const erreur = ref("");
const chargement = ref(true);

async function charger() {
  if (!props.pseudo) return;
  chargement.value = true;
  erreur.value = "";
  try {
    const reponse = await chargerProfilPublic(props.pseudo);
    profil.value = reponse.profil;
  } catch (e) {
    erreur.value = e.message;
    profil.value = null;
  } finally {
    chargement.value = false;
  }
}

onMounted(charger);
watch(() => props.pseudo, charger);
</script>

<template>
  <aside v-if="pseudo" class="carte-profil-public">
    <h3 class="titre-profil-public">Profil — {{ pseudo }}</h3>
    <p v-if="chargement" class="doux">Chargement…</p>
    <p v-else-if="erreur" class="erreur">{{ erreur }}</p>
    <template v-else-if="profil">
      <dl class="stats-profil-public">
        <div>
          <dt>Points totaux</dt>
          <dd>{{ profil.points_total }}</dd>
        </div>
        <div>
          <dt>Pronostics</dt>
          <dd>{{ profil.nb_pronos }}</dd>
        </div>
        <div>
          <dt>Matchs évalués</dt>
          <dd>{{ profil.nb_evalues }}</dd>
        </div>
        <div>
          <dt>Scores exacts</dt>
          <dd>{{ profil.nb_exacts }}</dd>
        </div>
      </dl>
      <p v-if="profil.badges?.length" class="badges-profil">
        <span v-for="badge in profil.badges" :key="badge" class="badge-classement">
          {{ badge }}
        </span>
      </p>
      <ul v-if="profil.par_championnat?.length" class="liste-par-championnat">
        <li v-for="entree in profil.par_championnat" :key="`${entree.championnat}-${entree.saison}`">
          {{ entree.championnat }} {{ entree.saison }} —
          {{ entree.points }} pt(s), {{ entree.nb_pronos }} prono(s)
        </li>
      </ul>
    </template>
  </aside>
</template>
