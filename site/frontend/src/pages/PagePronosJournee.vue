<script setup>
import { onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { CHAMPIONNATS_DEFAUT } from "../championnats.js";
import ChargementPage from "../composants/ChargementPage.vue";
import {
  chargerAccueil,
  chargerJourneesPronos,
  chargerPronosJournee,
  chargerUtilisateurConnecte,
  deposerPronostic,
  deposerPronosticsLot,
} from "../services/api.js";

const route = useRoute();
const routeur = useRouter();

const championnats = ref([...CHAMPIONNATS_DEFAUT]);
const championnat = ref("La Liga");
const saison = ref("2026-2027");
const saisons = ref(["2026-2027"]);
const journees = ref([]);
const journee = ref("");
const matchs = ref([]);
const reglePoints = ref("");
const erreur = ref("");
const message = ref("");
const chargement = ref(true);
const utilisateur = ref(null);
const envoiId = ref(null);
const envoiLot = ref(false);

/** Formulaire compact par match : clé domicile|exterieur */
const formulaires = ref({});

function cleMatch(match) {
  return `${match.domicile}|${match.exterieur}`;
}

function initFormulaire(match) {
  const prono = match.pronostic;
  if (prono) {
    return {
      type_pronostic: prono.type_pronostic,
      buts_domicile: prono.buts_domicile ?? 0,
      buts_exterieur: prono.buts_exterieur ?? 0,
      resultat_1x2: prono.resultat_1x2 || "1",
    };
  }
  return {
    type_pronostic: "1x2",
    buts_domicile: 0,
    buts_exterieur: 0,
    resultat_1x2: "1",
  };
}

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
    /* valeurs par défaut */
  }
}

async function chargerListeJournees() {
  try {
    const reponse = await chargerJourneesPronos(championnat.value, saison.value);
    journees.value = reponse.journees || [];
    if (!journees.value.includes(journee.value)) {
      journee.value = journees.value[0] || "";
    }
  } catch (e) {
    journees.value = [];
    erreur.value = e.message;
  }
}

async function chargerMatchs() {
  if (!utilisateur.value || !journee.value) {
    matchs.value = [];
    return;
  }
  chargement.value = true;
  erreur.value = "";
  try {
    const reponse = await chargerPronosJournee(
      championnat.value,
      saison.value,
      journee.value,
    );
    matchs.value = reponse.matchs || [];
    reglePoints.value = reponse.regle_points || "";
    const forms = {};
    for (const match of matchs.value) {
      forms[cleMatch(match)] = initFormulaire(match);
    }
    formulaires.value = forms;
  } catch (e) {
    matchs.value = [];
    erreur.value = e.message;
  } finally {
    chargement.value = false;
  }
}

async function soumettreProno(match) {
  const form = formulaires.value[cleMatch(match)];
  if (!form) return;
  envoiId.value = cleMatch(match);
  erreur.value = "";
  message.value = "";
  try {
    const corps = {
      championnat: match.championnat,
      saison: match.saison,
      domicile: match.domicile,
      exterieur: match.exterieur,
      type_pronostic: form.type_pronostic,
    };
    if (form.type_pronostic === "score") {
      corps.buts_domicile = Number(form.buts_domicile);
      corps.buts_exterieur = Number(form.buts_exterieur);
    } else {
      corps.resultat_1x2 = form.resultat_1x2;
    }
    await deposerPronostic(corps);
    message.value = `Pronostic enregistré : ${match.domicile} – ${match.exterieur}`;
    await chargerMatchs();
  } catch (e) {
    erreur.value = e.message;
  } finally {
    envoiId.value = null;
  }
}

async function soumettreJournee() {
  const ouverts = matchs.value.filter((m) => !m.verrouille && !m.match_deja_joue);
  if (!ouverts.length) {
    erreur.value = "Aucun match ouvert à enregistrer pour cette journée.";
    return;
  }
  envoiLot.value = true;
  erreur.value = "";
  message.value = "";
  try {
    const lot = ouverts.map((match) => {
      const form = formulaires.value[cleMatch(match)];
      const corps = {
        championnat: match.championnat,
        saison: match.saison,
        domicile: match.domicile,
        exterieur: match.exterieur,
        type_pronostic: form.type_pronostic,
      };
      if (form.type_pronostic === "score") {
        corps.buts_domicile = Number(form.buts_domicile);
        corps.buts_exterieur = Number(form.buts_exterieur);
      } else {
        corps.resultat_1x2 = form.resultat_1x2;
      }
      return corps;
    });
    const reponse = await deposerPronosticsLot(lot);
    message.value = `${reponse.nb_ok} prono(s) enregistré(s)`;
    if (reponse.nb_erreurs) {
      erreur.value = `${reponse.nb_erreurs} match(s) non enregistrés`;
    }
    await chargerMatchs();
  } catch (e) {
    erreur.value = e.message;
  } finally {
    envoiLot.value = false;
  }
}

onMounted(async () => {
  if (route.query.championnat) championnat.value = String(route.query.championnat);
  if (route.query.saison) saison.value = String(route.query.saison);
  if (route.query.journee) journee.value = String(route.query.journee);

  try {
    const session = await chargerUtilisateurConnecte();
    utilisateur.value = session.utilisateur;
  } catch {
    utilisateur.value = null;
    erreur.value = "Connectez-vous pour déposer des pronos de journée.";
    chargement.value = false;
    return;
  }

  await chargerMeta();
  await chargerListeJournees();
  await chargerMatchs();
});

