<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { CHAMPIONNATS_DEFAUT } from "../championnats.js";
import { formaterPseudoAffichage } from "../formaterPseudo.js";
import ChargementPage from "../composants/ChargementPage.vue";
import SelecteurEmoji from "../composants/SelecteurEmoji.vue";
import { insererEmojiDansChamp } from "../insererEmojiDansChamp.js";
import {
  chargerAccueil,
  chargerClassementLigue,
  chargerJourneesPronos,
  chargerLiguePrivee,
  chargerMessagesLigue,
  chargerMesLigues,
  chargerUtilisateurConnecte,
  creerLiguePrivee,
  publierMessageLigue,
  rejoindreLiguePrivee,
} from "../services/api.js";

const route = useRoute();
const routeur = useRouter();

const utilisateur = ref(null);
const ligues = ref([]);
const ligueActive = ref(null);
const membres = ref([]);
const classement = ref([]);
const messages = ref([]);
const nouveauMessage = ref("");
const reglePoints = ref("");
const erreur = ref("");
const message = ref("");
const chargement = ref(true);
const envoi = ref(false);
const envoiMessage = ref(false);
const lienCopie = ref("");

const nomNouvelle = ref("");
const codeRejoindre = ref("");

const championnats = ref([...CHAMPIONNATS_DEFAUT]);
const championnat = ref("La Liga");
const saison = ref("2026-2027");
const saisons = ref(["2026-2027"]);
const journees = ref([]);
const journee = ref("");

const codeRoute = computed(() => {
  const brut = route.params.code;
  return brut ? String(brut).toUpperCase() : "";
});

const urlInvitation = computed(() => {
  if (!ligueActive.value) return "";
  const base = typeof window !== "undefined" ? window.location.origin : "";
  return `${base}/ligue/${ligueActive.value.code_invitation}`;
});

async function chargerMeta() {
  try {
    const accueil = await chargerAccueil();
    if (accueil?.championnats?.length) {
      championnats.value = accueil.championnats.map((c) => c.nom);
    }
    if (accueil?.saison_courante) {
      saison.value = accueil.saison_courante;
      if (!saisons.value.includes(accueil.saison_courante)) {
        saisons.value.unshift(accueil.saison_courante);
      }
    }
  } catch {
    /* défaut */
  }
}

async function chargerListe() {
  const reponse = await chargerMesLigues();
  ligues.value = reponse.ligues || [];
  reglePoints.value = reponse.regle_points || "";
}

async function chargerJournees() {
  try {
    const reponse = await chargerJourneesPronos(championnat.value, saison.value);
    journees.value = reponse.journees || [];
    if (journee.value && !journees.value.includes(journee.value)) {
      journee.value = "";
    }
  } catch {
    journees.value = [];
  }
}

async function chargerDetail(code) {
  const detail = await chargerLiguePrivee(code);
  ligueActive.value = detail.ligue;
  membres.value = detail.membres || [];
  reglePoints.value = detail.regle_points || reglePoints.value;
  await Promise.all([chargerClassement(), chargerMessages(), chargerJournees()]);
}

async function chargerClassement() {
  if (!ligueActive.value) {
    classement.value = [];
    return;
  }
  const reponse = await chargerClassementLigue(
    ligueActive.value.code_invitation,
    championnat.value,
    saison.value,
    journee.value || "",
  );
  classement.value = reponse.classement || [];
}

async function chargerMessages() {
  if (!ligueActive.value) {
    messages.value = [];
    return;
  }
  const reponse = await chargerMessagesLigue(ligueActive.value.code_invitation);
  messages.value = reponse.messages || [];
}

async function creer() {
  envoi.value = true;
  erreur.value = "";
  message.value = "";
  try {
    const reponse = await creerLiguePrivee(nomNouvelle.value);
    nomNouvelle.value = "";
    message.value = `Ligue créée — code : ${reponse.ligue.code_invitation}`;
    await chargerListe();
    routeur.push(`/ligue/${reponse.ligue.code_invitation}`);
  } catch (e) {
    erreur.value = e.message;
  } finally {
    envoi.value = false;
  }
}

async function rejoindre() {
  envoi.value = true;
  erreur.value = "";
  message.value = "";
  try {
    const reponse = await rejoindreLiguePrivee(codeRejoindre.value);
    codeRejoindre.value = "";
    message.value = `Vous avez rejoint « ${reponse.ligue.nom} »`;
    await chargerListe();
    routeur.push(`/ligue/${reponse.ligue.code_invitation}`);
  } catch (e) {
    erreur.value = e.message;
  } finally {
    envoi.value = false;
  }
}

