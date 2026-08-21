<script setup>
import { computed, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import DiagrammeDensites from "../composants/DiagrammeDensites.vue";
import DiagrammeRadar from "../composants/DiagrammeRadar.vue";
import { AXES_JOUEUR, PLAFONDS_JOUEUR, axesDepuisJoueur, histogrammeLocal, nombre } from "../composants/axesDiagramme.js";
import { definirExtraNavigation, viderExtraNavigation } from "../contexteNavigation.js";
import { chargerJoueur } from "../services/api.js";

const route = useRoute();
const joueur = computed(() => route.params.joueur);
const championnat = computed(() => route.query.championnat || "");
const data = ref({ saisons: [], url_photo: "", reperes: null, buts: null, defense: { disponible: false, message: "", saisons: [] } });
const erreur = ref("");

async function charger() {
  erreur.value = "";
  try {
    data.value = await chargerJoueur(joueur.value, championnat.value || null);
  } catch (e) {
    erreur.value = e.message;
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
      <img
        v-if="data.url_photo"
        :src="data.url_photo"
        :alt="joueur"
        class="portrait-joueur"
      />
      <div v-else class="portrait-joueur portrait-vide">{{ joueur.slice(0, 1) }}</div>
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
        <div class="cartes-stats">
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
        </div>
        <p v-if="!totaux.ldcParJoueur" class="mention-ldc">{{ totaux.messageLdc }}</p>
        <p class="mention-ldc">
          xG construction (xGBuildup) mesure la participation aux séquences offensives, pas la défense.
        </p>
      </div>
    </div>
  </section>
  <div class="page">
    <p v-if="erreur" class="erreur">{{ erreur }}</p>
    <div class="bloc" v-if="axesJoueur.length">
      <h2>Profil de saison</h2>
      <p class="doux">
        {{ saisonRadar.saison }} · {{ saisonRadar.championnat }}
        · buts, xG, passes, xA, tirs, minutes
        {{ data.reperes && data.reperes.axes && data.reperes.axes.length
          ? "(scores relatifs au meilleur de la ligue)."
          : "(scores relatifs à un plafond de saison type)." }}
      </p>
      <div class="grille-diagrammes">
        <div class="cadre-diagramme">
          <p class="titre-cadre">Radar</p>
          <DiagrammeRadar :axes="axesJoueur" />
        </div>
        <div class="cadre-diagramme">
          <p class="titre-cadre">Densités</p>
          <DiagrammeDensites :lignes="axesJoueur" />
        </div>
      </div>
    </div>
    <div class="bloc">
      <h2>Statistiques par saison</h2>
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
      <p v-if="!totaux.ldcParJoueur" class="doux mention-ldc">
        Ces lignes viennent des 5 ligues (Understat). {{ totaux.messageLdc }}.
      </p>
    </div>
    <div class="bloc">
      <h2>Contribution défensive</h2>
      <p class="doux">{{ data.defense && data.defense.message }}</p>
      <table v-if="data.defense && data.defense.disponible && data.defense.saisons.length">
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
