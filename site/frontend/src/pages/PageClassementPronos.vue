<script setup>
import { onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import ProfilPublicPronos from "../composants/ProfilPublicPronos.vue";
import { CHAMPIONNATS_DEFAUT } from "../championnats.js";
import { chargerAccueil, chargerClassementPronos } from "../services/api.js";

const route = useRoute();
const routeur = useRouter();

const championnats = ref([...CHAMPIONNATS_DEFAUT]);
const championnat = ref("La Liga");
const saison = ref("2026-2027");
const saisons = ref(["2026-2027"]);
const classement = ref([]);
const reglePoints = ref("");
const disclaimer = ref("");
const erreur = ref("");
const chargement = ref(true);
const profilOuvert = ref(null);

async function chargerSaisons() {
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

async function chargerClassement() {
  chargement.value = true;
  erreur.value = "";
  try {
    const reponse = await chargerClassementPronos(championnat.value, saison.value);
    classement.value = reponse.classement || [];
    reglePoints.value = reponse.regle_points || "";
    disclaimer.value = reponse.disclaimer || "";
  } catch (e) {
    erreur.value = e.message;
    classement.value = [];
  } finally {
    chargement.value = false;
  }
}

function ouvrirProfil(pseudo) {
  profilOuvert.value = profilOuvert.value === pseudo ? null : pseudo;
  if (profilOuvert.value) {
    routeur.replace({
      path: route.path,
      query: { ...route.query, profil: pseudo },
    });
  } else {
    const { profil, ...reste } = route.query;
    routeur.replace({ path: route.path, query: reste });
  }
}

onMounted(async () => {
  if (route.query.championnat) {
    championnat.value = String(route.query.championnat);
  }
  if (route.query.saison) {
    saison.value = String(route.query.saison);
  }
  await chargerSaisons();
  if (route.query.profil) {
    profilOuvert.value = String(route.query.profil);
  }
  await chargerClassement();
});

watch([championnat, saison], () => {
  routeur.replace({
    path: route.path,
    query: {
      championnat: championnat.value,
      saison: saison.value,
      ...(profilOuvert.value ? { profil: profilOuvert.value } : {}),
    },
  });
  chargerClassement();
});
</script>

<template>
  <section class="hero hero-analyse">
    <div class="hero-inner">
      <header class="entete-analyse">
        <p class="sur-titre-analyse">Communauté</p>
        <h1 class="titre-analyse">Classement pronos</h1>
        <p class="intro-analyse">
          Classement ludique par championnat — aucun gain monétaire.
        </p>
      </header>

      <div class="filtres-analyse">
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
      </div>
    </div>
  </section>

  <div class="page">
    <p v-if="reglePoints" class="mention mention-communaute">{{ reglePoints }}</p>
    <p v-if="disclaimer" class="mention mention-communaute">{{ disclaimer }}</p>

    <p v-if="erreur" class="erreur">{{ erreur }}</p>
    <p v-if="chargement" class="doux">Chargement…</p>

    <p v-else-if="!classement.length" class="doux">
      Aucun pronostic pour ce championnat et cette saison.
      <router-link to="/match">Déposez le vôtre</router-link>
      après connexion.
    </p>

    <div v-else class="bloc-classement-pronos">
      <table class="table-classement-pronos">
        <thead>
          <tr>
            <th scope="col">#</th>
            <th scope="col">Pseudo</th>
            <th scope="col">Points</th>
            <th scope="col">Pronos</th>
            <th scope="col">Évalués</th>
            <th scope="col">Exacts</th>
            <th scope="col">Badges</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="ligne in classement"
            :key="ligne.utilisateur_id"
            :class="{ 'ligne-top3': ligne.rang <= 3 }"
          >
            <td class="col-rang">{{ ligne.rang }}</td>
            <td>
              <button
                type="button"
                class="lien-pseudo-classement"
                :class="{ actif: profilOuvert === ligne.pseudo }"
                @click="ouvrirProfil(ligne.pseudo)"
              >
                {{ ligne.pseudo }}
              </button>
            </td>
            <td class="col-points">{{ ligne.points }}</td>
            <td>{{ ligne.nb_pronos }}</td>
            <td>{{ ligne.nb_evalues }}</td>
            <td>{{ ligne.nb_exacts }}</td>
            <td>
              <span
                v-for="badge in ligne.badges"
                :key="badge"
                class="badge-classement"
              >
                {{ badge }}
              </span>
              <span v-if="!ligne.badges?.length" class="doux">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <ProfilPublicPronos v-if="profilOuvert" :pseudo="profilOuvert" />

    <p class="doux petit lien-mes-pronos">
      <router-link to="/mes-pronos">Voir nos pronostics</router-link>
    </p>
  </div>
</template>
