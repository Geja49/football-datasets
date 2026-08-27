<script setup>
import { computed, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import ChargementPage from "../composants/ChargementPage.vue";
import DiagrammeDensites from "../composants/DiagrammeDensites.vue";
import PortraitJoueur from "../composants/PortraitJoueur.vue";
import DiagrammeRadar from "../composants/DiagrammeRadar.vue";
import {
  AXES_JOUEUR,
  PLAFONDS_JOUEUR,
  axesComparaisonLigue,
  axesDepuisJoueur,
  histogrammeLocal,
  nombre,
} from "../composants/axesDiagramme.js";
import { definirExtraNavigation, viderExtraNavigation } from "../contexteNavigation.js";
import { chargerJoueur } from "../services/api.js";

const route = useRoute();
const joueur = computed(() => route.params.joueur);
const championnat = computed(() => route.query.championnat || "");
const data = ref({
  saisons: [],
  url_photo: "",
  reperes: null,
  buts: null,
  defense: { disponible: false, message: "", saisons: [] },
  valeur_marche: null,
  transferts: [],
});
const erreur = ref("");
const chargement = ref(true);

function texteEuros(valeur) {
  const n = Number(valeur);
  if (!Number.isFinite(n) || n <= 0) return "—";
  if (n >= 1_000_000) {
    const m = n / 1_000_000;
    return `${m >= 10 ? Math.round(m) : m.toFixed(1).replace(/\.0$/, "")} M€`;
  }
  if (n >= 1_000) return `${Math.round(n / 1_000)} k€`;
  return `${Math.round(n)} €`;
}

const blocMarche = computed(() => data.value.valeur_marche || null);

const historiqueTransferts = computed(() => {
  const directs = data.value.transferts || [];
  if (directs.length) return directs;
  return blocMarche.value?.transferts_recents || [];
});

function formaterDateTransfert(valeur) {
  if (!valeur) return "—";
  const parties = String(valeur).slice(0, 10).split("-");
  if (parties.length !== 3) return valeur;
  return `${parties[2]}/${parties[1]}/${parties[0]}`;
}

async function charger() {
  erreur.value = "";
  chargement.value = true;
  try {
    data.value = await chargerJoueur(joueur.value, championnat.value || null);
  } catch (e) {
    erreur.value = e.message;
  } finally {
    chargement.value = false;
  }
}

watch([joueur, championnat], charger, { immediate: true });

const saisonRecente = computed(() => (data.value.saisons || [])[0] || null);

watch(
  saisonRecente,
  (ligne) => {
    definirExtraNavigation({
      championnat: (ligne && ligne.championnat) || championnat.value,
      equipe: ligne ? (ligne.equipe || "").split(",")[0].trim() : "",
      saison: ligne ? ligne.saison : "",
    });
  },
  { immediate: true },
);

onUnmounted(viderExtraNavigation);

const saisonRadar = computed(() => {
  const lignes = data.value.saisons || [];
  if (!lignes.length) return null;
  const annee = lignes[0].saison;
  const candidates = lignes.filter((l) => l.saison === annee);
  return [...candidates].sort((a, b) => nombre(b.minutes) - nombre(a.minutes))[0];
});

const reperesRadar = computed(() => {
  if (data.value.reperes?.axes?.length) return data.value.reperes;
  const lignes = data.value.saisons || [];
  if (!lignes.length) return null;
  return {
    axes: AXES_JOUEUR.map((def) => {
      const plafond = Math.max(
        ...lignes.map((l) => nombre(l[def.cle])),
        PLAFONDS_JOUEUR[def.cle] || 1,
      );
      return {
        cle: def.cle,
        libelle: def.libelle,
        plafond,
        histogramme: histogrammeLocal(lignes.map((l) => nombre(l[def.cle])), plafond),
      };
    }),
  };
});

const axesJoueur = computed(() =>
  saisonRadar.value ? axesDepuisJoueur(saisonRadar.value, reperesRadar.value) : [],
);

const comparaisonLigue = computed(() => axesComparaisonLigue(axesJoueur.value));

const messageReperes = computed(() => {
  const r = data.value.reperes;
  if (!r) return "";
  if (r.message) return r.message;
  if (!r.axes?.length) return "Pas assez de données ligue pour comparer.";
  return "";
});

const totaux = computed(() => {
  const lignes = data.value.saisons || [];
  const butsApi = data.value.buts || {};
  const butsLigue =
    butsApi.championnat != null
      ? butsApi.championnat
      : lignes.reduce((s, l) => s + nombre(l.buts), 0);
  return {
    matchs: lignes.reduce((s, l) => s + nombre(l.matchs), 0),
    buts: butsLigue,
    butsLdc: butsApi.ldc_par_joueur ? butsApi.ligue_des_champions : null,
    ldcParJoueur: !!butsApi.ldc_par_joueur,
    messageLdc: butsApi.message_ldc || "Ligue des champions : non disponible par joueur",
    total: butsApi.total != null ? butsApi.total : butsLigue,
    passes: lignes.reduce((s, l) => s + nombre(l.passes_decisives), 0),
    xg: lignes.reduce((s, l) => s + nombre(l.xg), 0).toFixed(1),
    xa: lignes.reduce((s, l) => s + nombre(l.xa), 0).toFixed(1),
    passesCles: lignes.reduce((s, l) => s + nombre(l.passes_cles), 0),
    jaunes: lignes.reduce((s, l) => s + nombre(l.carton_jaune), 0),
    rouges: lignes.reduce((s, l) => s + nombre(l.carton_rouge), 0),
    xgChaine: lignes.reduce((s, l) => s + nombre(l.xg_chaine), 0).toFixed(1),
    xgConstruction: lignes.reduce((s, l) => s + nombre(l.xg_construction), 0).toFixed(1),
  };
});
</script>

<template>
  <section class="hero">
    <div class="hero-inner fiche-joueur">
      <div class="cadre-portrait">
        <PortraitJoueur
          :nom="joueur"
          :url-photo="data.url_photo"
          taille="grand"
        />
      </div>
      <div class="identite-joueur">
        <h1 class="titre-hero">{{ joueur }}</h1>
        <p v-if="saisonRecente" class="doux">
          {{ saisonRecente.poste }} ·
          <router-link
            class="lien-equipe"
            :to="{
              path: `/championnat/${encodeURIComponent(saisonRecente.championnat)}/equipe/${encodeURIComponent(saisonRecente.equipe.split(',')[0])}`,
              query: { saison: saisonRecente.saison },
            }"
          >
            {{ saisonRecente.equipe }}
          </router-link>
          ·
          <router-link
            :to="{
              path: `/championnat/${encodeURIComponent(saisonRecente.championnat)}`,
              query: { saison: saisonRecente.saison },
            }"
          >
            {{ saisonRecente.championnat }}
          </router-link>
        </p>
        <div class="cartes-stats cartes-stats-resume">
          <div class="carte-stat">
            <span>Matchs</span>
            <strong>{{ totaux.matchs }}</strong>
          </div>
          <div class="carte-stat">
            <span>Buts championnat</span>
            <strong>{{ totaux.buts }}</strong>
          </div>
          <div class="carte-stat" :class="{ manquant: !totaux.ldcParJoueur }">
            <span>Ligue des champions</span>
            <strong>{{ totaux.ldcParJoueur ? totaux.butsLdc : "—" }}</strong>
          </div>
          <div class="carte-stat">
            <span>Total</span>
            <strong>{{ totaux.total }}</strong>
          </div>
          <div class="carte-stat">
            <span>Passes D.</span>
            <strong>{{ totaux.passes }}</strong>
          </div>
          <div class="carte-stat">
            <span>xG</span>
            <strong>{{ totaux.xg }}</strong>
          </div>
        </div>
        <p class="titre-sous-section">Détail</p>
        <div class="cartes-stats cartes-stats-detail">
          <div class="carte-stat">
            <span>xA</span>
            <strong>{{ totaux.xa }}</strong>
          </div>
          <div class="carte-stat">
            <span>Passes clés</span>
            <strong>{{ totaux.passesCles }}</strong>
          </div>
          <div class="carte-stat">
            <span>Jaunes</span>
            <strong>{{ totaux.jaunes }}</strong>
          </div>
          <div class="carte-stat">
            <span>Rouges</span>
            <strong>{{ totaux.rouges }}</strong>
          </div>
          <div class="carte-stat">
            <span>xG chaîne</span>
            <strong>{{ totaux.xgChaine }}</strong>
          </div>
          <div class="carte-stat">
            <span>xG construction</span>
            <strong>{{ totaux.xgConstruction }}</strong>
          </div>
          <div
            v-if="blocMarche && blocMarche.valeur_marche_eur != null"
            class="carte-stat"
          >
            <span>Valeur marché</span>
            <strong>{{ texteEuros(blocMarche.valeur_marche_eur) }}</strong>
          </div>
        </div>
        <p v-if="!totaux.ldcParJoueur" class="mention-ldc">{{ totaux.messageLdc }}</p>
        <p
          v-if="blocMarche && blocMarche.valeur_marche_eur != null"
          class="mention-ldc"
        >
          {{ blocMarche.mention || "estimation dump public, pas à jour live" }}
          <template v-if="blocMarche.age != null"> · {{ blocMarche.age }} ans</template>
          <template v-if="blocMarche.valeur_max_eur">
            · pic {{ texteEuros(blocMarche.valeur_max_eur) }}
          </template>
        </p>
        <p class="mention-ldc">
          xG construction (xGBuildup) mesure la participation aux séquences offensives, pas la défense.
        </p>
        <router-link
          class="lien-comparer"
          :to="{ path: '/comparer', query: { type: 'joueurs', a: joueur } }"
        >
          Comparer ce joueur
        </router-link>
      </div>
    </div>
  </section>
  <div class="page">
    <p v-if="erreur" class="erreur">{{ erreur }}</p>
    <ChargementPage v-else-if="chargement" message="Chargement des stats" />
    <template v-else>
    <div class="bloc" v-if="historiqueTransferts.length">
      <header class="entete-bloc">
        <h2>Historique des transferts</h2>
        <p class="doux">
          Dump communautaire (pas de mise à jour live Transfermarkt).
        </p>
      </header>
      <div class="enveloppe-tableau">
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Saison</th>
            <th>Départ</th>
            <th>Arrivée</th>
            <th class="droit">Frais</th>
            <th class="droit">Valeur</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(ligne, i) in historiqueTransferts" :key="i + (ligne.date_transfert || '')">
            <td>{{ formaterDateTransfert(ligne.date_transfert) }}</td>
            <td>{{ ligne.saison_transfert || "—" }}</td>
            <td>{{ ligne.club_depart || "—" }}</td>
            <td>{{ ligne.club_arrivee || "—" }}</td>
            <td class="droit">{{ texteEuros(ligne.frais_eur) }}</td>
            <td class="droit">{{ texteEuros(ligne.valeur_marche_eur) }}</td>
          </tr>
        </tbody>
      </table>
      </div>
    </div>
    <div class="bloc" v-if="axesJoueur.length">
      <header class="entete-bloc">
        <h2>Profil de saison</h2>
        <p class="doux">
          {{ saisonRadar.saison }} · {{ saisonRadar.championnat }}
          · buts, xG, passes, xA, tirs, minutes.
          {{ data.reperes && data.reperes.axes && data.reperes.axes.length
            ? "Comparaison à la moyenne du championnat : polygone pointillé (radar) et losange (densités)."
            : "Position relative à un plafond de saison type (valeur + centile)." }}
        </p>
      </header>
      <p v-if="messageReperes" class="mention">{{ messageReperes }}</p>
      <div class="grille-diagrammes">
        <div class="cadre-diagramme">
          <p class="titre-cadre">Radar</p>
          <DiagrammeRadar
            :axes="axesJoueur"
            :comparaison="comparaisonLigue"
            libelle-sujet="Joueur"
            libelle-comparaison="Moyenne ligue"
          />
        </div>
        <div class="cadre-diagramme">
          <p class="titre-cadre">Densités (vs championnat)</p>
          <DiagrammeDensites :lignes="axesJoueur" libelle-sujet="Joueur" />
        </div>
      </div>
      <div class="enveloppe-tableau" v-if="comparaisonLigue.length">
      <table class="table-vs-ligue">
        <thead>
          <tr>
            <th>Métrique</th>
            <th class="droit">Joueur</th>
            <th class="droit">Moyenne ligue</th>
            <th>Écart</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="axe in axesJoueur" :key="'vs-' + axe.cle">
            <td>{{ axe.libelle }}</td>
            <td class="droit pts">{{ axe.texte }}</td>
            <td class="droit">{{ axe.texteLigue || "—" }}</td>
            <td class="ecart-cellule">{{ axe.texteEcart || "—" }}</td>
          </tr>
        </tbody>
      </table>
      </div>
    </div>
    <div class="bloc">
      <header class="entete-bloc">
        <h2>Statistiques par saison</h2>
      </header>
      <div class="enveloppe-tableau">
      <table>
        <thead>
          <tr>
            <th>Saison</th>
            <th>Championnat</th>
            <th>Club</th>
            <th>Poste</th>
            <th class="droit">M</th>
            <th class="droit">Min</th>
            <th class="droit">Buts</th>
            <th class="droit">PD</th>
            <th class="droit">Tirs</th>
            <th class="droit">xG</th>
            <th class="droit">xA</th>
            <th class="droit">PClés</th>
            <th class="droit">xG ch.</th>
            <th class="droit">xG constr.</th>
            <th class="droit">J</th>
            <th class="droit">R</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="ligne in data.saisons" :key="ligne.saison + ligne.championnat + ligne.equipe">
            <td>{{ ligne.saison }}</td>
            <td>{{ ligne.championnat }}</td>
            <td>
              <router-link
                :to="{
                  path: `/championnat/${encodeURIComponent(ligne.championnat)}/equipe/${encodeURIComponent(ligne.equipe.split(',')[0])}`,
                  query: { saison: ligne.saison },
                }"
              >
                {{ ligne.equipe }}
              </router-link>
            </td>
            <td>{{ ligne.poste }}</td>
            <td class="droit">{{ ligne.matchs }}</td>
            <td class="droit">{{ ligne.minutes }}</td>
            <td class="droit pts">{{ ligne.buts }}</td>
            <td class="droit">{{ ligne.passes_decisives }}</td>
            <td class="droit">{{ ligne.tirs }}</td>
            <td class="droit">{{ ligne.xg }}</td>
            <td class="droit">{{ ligne.xa }}</td>
            <td class="droit">{{ ligne.passes_cles }}</td>
            <td class="droit">{{ ligne.xg_chaine }}</td>
            <td class="droit">{{ ligne.xg_construction }}</td>
            <td class="droit">{{ ligne.carton_jaune }}</td>
            <td class="droit">{{ ligne.carton_rouge }}</td>
          </tr>
        </tbody>
      </table>
      </div>
      <p v-if="!totaux.ldcParJoueur" class="doux mention-ldc">
        Ces lignes viennent des 5 ligues (Understat). {{ totaux.messageLdc }}.
      </p>
    </div>
    <div class="bloc">
      <header class="entete-bloc">
        <h2>Contribution défensive</h2>
        <p class="doux">{{ data.defense && data.defense.message }}</p>
      </header>
      <div
        class="enveloppe-tableau"
        v-if="data.defense && data.defense.disponible && data.defense.saisons.length"
      >
      <table>
        <thead>
          <tr>
            <th>Saison</th>
            <th>Championnat</th>
            <th>Club</th>
            <th class="droit">M</th>
            <th class="droit">Tacles</th>
            <th class="droit">Réussis</th>
            <th class="droit">Interc.</th>
            <th class="droit">Blocs</th>
            <th class="droit">Dég.</th>
            <th class="droit">Duels</th>
            <th class="droit">Arrêts</th>
            <th class="droit">xG subis</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="ligne in data.defense.saisons" :key="ligne.saison + ligne.championnat + ligne.equipe">
            <td>{{ ligne.saison }}</td>
            <td>{{ ligne.championnat }}</td>
            <td>{{ ligne.equipe }}</td>
            <td class="droit">{{ ligne.matchs }}</td>
            <td class="droit">{{ ligne.tacles }}</td>
            <td class="droit">{{ ligne.tacles_reussis }}</td>
            <td class="droit">{{ ligne.interceptions }}</td>
            <td class="droit">{{ ligne.blocs }}</td>
            <td class="droit">{{ ligne.degagements }}</td>
            <td class="droit">{{ ligne.duels }}</td>
            <td class="droit">{{ ligne.arrets }}</td>
            <td class="droit">{{ ligne.xg_tirs_subis }}</td>
          </tr>
        </tbody>
      </table>
      </div>
    </div>
    </template>
  </div>
</template>
