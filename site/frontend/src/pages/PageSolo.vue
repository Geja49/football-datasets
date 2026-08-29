<script setup>
import { computed, onMounted, ref } from "vue";
import ChargementPage from "../composants/ChargementPage.vue";
import MentionJeuResponsable from "../composants/MentionJeuResponsable.vue";
import { CLASSES_CARTES } from "../championnats.js";
import {
  chargerBilanWeekendSolo,
  chargerPronosWeekendSolo,
  chargerUtilisateurConnecte,
} from "../services/api.js";

const utilisateur = ref(null);
const donnees = ref(null);
const bilan = ref(null);
const erreur = ref("");
const chargement = ref(true);
const chargementBilan = ref(false);
const afficherBilan = ref(false);
const dateDebut = ref(null);

function vendrediWeekend(reference) {
  const ref = new Date(reference);
  ref.setHours(12, 0, 0, 0);
  const wd = (ref.getDay() + 6) % 7;
  if (wd === 0) {
    ref.setDate(ref.getDate() - 3);
  } else if (wd <= 3) {
    ref.setDate(ref.getDate() + (4 - wd));
  } else {
    ref.setDate(ref.getDate() - (wd - 4));
  }
  return ref.toISOString().slice(0, 10);
}

function decalageWeekend(jours) {
  const base = dateDebut.value || vendrediWeekend(new Date());
  const d = new Date(`${base}T12:00:00`);
  d.setDate(d.getDate() + jours);
  dateDebut.value = d.toISOString().slice(0, 10);
  afficherBilan.value = false;
  bilan.value = null;
  charger();
}

async function charger() {
  chargement.value = true;
  erreur.value = "";
  try {
    donnees.value = await chargerPronosWeekendSolo({
      dateDebut: dateDebut.value || undefined,
    });
    dateDebut.value = donnees.value.weekend?.date_debut || dateDebut.value;
  } catch (e) {
    erreur.value = e.message;
    donnees.value = null;
  } finally {
    chargement.value = false;
  }
}

async function chargerBilan() {
  if (!dateDebut.value) return;
  chargementBilan.value = true;
  try {
    bilan.value = await chargerBilanWeekendSolo({
      dateDebut: dateDebut.value,
    });
    afficherBilan.value = true;
  } catch (e) {
    erreur.value = e.message;
    bilan.value = null;
  } finally {
    chargementBilan.value = false;
  }
}

const libelleWeekend = computed(
  () => donnees.value?.weekend?.libelle || "Weekend sélectionné",
);

const estFige = computed(() => donnees.value?.source === "fige");

const libelleBadgeSource = computed(() => {
  if (!donnees.value) return "";
  if (estFige.value) {
    const quand = formaterDateCourte(donnees.value.fige_le);
    return quand ? `Figé le ${quand}` : "Figé";
  }
  return "Live";
});

function formaterDateCourte(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso.slice(0, 16);
    return d.toLocaleString("fr-FR", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso.slice(0, 16);
  }
}

function grouperPronosFallback(pronos) {
  const parChampionnat = new Map();
  for (const match of pronos) {
    const liste = parChampionnat.get(match.championnat) || [];
    liste.push(match);
    parChampionnat.set(match.championnat, liste);
  }
  return [...parChampionnat.entries()]
    .sort(([a], [b]) => a.localeCompare(b, "fr"))
    .map(([championnat, matchs]) => ({
      championnat,
      pronos: [...matchs].sort((a, b) =>
        `${a.date}${a.heure || ""}`.localeCompare(`${b.date}${b.heure || ""}`),
      ),
    }));
}

const groupesChampionnats = computed(() => {
  const groupes = donnees.value?.pronos_par_championnat || [];
  const groupesNonVides = groupes.filter((g) => g.pronos?.length);
  if (groupesNonVides.length) return groupesNonVides;
  const pronos = donnees.value?.pronos || [];
  if (!pronos.length) return [];
  return grouperPronosFallback(pronos);
});

const nbPronosVisibles = computed(() =>
  groupesChampionnats.value.reduce((total, g) => total + g.pronos.length, 0),
);

function classeCarteChampionnat(nom) {
  return CLASSES_CARTES[nom] || "";
}

function formaterProba(valeur) {
  if (valeur == null) return "—";
  return `${valeur} %`;
}

function libelleMarche(marche) {
  if (marche.signal_fort && marche.probabilite == null) {
    return `${marche.libelle} (signal fort)`;
  }
  return marche.libelle;
}

function classeVerdict(verdict) {
  if (!verdict) return "";
  return verdict.vrai ? "verdict-vrai" : "verdict-faux";
}

function libelleVerdictCourt(verdict) {
  if (!verdict) return "";
  return verdict.vrai ? "Vrai" : "Faux";
}

