<script setup>
import { onMounted, ref, watch } from "vue";
import AvatarUtilisateur from "./AvatarUtilisateur.vue";
import { formaterPseudoAffichage } from "../formaterPseudo.js";
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
    <h3 class="titre-profil-public">Profil — {{ formaterPseudoAffichage(pseudo) }}</h3>
    <p v-if="chargement" class="doux">Chargement…</p>
    <p v-else-if="erreur" class="erreur">{{ erreur }}</p>
    <template v-else-if="profil">
      <div class="entete-profil-public">
        <AvatarUtilisateur
          :pseudo="profil.pseudo"
          :avatar-id="profil.avatar_id"
          :taille="48"
        />
        <div>
          <p v-if="profil.equipe_favorite" class="doux">
            Fan de <strong>{{ profil.equipe_favorite }}</strong>
          </p>
        </div>
      </div>
      <p v-if="profil.bio" class="bio-profil">{{ profil.bio }}</p>
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
          <dt>Taux d’exacts</dt>
          <dd>{{ profil.taux_exacts }} %</dd>
        </div>
        <div>
          <dt>Scores exacts</dt>
          <dd>{{ profil.nb_exacts }}</dd>
        </div>
      </dl>
      <section
        v-if="profil.vs_modele?.nb_pronos"
        class="bloc-vs-modele"
        aria-label="Comparaison au modèle"
      >
        <h4 class="titre-vs-modele">Vous vs le modèle</h4>
        <p class="doux petit">
          Sur {{ profil.vs_modele.nb_pronos }} match(s) joué(s) avec prévision figée (1X2).
        </p>
        <dl class="stats-vs-modele">
          <div>
            <dt>Vous</dt>
            <dd>
              {{ profil.vs_modele.score_utilisateur }} %
              <span class="doux petit">
                ({{ profil.vs_modele.nb_corrects_utilisateur }} bon(s))
              </span>
            </dd>
          </div>
          <div>
            <dt>Modèle</dt>
            <dd>
              {{ profil.vs_modele.score_modele }} %
              <span class="doux petit">
                ({{ profil.vs_modele.nb_corrects_modele }} bon(s))
              </span>
            </dd>
          </div>
        </dl>
      </section>
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
      <h4 v-if="profil.historique_recent?.length" class="titre-historique-public">
        Historique récent
      </h4>
      <ul v-if="profil.historique_recent?.length" class="liste-historique-public">
        <li
          v-for="(item, idx) in profil.historique_recent"
          :key="`${item.domicile}-${item.exterieur}-${idx}`"
        >
          <span>{{ item.domicile }} – {{ item.exterieur }}</span>
          <strong>{{ item.libelle }}</strong>
          <span
            v-if="item.evaluation"
            class="badge-pronostic"
            :class="item.evaluation.exact ? 'badge-exact' : 'badge-rate'"
          >
            {{ item.evaluation.exact ? "Exact" : `${item.evaluation.points} pt` }}
          </span>
          <span v-else class="doux petit">En attente</span>
        </li>
      </ul>
      <p v-else-if="!profil.nb_pronos" class="doux message-vide-communaute">
        Aucun prono public pour ce profil.
      </p>
    </template>
  </aside>
</template>
