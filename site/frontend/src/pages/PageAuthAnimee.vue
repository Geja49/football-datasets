<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import AvatarChienAuth from "../composants/AvatarChienAuth.vue";
import {
  chargerConfigCommunaute,
  connecterGoogle,
  connecterUtilisateur,
  inscrireUtilisateur,
} from "../services/api.js";

const route = useRoute();
const routeur = useRouter();

const modeInscription = computed(() => route.path === "/inscription");

const identifiant = ref("");
const motDePasseConnexion = ref("");
const email = ref("");
const pseudo = ref("");
const motDePasseInscription = ref("");
const age18Plus = ref(false);
const cguAcceptees = ref(false);

const erreur = ref("");
const chargement = ref(false);
const oauthGoogleActif = ref(false);
const chargementGoogle = ref(false);
const motDePasseVisible = ref(false);

const champSuiviFocus = ref(false);
const champMotDePasseFocus = ref(false);
const texteSuiviActif = ref("");

let scriptGoogle = null;
let lienIcones = null;

function queryRetour() {
  return route.query.retour ? { retour: route.query.retour } : {};
}

function destinationApresAuth() {
  const retour = route.query.retour;
  if (typeof retour === "string" && retour.startsWith("/")) {
    return retour;
  }
  return "/match";
}

function activerSuivi(texte) {
  champSuiviFocus.value = true;
  champMotDePasseFocus.value = false;
  texteSuiviActif.value = texte;
}

function majSuivi(texte) {
  texteSuiviActif.value = texte;
}

function desactiverSuivi() {
  champSuiviFocus.value = false;
}

function activerMasqueMotDePasse() {
  champMotDePasseFocus.value = true;
  champSuiviFocus.value = false;
}

function desactiverMasqueMotDePasse() {
  champMotDePasseFocus.value = false;
}

function basculerVisibiliteMotDePasse() {
  motDePasseVisible.value = !motDePasseVisible.value;
}

watch(
  () => route.path,
  () => {
    erreur.value = "";
    champSuiviFocus.value = false;
    champMotDePasseFocus.value = false;
    motDePasseVisible.value = false;
    texteSuiviActif.value = "";
  },
);

async function soumettreConnexion() {
  erreur.value = "";
  chargement.value = true;
  try {
    await connecterUtilisateur({
      identifiant: identifiant.value.trim(),
      mot_de_passe: motDePasseConnexion.value,
    });
    routeur.push(destinationApresAuth());
  } catch (e) {
    erreur.value = e.message;
  } finally {
    chargement.value = false;
  }
}

async function soumettreInscription() {
  erreur.value = "";
  if (!age18Plus.value) {
    erreur.value = "Vous devez confirmer avoir 18 ans ou plus.";
    return;
  }
  if (!cguAcceptees.value) {
    erreur.value = "Vous devez accepter les conditions d'utilisation.";
    return;
  }
  chargement.value = true;
  try {
    await inscrireUtilisateur({
      email: email.value.trim(),
      pseudo: pseudo.value.trim(),
      mot_de_passe: motDePasseInscription.value,
      age_18_plus: age18Plus.value,
      cgu_acceptees: cguAcceptees.value,
    });
    routeur.push(destinationApresAuth());
  } catch (e) {
    erreur.value = e.message;
  } finally {
    chargement.value = false;
  }
}

function allerInscription() {
  routeur.push({ path: "/inscription", query: queryRetour() });
}

function allerConnexion() {
  routeur.push({ path: "/connexion", query: queryRetour() });
}

function initialiserBoutonGoogle(clientId) {
  if (!window.google?.accounts?.id || !document.getElementById("bouton-google-auth")) {
    return;
  }
  window.google.accounts.id.initialize({
    client_id: clientId,
    callback: async (reponse) => {
      if (!reponse?.credential) return;
      erreur.value = "";
      chargementGoogle.value = true;
      try {
        await connecterGoogle(reponse.credential);
        routeur.push(destinationApresAuth());
      } catch (e) {
        erreur.value = e.message;
      } finally {
        chargementGoogle.value = false;
      }
    },
  });
  window.google.accounts.id.renderButton(document.getElementById("bouton-google-auth"), {
    theme: "filled_black",
    size: "large",
    text: "continue_with",
    locale: "fr",
    width: 280,
  });
}

