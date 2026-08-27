<script setup>
import { computed, nextTick, onMounted, onBeforeUnmount, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import ChargementPage from "../composants/ChargementPage.vue";
import AvatarUtilisateur from "../composants/AvatarUtilisateur.vue";
import SelecteurEmoji from "../composants/SelecteurEmoji.vue";
import BlocSondage from "../composants/BlocSondage.vue";
import { formaterDate } from "../dates.js";
import { formaterPseudoAffichage } from "../formaterPseudo.js";
import { insererEmojiDansChamp } from "../insererEmojiDansChamp.js";
import {
  basculerReactionMessageForum,
  chargerSujetForum,
  chargerUtilisateurConnecte,
  creerSondageForum,
  modifierMessageForum,
  modifierSujetForum,
  publierMessageForum,
  signalerMessageForum,
  supprimerMessageForum,
  supprimerSondageForum,
  supprimerSujetForum,
  voterSondageForum,
} from "../services/api.js";

const TYPES_REACTION_UI = [
  { cle: "pouce", libelle: "👍" },
  { cle: "coeur", libelle: "❤️" },
  { cle: "ballon", libelle: "⚽" },
  { cle: "feu", libelle: "🔥" },
  { cle: "rire", libelle: "😂" },
  { cle: "applaudir", libelle: "👏" },
];

const SEUIL_SWIPE_REPONDRE = 64;
const MAX_DECALAGE_SWIPE = 88;

const route = useRoute();
const routeur = useRouter();

const utilisateur = ref(null);
const sujet = ref(null);
const messages = ref([]);
const sondage = ref(null);
const typesReaction = ref(["pouce", "coeur", "ballon", "feu", "rire", "applaudir"]);
const erreur = ref("");
const messageOk = ref("");
const chargement = ref(true);
const envoi = ref(false);
const contenuNouveau = ref("");
const zoneFil = ref(null);
const suppressionEnCours = ref(null);

const editionTitre = ref(false);
const titreEdition = ref("");
const enregistrementTitre = ref(false);
const messageEnEdition = ref(null);
const contenuEdition = ref("");
const enregistrementMessage = ref(false);

const formulaireSondage = ref(false);
const questionSondage = ref("");
const optionsSondage = ref(["", ""]);
const envoiSondage = ref(false);
const voteSondageEnCours = ref(false);

/** Message dont le menu d'actions (réagir / répondre) est ouvert */
const messageMenuId = ref(null);
/** Affiche la palette emoji de réaction pour ce message */
const messagePaletteId = ref(null);
/** Contexte de réponse dans le composeur */
const messageReponse = ref(null);

/** Suivi swipe tactile */
const swipeActif = ref(null);
const decalagesSwipe = ref({});
let aSwipeRecemment = false;

const sujetId = computed(() => {
  const brut = Number(route.params.id);
  return Number.isFinite(brut) && brut > 0 ? brut : 0;
});

const typesReactionAffiches = computed(() =>
  TYPES_REACTION_UI.filter((t) => typesReaction.value.includes(t.cle)),
);

function formaterHeure(iso) {
  if (!iso || iso.length < 16) return "";
  return iso.slice(11, 16);
}

function formaterInstant(iso) {
  if (!iso) return "";
  const date = formaterDate(iso);
  const heure = formaterHeure(iso);
  return heure ? `${date} · ${heure}` : date;
}

function idsAuteurEgaux(a, b) {
  if (a == null || b == null) return false;
  return Number(a) === Number(b);
}

function estMonMessage(item) {
  return Boolean(
    utilisateur.value && idsAuteurEgaux(item.auteur_id, utilisateur.value.id),
  );
}

function peutModifier(auteurId) {
  if (!utilisateur.value) return false;
  return (
    idsAuteurEgaux(utilisateur.value.id, auteurId) ||
    Boolean(utilisateur.value.est_admin)
  );
}

function memeAuteurQuePrecedent(index) {
  if (index <= 0) return false;
  return idsAuteurEgaux(
    messages.value[index].auteur_id,
    messages.value[index - 1].auteur_id,
  );
}

function memeAuteurQueSuivant(index) {
  if (index >= messages.value.length - 1) return false;
  return idsAuteurEgaux(
    messages.value[index].auteur_id,
    messages.value[index + 1].auteur_id,
  );
}

function afficherPseudo(item, index) {
  if (estMonMessage(item)) return false;
  return !memeAuteurQuePrecedent(index);
}

function aReagi(item, typeReaction) {
  return (item.mes_reactions || []).includes(typeReaction);
}

function nbReaction(item, typeReaction) {
  return (item.reactions && item.reactions[typeReaction]) || 0;
}

function libelleParent(parent) {
  if (!parent) return "";
  if (parent.supprime) return "Message supprimé";
  const pseudo = formaterPseudoAffichage(parent.auteur_pseudo || "?");
  return `${pseudo} · ${parent.extrait || ""}`;
}

function decalagePour(messageId) {
  return decalagesSwipe.value[messageId] || 0;
}

function styleDecalage(messageId) {
  const dx = decalagePour(messageId);
  if (!dx) return undefined;
  return { transform: `translateX(${dx}px)` };
}

async function scrollerBas() {
  await nextTick();
  if (zoneFil.value) {
    zoneFil.value.scrollTop = zoneFil.value.scrollHeight;
  }
}

function fermerMenusMessage() {
  messageMenuId.value = null;
  messagePaletteId.value = null;
}

function basculerMenuMessage(item, event) {
  if (event) {
    const cible = event.target;
    if (
      cible &&
      typeof cible.closest === "function" &&
      cible.closest(
        "button, a, textarea, input, .menu-actions-message-forum, .palette-reaction-forum",
      )
    ) {
      return;
    }
  }
  if (aSwipeRecemment) return;
  if (messageEnEdition.value === item.id) return;
  if (messageMenuId.value === item.id) {
    fermerMenusMessage();
    return;
  }
  messageMenuId.value = item.id;
  messagePaletteId.value = null;
}

function commencerRepondre(item) {
  if (!utilisateur.value) {
    erreur.value = "Connectez-vous pour répondre.";
    return;
  }
  messageReponse.value = {
    id: item.id,
    auteur_pseudo: item.auteur_pseudo,
    extrait: (item.contenu || "").slice(0, 80),
  };
  fermerMenusMessage();
  nextTick(() => {
    const champ = document.getElementById("zone-reponse-forum");
    if (champ) champ.focus();
  });
}

function annulerRepondre() {
  messageReponse.value = null;
}

function ouvrirPaletteReaction(item) {
  if (!utilisateur.value) {
    erreur.value = "Connectez-vous pour réagir.";
    return;
  }
  messageMenuId.value = item.id;
  messagePaletteId.value =
    messagePaletteId.value === item.id ? null : item.id;
}

async function charger() {
  if (!sujetId.value) {
    throw new Error("Sujet invalide");
  }
  const reponse = await chargerSujetForum(sujetId.value);
  sujet.value = reponse.sujet;
  messages.value = reponse.messages || [];
  sondage.value = reponse.sondage || null;
  typesReaction.value =
    reponse.types_reaction ||
    ["pouce", "coeur", "ballon", "feu", "rire", "applaudir"];
  editionTitre.value = false;
  messageEnEdition.value = null;
  formulaireSondage.value = false;
  fermerMenusMessage();
  messageReponse.value = null;
  decalagesSwipe.value = {};
  await scrollerBas();
}

function commencerEditionTitre() {
  if (!sujet.value) return;
  titreEdition.value = sujet.value.titre;
  editionTitre.value = true;
  messageOk.value = "";
  erreur.value = "";
}

function annulerEditionTitre() {
  editionTitre.value = false;
  titreEdition.value = "";
}

async function enregistrerTitre() {
  enregistrementTitre.value = true;
  erreur.value = "";
  messageOk.value = "";
  try {
    const reponse = await modifierSujetForum(sujetId.value, titreEdition.value);
    sujet.value = { ...sujet.value, ...reponse.sujet };
    editionTitre.value = false;
    messageOk.value = "Titre mis à jour.";
  } catch (e) {
    erreur.value = e.message;
  } finally {
    enregistrementTitre.value = false;
  }
}

function commencerEditionMessage(item) {
  fermerMenusMessage();
  messageEnEdition.value = item.id;
  contenuEdition.value = item.contenu;
  erreur.value = "";
  messageOk.value = "";
}

function annulerEditionMessage() {
  messageEnEdition.value = null;
  contenuEdition.value = "";
}

async function insererEmojiNouveau(emoji) {
  const champ = document.getElementById("zone-reponse-forum");
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

async function insererEmojiEdition(emoji, messageId) {
  const champ = document.getElementById(`champ-message-forum-${messageId}`);
  const { valeur, position } = insererEmojiDansChamp(
    champ,
    contenuEdition.value,
    emoji,
  );
  contenuEdition.value = valeur;
  await nextTick();
  if (champ) {
    champ.focus();
    champ.setSelectionRange(position, position);
  }
}

async function enregistrerMessage(item) {
  enregistrementMessage.value = true;
  erreur.value = "";
  messageOk.value = "";
  try {
    const reponse = await modifierMessageForum(item.id, contenuEdition.value);
    const index = messages.value.findIndex((m) => m.id === item.id);
    if (index >= 0) {
      messages.value[index] = { ...messages.value[index], ...reponse.message };
    }
    messageEnEdition.value = null;
    messageOk.value = "Message mis à jour.";
  } catch (e) {
    erreur.value = e.message;
  } finally {
    enregistrementMessage.value = false;
  }
}

async function publier() {
  envoi.value = true;
  erreur.value = "";
  messageOk.value = "";
  try {
    const parentId = messageReponse.value?.id ?? null;
    const reponse = await publierMessageForum(
      sujetId.value,
      contenuNouveau.value,
      parentId,
    );
    contenuNouveau.value = "";
    messageReponse.value = null;
    messages.value = [...messages.value, reponse.message];
    if (sujet.value) {
      sujet.value = {
        ...sujet.value,
        nb_messages: (sujet.value.nb_messages || 0) + 1,
        dernier_message_le: reponse.message.cree_le,
      };
    }
    await scrollerBas();
  } catch (e) {
    erreur.value = e.message;
  } finally {
    envoi.value = false;
  }
}

async function basculerReaction(item, typeReaction) {
  if (!utilisateur.value) {
    erreur.value = "Connectez-vous pour réagir.";
    return;
  }
  try {
    const reponse = await basculerReactionMessageForum(item.id, typeReaction);
    item.reactions = reponse.reactions;
    item.mes_reactions = reponse.mes_reactions || [];
    item.nb_reactions = reponse.nb_reactions;
  } catch (e) {
    erreur.value = e.message;
  }
}

async function signaler(item) {
  if (!utilisateur.value) {
    erreur.value = "Connectez-vous pour signaler.";
    return;
  }
  try {
    await signalerMessageForum(item.id);
    messageOk.value = "Signalement enregistré. Merci.";
  } catch (e) {
    erreur.value = e.message;
  }
}

async function supprimerMessage(item) {
  if (!peutModifier(item.auteur_id)) return;
  const confirmation = window.confirm("Supprimer ce message ?");
  if (!confirmation) return;
  suppressionEnCours.value = item.id;
  erreur.value = "";
  messageOk.value = "";
  try {
    const reponse = await supprimerMessageForum(item.id);
    if (reponse.sujet_supprime) {
      const champ = sujet.value?.championnat;
      messageOk.value = "Sujet supprimé.";
      if (champ) {
        await routeur.push(`/forum/${encodeURIComponent(champ)}`);
      } else {
        await routeur.push("/forum");
      }
      return;
    }
    messages.value = messages.value.filter((m) => m.id !== item.id);
    if (sujet.value) {
      sujet.value = {
        ...sujet.value,
        nb_messages: Math.max(0, (sujet.value.nb_messages || 1) - 1),
      };
    }
    if (messageEnEdition.value === item.id) {
      annulerEditionMessage();
    }
    if (messageReponse.value?.id === item.id) {
      annulerRepondre();
    }
    if (messageMenuId.value === item.id) {
      fermerMenusMessage();
    }
    messageOk.value = "Message supprimé.";
  } catch (e) {
    erreur.value = e.message;
  } finally {
    suppressionEnCours.value = null;
  }
}

async function supprimerSujet() {
  if (!sujet.value || !peutModifier(sujet.value.auteur_id)) return;
  const confirmation = window.confirm(
    "Supprimer tout le sujet et ses messages ?",
  );
  if (!confirmation) return;
  erreur.value = "";
  messageOk.value = "";
  try {
    await supprimerSujetForum(sujetId.value);
    const champ = sujet.value.championnat;
    await routeur.push(`/forum/${encodeURIComponent(champ)}`);
  } catch (e) {
    erreur.value = e.message;
  }
}

function ouvrirFormulaireSondage() {
  formulaireSondage.value = true;
  questionSondage.value = "";
  optionsSondage.value = ["", ""];
  erreur.value = "";
  messageOk.value = "";
}

function annulerFormulaireSondage() {
  formulaireSondage.value = false;
  questionSondage.value = "";
  optionsSondage.value = ["", ""];
}

function ajouterOptionSondage() {
  if (optionsSondage.value.length >= 6) return;
  optionsSondage.value = [...optionsSondage.value, ""];
}

function retirerOptionSondage(index) {
  if (optionsSondage.value.length <= 2) return;
  optionsSondage.value = optionsSondage.value.filter((_, i) => i !== index);
}

async function creerSondage() {
  envoiSondage.value = true;
  erreur.value = "";
  messageOk.value = "";
  try {
    const options = optionsSondage.value.map((o) => o.trim()).filter(Boolean);
    const reponse = await creerSondageForum(
      sujetId.value,
      questionSondage.value.trim(),
      options,
    );
    sondage.value = reponse.sondage;
    formulaireSondage.value = false;
    messageOk.value = "Sondage créé.";
  } catch (e) {
    erreur.value = e.message;
  } finally {
    envoiSondage.value = false;
  }
}

async function voterSondage(optionId) {
  if (!utilisateur.value || !sondage.value) return;
  voteSondageEnCours.value = true;
  erreur.value = "";
  try {
    const reponse = await voterSondageForum(sondage.value.id, optionId);
    sondage.value = reponse.sondage;
  } catch (e) {
    erreur.value = e.message;
  } finally {
    voteSondageEnCours.value = false;
  }
}

async function supprimerSondage() {
  if (!sondage.value || !peutModifier(sondage.value.auteur_id)) return;
  const confirmation = window.confirm("Supprimer ce sondage ?");
  if (!confirmation) return;
  envoiSondage.value = true;
  erreur.value = "";
  try {
    await supprimerSondageForum(sondage.value.id);
    sondage.value = null;
    messageOk.value = "Sondage supprimé.";
  } catch (e) {
    erreur.value = e.message;
  } finally {
    envoiSondage.value = false;
  }
}

function surDebutTouche(item, event) {
  if (!utilisateur.value || messageEnEdition.value === item.id) return;
  const touche = event.changedTouches?.[0];
  if (!touche) return;
  swipeActif.value = {
    id: item.id,
    x0: touche.clientX,
    y0: touche.clientY,
    item,
    horizontal: null,
  };
}

function surMouvementTouche(event) {
  const etat = swipeActif.value;
  if (!etat) return;
  const touche = event.changedTouches?.[0] || event.touches?.[0];
  if (!touche) return;
  const dx = touche.clientX - etat.x0;
  const dy = touche.clientY - etat.y0;
  if (etat.horizontal === null) {
    if (Math.abs(dx) < 8 && Math.abs(dy) < 8) return;
    etat.horizontal = Math.abs(dx) > Math.abs(dy);
    if (!etat.horizontal) {
      swipeActif.value = null;
      return;
    }
  }
  if (!etat.horizontal) return;
  event.preventDefault();
  const lim = Math.max(-MAX_DECALAGE_SWIPE, Math.min(MAX_DECALAGE_SWIPE, dx));
  decalagesSwipe.value = { ...decalagesSwipe.value, [etat.id]: lim };
}

function surFinTouche() {
  const etat = swipeActif.value;
  if (!etat) return;
  const dx = decalagePour(etat.id);
  swipeActif.value = null;
  decalagesSwipe.value = { ...decalagesSwipe.value, [etat.id]: 0 };
  if (Math.abs(dx) >= SEUIL_SWIPE_REPONDRE) {
    aSwipeRecemment = true;
    commencerRepondre(etat.item);
    setTimeout(() => {
      aSwipeRecemment = false;
    }, 350);
  }
}

function surToucheClavierMessage(item, event) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    basculerMenuMessage(item);
  } else if (event.key === "Escape") {
    fermerMenusMessage();
  } else if (event.key === "r" || event.key === "R") {
    if (utilisateur.value) {
      event.preventDefault();
      commencerRepondre(item);
    }
  }
}