async function copierLien() {
  if (!urlInvitation.value) return;
  try {
    await navigator.clipboard.writeText(urlInvitation.value);
    lienCopie.value = "Lien copié !";
    setTimeout(() => {
      lienCopie.value = "";
    }, 2000);
  } catch {
    lienCopie.value = urlInvitation.value;
  }
}

async function envoyerMessage() {
  if (!ligueActive.value || !nouveauMessage.value.trim()) return;
  envoiMessage.value = true;
  erreur.value = "";
  try {
    await publierMessageLigue(ligueActive.value.code_invitation, nouveauMessage.value);
    nouveauMessage.value = "";
    await chargerMessages();
  } catch (e) {
    erreur.value = e.message;
  } finally {
    envoiMessage.value = false;
  }
}

async function insererEmojiMessageLigue(emoji) {
  const champ = document.getElementById("champ-message-ligue");
  const { valeur, position } = insererEmojiDansChamp(
    champ,
    nouveauMessage.value,
    emoji,
  );
  nouveauMessage.value = valeur;
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
    erreur.value = "Connectez-vous pour gérer vos ligues privées.";
    chargement.value = false;
    return;
  }

  await chargerMeta();
  try {
    await chargerListe();
    if (codeRoute.value) {
      await chargerDetail(codeRoute.value);
    }
  } catch (e) {
    erreur.value = e.message;
  } finally {
    chargement.value = false;
  }
});

watch(
  () => route.params.code,
  async (code) => {
    if (!utilisateur.value) return;
    erreur.value = "";
    if (!code) {
      ligueActive.value = null;
      membres.value = [];
      classement.value = [];
      messages.value = [];
      return;
    }
    chargement.value = true;
    try {
      await chargerDetail(String(code).toUpperCase());
    } catch (e) {
      erreur.value = e.message;
      ligueActive.value = null;
    } finally {
      chargement.value = false;
    }
  },
);

watch([championnat, saison], async () => {
  await chargerJournees();
  if (ligueActive.value) {
    chargerClassement().catch((e) => {
      erreur.value = e.message;
    });
  }
});

watch(journee, () => {
  if (ligueActive.value) {
    chargerClassement().catch((e) => {
      erreur.value = e.message;
    });
  }
});
</script>

