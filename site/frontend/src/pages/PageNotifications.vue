<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import ChargementPage from "../composants/ChargementPage.vue";
import {
  chargerNotifications,
  chargerUtilisateurConnecte,
  marquerNotificationLue,
  marquerToutesNotificationsLues,
} from "../services/api.js";

const routeur = useRouter();
const utilisateur = ref(null);
const notifications = ref([]);
const nbNonLues = ref(0);
const erreur = ref("");
const chargement = ref(true);

function formaterDate(iso) {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("fr-FR", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function charger() {
  chargement.value = true;
  erreur.value = "";
  try {
    const reponse = await chargerNotifications();
    notifications.value = reponse.notifications || [];
    nbNonLues.value = reponse.nb_non_lues || 0;
  } catch (e) {
    erreur.value = e.message;
  } finally {
    chargement.value = false;
  }
}

async function ouvrir(notif) {
  try {
    if (!notif.lue) {
      await marquerNotificationLue(notif.id);
      notif.lue = true;
      nbNonLues.value = Math.max(0, nbNonLues.value - 1);
    }
  } catch {
    /* ignore */
  }
  if (notif.lien) {
    routeur.push(notif.lien);
  }
}

async function toutLire() {
  try {
    await marquerToutesNotificationsLues();
    notifications.value = notifications.value.map((n) => ({ ...n, lue: true }));
    nbNonLues.value = 0;
  } catch (e) {
    erreur.value = e.message;
  }
}

onMounted(async () => {
  try {
    const session = await chargerUtilisateurConnecte();
    utilisateur.value = session.utilisateur;
  } catch {
    utilisateur.value = null;
    erreur.value = "Connectez-vous pour voir vos notifications.";
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
        <h1 class="titre-analyse">Notifications</h1>
        <p class="intro-analyse">
          Rappels avant coup d’envoi, résultats de pronos et réponses aux commentaires.
        </p>
      </header>
    </div>
  </section>

  <div class="page">
    <p v-if="erreur" class="erreur">{{ erreur }}</p>
    <ChargementPage v-if="chargement" message="Chargement des notifications" />

    <p v-else-if="!utilisateur" class="doux">
      <router-link to="/connexion">Connectez-vous</router-link>
      pour accéder à vos notifications.
    </p>

    <template v-else>
      <div class="barre-actions-notif">
        <p class="doux" v-if="nbNonLues">{{ nbNonLues }} non lue(s)</p>
        <p class="doux" v-else>Tout est à jour</p>
        <button
          v-if="nbNonLues"
          type="button"
          class="lien-action"
          @click="toutLire"
        >
          Tout marquer comme lu
        </button>
      </div>

      <p v-if="!notifications.length" class="doux message-vide-communaute">
        Aucune notification pour l’instant. Les rappels de match et résultats
        apparaîtront ici.
      </p>

      <ul v-else class="liste-notifications">
        <li
          v-for="notif in notifications"
          :key="notif.id"
          class="carte-notification"
          :class="{ 'non-lue': !notif.lue }"
        >
          <button type="button" class="bouton-notif" @click="ouvrir(notif)">
            <span class="titre-notif">{{ notif.titre }}</span>
            <span v-if="notif.corps" class="corps-notif">{{ notif.corps }}</span>
            <time class="doux petit">{{ formaterDate(notif.cree_le) }}</time>
          </button>
        </li>
      </ul>
    </template>
  </div>
</template>
