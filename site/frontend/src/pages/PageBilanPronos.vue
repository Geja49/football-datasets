<script setup>
import { computed, onMounted, ref } from "vue";
import ChargementPage from "../composants/ChargementPage.vue";
import MentionJeuResponsable from "../composants/MentionJeuResponsable.vue";
import { aAccesSolo } from "../accesSolo.js";
import {
  chargerBilanPronos,
  chargerUtilisateurConnecte,
} from "../services/api.js";
import {
  estMarcheCarton,
  indiceTriMarche,
  libelleTypeMarche,
  palierHitRate,
} from "../libellesMarches.js";
import { construireSyntheseBilan } from "../syntheseBilan.js";

/** Aligné sur SEUIL_BILAN_PRONOS côté API. */
const SEUIL_BILAN_PRONOS = 70;

const utilisateur = ref(null);
const bilan = ref(null);
const erreur = ref("");
const chargement = ref(true);
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
  charger();
}

async function charger() {
  chargement.value = true;
  erreur.value = "";
  try {
    bilan.value = await chargerBilanPronos({
      dateDebut: dateDebut.value || undefined,
      probaMin: SEUIL_BILAN_PRONOS,
    });
    dateDebut.value = bilan.value.weekend?.date_debut || dateDebut.value;
  } catch (e) {
    erreur.value = e.message;
    bilan.value = null;
  } finally {
    chargement.value = false;
  }
}

const libelleWeekend = computed(
  () => bilan.value?.weekend?.libelle || "Weekend sélectionné",
);

const seuilAffiche = computed(
  () => bilan.value?.seuil_probabilite ?? SEUIL_BILAN_PRONOS,
);

const palierGlobal = computed(() =>
  palierHitRate(bilan.value?.hit_rate, seuilAffiche.value),
);

const syntheseBilan = computed(() => construireSyntheseBilan(bilan.value));

const statsParMarche = computed(() => {
  const blocs = bilan.value?.par_marche || {};
  return Object.entries(blocs)
    .filter(([type]) => !estMarcheCarton(type))
    .map(([type, stats]) => ({
      type,
      libelle: libelleTypeMarche(type),
      palier: palierHitRate(stats.hit_rate, seuilAffiche.value),
      ...stats,
    }))
    .sort((a, b) => indiceTriMarche(a.type) - indiceTriMarche(b.type));
});

function formaterScore(ligne) {
  if (ligne.buts_domicile == null || ligne.buts_exterieur == null) {
    return "—";
  }
  return `${ligne.buts_domicile}–${ligne.buts_exterieur}`;
}

function formaterProba(valeur) {
  if (valeur == null) return "—";
  return `${valeur} %`;
}