function chargerScriptGoogle(clientId) {
  if (scriptGoogle) {
    initialiserBoutonGoogle(clientId);
    return;
  }
  scriptGoogle = document.createElement("script");
  scriptGoogle.src = "https://accounts.google.com/gsi/client";
  scriptGoogle.async = true;
  scriptGoogle.defer = true;
  scriptGoogle.onload = () => initialiserBoutonGoogle(clientId);
  document.head.appendChild(scriptGoogle);
}

function chargerStylesExternes() {
  lienIcones = document.createElement("link");
  lienIcones.rel = "stylesheet";
  lienIcones.href = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.1.2/css/all.min.css";
  document.head.appendChild(lienIcones);
}

onMounted(async () => {
  chargerStylesExternes();
  try {
    const config = await chargerConfigCommunaute();
    oauthGoogleActif.value = Boolean(config.oauth_google_actif);
    if (config.oauth_google_actif && config.google_client_id) {
      chargerScriptGoogle(config.google_client_id);
    }
  } catch {
    oauthGoogleActif.value = false;
  }
});

onUnmounted(() => {
  scriptGoogle = null;
  lienIcones?.remove();
});
</script>

<template>
  <div class="page-auth-animee" :class="{ 'mode-inscription': modeInscription }">
    <div class="fond-sobre" aria-hidden="true"></div>

    <div class="scene-auth">
      <div class="carte-auth">
        <AvatarChienAuth
          :texte-suivi="texteSuiviActif"
          :suivi-actif="champSuiviFocus"
          :masque-mot-de-passe="champMotDePasseFocus"
          :mot-de-passe-visible="motDePasseVisible"
        />

        <div class="piste-panneaux">
          <section class="panneau panneau-connexion" aria-label="Connexion">
            <div class="contenu-panneau">
              <h1 class="titre-auth">Connexion</h1>
              <p class="sous-titre-auth">Stats Foot</p>

              <p v-if="erreur && !modeInscription" class="erreur">{{ erreur }}</p>

              <div v-if="oauthGoogleActif" class="bloc-oauth">
                <div id="bouton-google-auth" class="conteneur-bouton-google"></div>
                <p v-if="chargementGoogle" class="doux">Connexion Google…</p>
                <p class="separateur-auth">ou avec pseudo / e-mail</p>
              </div>

              <form class="formulaire-auth" @submit.prevent="soumettreConnexion">
                <label class="boite-champ">
                  <i class="fas fa-user" aria-hidden="true"></i>
                  <input
                    v-model="identifiant"
                    class="champ-texte"
                    type="text"
                    required
                    autocomplete="username"
                    placeholder="Pseudo ou e-mail"
                    @focus="activerSuivi(identifiant)"
                    @blur="desactiverSuivi"
                    @input="majSuivi($event.target.value)"
                  />
                </label>

                <label class="boite-champ">
                  <i class="fas fa-lock" aria-hidden="true"></i>
                  <input
                    v-model="motDePasseConnexion"
                    class="champ-texte champ-mdp"
                    :type="motDePasseVisible ? 'text' : 'password'"
                    required
                    minlength="8"
                    autocomplete="current-password"
                    placeholder="Mot de passe"
                    @focus="activerMasqueMotDePasse"
                    @blur="desactiverMasqueMotDePasse"
                  />
                  <button
                    type="button"
                    class="bouton-visibilite"
                    @mousedown.prevent
                    @click="basculerVisibiliteMotDePasse"
                  >
                    {{ motDePasseVisible ? "cacher" : "voir" }}
                  </button>
                </label>

                <button type="submit" class="bouton-auth" :disabled="chargement">
                  {{ chargement && !modeInscription ? "Connexion…" : "Se connecter" }}
                </button>
              </form>

              <p class="pied-auth">
                Pas encore de compte ?
                <button type="button" class="lien-pied" @click="allerInscription">S'inscrire</button>
              </p>
              <p class="pied-auth pied-secondaire">
                <router-link class="lien-pied" to="/conditions">Conditions</router-link>
              </p>
            </div>
          </section>

          <section class="panneau panneau-inscription" aria-label="Inscription">
            <div class="contenu-panneau">
              <h1 class="titre-auth">Inscription</h1>
              <p class="sous-titre-auth">Stats Foot</p>

              <p v-if="erreur && modeInscription" class="erreur">{{ erreur }}</p>

              <form class="formulaire-auth" @submit.prevent="soumettreInscription">
                <label class="boite-champ">
                  <i class="fas fa-envelope" aria-hidden="true"></i>
                  <input
                    v-model="email"
                    class="champ-texte"
                    type="email"
                    required
                    autocomplete="email"
                    placeholder="E-mail"
                    @focus="activerSuivi(email)"
                    @blur="desactiverSuivi"
                    @input="majSuivi($event.target.value)"
                  />
                </label>

                <label class="boite-champ">
                  <i class="fas fa-user" aria-hidden="true"></i>
                  <input
                    v-model="pseudo"
                    class="champ-texte"
                    type="text"
                    required
                    minlength="3"
                    maxlength="30"
                    autocomplete="username"
                    pattern="[A-Za-z0-9_\-\s]{3,30}"
                    placeholder="Pseudo"
                    @focus="activerSuivi(pseudo)"
                    @blur="desactiverSuivi"
                    @input="majSuivi($event.target.value)"
                  />
                </label>

                <label class="boite-champ">
                  <i class="fas fa-lock" aria-hidden="true"></i>
                  <input
                    v-model="motDePasseInscription"
                    class="champ-texte champ-mdp"
                    :type="motDePasseVisible ? 'text' : 'password'"
                    required
                    minlength="8"
                    autocomplete="new-password"
                    placeholder="Mot de passe"
                    @focus="activerMasqueMotDePasse"
                    @blur="desactiverMasqueMotDePasse"
                  />
                  <button
                    type="button"
                    class="bouton-visibilite"
                    @mousedown.prevent
                    @click="basculerVisibiliteMotDePasse"
                  >
                    {{ motDePasseVisible ? "cacher" : "voir" }}
                  </button>
                </label>

                <label class="case-auth">
                  <input v-model="age18Plus" type="checkbox" required />
                  J'ai 18 ans ou plus
                </label>

                <label class="case-auth">
                  <input v-model="cguAcceptees" type="checkbox" required />
                  J'accepte les
                  <router-link to="/conditions">conditions</router-link>
                </label>

                <button type="submit" class="bouton-auth" :disabled="chargement">
                  {{ chargement && modeInscription ? "Création…" : "Créer mon compte" }}
                </button>
              </form>

              <p class="pied-auth">
                Déjà un compte ?
                <button type="button" class="lien-pied" @click="allerConnexion">Se connecter</button>
              </p>
            </div>
          </section>
        </div>
      </div>

      <p class="mention-auth">
        Contenu informatif — pas un conseil en paris. 18+.
      </p>
    </div>
  </div>
