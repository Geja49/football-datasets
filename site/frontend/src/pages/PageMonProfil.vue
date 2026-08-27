<script setup>

import { onMounted, onUnmounted, ref } from "vue";

import AvatarUtilisateur from "../composants/AvatarUtilisateur.vue";

import ChargementPage from "../composants/ChargementPage.vue";

import { urlAvatar } from "../catalogueAvatars.js";

import { formaterPseudoAffichage } from "../formaterPseudo.js";

import {

  chargerCatalogueAvatars,

  chargerProfilPublic,

  chargerUtilisateurConnecte,

  majProfilCommunaute,

  rechercher,

} from "../services/api.js";



const utilisateur = ref(null);

const bio = ref("");

const equipeFavorite = ref("");

const avatarId = ref("");

const catalogueAvatars = ref([]);

const profilPublic = ref(null);

const erreur = ref("");

const message = ref("");

const chargement = ref(true);

const envoi = ref(false);

const conteneurEquipe = ref(null);

const suggestionsEquipes = ref([]);

const indexSuggestion = ref(-1);

const listeSuggestionsOuverte = ref(false);

let delaiRecherche = null;



function dedupliquerEquipes(equipes) {

  const vus = new Set();

  const resultat = [];

  for (const item of equipes || []) {

    const nom = (item.equipe || "").trim();

    if (!nom || vus.has(nom.toLowerCase())) continue;

    vus.add(nom.toLowerCase());

    resultat.push({ equipe: nom, championnat: item.championnat || "" });

    if (resultat.length >= 8) break;

  }

  return resultat;

}



function fermerSuggestions() {

  suggestionsEquipes.value = [];

  indexSuggestion.value = -1;

  listeSuggestionsOuverte.value = false;

}



function surSaisieEquipe() {

  clearTimeout(delaiRecherche);

  indexSuggestion.value = -1;

  const q = equipeFavorite.value.trim();

  if (q.length < 2) {

    fermerSuggestions();

    return;

  }

  delaiRecherche = setTimeout(async () => {

    try {

      const reponse = await rechercher(q);

      suggestionsEquipes.value = dedupliquerEquipes(reponse.equipes);

      listeSuggestionsOuverte.value = suggestionsEquipes.value.length > 0;

    } catch {

      fermerSuggestions();

    }

  }, 300);

}



function choisirEquipe(item) {

  equipeFavorite.value = item.equipe;

  fermerSuggestions();

}



function onKeydownEquipe(event) {

  if (event.key === "Escape") {

    if (listeSuggestionsOuverte.value) {

      event.preventDefault();

      fermerSuggestions();

    }

    return;

  }

  if (!listeSuggestionsOuverte.value || !suggestionsEquipes.value.length) return;

  const nb = suggestionsEquipes.value.length;

  if (event.key === "ArrowDown") {

    event.preventDefault();

    indexSuggestion.value = (indexSuggestion.value + 1) % nb;

  } else if (event.key === "ArrowUp") {

    event.preventDefault();

    indexSuggestion.value = indexSuggestion.value <= 0 ? nb - 1 : indexSuggestion.value - 1;

  } else if (event.key === "Enter" && indexSuggestion.value >= 0) {

    event.preventDefault();

    choisirEquipe(suggestionsEquipes.value[indexSuggestion.value]);

  }

}



function onClicExterieur(event) {

  if (conteneurEquipe.value && !conteneurEquipe.value.contains(event.target)) {

    fermerSuggestions();

  }

}



async function charger() {

  chargement.value = true;

  erreur.value = "";

  try {

    const [session, catalogue] = await Promise.all([

      chargerUtilisateurConnecte(),

      chargerCatalogueAvatars(),

    ]);

    utilisateur.value = session.utilisateur;

    bio.value = session.utilisateur.bio || "";

    equipeFavorite.value = session.utilisateur.equipe_favorite || "";

    avatarId.value = session.utilisateur.avatar_id || "";

    catalogueAvatars.value = catalogue.avatars || [];

    const public_ = await chargerProfilPublic(session.utilisateur.pseudo);

    profilPublic.value = public_.profil;

  } catch (e) {

    utilisateur.value = null;

    erreur.value = e.message || "Connectez-vous pour gérer votre profil.";

  } finally {

    chargement.value = false;

  }

}



function choisirAvatar(id) {

  avatarId.value = id || "";

}



async function enregistrer() {

  envoi.value = true;

  erreur.value = "";

  message.value = "";

  try {

    const reponse = await majProfilCommunaute({

      bio: bio.value,

      equipe_favorite: equipeFavorite.value,

      avatar_id: avatarId.value,

    });

    utilisateur.value = reponse.utilisateur;

    avatarId.value = reponse.utilisateur.avatar_id || "";

    message.value = "Profil mis à jour.";

    const public_ = await chargerProfilPublic(reponse.utilisateur.pseudo);

    profilPublic.value = public_.profil;

  } catch (e) {

    erreur.value = e.message;

  } finally {

    envoi.value = false;

  }

}



onMounted(() => {

  document.addEventListener("click", onClicExterieur);

  charger();

});



onUnmounted(() => {

  document.removeEventListener("click", onClicExterieur);

  clearTimeout(delaiRecherche);

});

</script>