onMounted(async () => {
  try {
    const session = await chargerUtilisateurConnecte();
    utilisateur.value = session.utilisateur;
    if (!aAccesSolo(session.utilisateur)) {
      erreur.value =
        "Accès réservé aux administrateurs et super utilisateurs.";
      chargement.value = false;
      return;
    }
  } catch {
    utilisateur.value = null;
    erreur.value = "Connexion requise pour accéder au bilan des pronos.";
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
        <p class="sur-titre-analyse">Après match</p>
        <h1 class="titre-analyse">Bilan pronos</h1>
        <p class="intro-analyse">
          Écarts prédits vs réalité — uniquement les marchés figés à
          {{ seuilAffiche }}&nbsp;% ou plus.
        </p>
      </header>
    </div>
  </section>

  <div class="page page-bilan-pronos">
    <p v-if="erreur" class="erreur">{{ erreur }}</p>
    <ChargementPage v-if="chargement" message="Chargement du bilan" />

    <template v-else-if="aAccesSolo(utilisateur) && bilan">
      <div class="barre-filtres-solo">
        <div class="groupe-weekend-solo">
          <button
            type="button"
            class="bouton-secondaire"
            @click="decalageWeekend(-7)"
          >
            ← Weekend précédent
          </button>
          <span class="libelle-weekend-solo">{{ libelleWeekend }}</span>
          <button
            type="button"
            class="bouton-secondaire"
            @click="decalageWeekend(7)"
          >
            Weekend suivant →
          </button>
        </div>

        <p class="doux petit stats-solo">
          Seuil {{ seuilAffiche }} % ·
          {{ bilan.nb_pronos }} marché(s) figé(s) ·
          {{ bilan.nb_juges }} jugé(s)
        </p>
      </div>

      <section
        class="bloc-competitions section-bilan-solo"
        aria-label="Hit-rate"
      >
        <header class="entete-competitions">
          <p class="tag-section">Performance</p>
          <h2 class="titre-section-competitions">
            Hit-rate (≥ {{ seuilAffiche }} %)
          </h2>
        </header>

        <article
          v-if="bilan.hit_rate != null"
          class="tuile-competition tuile-bilan-global"
          :class="`palier-${palierGlobal}`"
          :aria-label="`Hit-rate global : ${bilan.hit_rate} %`"
        >
          <div class="tuile-contenu">
            <p class="tag">Global</p>
            <h3 class="tuile-titre">{{ bilan.hit_rate }} %</h3>
            <p class="tuile-action">
              {{ bilan.nb_vrais }}/{{ bilan.nb_juges }} pronos corrects ·
              {{ bilan.nb_pronos }} marché(s) figé(s)
            </p>
          </div>
          <span class="tuile-code" aria-hidden="true">{{ bilan.hit_rate }}</span>
        </article>

        <p v-else class="resume-bilan-solo doux">
          <template v-if="bilan.nb_pronos === 0">
            Aucun marché figé à {{ seuilAffiche }} % ou plus pour ce weekend.
            Figer d’abord avec
            <code>python scripts/figer_pronos_solo.py</code>,
            puis juger avec
            <code>python scripts/juger_pronos_solo.py</code>.
          </template>
          <template v-else>
            Aucun marché jugé pour l’instant
            ({{ bilan.nb_pronos }} figé(s) ≥ {{ seuilAffiche }} % — lancer
            <code>python scripts/juger_pronos_solo.py</code>).
          </template>
        </p>

        <div
          v-if="statsParMarche.length"
          class="grille grille-competitions grille-bilan-marches"
        >
          <article
            v-for="ligne in statsParMarche"
            :key="ligne.type"
            class="tuile-competition tuile-bilan-marche"
            :class="`palier-${ligne.palier}`"
            :aria-label="`${ligne.libelle} : ${ligne.hit_rate ?? 'non jugé'} %`"
          >
            <div class="tuile-contenu">
              <p class="tag">{{ ligne.libelle }}</p>
              <h3 class="tuile-titre">
                <template v-if="ligne.hit_rate != null">
                  {{ ligne.hit_rate }} %
                </template>
                <template v-else>—</template>
              </h3>
              <p class="tuile-action">
                <template v-if="ligne.total">
                  {{ ligne.vrais }}/{{ ligne.total }} pronos
                </template>
                <template v-else>—</template>
              </p>
            </div>
            <span
              v-if="ligne.hit_rate != null"
              class="tuile-code"
              aria-hidden="true"
            >{{ ligne.hit_rate }}</span>
          </article>
        </div>
      </section>

      <ul v-if="bilan.details?.length" class="liste-verdicts-solo">
        <li
          v-for="(ligne, i) in bilan.details"
          :key="i"
          :class="ligne.vrai ? 'verdict-vrai' : 'verdict-faux'"
        >
          <div class="ligne-detail-bilan">
            <div class="colonne-verdict colonne-match">
              <span class="libelle-verdict-solo">
                {{ ligne.domicile }} – {{ ligne.exterieur }}
              </span>
              <span class="meta-match-bilan">
                {{ ligne.date_match }} · {{ ligne.championnat }}
              </span>
            </div>
            <div class="colonne-verdict colonne-marche">
              <span class="marche-proba-bilan">
                {{ libelleTypeMarche(ligne.type_marche, ligne.libelle_marche) }}
                · {{ formaterProba(ligne.probabilite) }}
              </span>
            </div>
            <div class="colonne-verdict colonne-score">
              <span class="score-reel-bilan">
                Réel {{ formaterScore(ligne) }}
              </span>
            </div>
            <div class="colonne-verdict colonne-etat">
              <span class="etat-verdict-solo">
                {{ ligne.vrai ? "Vrai" : "Faux" }}
                <template v-if="ligne.motif_texte">
                  — {{ ligne.motif_texte }}
                </template>
              </span>
            </div>
          </div>
        </li>
      </ul>

      <p v-else-if="bilan.nb_juges === 0" class="doux message-vide-communaute">
        Pas encore de verdicts à afficher pour ce filtre.
      </p>

      <section
        v-if="syntheseBilan"
        class="bloc-analyse-section section-synthese-bilan"
        aria-label="Synthèse du bilan"
      >
        <header class="entete-competitions">
          <p class="tag-section">Lecture</p>
          <h2 class="titre-section-competitions">Synthèse du weekend</h2>
        </header>
        <div class="bilan-analyse synthese-bilan-texte">
          <p v-html="syntheseBilan.paragrapheBilan" />
          <p
            class="recommandation-bilan"
            v-html="syntheseBilan.paragrapheRecommandation"
          />
        </div>
      </section>

      <MentionJeuResponsable />
    </template>
  </div>
</template>

<style scoped>
.page-bilan-pronos {
  padding-bottom: 2rem;
}

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

.stats-solo {
  margin: 0;
}

.section-bilan-solo {
  margin-bottom: 1.75rem;
}

.resume-bilan-solo {
  margin: 0 0 0.75rem;
}

.resume-bilan-solo code {
  font-size: 0.85em;
}

.tuile-bilan-global {
  margin-bottom: 14px;
}

.grille-bilan-marches {
  margin-top: 0;
}

.tuile-bilan-marche .tuile-contenu,
.tuile-bilan-global .tuile-contenu {
  max-width: 78%;
}

.tuile-bilan-marche.palier-haute,
.tuile-bilan-global.palier-haute {
  --carte-accent: #3fb950;
  --fond-tuile: #0d1a12;
}

.tuile-bilan-marche.palier-moyenne,
.tuile-bilan-global.palier-moyenne {
  --carte-accent: #d29922;
  --fond-tuile: #1a1408;
}

.tuile-bilan-marche.palier-basse,
.tuile-bilan-global.palier-basse {
  --carte-accent: #f85149;
  --fond-tuile: #1a0e0e;
}

.tuile-bilan-marche.palier-neutre,
.tuile-bilan-global.palier-neutre {
  --carte-accent: var(--texte-doux, #9aa8bc);
  --fond-tuile: var(--fond-carte, #121a28);
}

.liste-verdicts-solo {
  list-style: none;
  margin: 0 0 1.5rem;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.liste-verdicts-solo li {
  padding: 0.65rem 0;
  border-bottom: 1px solid var(--bordure-douce, rgba(255, 255, 255, 0.06));
  font-size: 0.92rem;
}

.ligne-detail-bilan {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 1.25rem;
}

.colonne-verdict {
  min-width: 0;
}

.colonne-match {
  flex: 2 1 14rem;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.colonne-marche {
  flex: 2 1 11rem;
}

.colonne-score {
  flex: 0 1 auto;
  white-space: nowrap;
}

.colonne-etat {
  flex: 2 1 10rem;
  margin-left: auto;
  text-align: right;
}

.libelle-verdict-solo {
  font-weight: 600;
}

.meta-match-bilan {
  font-weight: 400;
  opacity: 0.75;
  font-size: 0.88em;
}

.marche-proba-bilan,
.score-reel-bilan {
  opacity: 0.9;
}

.verdict-vrai {
  color: #3fb950;
}

.verdict-faux {
  color: #f85149;
}

.etat-verdict-solo {
  font-weight: 600;
}

@media (max-width: 720px) {
  .colonne-match,
  .colonne-marche {
    flex: 1 1 calc(50% - 0.75rem);
  }

  .colonne-score,
  .colonne-etat {
    flex: 1 1 calc(50% - 0.75rem);
    margin-left: 0;
    text-align: left;
  }
}

@media (max-width: 480px) {
  .colonne-match,
  .colonne-marche,
  .colonne-score,
  .colonne-etat {
    flex: 1 1 100%;
  }
}

.section-synthese-bilan {
  margin-top: 0.5rem;
  margin-bottom: 1.75rem;
}

.synthese-bilan-texte p {
  margin: 0 0 0.85rem;
  line-height: 1.55;
  color: var(--texte-doux, #9aa8bc);
}

.synthese-bilan-texte p:last-child {
  margin-bottom: 0;
}

.recommandation-bilan {
  padding-top: 0.35rem;
  border-top: 1px solid var(--bordure-douce, rgba(255, 255, 255, 0.06));
}

.synthese-bilan-texte :deep(.synthese-accent) {
  font-weight: 600;
  color: var(--accent);
}

.synthese-bilan-texte :deep(.synthese-accent-prudence) {
  font-weight: 600;
  color: #d29922;
}
</style>