</template>

<style scoped>
/* Structure Avatar-Animation-Login-Page ; couleurs Stats Foot (variables du site) */
.page-auth-animee {
  position: relative;
  min-height: calc(100vh - 140px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 16px;
  overflow: hidden;
  isolation: isolate;
  font-family: Manrope, "Segoe UI", sans-serif;
}

.fond-sobre {
  position: absolute;
  inset: 0;
  z-index: 0;
  background:
    radial-gradient(ellipse 55% 40% at 50% 0%, color-mix(in srgb, var(--accent) 14%, transparent), transparent 60%),
    var(--fond);
}

.scene-auth {
  position: relative;
  z-index: 2;
  width: min(380px, 100%);
}

.carte-auth {
  position: relative;
  overflow: hidden;
  border-radius: 12px;
  background: var(--fond-carte);
  border: 1px solid var(--ligne);
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.45);
}

.piste-panneaux {
  display: flex;
  width: 200%;
  transition: transform 0.55s cubic-bezier(0.4, 0, 0.2, 1);
  transform: translateX(0);
}

.page-auth-animee.mode-inscription .piste-panneaux {
  transform: translateX(-50%);
}

.panneau {
  width: 50%;
  flex-shrink: 0;
  padding: 8px 28px 28px;
  box-sizing: border-box;
}

.contenu-panneau {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.titre-auth {
  margin: 0;
  font-family: Oswald, Impact, sans-serif;
  font-size: 1.45rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-align: center;
  text-transform: uppercase;
  color: var(--texte);
}

.sous-titre-auth {
  margin: -6px 0 4px;
  text-align: center;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--accent);
}