<template>

  <section class="hero hero-analyse">

    <div class="hero-inner">

      <header class="entete-analyse">

        <p class="sur-titre-analyse">Communauté</p>

        <h1 class="titre-analyse">Mon profil</h1>

        <p class="intro-analyse">

          Avatar, bio courte, équipe favorite et aperçu de votre historique public.

        </p>

      </header>

    </div>

  </section>



  <div class="page">

    <p v-if="erreur" class="erreur">{{ erreur }}</p>

    <p v-if="message" class="message-ok">{{ message }}</p>

    <ChargementPage v-if="chargement" message="Chargement du profil" />



    <p v-else-if="!utilisateur" class="doux">

      <router-link to="/connexion">Connectez-vous</router-link>

      pour éditer votre profil.

    </p>



    <template v-else>

      <form class="bloc formulaire-communaute" @submit.prevent="enregistrer">

        <div class="entete-profil-edition">

          <AvatarUtilisateur

            :pseudo="utilisateur.pseudo"

            :avatar-id="avatarId"

            :taille="56"

          />

          <h2>{{ formaterPseudoAffichage(utilisateur.pseudo) }}</h2>

        </div>



        <fieldset class="choix-avatars">

          <legend>Avatar</legend>

          <p class="doux petit">

            Choisissez un avatar prédéfini ou laissez vos initiales colorées.

          </p>

          <div class="grille-avatars">

            <button

              type="button"

              class="bouton-avatar"

              :class="{ actif: !avatarId }"

              title="Initiales colorées"

              @click="choisirAvatar('')"

            >

              <AvatarUtilisateur

                :pseudo="utilisateur.pseudo"

                avatar-id=""

                :taille="44"

              />

              <span class="libelle-avatar">Initiales</span>

            </button>

            <button

              v-for="item in catalogueAvatars"

              :key="item.id"

              type="button"

              class="bouton-avatar"

              :class="{ actif: avatarId === item.id }"

              :title="item.libelle"

              @click="choisirAvatar(item.id)"

            >

              <img :src="urlAvatar(item.id)" :alt="item.libelle" class="apercu-avatar" />

              <span class="libelle-avatar">{{ item.libelle }}</span>

            </button>

          </div>

        </fieldset>



        <label ref="conteneurEquipe" class="champ-filtre champ-equipe-favorite">

          Équipe favorite

          <input

            v-model="equipeFavorite"

            type="text"

            maxlength="60"

            placeholder="Ex. Barcelona"

            autocomplete="off"

            role="combobox"

            aria-autocomplete="list"

            :aria-expanded="listeSuggestionsOuverte"

            aria-controls="liste-equipes-favorite"

            @input="surSaisieEquipe"

            @keydown="onKeydownEquipe"

            @focus="surSaisieEquipe"

          />

          <ul

            v-if="listeSuggestionsOuverte"

            id="liste-equipes-favorite"

            class="liste-suggestions-equipes"

            role="listbox"

          >

            <li

              v-for="(item, i) in suggestionsEquipes"

              :key="item.equipe"

              role="option"

              :aria-selected="i === indexSuggestion"

            >

              <button

                type="button"

                :class="{ actif: i === indexSuggestion }"

                @mousedown.prevent

                @click="choisirEquipe(item)"

              >

                <span class="nom-equipe">{{ item.equipe }}</span>

                <span v-if="item.championnat" class="doux petit">{{ item.championnat }}</span>

              </button>

            </li>

          </ul>

        </label>

        <label class="champ-filtre">

          Bio

          <textarea

            v-model="bio"

            rows="3"

            maxlength="160"

            placeholder="Quelques mots sur votre façon de suivre le foot…"

          ></textarea>

          <span class="compteur-champ" aria-live="polite">{{ bio.length }}/160</span>

        </label>

        <button type="submit" class="bouton-principal" :disabled="envoi">

          {{ envoi ? "Enregistrement…" : "Enregistrer" }}

        </button>

      </form>



      <aside v-if="profilPublic" class="carte-profil-public">

        <h3 class="titre-profil-public">Aperçu public</h3>

        <div class="entete-profil-public">

          <AvatarUtilisateur

            :pseudo="profilPublic.pseudo"

            :avatar-id="profilPublic.avatar_id"

            :taille="48"

          />

          <div>

            <p class="pseudo-profil-public">

              {{ formaterPseudoAffichage(profilPublic.pseudo) }}

            </p>

            <p v-if="profilPublic.equipe_favorite" class="doux">

              Fan de <strong>{{ profilPublic.equipe_favorite }}</strong>

            </p>

          </div>

        </div>

        <p v-if="profilPublic.bio" class="bio-profil">{{ profilPublic.bio }}</p>

        <dl class="stats-profil-public">

          <div>

            <dt>Points</dt>

            <dd>{{ profilPublic.points_total }}</dd>

          </div>

          <div>

            <dt>Taux d’exacts</dt>

            <dd>{{ profilPublic.taux_exacts }} %</dd>

          </div>

          <div>

            <dt>Scores exacts</dt>

            <dd>{{ profilPublic.nb_exacts }}</dd>

          </div>

          <div>

            <dt>Pronos</dt>

            <dd>{{ profilPublic.nb_pronos }}</dd>

          </div>

        </dl>

      </aside>

    </template>

  </div>

</template>