function surClicDocument(event) {
  if (!messageMenuId.value) return;
  const cible = event.target;
  if (
    cible &&
    typeof cible.closest === "function" &&
    cible.closest(".rangee-message-forum, .menu-actions-message-forum")
  ) {
    return;
  }
  fermerMenusMessage();
}

onMounted(async () => {
  document.addEventListener("click", surClicDocument, true);
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

onBeforeUnmount(() => {
  document.removeEventListener("click", surClicDocument, true);
});

watch(
  () => route.params.id,
  async () => {
    chargement.value = true;
    erreur.value = "";
    messageOk.value = "";
    try {
      await charger();
    } catch (e) {
      erreur.value = e.message;
      sujet.value = null;
      messages.value = [];
      sondage.value = null;
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
        <template v-if="editionTitre">
          <form class="formulaire-edition-titre-forum" @submit.prevent="enregistrerTitre">
            <label class="libelle-edition-forum" for="champ-titre-sujet-forum">
              Titre du sujet
            </label>
            <input
              id="champ-titre-sujet-forum"
              v-model="titreEdition"
              type="text"
              maxlength="120"
              required
              class="champ-titre-forum"
              autocomplete="off"
            />
            <div class="actions-edition-forum">
              <button
                type="submit"
                class="bouton-principal"
                :disabled="enregistrementTitre"
              >
                Enregistrer
              </button>
              <button
                type="button"
                class="bouton-secondaire"
                :disabled="enregistrementTitre"
                @click="annulerEditionTitre"
              >
                Annuler
              </button>
            </div>
          </form>
        </template>
        <template v-else>
          <h1 class="titre-analyse">{{ sujet?.titre || "Sujet" }}</h1>
          <p v-if="sujet" class="intro-analyse">
            {{ sujet.championnat }} · par {{ formaterPseudoAffichage(sujet.auteur_pseudo) }}
            <span v-if="sujet.modifie" class="badge-modifie-forum"> · modifié</span>
          </p>
          <div v-if="sujet && peutModifier(sujet.auteur_id)" class="actions-sujet-forum">
            <button
              type="button"
              class="bouton-modifier-forum"
              @click="commencerEditionTitre"
            >
              Modifier le titre
            </button>
            <button
              type="button"
              class="bouton-supprimer-forum"
              @click="supprimerSujet"
            >
              Supprimer le sujet
            </button>
          </div>
        </template>
      </header>
    </div>
  </section>

  <div class="page page-forum page-forum-sujet">
    <p v-if="sujet" class="fil-forum">
      <router-link to="/forum">Forum</router-link>
      <span aria-hidden="true"> / </span>
      <router-link :to="`/forum/${encodeURIComponent(sujet.championnat)}`">
        {{ sujet.championnat }}
      </router-link>
      <span aria-hidden="true"> / </span>
      <span>{{ sujet.titre }}</span>
    </p>

    <p v-if="erreur" class="erreur">{{ erreur }}</p>
    <p v-if="messageOk" class="message-ok">{{ messageOk }}</p>
    <ChargementPage v-if="chargement" message="Chargement du sujet" />

    <template v-else-if="sujet">
      <div v-if="sondage" class="zone-sondage-forum">
        <BlocSondage
          :question="sondage.question"
          :options="sondage.options"
          :a-vote="sondage.a_vote"
          :mon-cle="sondage.mon_option_id"
          :nb-votes-total="sondage.nb_votes_total"
          :connecte="Boolean(utilisateur)"
          :envoi="voteSondageEnCours || envoiSondage"
          :peut-supprimer="peutModifier(sondage.auteur_id)"
          cle-option="id"
          @voter="voterSondage"
          @supprimer="supprimerSondage"
        />
      </div>

      <div
        v-else-if="utilisateur && !formulaireSondage"
        class="actions-creer-sondage"
      >
        <button
          type="button"
          class="bouton-secondaire"
          @click="ouvrirFormulaireSondage"
        >
          Ajouter un sondage
        </button>
      </div>

      <form
        v-else-if="utilisateur && formulaireSondage"
        class="formulaire-creer-sondage"
        @submit.prevent="creerSondage"
      >
        <h2 class="titre-formulaire-sondage">Nouveau sondage</h2>
        <label class="champ-filtre" for="question-sondage-forum">
          Question
          <input
            id="question-sondage-forum"
            v-model="questionSondage"
            type="text"
            maxlength="160"
            required
            autocomplete="off"
          />
        </label>
        <div
          v-for="(_, index) in optionsSondage"
          :key="index"
          class="rangee-option-sondage"
        >
          <label class="champ-filtre" :for="`option-sondage-forum-${index}`">
            Option {{ index + 1 }}
            <input
              :id="`option-sondage-forum-${index}`"
              v-model="optionsSondage[index]"
              type="text"
              maxlength="80"
              required
              autocomplete="off"
            />
          </label>
          <button
            v-if="optionsSondage.length > 2"
            type="button"
            class="bouton-retirer-option"
            @click="retirerOptionSondage(index)"
          >
            Retirer
          </button>
        </div>
        <div class="actions-edition-forum">
          <button
            type="button"
            class="bouton-secondaire"
            :disabled="optionsSondage.length >= 6 || envoiSondage"
            @click="ajouterOptionSondage"
          >
            Ajouter une option
          </button>
          <button
            type="submit"
            class="bouton-principal"
            :disabled="envoiSondage"
          >
            Publier le sondage
          </button>
          <button
            type="button"
            class="bouton-secondaire"
            :disabled="envoiSondage"
            @click="annulerFormulaireSondage"
          >
            Annuler
          </button>
        </div>
      </form>

      <div class="cadre-chat-forum">
        <div ref="zoneFil" class="fil-messages-forum" role="log" aria-live="polite">
          <article
            v-for="(item, index) in messages"
            :key="item.id"
            class="rangee-message-forum"
            :class="[
              estMonMessage(item) ? 'message-moi' : 'message-autre',
              {
                'groupe-suite': memeAuteurQuePrecedent(index),
                'groupe-fin': !memeAuteurQueSuivant(index),
                'menu-ouvert': messageMenuId === item.id,
              },
            ]"
            :style="styleDecalage(item.id)"
            @touchstart.passive="surDebutTouche(item, $event)"
            @touchmove="surMouvementTouche"
            @touchend="surFinTouche"
            @touchcancel="surFinTouche"
          >
            <AvatarUtilisateur
              v-if="afficherPseudo(item, index)"
              class="avatar-message-forum"
              :class="estMonMessage(item) ? 'avatar-moi' : 'avatar-autre'"
              :pseudo="item.auteur_pseudo"
              :avatar-id="item.auteur_avatar_id"
              :taille="32"
            />
            <div
              v-else
              class="avatar-message-forum avatar-placeholder"
              aria-hidden="true"
            />
            <div
              class="bulle-message-forum"
              :class="estMonMessage(item) ? 'bulle-moi' : 'bulle-autre'"
              role="button"
              tabindex="0"
              :aria-expanded="messageMenuId === item.id"
              :aria-label="`Message de ${formaterPseudoAffichage(item.auteur_pseudo)}. Entrée pour actions, R pour répondre.`"
              @click="basculerMenuMessage(item, $event)"
              @keydown="surToucheClavierMessage(item, $event)"
            >
              <strong
                v-if="afficherPseudo(item, index)"
                class="pseudo-message-forum"
              >
                {{ formaterPseudoAffichage(item.auteur_pseudo) }}
              </strong>

              <div
                v-if="item.message_parent"
                class="citation-reponse-forum"
                :title="libelleParent(item.message_parent)"
              >
                <span class="citation-reponse-libelle">En réponse à</span>
                <strong v-if="!item.message_parent.supprime">
                  {{ formaterPseudoAffichage(item.message_parent.auteur_pseudo) }}
                </strong>
                <span class="citation-reponse-extrait">
                  {{ item.message_parent.extrait }}
                </span>
              </div>

              <template v-if="messageEnEdition === item.id">
                <form
                  class="formulaire-edition-message-forum"
                  @submit.prevent="enregistrerMessage(item)"
                >
                  <label class="libelle-edition-forum" :for="`champ-message-forum-${item.id}`">
                    Message
                  </label>
                  <div class="rang-saisie-emoji">
                    <textarea
                      :id="`champ-message-forum-${item.id}`"
                      v-model="contenuEdition"
                      class="zone-message-forum champ-edition-message-forum"
                      maxlength="1000"
                      rows="4"
                      required
                    />
                    <SelecteurEmoji
                      :cible-id="`champ-message-forum-${item.id}`"
                      :disabled="enregistrementMessage"
                      @inserer="(emoji) => insererEmojiEdition(emoji, item.id)"
                    />
                  </div>
                  <div class="actions-edition-forum">
                    <button
                      type="submit"
                      class="bouton-principal"
                      :disabled="enregistrementMessage"
                    >
                      Enregistrer
                    </button>
                    <button
                      type="button"
                      class="bouton-secondaire"
                      :disabled="enregistrementMessage"
                      @click="annulerEditionMessage"
                    >
                      Annuler
                    </button>
                  </div>
                </form>
              </template>
              <template v-else>
                <p class="corps-message-forum">{{ item.contenu }}</p>
                <time class="heure-message-forum" :datetime="item.cree_le">
                  {{ formaterHeure(item.cree_le) || formaterInstant(item.cree_le) }}
                  <span v-if="item.modifie"> · modifié</span>
                </time>
              </template>

              <div
                v-if="messageMenuId === item.id && messageEnEdition !== item.id"
                class="menu-actions-message-forum"
                role="toolbar"
                aria-label="Actions sur le message"
                @click.stop
              >
                <button
                  type="button"
                  class="bouton-menu-message"
                  :disabled="!utilisateur"
                  @click="ouvrirPaletteReaction(item)"
                >
                  Réagir
                </button>
                <button
                  type="button"
                  class="bouton-menu-message"
                  :disabled="!utilisateur"
                  @click="commencerRepondre(item)"
                >
                  Répondre
                </button>
                <div
                  v-if="messagePaletteId === item.id"
                  class="palette-reaction-forum"
                  role="group"
                  aria-label="Choisir une réaction"
                >
                  <button
                    v-for="typeR in typesReactionAffiches"
                    :key="typeR.cle"
                    type="button"
                    class="bouton-reaction"
                    :class="{ actif: aReagi(item, typeR.cle) }"
                    :title="typeR.libelle"
                    :aria-pressed="aReagi(item, typeR.cle)"
                    @click="basculerReaction(item, typeR.cle)"
                  >
                    <span aria-hidden="true">{{ typeR.libelle }}</span>
                  </button>
                </div>
              </div>

              <footer class="actions-message-forum">
                <button
                  v-for="typeR in typesReactionAffiches.filter(
                    (t) => nbReaction(item, t.cle) > 0 || aReagi(item, t.cle),
                  )"
                  :key="typeR.cle"
                  type="button"
                  class="bouton-reaction"
                  :class="{ actif: aReagi(item, typeR.cle) }"
                  :title="aReagi(item, typeR.cle) ? 'Retirer la réaction' : 'Réagir'"
                  :disabled="!utilisateur"
                  @click.stop="basculerReaction(item, typeR.cle)"
                >
                  <span aria-hidden="true">{{ typeR.libelle }}</span>
                  <span class="compteur-reaction">{{ nbReaction(item, typeR.cle) }}</span>
                </button>
                <button
                  v-if="peutModifier(item.auteur_id) && messageEnEdition !== item.id"
                  type="button"
                  class="bouton-modifier-forum"
                  @click.stop="commencerEditionMessage(item)"
                >
                  Modifier
                </button>
                <button
                  v-if="peutModifier(item.auteur_id)"
                  type="button"
                  class="bouton-supprimer-forum"
                  :disabled="suppressionEnCours === item.id"
                  @click.stop="supprimerMessage(item)"
                >
                  Supprimer
                </button>
                <button
                  v-if="!estMonMessage(item)"
                  type="button"
                  class="bouton-signaler-forum"
                  :disabled="!utilisateur"
                  @click.stop="signaler(item)"
                >
                  Signaler
                </button>
              </footer>
            </div>
          </article>
          <p v-if="!messages.length" class="doux">Aucun message.</p>
        </div>

        <form
          v-if="utilisateur"
          class="formulaire-reponse-forum"
          @submit.prevent="publier"
        >
          <div
            v-if="messageReponse"
            class="bandeau-reponse-forum"
            role="status"
          >
            <div class="bandeau-reponse-texte">
              <span class="bandeau-reponse-titre">
                Réponse à {{ formaterPseudoAffichage(messageReponse.auteur_pseudo) }}
              </span>
              <span class="bandeau-reponse-extrait">{{ messageReponse.extrait }}</span>
            </div>
            <button
              type="button"
              class="bouton-annuler-reponse"
              aria-label="Annuler la réponse"
              @click="annulerRepondre"
            >
              Annuler
            </button>
          </div>
          <label class="visuellement-cache" for="zone-reponse-forum">
            Votre message
          </label>
          <div class="rang-saisie-emoji rang-saisie-chat">
            <textarea
              id="zone-reponse-forum"
              v-model="contenuNouveau"
              class="zone-message-forum zone-saisie-chat"
              maxlength="1000"
              rows="2"
              required
              placeholder="Écrire un message…"
            />
            <SelecteurEmoji
              cible-id="zone-reponse-forum"
              :disabled="envoi"
              @inserer="insererEmojiNouveau"
            />
          </div>
          <button type="submit" class="bouton-principal bouton-envoyer-chat" :disabled="envoi">
            Envoyer
          </button>
        </form>
        <p v-else class="doux barre-connexion-forum">
          <router-link to="/connexion">Connectez-vous</router-link>
          pour répondre.
        </p>
      </div>
    </template>
  </div>
</template>
