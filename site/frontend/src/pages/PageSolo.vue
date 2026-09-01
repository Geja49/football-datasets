<script setup>
import { computed, onMounted, ref } from "vue";
import ChargementPage from "../composants/ChargementPage.vue";
import MentionJeuResponsable from "../composants/MentionJeuResponsable.vue";
import { CLASSES_CARTES, LOGOS_CARTES } from "../championnats.js";
import { aAccesSolo } from "../accesSolo.js";
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
/** Clé du match déplié (un seul à la fois). */
const matchOuvertCle = ref(null);

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
  matchOuvertCle.value = null;
  charger();
}

async function charger() {
  chargement.value = true;
  erreur.value = "";
  matchOuvertCle.value = null;
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

function formaterDateAffiche(dateIso, heure) {
  if (!dateIso) return "";
  const heureCourte = (heure || "").slice(0, 5);
  try {
    const d = new Date(`${dateIso}T${heureCourte || "12:00"}:00`);
    if (Number.isNaN(d.getTime())) {
      return heureCourte ? `${dateIso} · ${heureCourte}` : dateIso;
    }
    const jour = d.toLocaleDateString("fr-FR", {
      weekday: "short",
      day: "numeric",
      month: "short",
    });
    if (!heureCourte) return jour;
    return `${jour} · ${heureCourte}`;
  } catch {
    return heureCourte ? `${dateIso} · ${heureCourte}` : dateIso;
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

function logoChampionnat(nom) {
  return LOGOS_CARTES[nom] || "";
}

function cleMatch(championnat, match, index) {
  return `${championnat}|${match.date}|${match.domicile}|${match.exterieur}|${index}`;
}

function matchsAvecCle(groupe) {
  return (groupe.pronos || []).map((match, index) => ({
    match,
    index,
    cle: cleMatch(groupe.championnat, match, index),
  }));
}

function estMatchOuvert(cle) {
  return matchOuvertCle.value === cle;
}

function basculerMatch(cle) {
  matchOuvertCle.value = matchOuvertCle.value === cle ? null : cle;
}

function formaterProba(valeur) {
  if (valeur == null) return "—";
  return `${valeur} %`;
}

function formaterNombreFr(valeur, decimales = 1) {
  if (valeur == null || Number.isNaN(Number(valeur))) return null;
  return Number(valeur).toLocaleString("fr-FR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: decimales,
  });
}

/** Potentiel buts pour l’affiche (API ou marchés over 1.5 / 2.5). */
function infoButs(match) {
  let total = match?.buts_prevus_total;
  let proba25 = match?.proba_over_2_5;
  let proba15 = match?.proba_over_1_5;
  const over25 = (match?.marches || []).find((m) => m.type === "over_2_5");
  const over15 = (match?.marches || []).find((m) => m.type === "over_1_5");
  if (total == null || proba25 == null) {
    if (over25) {
      if (proba25 == null) proba25 = over25.probabilite;
      if (total == null && over25.detail) {
        const m = String(over25.detail).match(/≈\s*([\d.,]+)/);
        if (m) total = Number(m[1].replace(",", "."));
      }
    }
  }
  if (proba15 == null && over15) {
    proba15 = over15.probabilite;
  }
  if (total == null && proba25 == null && proba15 == null) return null;
  const potentiel =
    Boolean(over25) ||
    Boolean(over15) ||
    (total != null && Number(total) > 1.5) ||
    (proba25 != null && Number(proba25) > 50) ||
    (proba15 != null && Number(proba15) >= 55);
  if (!potentiel) return null;
  return { total, proba25, proba15 };
}

function texteIndicateurButs(match) {
  const info = infoButs(match);
  if (!info) return "";
  const parties = [];
  if (info.total != null) {
    parties.push(`≈ ${formaterNombreFr(info.total)} buts`);
  }
  if (info.proba25 != null && Number(info.total || 0) > 2) {
    parties.push(`Over 2,5 · ${formaterProba(info.proba25)}`);
  } else if (info.proba15 != null) {
    parties.push(`Over 1,5 · ${formaterProba(info.proba15)}`);
  } else if (info.proba25 != null) {
    parties.push(`Over 2,5 · ${formaterProba(info.proba25)}`);
  }
  return parties.join(" · ");
}

function aPotentielButs(match) {
  return Boolean(texteIndicateurButs(match));
}

function estFortCorners(match) {
  const c = match?.corners;
  if (!c?.disponible) return false;
  if (c.fort) return true;
  return c.total_prevu != null && Number(c.total_prevu) > 9;
}

function estPotentielCorners(match) {
  const c = match?.corners;
  return Boolean(c?.disponible && c.potentiel);
}

function texteIndicateurCorners(match) {
  const c = match?.corners;
  if (!c?.disponible || c.total_prevu == null) return "";
  const approx = `≈ ${formaterNombreFr(c.total_prevu)} corners`;
  if (estFortCorners(match)) return `Corners ↑ · ${approx}`;
  if (c.potentiel) return approx;
  return "";
}

function libelleMarche(marche) {
  if (marche.signal_fort && marche.probabilite == null) {
    return `${marche.libelle} (signal fort)`;
  }
  return marche.libelle;
}

function seuilHauteConfiance() {
  return donnees.value?.seuil_probabilite ?? 85;
}

function seuilMiseEnAvant() {
  return donnees.value?.seuil_mise_en_avant ?? 75;
}

function estMisEnAvant(marcheOuCorners) {
  if (!marcheOuCorners) return false;
  if (marcheOuCorners.haute_confiance || marcheOuCorners.mise_en_avant) return true;
  const p = marcheOuCorners.probabilite;
  return p != null && Number(p) >= seuilMiseEnAvant();
}

function estHauteConfiance(marcheOuCorners) {
  if (!marcheOuCorners) return false;
  if (marcheOuCorners.haute_confiance) return true;
  const p = marcheOuCorners.probabilite;
  return p != null && Number(p) >= seuilHauteConfiance();
}

function niveauConfiance(marcheOuCorners) {
  if (estHauteConfiance(marcheOuCorners)) return 2;
  if (estMisEnAvant(marcheOuCorners)) return 1;
  return 0;
}

function libelleBadgeConfiance(marcheOuCorners) {
  if (!marcheOuCorners) return "";
  if (estHauteConfiance(marcheOuCorners)) {
    return `Haute confiance ≥ ${seuilHauteConfiance()} %`;
  }
  if (estMisEnAvant(marcheOuCorners)) {
    return `Confiance ≥ ${seuilMiseEnAvant()} %`;
  }
  return "Potentiel";
}

function classeBadgeConfiance(marcheOuCorners) {
  const niveau = niveauConfiance(marcheOuCorners);
  if (niveau >= 2) return "badge-haute-confiance";
  if (niveau >= 1) return "badge-mise-en-avant";
  return "badge-potentiel";
}

/** Marchés triés : ≥ 85 %, puis ≥ 75 %, puis le reste (proba décroissante). */
function marchesTries(match) {
  return [...(match?.marches || [])].sort((a, b) => {
    const diff = niveauConfiance(b) - niveauConfiance(a);
    if (diff !== 0) return diff;
    return (Number(b.probabilite) || 0) - (Number(a.probabilite) || 0);
  });
}

function aMarcheMisEnAvant(match) {
  if ((match?.marches || []).some((m) => estMisEnAvant(m))) return true;
  const c = match?.corners;
  return Boolean(c?.disponible && c.potentiel && estMisEnAvant(c));
}

function texteCorners(corners) {
  if (!corners?.disponible) {
    return corners?.message || "non disponible";
  }
  const parties = [];
  if (corners.total_prevu != null) {
    parties.push(`≈ ${formaterNombreFr(corners.total_prevu)} prévus`);
  }
  if (corners.ligne_over != null && corners.probabilite != null) {
    parties.push(
      `over ${String(corners.ligne_over).replace(".", ",")} : ${formaterProba(corners.probabilite)}`,
    );
  } else if (corners.probabilite != null) {
    parties.push(formaterProba(corners.probabilite));
  } else if (corners.detail) {
    parties.push(corners.detail);
  }
  return parties.length ? parties.join(" · ") : corners.detail || "—";
}

function texteDetailButs(match) {
  const info = infoButs(match);
  if (!info) return "";
  const parties = [];
  if (info.total != null) {
    parties.push(`total prévu ≈ ${formaterNombreFr(info.total)}`);
  }
  if (info.proba != null) {
    parties.push(`Over 2,5 : ${formaterProba(info.proba)}`);
  }
  return parties.join(" · ");
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
    if (!aAccesSolo(session.utilisateur)) {
      erreur.value =
        "Accès réservé aux administrateurs et super utilisateurs.";
      chargement.value = false;
      return;
    }
  } catch {
    utilisateur.value = null;
    erreur.value = "Connexion requise pour accéder aux pronos Solo.";
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
        <p class="sur-titre-analyse">Pronostics</p>
        <h1 class="titre-analyse">Solo</h1>
        <p class="intro-analyse">
          Pronostics du weekend (ven. 00h → lun. 23h59) : cliquez un match pour
          voir victoire, buts, corners
          <template v-if="estFige"> (snapshot figé)</template>
          <template v-else> — recalculés en direct</template>.
        </p>
      </header>
    </div>
  </section>

  <div class="page page-solo">
    <p v-if="erreur" class="erreur">{{ erreur }}</p>
    <ChargementPage v-if="chargement" message="Analyse des matchs du weekend" />

    <template v-else-if="aAccesSolo(utilisateur) && donnees">
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
            {{ donnees.nb_matchs_avec_prono }} avec prono (victoire, buts ou corners)
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
        Aucun prono (victoire, buts &gt; 2 ou corners &gt; 8) ce weekend.
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
            <img
              v-if="logoChampionnat(groupe.championnat)"
              :src="logoChampionnat(groupe.championnat)"
              :alt="groupe.championnat"
              class="logo-championnat-solo"
            />
            {{ groupe.championnat }}
          </h2>

          <div class="liste-affiches-solo">
            <article
              v-for="item in matchsAvecCle(groupe)"
              :key="item.cle"
              class="carte-prono-solo"
              :class="{ ouverte: estMatchOuvert(item.cle) }"
            >
              <button
                type="button"
                class="affiche-match-solo"
                :aria-expanded="estMatchOuvert(item.cle)"
                :aria-controls="`detail-solo-${groupe.championnat.replace(/\s+/g, '-')}-${item.index}`"
                @click="basculerMatch(item.cle)"
              >
                <div class="meta-affiche-solo">
                  <span class="date-affiche-solo">
                    {{ formaterDateAffiche(item.match.date, item.match.heure) }}
                    <template v-if="item.match.journee"> · J{{ item.match.journee }}</template>
                  </span>
                  <span class="chevron-affiche-solo" aria-hidden="true">
                    {{ estMatchOuvert(item.cle) ? "▾" : "▸" }}
                  </span>
                </div>

                <div class="equipes-affiche-solo">
                  <div class="club-affiche-solo club-domicile-solo">
                    <img
                      v-if="item.match.url_logo_domicile"
                      :src="item.match.url_logo_domicile"
                      :alt="item.match.domicile"
                      class="blason"
                    />
                    <span class="nom-club-solo">{{ item.match.domicile }}</span>
                  </div>
                  <div class="milieu-affiche-solo">
                    <strong class="versus-solo">vs</strong>
                    <small class="ligue-affiche-solo">{{ item.match.championnat }}</small>
                  </div>
                  <div class="club-affiche-solo club-exterieur-solo">
                    <img
                      v-if="item.match.url_logo_exterieur"
                      :src="item.match.url_logo_exterieur"
                      :alt="item.match.exterieur"
                      class="blason"
                    />
                    <span class="nom-club-solo">{{ item.match.exterieur }}</span>
                  </div>
                </div>

                <div
                  v-if="aPotentielButs(item.match) || estPotentielCorners(item.match) || aMarcheMisEnAvant(item.match)"
                  class="indicateurs-affiche-solo"
                >
                  <span
                    v-if="aMarcheMisEnAvant(item.match)"
                    class="indicateur-confiance-solo"
                  >Confiance ≥ {{ seuilMiseEnAvant() }} %</span>
                  <span
                    v-if="aPotentielButs(item.match)"
                    class="indicateur-buts-solo"
                  >{{ texteIndicateurButs(item.match) }}</span>
                  <span
                    v-if="texteIndicateurCorners(item.match)"
                    class="indicateur-corners-solo"
                    :class="estFortCorners(item.match) ? 'corners-fort' : 'corners-potentiel'"
                  >{{ texteIndicateurCorners(item.match) }}</span>
                </div>
              </button>

              <div
                v-show="estMatchOuvert(item.cle)"
                :id="`detail-solo-${groupe.championnat.replace(/\s+/g, '-')}-${item.index}`"
                class="detail-prono-solo"
              >
                <p v-if="item.match.score_modal" class="doux petit">
                  Score modal : <strong>{{ item.match.score_modal }}</strong>
                </p>
                <p
                  v-if="item.match.match_physique && item.match.match_physique.actif"
                  class="badge-physique-solo"
                >
                  {{ item.match.match_physique.detail || "Match physique" }}
                </p>

                <p v-if="texteDetailButs(item.match)" class="bloc-detail-buts-solo">
                  <strong>Buts</strong>
                  — {{ texteDetailButs(item.match) }}
                </p>

                <ul class="liste-marches-solo">
                  <li v-for="(marche, i) in marchesTries(item.match)" :key="i">
                    <span class="libelle-marche-solo">
                      {{ libelleMarche(marche) }}
                      <span
                        class="badge-confiance-solo"
                        :class="classeBadgeConfiance(marche)"
                      >
                        {{ libelleBadgeConfiance(marche) }}
                      </span>
                      <span
                        v-if="marche.detail"
                        class="detail-marche-solo doux"
                      > — {{ marche.detail }}</span>
                    </span>
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

                <div
                  v-if="item.match.corners.disponible && item.match.corners.potentiel"
                  class="bloc-detail-corners-solo"
                >
                  <p class="titre-bloc-corners-solo">
                    <strong>Corners</strong>
                    <span
                      v-if="estFortCorners(item.match)"
                      class="indicateur-corners-solo corners-fort"
                    >Fort potentiel</span>
                    <span
                      class="badge-confiance-solo"
                      :class="classeBadgeConfiance(item.match.corners)"
                    >
                      {{ libelleBadgeConfiance(item.match.corners) }}
                    </span>
                    <span
                      v-if="item.match.corners.verdict"
                      class="badge-verdict-solo"
                      :class="classeVerdict(item.match.corners.verdict)"
                      :title="item.match.corners.verdict.motif_texte || ''"
                    >
                      {{ libelleVerdictCourt(item.match.corners.verdict) }}
                    </span>
                  </p>
                  <p class="doux petit corners-solo">
                    {{ texteCorners(item.match.corners) }}
                  </p>
                  <p
                    v-if="
                      item.match.corners.detail &&
                      !String(item.match.corners.detail).startsWith('Environ')
                    "
                    class="doux petit detail-corners-texte-solo"
                  >
                    {{ item.match.corners.detail }}
                  </p>
                </div>
                <p
                  v-else-if="item.match.corners.disponible && !item.match.corners.potentiel"
                  class="doux petit corners-solo"
                >
                  Corners : pas de potentiel &gt; 8
                  <template v-if="item.match.corners.total_prevu != null">
                    (≈ {{ formaterNombreFr(item.match.corners.total_prevu) }} prévus)
                  </template>
                </p>
                <p v-else class="doux petit corners-solo">
                  Corners : {{ item.match.corners.message || "non disponible" }}
                </p>
              </div>
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
  display: flex;
  align-items: center;
  gap: 0.55rem;
  font-size: 1.15rem;
  font-weight: 700;
  margin: 0;
  padding-bottom: 0.35rem;
  border-bottom: 2px solid var(--bordure-douce, rgba(255, 255, 255, 0.12));
}

.logo-championnat-solo {
  width: 1.4rem;
  height: 1.4rem;
  object-fit: contain;
}

.liste-affiches-solo {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.carte-prono-solo {
  background: var(--surface-carte, rgba(255, 255, 255, 0.04));
  border: 1px solid var(--bordure-douce, rgba(255, 255, 255, 0.08));
  border-radius: 0.75rem;
  overflow: hidden;
  transition: border-color 0.15s ease;
}

.carte-prono-solo.ouverte {
  border-color: var(--accent, #58a6ff);
}

.affiche-match-solo {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  width: 100%;
  margin: 0;
  padding: 0.75rem 0.9rem;
  background: transparent;
  border: none;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.affiche-match-solo:hover,
.affiche-match-solo:focus-visible {
  background: color-mix(in srgb, var(--accent, #58a6ff) 8%, transparent);
  outline: none;
}

.meta-affiche-solo {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}

.date-affiche-solo {
  font-size: 0.82rem;
  color: var(--texte-doux, #9aa4b2);
}

.chevron-affiche-solo {
  font-size: 0.85rem;
  color: var(--texte-doux, #9aa4b2);
  flex-shrink: 0;
}

.equipes-affiche-solo {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 0.5rem;
  align-items: center;
}

.club-affiche-solo {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  min-width: 0;
}

.club-domicile-solo {
  justify-content: flex-end;
  text-align: right;
}

.club-exterieur-solo {
  justify-content: flex-start;
  text-align: left;
}

.club-domicile-solo .nom-club-solo {
  order: -1;
}

.nom-club-solo {
  font-weight: 700;
  font-size: 0.95rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.milieu-affiche-solo {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.1rem;
  min-width: 2.8rem;
}

.versus-solo {
  font-size: 0.85rem;
  font-weight: 700;
  opacity: 0.75;
}

.ligue-affiche-solo {
  font-size: 0.65rem;
  color: var(--texte-doux, #9aa4b2);
  max-width: 5.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: center;
}

.indicateurs-affiche-solo {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem 0.5rem;
  align-items: center;
}

.indicateur-buts-solo,
.indicateur-corners-solo,
.indicateur-jaunes-solo,
.indicateur-confiance-solo {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.15rem 0.45rem;
  border-radius: 0.3rem;
  line-height: 1.3;
}

.indicateur-confiance-solo {
  background: color-mix(in srgb, #3fb8af 16%, transparent);
  border: 1px solid color-mix(in srgb, #3fb8af 42%, var(--ligne, #ccc));
  color: var(--texte, inherit);
}

.indicateur-buts-solo {
  background: color-mix(in srgb, #58a6ff 12%, transparent);
  border: 1px solid color-mix(in srgb, #58a6ff 35%, var(--ligne, #ccc));
  color: var(--texte, inherit);
}

.indicateur-jaunes-solo {
  background: color-mix(in srgb, #e3b341 14%, transparent);
  border: 1px solid color-mix(in srgb, #e3b341 42%, var(--ligne, #ccc));
  color: var(--texte, inherit);
}

.indicateur-corners-solo.corners-potentiel {
  background: color-mix(in srgb, #d29922 14%, transparent);
  border: 1px solid color-mix(in srgb, #d29922 40%, var(--ligne, #ccc));
}

.indicateur-corners-solo.corners-fort {
  background: color-mix(in srgb, #f0883e 18%, transparent);
  border: 1px solid color-mix(in srgb, #f0883e 50%, var(--ligne, #ccc));
}

.detail-prono-solo {
  padding: 0 0.9rem 0.9rem;
  border-top: 1px solid var(--bordure-douce, rgba(255, 255, 255, 0.08));
}

.bloc-detail-buts-solo {
  margin: 0.65rem 0 0.25rem;
  font-size: 0.9rem;
}

.bloc-detail-corners-solo {
  margin-top: 0.55rem;
}

.titre-bloc-corners-solo {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem;
  margin: 0 0 0.15rem;
  font-size: 0.9rem;
}

.detail-corners-texte-solo {
  margin: 0.15rem 0 0;
  font-style: italic;
}

.liste-marches-solo {
  list-style: none;
  margin: 0.65rem 0;
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

.badge-confiance-solo {
  display: inline-block;
  margin-left: 0.35rem;
  padding: 0.1rem 0.35rem;
  font-size: 0.68rem;
  font-weight: 600;
  font-style: normal;
  border-radius: 0.25rem;
  vertical-align: middle;
}

.badge-haute-confiance {
  background: color-mix(in srgb, #3fb950 20%, transparent);
  border: 1px solid color-mix(in srgb, #3fb950 45%, var(--ligne, #ccc));
}

.badge-mise-en-avant {
  background: color-mix(in srgb, #3fb8af 18%, transparent);
  border: 1px solid color-mix(in srgb, #3fb8af 45%, var(--ligne, #ccc));
}

.badge-potentiel {
  background: color-mix(in srgb, #58a6ff 16%, transparent);
  border: 1px solid color-mix(in srgb, #58a6ff 40%, var(--ligne, #ccc));
}

.detail-marche-solo {
  font-weight: 400;
  font-size: 0.85em;
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

@media (max-width: 560px) {
  .equipes-affiche-solo {
    grid-template-columns: 1fr;
    gap: 0.35rem;
  }

  .club-domicile-solo,
  .club-exterieur-solo {
    justify-content: flex-start;
    text-align: left;
  }

  .club-domicile-solo .nom-club-solo {
    order: 0;
  }

  .milieu-affiche-solo {
    flex-direction: row;
    justify-content: flex-start;
    gap: 0.45rem;
    padding-left: 0.1rem;
  }

  .liste-marches-solo li {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
  }
}

</style>