<template>
  <section class="hero hero-analyse">
    <div class="hero-inner">
      <header class="entete-analyse">
        <p class="sur-titre-analyse">Communauté</p>
        <h1 class="titre-analyse">Ligues privées</h1>
        <p class="intro-analyse">
          Créez une ligue entre amis ou rejoignez-en une par lien — ludique, sans gain.
        </p>
      </header>
    </div>
  </section>

  <div class="page">
    <p v-if="reglePoints" class="mention">{{ reglePoints }}</p>

    <p v-if="erreur" class="erreur">{{ erreur }}</p>
    <p v-if="message" class="message-ok">{{ message }}</p>
    <ChargementPage v-if="chargement" message="Chargement des ligues" />

    <p v-else-if="!utilisateur" class="doux">
      <router-link to="/connexion">Connectez-vous</router-link>
      ou
      <router-link to="/inscription">créez un compte</router-link>.
    </p>

    <template v-else>
      <div class="grille-ligues-actions">
        <form class="bloc formulaire-communaute" @submit.prevent="creer">
          <h2>Créer une ligue</h2>
          <label class="champ-filtre">
            Nom
            <input
              v-model="nomNouvelle"
              type="text"
              maxlength="40"
              minlength="3"
              required
              placeholder="Ex. Copains du dimanche"
            />
          </label>
          <button type="submit" class="bouton-principal" :disabled="envoi">
            Créer
          </button>
        </form>

        <form class="bloc formulaire-communaute" @submit.prevent="rejoindre">
          <h2>Rejoindre</h2>
          <label class="champ-filtre">
            Code d'invitation
            <input
              v-model="codeRejoindre"
              type="text"
              maxlength="12"
              required
              placeholder="Ex. AB12CD34"
              class="input-code-ligue"
            />
          </label>
          <button type="submit" class="bouton-principal" :disabled="envoi">
            Rejoindre
          </button>
        </form>
      </div>

      <section class="bloc" v-if="ligues.length">
        <h2>Mes ligues</h2>
        <ul class="liste-ligues">
          <li v-for="ligue in ligues" :key="ligue.id">
            <router-link
              :to="`/ligue/${ligue.code_invitation}`"
              class="lien-ligue"
              :class="{ actif: ligueActive?.id === ligue.id }"
            >
              <strong>{{ ligue.nom }}</strong>
              <span class="doux petit">
                Code {{ ligue.code_invitation }} · {{ ligue.nb_membres }} membre(s)
              </span>
            </router-link>
          </li>
        </ul>
      </section>

      <section v-if="ligueActive" class="bloc bloc-detail-ligue">
        <h2>{{ ligueActive.nom }}</h2>
        <p class="doux">
          Code invitation :
          <strong class="code-invitation">{{ ligueActive.code_invitation }}</strong>
          — créé par {{ formaterPseudoAffichage(ligueActive.createur_pseudo) }}
        </p>
        <div class="barre-lien-invitation">
          <code class="lien-invitation-texte">{{ urlInvitation }}</code>
          <button type="button" class="lien-action" @click="copierLien">
            Copier le lien
          </button>
          <span v-if="lienCopie" class="message-ok petit">{{ lienCopie }}</span>
        </div>

        <h3>Membres</h3>
        <ul class="liste-membres-ligue">
          <li v-for="m in membres" :key="m.utilisateur_id">{{ formaterPseudoAffichage(m.pseudo) }}</li>
        </ul>

        <div class="filtres-analyse filtres-ligue">
          <label class="champ-filtre">
            <span class="doux">Championnat</span>
            <select v-model="championnat">
              <option v-for="c in championnats" :key="c" :value="c">{{ c }}</option>
            </select>
          </label>
          <label class="champ-filtre">
            <span class="doux">Saison</span>
            <select v-model="saison">
              <option v-for="s in saisons" :key="s" :value="s">{{ s }}</option>
            </select>
          </label>
          <label class="champ-filtre">
            <span class="doux">Journée</span>
            <select v-model="journee">
              <option value="">Saison entière</option>
              <option v-for="j in journees" :key="j" :value="j">Journée {{ j }}</option>
            </select>
          </label>
        </div>

        <h3>
          Classement
          <span v-if="journee" class="doux">— journée {{ journee }}</span>
        </h3>
        <p v-if="!classement.length" class="doux message-vide-communaute">
          Aucun prono évalué pour ce filtre parmi les membres.
        </p>
        <div v-else class="bloc-classement-pronos">
          <table class="table-classement-pronos">
            <thead>
              <tr>
                <th scope="col">#</th>
                <th scope="col">Pseudo</th>
                <th scope="col">Points</th>
                <th scope="col">Pronos</th>
                <th scope="col">Exacts</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="ligne in classement"
                :key="ligne.utilisateur_id"
                :class="{ 'ligne-top3': ligne.rang <= 3 }"
              >
                <td class="col-rang">{{ ligne.rang }}</td>
                <td>{{ formaterPseudoAffichage(ligne.pseudo) }}</td>
                <td class="col-points">{{ ligne.points }}</td>
                <td>{{ ligne.nb_pronos }}</td>
                <td>{{ ligne.nb_exacts }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <h3>Chat de la ligue</h3>
        <ul class="liste-messages-ligue">
          <li v-for="msg in messages" :key="msg.id" class="message-ligue">
            <strong>{{ formaterPseudoAffichage(msg.pseudo) }}</strong>
            <span class="texte-commentaire">{{ msg.contenu }}</span>
          </li>
        </ul>
        <p v-if="!messages.length" class="doux">Aucun message — dites bonjour.</p>
        <form class="formulaire-message-ligue" @submit.prevent="envoyerMessage">
          <label class="champ-filtre champ-message-ligue-emoji">
            Message
            <div class="rang-saisie-emoji">
              <input
                id="champ-message-ligue"
                v-model="nouveauMessage"
                type="text"
                maxlength="300"
                required
                placeholder="Message court (sans lien)…"
              />
              <SelecteurEmoji
                cible-id="champ-message-ligue"
                :disabled="envoiMessage"
                @inserer="insererEmojiMessageLigue"
              />
            </div>
          </label>
          <button type="submit" class="bouton-principal" :disabled="envoiMessage">
            Envoyer
          </button>
        </form>
      </section>

      <p class="doux petit lien-mes-pronos">
        <router-link to="/pronos-journee">Pronos journée</router-link>
        ·
        <router-link to="/classement-pronos">Classement public</router-link>
      </p>
    </template>
  </div>
</template>
