<script setup>
import { computed, onMounted, ref } from "vue";
import ChargementPage from "../composants/ChargementPage.vue";
import { chargerMesPronostics, chargerMatchsSansProno, chargerUtilisateurConnecte } from "../services/api.js";

const pronostics = ref([]);
const matchsSansProno = ref([]);
const stats = ref(null);
const erreur = ref("");
const chargement = ref(true);
const utilisateur = ref(null);

const resume = computed(() => {
  if (stats.value) {
    return {
      total: stats.value.nb_pronos,
      exacts: stats.value.nb_exacts,
      rates: Math.max(0, (stats.value.nb_evalues || 0) - (stats.value.nb_exacts || 0)),
      enAttente: Math.max(0, (stats.value.nb_pronos || 0) - (stats.value.nb_evalues || 0)),
      points: stats.value.points,
      tauxExacts: stats.value.taux_exacts ?? 0,
    };
  }
  const liste = pronostics.value;
  let exacts = 0;
  let rates = 0;
  let enAttente = 0;
  let points = 0;
  for (const prono of liste) {
    if (prono.evaluation) {
      if (prono.evaluation.exact) exacts += 1;
      else rates += 1;
      points += Number(prono.evaluation.points) || 0;
    } else {
      enAttente += 1;
    }
  }
  const evalues = exacts + rates;
  return {
    total: liste.length,
    exacts,
    rates,
    enAttente,
    points,
    tauxExacts: evalues ? Math.round((1000 * exacts) / evalues) / 10 : 0,
  };
});