.formulaire-auth {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.boite-champ {
  position: relative;
  display: block;
  width: 100%;
  padding: 0.375rem 0.75rem;
  font-weight: 400;
  line-height: 1.5;
  color: var(--texte);
  background-color: var(--fond-lisible);
  border: 1px solid var(--ligne);
  border-radius: 10px;
  margin: 1px;
  box-sizing: border-box;
  transition: border-color 0.15s ease;
}

.boite-champ:focus-within {
  border-color: var(--accent);
  outline: 2px solid color-mix(in srgb, var(--accent) 35%, transparent);
  outline-offset: 1px;
}

.boite-champ .fas {
  position: absolute;
  top: 32%;
  left: 16px;
  font-size: 1.1rem;
  color: var(--accent);
  pointer-events: none;
}

.champ-texte {
  width: 100%;
  height: 35px;
  border: none;
  border-radius: 10px;
  font-size: 1rem;
  font-family: inherit;
  padding: 0 12px 0 36px;
  margin: 5px 0;
  box-shadow: none;
  outline: none;
  background: transparent;
  color: var(--texte);
  box-sizing: border-box;
}

.champ-mdp {
  padding-right: 90px;
}

.champ-texte::placeholder {
  color: var(--texte-doux);
  text-transform: capitalize;
}

.bouton-visibilite {
  position: absolute;
  top: 15px;
  right: 10px;
  display: flex;
  justify-content: center;
  align-items: center;
  width: 80px;
  height: 27px;
  border-radius: 10px;
  border: none;
  outline: none;
  background-color: var(--accent);
  color: #041016;
  font: inherit;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  text-transform: capitalize;
}

.bouton-visibilite:hover {
  filter: brightness(1.08);
}

.bouton-visibilite:active {
  transform: scale(0.95);
}

.bouton-auth {
  width: 100%;
  height: 35px;
  margin: 12px 0 0;
  border: none;
  border-radius: 10px;
  outline: none;
  background-color: var(--accent);
  color: #041016;
  font: inherit;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  text-transform: capitalize;
  transition: filter 0.15s, transform 0.1s, opacity 0.15s;
}

.bouton-auth:hover:not(:disabled) {
  filter: brightness(1.08);
}

.bouton-auth:active:not(:disabled) {
  transform: scale(0.95);
}

.bouton-auth:disabled {
  opacity: 0.65;
  cursor: wait;
}

.pied-auth {
  margin: 8px 0 0;
  text-align: center;
  font-size: 0.95rem;
  color: var(--texte-doux);
}

.pied-secondaire {
  margin-top: 4px;
  font-size: 0.85rem;
}

.lien-pied {
  background: none;
  border: none;
  padding: 0;
  color: var(--accent);
  font: inherit;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  transition: color 0.2s ease-in-out, filter 0.2s;
}

.lien-pied:hover {
  filter: brightness(1.15);
  color: var(--texte);
}

.case-auth {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 4px;
  color: var(--texte-doux);
  font-size: 0.88rem;
  line-height: 1.35;
  text-transform: none;
}

.case-auth a {
  color: var(--accent);
  font-weight: 600;
}

.case-auth a:hover {
  color: var(--texte);
}

.bloc-oauth {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.separateur-auth {
  margin: 4px 0 0;
  color: var(--texte-doux);
  font-size: 0.85rem;
  text-transform: none;
}

.erreur {
  margin: 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: color-mix(in srgb, #b91c1c 22%, var(--fond-lisible));
  border: 1px solid color-mix(in srgb, #f87171 40%, transparent);
  color: #fecaca;
  font-size: 0.9rem;
  text-transform: none;
}

.doux {
  margin: 0;
  color: var(--texte-doux);
  font-size: 0.85rem;
  text-transform: none;
}

.mention-auth {
  margin: 16px 8px 0;
  text-align: center;
  color: var(--texte-doux);
  font-size: 0.8rem;
}

.mention-auth::before {
  content: "";
  display: inline-block;
  width: 8px;
  height: 8px;
  margin-right: 6px;
  border-radius: 50%;
  background: var(--accent);
  vertical-align: middle;
}

@media (max-width: 480px) {
  .page-auth-animee {
    padding-top: 36px;
  }

  .panneau {
    padding: 4px 18px 22px;
  }

  .titre-auth {
    font-size: 1.2rem;
  }
}
</style>
