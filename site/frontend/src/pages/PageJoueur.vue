<script setup>
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { chargerJoueur } from "../services/api.js";

const route = useRoute();
const joueur = computed(() => route.params.joueur);
const championnat = computed(() => route.query.championnat || "");
const data = ref({ saisons: [], url_photo: "" });
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

function nombre(valeur) {
  const n = Number(valeur);
  return Number.isFinite(n) ? n : 0;
}

const totaux = computed(() => {
  const lignes = data.value.saisons || [];
  return {
    matchs: lignes.reduce((s, l) => s + nombre(l.matchs), 0),
    buts: lignes.reduce((s, l) => s + nombre(l.buts), 0),
    passes: lignes.reduce((s, l) => s + nombre(l.passes_decisives), 0),
    xg: lignes.reduce((s, l) => s + nombre(l.xg), 0).toFixed(1),
    xa: lignes.reduce((s, l) => s + nombre(l.xa), 0).toFixed(1),
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
        <router-link to="/" class="doux">← Ligues</router-link>
        <h1 class="titre-hero">{{ joueur }}</h1>
        <p v-if="saisonRecente" class="doux">
          {{ saisonRecente.poste }} · {{ saisonRecente.equipe }} · {{ saisonRecente.championnat }}
        </p>
        <div class="cartes-stats">
          <div class="carte-stat">
            <span>Matchs</span>
            <strong>{{ totaux.matchs }}</strong>
          </div>
          <div class="carte-stat">
            <span>Buts</span>
            <strong>{{ totaux.buts }}</strong>
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
        </div>
      </div>
    </div>
  </section>
  <div class="page">
    <p v-if="erreur" class="erreur">{{ erreur }}</p>
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
            <th class="droit">xG</th>
            <th class="droit">xA</th>
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
            <td class="droit">{{ ligne.xg }}</td>
            <td class="droit">{{ ligne.xa }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
