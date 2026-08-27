<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import ChargementPage from "../composants/ChargementPage.vue";
import SelecteurEmoji from "../composants/SelecteurEmoji.vue";
import { formaterDate } from "../dates.js";
import { formaterPseudoAffichage } from "../formaterPseudo.js";
import { insererEmojiDansChamp } from "../insererEmojiDansChamp.js";
import {
  chargerSujetsForum,
  chargerUtilisateurConnecte,
  creerSujetForum,
} from "../services/api.js";

const route = useRoute();
const routeur = useRouter();

const utilisateur = ref(null);
const sujets = ref([]);
const erreur = ref("");
const message = ref("");
const chargement = ref(true);
const envoi = ref(false);

const titreNouveau = ref("");
const contenuNouveau = ref("");

const championnat = computed(() => {
  const brut = route.params.championnat;
  return brut ? decodeURIComponent(String(brut)) : "";
});

function formaterInstant(iso) {
  if (!iso) return "";
  const date = formaterDate(iso);
  const heure = iso.length >= 16 ? iso.slice(11, 16) : "";
  return heure ? `${date} · ${heure}` : date;
}

async function charger() {
  if (!championnat.value) return;
  const reponse = await chargerSujetsForum(championnat.value);
  sujets.value = reponse.sujets || [];
}

async function creerSujet() {
  envoi.value = true;
  erreur.value = "";
  message.value = "";
  try {
    const reponse = await creerSujetForum(
      championnat.value,
      titreNouveau.value,
      contenuNouveau.value,
    );
    titreNouveau.value = "";
    contenuNouveau.value = "";
    message.value = "Sujet créé";
    await charger();
    routeur.push(`/forum/sujet/${reponse.sujet.id}`);
  } catch (e) {
    erreur.value = e.message;
  } finally {
    envoi.value = false;
  }
}

async function insererEmojiPremierMessage(emoji) {
  const champ = document.getElementById("zone-premier-message-forum");
  const { valeur, position } = insererEmojiDansChamp(
    champ,
    contenuNouveau.value,
    emoji,
  );
  contenuNouveau.value = valeur;
  await nextTick();
  if (champ) {
    champ.focus();
    champ.setSelectionRange(position, position);
  }
}

onMounted(async () => {
  try {
    const session = await chargerUtilisateurConnecte();
    utilisateur.value = session.utilisateur;
  } catch {
    utilisateur.value = null;
  }
  try {
    await charger();
  } catch (e) {
    erreur.value = e.message;
  } finally {
    chargement.value = false;
  }
});

watch(
  () => route.params.championnat,
  async () => {
    chargement.value = true;
    erreur.value = "";
    try {
      await charger();
    } catch (e) {
      erreur.value = e.message;
      sujets.value = [];
    } finally {
      chargement.value = false;
    }
  },
);
</script>

<template>
  <section class="hero hero-analyse">
    <div class="hero-inner">
      <header class="entete-analyse">
        <p class="sur-titre-analyse">Forum</p>
        <h1 class="titre-analyse">{{ championnat }}</h1>
        <p class="intro-analyse">
          Sujets du championnat — style fil chronologique, sans paris.
        </p>
      </header>
    </div>
  </section>

  <div class="page page-forum">
    <p class="fil-forum">
      <router-link to="/forum">Forum</router-link>
      <span aria-hidden="true"> / </span>
      <span>{{ championnat }}</span>
    </p>

    <p v-if="erreur" class="erreur">{{ erreur }}</p>
    <p v-if="message" class="message-ok">{{ message }}</p>
    <ChargementPage v-if="chargement" message="Chargement des sujets" />

    <template v-else>
      <section v-if="utilisateur" class="bloc formulaire-communaute">
        <h2>Nouveau sujet</h2>
        <form @submit.prevent="creerSujet">
          <label class="champ-filtre">
            Titre
            <input
              v-model="titreNouveau"
              type="text"
              maxlength="120"
              required
              placeholder="Ex. Forme des équipes ce week-end"
            />
          </label>
          <label class="champ-filtre">
            Premier message
            <div class="rang-saisie-emoji">
              <textarea
                id="zone-premier-message-forum"
                v-model="contenuNouveau"
                class="zone-message-forum"
                maxlength="1000"
                rows="4"
                required
                placeholder="Votre message…"
              />
              <SelecteurEmoji
                cible-id="zone-premier-message-forum"
                :disabled="envoi"
                @inserer="insererEmojiPremierMessage"
              />
            </div>
          </label>
          <button type="submit" class="bouton-principal" :disabled="envoi">
            Publier
          </button>
        </form>
      </section>
      <p v-else class="doux">
        <router-link to="/connexion">Connectez-vous</router-link>
        pour créer un sujet.
      </p>

      <section class="bloc">
        <h2>Sujets</h2>
        <p v-if="!sujets.length" class="doux">Aucun sujet pour l’instant.</p>
        <ul v-else class="liste-sujets-forum">
          <li v-for="sujet in sujets" :key="sujet.id">
            <router-link
              class="lien-sujet-forum"
              :to="`/forum/sujet/${sujet.id}`"
            >
              <strong class="titre-sujet-forum">{{ sujet.titre }}</strong>
              <span class="meta-sujet-forum doux petit">
                {{ formaterPseudoAffichage(sujet.auteur_pseudo) }} · {{ sujet.nb_messages }} msg ·
                dernier {{ formaterInstant(sujet.dernier_message_le) }}
              </span>
            </router-link>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>