watch([championnat, saison], async () => {
  routeur.replace({
    path: route.path,
    query: {
      championnat: championnat.value,
      saison: saison.value,
      ...(journee.value ? { journee: journee.value } : {}),
    },
  });
  await chargerListeJournees();
  await chargerMatchs();
});

watch(journee, () => {
  routeur.replace({
    path: route.path,
    query: {
      championnat: championnat.value,
      saison: saison.value,
      journee: journee.value,
    },
  });
  chargerMatchs();
});
</script>

<template>
  <section class="hero hero-analyse">
    <div class="hero-inner">
      <header class="entete-analyse">
        <p class="sur-titre-analyse">Communauté</p>
        <h1 class="titre-analyse">Pronos journée</h1>
        <p class="intro-analyse">
          Déposez plusieurs prévisions pour une journée.
        </p>
      </header>

      <div v-if="utilisateur" class="filtres-analyse">
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
          <select v-model="journee" :disabled="!journees.length">
            <option v-for="j in journees" :key="j" :value="j">Journée {{ j }}</option>
          </select>
        </label>
      </div>
    </div>
  </section>

  <div class="page">
    <p v-if="reglePoints" class="mention">{{ reglePoints }}</p>

    <p v-if="erreur" class="erreur">{{ erreur }}</p>
    <p v-if="message" class="message-ok">{{ message }}</p>
    <ChargementPage v-if="chargement" message="Chargement des pronos" />

    <p v-else-if="!utilisateur" class="doux">
      <router-link to="/connexion">Connectez-vous</router-link>
      ou
      <router-link to="/inscription">créez un compte</router-link>.
    </p>

    <p v-else-if="!matchs.length" class="doux message-vide-communaute">
      Aucun match pour cette journée — choisissez une autre journée ou un autre championnat.
    </p>

    <template v-else>
      <div class="barre-actions-journee">
        <button
          type="button"
          class="bouton-principal"
          :disabled="envoiLot"
          @click="soumettreJournee"
        >
          {{ envoiLot ? "Enregistrement…" : "Enregistrer toute la journée" }}
        </button>
        <p class="doux petit">
          Enregistre tous les matchs encore ouverts avec les scores saisis ci-dessous.
        </p>
      </div>

    <ul class="liste-pronos-journee">
      <li v-for="match in matchs" :key="cleMatch(match)" class="carte-prono-journee">
        <header class="entete-prono-journee">
          <div>
            <p class="doux petit">{{ formaterDate(match.commence_at) }}</p>
            <h2 class="titre-match-prono">
              {{ match.domicile }}
              <span class="doux">–</span>
              {{ match.exterieur }}
            </h2>
          </div>
          <span v-if="match.pronostic" class="badge-pronostic">Déposé</span>
          <span v-else-if="match.verrouille || match.match_deja_joue" class="badge-pronostic badge-verrouille">
            Verrouillé
          </span>
        </header>

        <form
          v-if="!match.verrouille && !match.match_deja_joue"
          class="formulaire-prono-compact"
          @submit.prevent="soumettreProno(match)"
        >
          <div class="ligne-type-prono">
            <label>
              <input
                v-model="formulaires[cleMatch(match)].type_pronostic"
                type="radio"
                value="1x2"
              />
              1X2
            </label>
            <label>
              <input
                v-model="formulaires[cleMatch(match)].type_pronostic"
                type="radio"
                value="score"
              />
              Score
            </label>
          </div>

          <div
            v-if="formulaires[cleMatch(match)].type_pronostic === '1x2'"
            class="ligne-1x2"
          >
            <button
              v-for="opt in ['1', 'N', '2']"
              :key="opt"
              type="button"
              class="bouton-1x2"
              :class="{ actif: formulaires[cleMatch(match)].resultat_1x2 === opt }"
              @click="formulaires[cleMatch(match)].resultat_1x2 = opt"
            >
              {{ opt }}
            </button>
          </div>

          <div v-else class="ligne-score-prono">
            <label>
              Dom.
              <input
                v-model.number="formulaires[cleMatch(match)].buts_domicile"
                type="number"
                min="0"
                max="15"
              />
            </label>
            <span class="doux">–</span>
            <label>
              Ext.
              <input
                v-model.number="formulaires[cleMatch(match)].buts_exterieur"
                type="number"
                min="0"
                max="15"
              />
            </label>
          </div>

          <button
            type="submit"
            class="bouton-principal"
            :disabled="envoiId === cleMatch(match)"
          >
            {{
              envoiId === cleMatch(match)
                ? "Enregistrement…"
                : match.pronostic
                  ? "Mettre à jour"
                  : "Déposer"
            }}
          </button>
        </form>

        <p v-else-if="match.pronostic" class="doux">
          Votre prono : <strong>{{ match.pronostic.libelle }}</strong>
        </p>
      </li>
    </ul>
    </template>

    <p class="doux petit lien-mes-pronos">
      <router-link to="/mes-pronos">Nos pronostics</router-link>
      ·
      <router-link to="/ligues">Ligues privées</router-link>
    </p>
  </div>
</template>
