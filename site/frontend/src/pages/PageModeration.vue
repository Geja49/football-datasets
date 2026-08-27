<script setup>
import { onMounted, ref } from "vue";
import ChargementPage from "../composants/ChargementPage.vue";
import { formaterPseudoAffichage } from "../formaterPseudo.js";
import {
  chargerSignalementsAdmin,
  chargerUtilisateurConnecte,
  supprimerCommentaireMatch,
  traiterSignalementAdmin,
} from "../services/api.js";

const utilisateur = ref(null);
const signalements = ref([]);
const erreur = ref("");
const message = ref("");
const chargement = ref(true);
const filtre = ref("ouvert");

async function charger() {
  chargement.value = true;
  erreur.value = "";
  try {
    const reponse = await chargerSignalementsAdmin(filtre.value);
    signalements.value = reponse.signalements || [];
  } catch (e) {
    erreur.value = e.message;
    signalements.value = [];
  } finally {
    chargement.value = false;
  }
}

async function traiter(id) {
  try {
    await traiterSignalementAdmin(id, "traite");
    message.value = "Signalement marqué comme traité.";
    await charger();
  } catch (e) {
    erreur.value = e.message;
  }
}

async function supprimerEtTraiter(item) {
  try {
    if (!item.supprime) {
      await supprimerCommentaireMatch(item.commentaire_id);
    }
    await traiterSignalementAdmin(item.id, "traite");
    message.value = "Commentaire supprimé et signalement traité.";
    await charger();
  } catch (e) {
    erreur.value = e.message;
  }
}

onMounted(async () => {
  try {
    const session = await chargerUtilisateurConnecte();
    utilisateur.value = session.utilisateur;
    if (!session.utilisateur.est_admin) {
      erreur.value = "Accès réservé aux administrateurs.";
      chargement.value = false;
      return;
    }
  } catch {
    utilisateur.value = null;
    erreur.value = "Connexion admin requise.";
    chargement.value = false;
    return;
  }
  await charger();
});
</script>

<template>
  <section class="hero hero-analyse">
    <div class="hero-inner">
      <header class="entete-analyse">
        <p class="sur-titre-analyse">Communauté</p>
        <h1 class="titre-analyse">Modération</h1>
        <p class="intro-analyse">
          File des signalements — traiter ou supprimer un commentaire abusif.
        </p>
      </header>
    </div>
  </section>

  <div class="page">
    <p v-if="erreur" class="erreur">{{ erreur }}</p>
    <p v-if="message" class="message-ok">{{ message }}</p>
    <ChargementPage v-if="chargement" message="Chargement de la modération" />

    <template v-else-if="utilisateur?.est_admin">
      <label class="champ-filtre">
        Statut
        <select v-model="filtre" @change="charger">
          <option value="ouvert">Ouverts</option>
          <option value="traite">Traités</option>
          <option value="tous">Tous</option>
        </select>
      </label>

      <p v-if="!signalements.length" class="doux message-vide-communaute">
        Aucun signalement {{ filtre === "ouvert" ? "ouvert" : "" }} pour le moment.
      </p>

      <ul v-else class="liste-signalements">
        <li v-for="item in signalements" :key="item.id" class="carte-signalement">
          <header class="entete-commentaire">
            <strong>{{ formaterPseudoAffichage(item.auteur_commentaire) }}</strong>
            <span class="doux petit">{{ item.statut }}</span>
          </header>
          <p class="texte-commentaire">{{ item.contenu }}</p>
          <p class="doux petit">
            {{ item.match.domicile }} – {{ item.match.exterieur }}
            ({{ item.match.championnat }})
            · signalé par {{ item.pseudo_signalant ? formaterPseudoAffichage(item.pseudo_signalant) : "—" }}
            <template v-if="item.motif"> · motif : {{ item.motif }}</template>
          </p>
          <div class="actions-commentaire" v-if="item.statut === 'ouvert'">
            <button type="button" class="lien-action" @click="traiter(item.id)">
              Marquer traité
            </button>
            <button
              type="button"
              class="lien-action lien-danger"
              @click="supprimerEtTraiter(item)"
            >
              Supprimer le commentaire
            </button>
          </div>
        </li>
      </ul>
    </template>
  </div>
</template>