onMounted(async () => {
  try {
    const session = await chargerUtilisateurConnecte();
    utilisateur.value = session.utilisateur;
    if (!session.utilisateur.est_admin) {
      erreur.value = "Accès réservé aux administrateurs.";
      chargement.value = false;
      return;
    }
  } catch {
    utilisateur.value = null;
    erreur.value = "Connexion admin requise.";
    chargement.value = false;
    return;
  }
  dateDebut.value = vendrediWeekend(new Date());
  await charger();
});
</script>

<template>
  <section class="hero hero-analyse">
    <div class="hero-inner">
      <header class="entete-analyse">
        <p class="sur-titre-analyse">Administration</p>
        <h1 class="titre-analyse">Solo</h1>
        <p class="intro-analyse">
          Pronostics statistiques du weekend (ven. 00h → lun. 23h59) — marchés
          ≥ {{ donnees?.seuil_probabilite ?? 85 }} %
          <template v-if="estFige"> (snapshot figé)</template>
          <template v-else> recalculés en direct</template>.
        </p>
      </header>
    </div>
  </section>

  <div class="page page-solo">
    <p v-if="erreur" class="erreur">{{ erreur }}</p>
    <ChargementPage v-if="chargement" message="Analyse des matchs du weekend" />

    <template v-else-if="utilisateur?.est_admin && donnees">
      <p class="avertissement-analyse">{{ donnees.avertissement }}</p>

      <div class="barre-filtres-solo">
        <div class="groupe-weekend-solo">
          <button type="button" class="bouton-secondaire" @click="decalageWeekend(-7)">
            ← Weekend précédent
          </button>
          <span class="libelle-weekend-solo">{{ libelleWeekend }}</span>
          <button type="button" class="bouton-secondaire" @click="decalageWeekend(7)">
            Weekend suivant →
          </button>
        </div>

        <div class="ligne-statut-solo">
          <span
            class="badge-source-solo"
            :class="estFige ? 'badge-fige' : 'badge-live'"
          >
            {{ libelleBadgeSource }}
          </span>
          <p class="doux petit stats-solo">
            {{ donnees.nb_matchs_analyses }} match(s) analysé(s) ·
            {{ donnees.nb_matchs_avec_prono }} avec marché ≥ {{ donnees.seuil_probabilite }} %
          </p>
        </div>

        <p v-if="!estFige" class="message-live-solo doux petit">
          Prévisions live — figer avec le script vendredi
          (<code>python scripts/figer_pronos_solo.py</code>
        </p>

        <div v-if="estFige" class="actions-bilan-solo">
          <button
            type="button"
            class="bouton-secondaire"
            :disabled="chargementBilan"
            @click="chargerBilan"
          >
            {{ afficherBilan ? "Actualiser le bilan" : "Bilan weekend" }}
          </button>
        </div>
      </div>

      <section v-if="afficherBilan && bilan" class="section-bilan-solo">
        <h2 class="titre-bilan-solo">Bilan weekend</h2>
        <p class="resume-bilan-solo">
          <template v-if="bilan.hit_rate != null">
            {{ bilan.hit_rate }} % de réussites
            ({{ bilan.nb_vrais }}/{{ bilan.nb_juges }} jugés
            · {{ bilan.nb_pronos }} marchés figés)
          </template>
          <template v-else>
            Aucun marché jugé pour l’instant
            ({{ bilan.nb_pronos }} figé(s) — lancer
            <code>python scripts/juger_pronos_solo.py</code>).
          </template>
        </p>

        <ul v-if="bilan.details?.length" class="liste-verdicts-solo">
          <li
            v-for="(ligne, i) in bilan.details"
            :key="i"
            :class="ligne.vrai ? 'verdict-vrai' : 'verdict-faux'"
          >
            <span class="libelle-verdict-solo">
              {{ ligne.domicile }} – {{ ligne.exterieur }}
              · {{ ligne.libelle_marche || ligne.type_marche }}
            </span>
            <span class="etat-verdict-solo">
              {{ ligne.vrai ? "Vrai" : "Faux" }}
              <template v-if="ligne.motif_texte"> — {{ ligne.motif_texte }}</template>
            </span>
          </li>
        </ul>
      </section>

      <p v-if="!nbPronosVisibles" class="doux message-vide-communaute">
        Aucun prono ≥ {{ donnees.seuil_probabilite }} % ce weekend.
      </p>

      <div v-else class="sections-championnats-solo">
        <section
          v-for="groupe in groupesChampionnats"
          :key="groupe.championnat"
          class="section-championnat-solo"
        >
          <h2
            class="titre-section-championnat-solo"
            :class="classeCarteChampionnat(groupe.championnat)"
          >
            {{ groupe.championnat }}
          </h2>

          <div class="grille-pronos-solo">
            <article
              v-for="(match, index) in groupe.pronos"
              :key="`${groupe.championnat}-${match.date}-${match.domicile}-${index}`"
              class="carte-prono-solo"
            >
              <header class="entete-prono-solo">
                <span class="doux petit">
                  {{ match.date }}
                  <template v-if="match.heure"> · {{ match.heure }}</template>
                  <template v-if="match.journee"> · J{{ match.journee }}</template>
                </span>
              </header>
              <h3 class="titre-match-solo">
                {{ match.domicile }} – {{ match.exterieur }}
              </h3>
              <p v-if="match.score_modal" class="doux petit">
                Score modal : <strong>{{ match.score_modal }}</strong>
              </p>
              <p
                v-if="match.match_physique && match.match_physique.actif"
                class="badge-physique-solo"
              >
                {{ match.match_physique.detail || "Match physique" }}
              </p>

              <ul class="liste-marches-solo">
                <li v-for="(marche, i) in match.marches" :key="i">
                  <span class="libelle-marche-solo">{{ libelleMarche(marche) }}</span>
                  <span class="proba-marche-solo">
                    {{ formaterProba(marche.probabilite) }}
                    <span
                      v-if="marche.verdict"
                      class="badge-verdict-solo"
                      :class="classeVerdict(marche.verdict)"
                      :title="marche.verdict.motif_texte || ''"
                    >
                      {{ libelleVerdictCourt(marche.verdict) }}
                    </span>
                  </span>
                </li>
              </ul>

              <p class="doux petit corners-solo">
                Corners :
                <template v-if="match.corners.disponible">
                  {{ match.corners.detail || formaterProba(match.corners.probabilite) }}
                  <span
                    v-if="match.corners.verdict"
                    class="badge-verdict-solo"
                    :class="classeVerdict(match.corners.verdict)"
                    :title="match.corners.verdict.motif_texte || ''"
                  >
                    {{ libelleVerdictCourt(match.corners.verdict) }}
                  </span>
                </template>
                <template v-else>{{ match.corners.message || "non disponible" }}</template>
              </p>
            </article>
          </div>
        </section>
      </div>

      <MentionJeuResponsable />
    </template>
  </div>
</template>

<style scoped>
.barre-filtres-solo {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.groupe-weekend-solo {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}

.libelle-weekend-solo {
  font-weight: 600;
  min-width: 10rem;
  text-align: center;
}

.ligne-statut-solo {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}

.badge-source-solo {
  display: inline-block;
  font-size: 0.8rem;
  font-weight: 600;
  padding: 0.2rem 0.55rem;
  border-radius: 0.35rem;
  border: 1px solid var(--bordure-douce, rgba(255, 255, 255, 0.15));
}

.badge-fige {
  background: rgba(46, 160, 67, 0.15);
}

.badge-live {
  background: rgba(88, 166, 255, 0.12);
}

.message-live-solo code,
.resume-bilan-solo code {
  font-size: 0.85em;
}

.section-bilan-solo {
  margin-bottom: 1.75rem;
  padding: 1rem 1.1rem;
  border: 1px solid var(--bordure-douce, rgba(255, 255, 255, 0.1));
  border-radius: 0.75rem;
}

.titre-bilan-solo {
  margin: 0 0 0.5rem;
  font-size: 1.1rem;
}

.resume-bilan-solo {
  margin: 0 0 0.75rem;
}

.liste-verdicts-solo {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.liste-verdicts-solo li {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.35rem 0;
  border-bottom: 1px solid var(--bordure-douce, rgba(255, 255, 255, 0.06));
  font-size: 0.92rem;
}

.verdict-vrai {
  color: #3fb950;
}

.verdict-faux {
  color: #f85149;
}

.badge-verdict-solo {
  margin-left: 0.4rem;
  font-size: 0.75rem;
  font-weight: 700;
}

.sections-championnats-solo {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.section-championnat-solo {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.titre-section-championnat-solo {
  font-size: 1.15rem;
  font-weight: 700;
  margin: 0;
  padding-bottom: 0.35rem;
  border-bottom: 2px solid var(--bordure-douce, rgba(255, 255, 255, 0.12));
}

.grille-pronos-solo {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 20rem), 1fr));
}

.carte-prono-solo {
  background: var(--surface-carte, rgba(255, 255, 255, 0.04));
  border: 1px solid var(--bordure-douce, rgba(255, 255, 255, 0.08));
  border-radius: 0.75rem;
  padding: 1rem 1.1rem;
}

.entete-prono-solo {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-bottom: 0.35rem;
}

.titre-match-solo {
  font-size: 1.05rem;
  margin: 0 0 0.5rem;
}

.liste-marches-solo {
  list-style: none;
  margin: 0.75rem 0;
  padding: 0;
}

.liste-marches-solo li {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.35rem 0;
  border-bottom: 1px solid var(--bordure-douce, rgba(255, 255, 255, 0.06));
}

.proba-marche-solo {
  font-weight: 700;
  white-space: nowrap;
}

.corners-solo {
  margin-top: 0.5rem;
  font-style: italic;
}

.badge-physique-solo {
  display: inline-block;
  margin: 0.35rem 0 0.25rem;
  padding: 0.2rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 600;
  border-radius: 4px;
  background: color-mix(in srgb, #b45309 18%, transparent);
  border: 1px solid color-mix(in srgb, #b45309 40%, var(--ligne, #ccc));
}

</style>