function formaterDate(iso) {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("fr-FR", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function lienMatch(prono) {
  return {
    path: "/match",
    query: {
      championnat: prono.championnat,
      saison: prono.saison,
      domicile: prono.domicile,
      exterieur: prono.exterieur,
    },
  };
}

function libelleStatut(prono) {
  if (prono.evaluation) {
    return prono.evaluation.exact ? "Exact" : "Raté";
  }
  if (prono.verrouille) return "Verrouillé";
  return "En attente";
}

function lienMatchSansProno(match) {
  return {
    path: "/match",
    query: {
      championnat: match.championnat,
      saison: match.saison,
      domicile: match.domicile,
      exterieur: match.exterieur,
    },
  };
}

onMounted(async () => {
  try {
    const session = await chargerUtilisateurConnecte();
    utilisateur.value = session.utilisateur;
  } catch {
    utilisateur.value = null;
    erreur.value = "Connectez-vous pour voir vos pronostics.";
    chargement.value = false;
    return;
  }
  try {
    const [reponse, rappels] = await Promise.all([
      chargerMesPronostics(),
      chargerMatchsSansProno(),
    ]);
    pronostics.value = reponse.pronostics || [];
    stats.value = reponse.stats || null;
    matchsSansProno.value = rappels.matchs || [];
  } catch (e) {
    erreur.value = e.message;
  } finally {
    chargement.value = false;
  }
});
</script>

<template>
  <section class="hero hero-analyse">
    <div class="hero-inner">
      <header class="entete-analyse">
        <p class="sur-titre-analyse">Communauté</p>
        <h1 class="titre-analyse">Nos pronos</h1>
        <p class="intro-analyse">
          Votre historique privé, les matchs à venir sans prono, et les liens vers
          la journée et le classement.
        </p>
      </header>
    </div>
  </section>

  <div class="page">
    <nav v-if="utilisateur" class="raccourcis-pronos" aria-label="Raccourcis pronostics">
      <router-link to="/pronos-journee" class="puce-raccourci-prono">Prono journée</router-link>
      <router-link to="/classement-pronos" class="puce-raccourci-prono">Classement</router-link>
      <router-link to="/ligues" class="puce-raccourci-prono">Ligues privées</router-link>
      <router-link to="/match" class="puce-raccourci-prono">Analyser un match</router-link>
    </nav>

    <section v-if="utilisateur && matchsSansProno.length" class="bloc bloc-rappels-pronos">
      <h2 class="titre-rappels">Matchs à pronostiquer bientôt</h2>
      <p class="doux">Prochains matchs sans votre prono (7 jours).</p>
      <ul class="liste-rappels-pronos">
        <li v-for="match in matchsSansProno" :key="`${match.championnat}-${match.domicile}-${match.exterieur}`">
          <router-link :to="lienMatchSansProno(match)" class="lien-rappel-prono">
            <span class="doux petit">{{ match.championnat }} · {{ formaterDate(match.commence_at) }}</span>
            <strong>{{ match.domicile }} – {{ match.exterieur }}</strong>
          </router-link>
        </li>
      </ul>
      <p class="doux petit lien-journee-rappel">
        Ou déposez plusieurs d’un coup via
        <router-link to="/pronos-journee">le prono journée</router-link>.
      </p>
    </section>

    <p v-if="erreur" class="erreur">{{ erreur }}</p>
    <ChargementPage v-if="chargement" message="Chargement de vos pronostics" />

    <p v-else-if="!utilisateur" class="doux">

      <router-link to="/connexion">Connectez-vous</router-link>
      ou
      <router-link to="/inscription">créez un compte</router-link>
      pour voir et déposer vos pronostics.
    </p>

    <template v-else>
      <section v-if="resume.total" class="resume-pronos" aria-label="Résumé de vos pronostics">
        <div class="case-resume">
          <span class="chiffre-resume">{{ resume.total }}</span>
          <span class="libelle-resume">Prono(s)</span>
        </div>
        <div class="case-resume">
          <span class="chiffre-resume">{{ resume.points }}</span>
          <span class="libelle-resume">Point(s)</span>
        </div>
        <div class="case-resume">
          <span class="chiffre-resume">{{ resume.exacts }}</span>
          <span class="libelle-resume">Exact(s)</span>
        </div>
        <div class="case-resume">
          <span class="chiffre-resume">{{ resume.tauxExacts }}%</span>
          <span class="libelle-resume">Taux exacts</span>
        </div>
        <div class="case-resume">
          <span class="chiffre-resume">{{ resume.enAttente }}</span>
          <span class="libelle-resume">En attente</span>
        </div>
      </section>

      <h2 class="titre-historique-pronos">Votre historique</h2>

      <p v-if="!pronostics.length" class="doux message-vide-communaute">
        Aucun pronostic pour l’instant.
        <router-link to="/match">Analysez un match à venir</router-link>
        ou passez par
        <router-link to="/pronos-journee">le prono journée</router-link>.
      </p>

      <ul v-else class="liste-pronostics">
        <li v-for="prono in pronostics" :key="prono.id" class="carte-pronostic">
          <header class="entete-pronostic">
            <div>
              <p class="doux petit">{{ prono.championnat }} · {{ prono.saison }}</p>
              <h3 class="titre-match-prono">
                {{ prono.domicile }}
                <span class="doux">–</span>
                {{ prono.exterieur }}
              </h3>
            </div>
            <span
              class="badge-pronostic"
              :class="{
                'badge-exact': prono.evaluation && prono.evaluation.exact,
                'badge-rate': prono.evaluation && !prono.evaluation.exact,
                'badge-verrouille': prono.verrouille && !prono.evaluation,
              }"
            >
              {{ libelleStatut(prono) }}
            </span>
          </header>

          <div class="corps-pronostic">
            <div class="ligne-prono">
              <span class="doux">Votre prono</span>
              <strong class="valeur-prono">{{ prono.libelle }}</strong>
              <span class="doux petit">({{ prono.type_pronostic === "score" ? "Score" : "1X2" }})</span>
            </div>
            <div class="ligne-prono" v-if="prono.evaluation">
              <span class="doux">Score réel</span>
              <strong>{{ prono.evaluation.score_reel }}</strong>
            </div>
            <div class="ligne-prono" v-if="prono.evaluation">
              <span class="doux">Points</span>
              <strong class="valeur-prono">{{ prono.evaluation.points }} pt(s)</strong>
            </div>
            <div class="ligne-prono">
              <span class="doux">Coup d’envoi</span>
              <time>{{ formaterDate(prono.commence_at) }}</time>
            </div>
            <div class="ligne-prono">
              <span class="doux">Déposé le</span>
              <time>{{ formaterDate(prono.cree_le) }}</time>
            </div>
          </div>

          <router-link :to="lienMatch(prono)" class="lien-match-prono">
            Voir l’analyse du match →
          </router-link>
        </li>
      </ul>
    </template>
  </div>
</template>
