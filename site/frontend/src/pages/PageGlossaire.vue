<script setup>
const sections = [
  { id: "xg", titre: "xG et dérivés" },
  { id: "attaque", titre: "Buts, passes, tirs" },
  { id: "defense", titre: "Actions défensives" },
  { id: "diagrammes", titre: "Radar et densités" },
  { id: "analyse", titre: "Analyse de match" },
  { id: "elo", titre: "Elo ClubElo" },
  { id: "marche", titre: "Valeurs et transferts" },
  { id: "cotes", titre: "Cotes marché" },
  { id: "pronos", titre: "Pronostics communautaires" },
  { id: "sources", titre: "Sources de données" },
];
</script>

<template>
  <section class="hero hero-compact">
    <div class="hero-inner">
      <p class="tag">Pédagogie</p>
      <h1 class="titre-analyse">Comprendre les stats</h1>
      <p class="doux">
        Glossaire des indicateurs affichés dans Stats Foot — définitions courtes,
        limites de couverture, sans métriques inventées.
      </p>
    </div>
  </section>

  <div class="page page-glossaire">
    <nav class="sommaire-glossaire" aria-label="Sommaire du glossaire">
      <p class="tag-section">Sommaire</p>
      <ul>
        <li v-for="s in sections" :key="s.id">
          <a :href="`#${s.id}`">{{ s.titre }}</a>
        </li>
      </ul>
    </nav>

    <article class="bloc texte-cgu">
      <h2 id="xg">xG et dérivés</h2>
      <dl class="liste-concepts">
        <div>
          <dt>xG (expected goals)</dt>
          <dd>
            Probabilité qu’un tir se transforme en but, selon la qualité de
            l’occasion. Cumulé sur une saison ou un match, il estime le volume
            d’occasions créées — pas le score réel.
          </dd>
        </div>
        <div>
          <dt>xA (expected assists)</dt>
          <dd>
            Probabilité qu’une passe mène à un but (souvent via le xG du tir
            suivant). Visible sur les fiches joueur et les classements passeurs
            (accueil / championnat).
          </dd>
        </div>
        <div>
          <dt>xG marqués / xG encaissés</dt>
          <dd>
            Pour une équipe : xG créés (attaque) et xG concédés (défense), en
            moyenne par match selon le lieu (domicile / extérieur) sur l’analyse.
            Sur le radar club, « xG encaissés » et « Solidité » (buts contre)
            sont des axes inversés : moins = mieux.
          </dd>
        </div>
        <div>
          <dt>xG chaîne (xGChain)</dt>
          <dd>
            Part du xG des séquences auxquelles le joueur a participé (passe ou
            action dans la chaîne). Source Understat, pages joueur.
          </dd>
        </div>
        <div>
          <dt>xG construction (xGBuildup)</dt>
          <dd>
            Comme la chaîne, mais sans compter le tireur ni le passeur décisif :
            participation au build-up offensif, pas la défense.
          </dd>
        </div>
        <div>
          <dt>xG des tirs subis</dt>
          <dd>
            Sur la contribution défensive historique : xG des tirs adverses
            (StatsBomb), pas un PSxG (post-shot). Seulement quand la source
            défensive est disponible.
          </dd>
        </div>
        <div>
          <dt>xG prévu (analyse)</dt>
          <dd>
            Lambda du modèle Poisson pour le match à venir (ou rejoué) :
            occasions attendues domicile / extérieur, pas un tipster.
          </dd>
        </div>
      </dl>
      <p class="mention-ldc">
        Stats Foot n’affiche pas de NP-xG (xG hors penalties) distinct : les
        totaux Understat utilisés ici sont ceux fournis par la source.
      </p>

      <h2 id="attaque">Buts, passes, tirs</h2>
      <dl class="liste-concepts">
        <div>
          <dt>Buts</dt>
          <dd>
            Buts marqués en championnat (et LDC quand les données existent). Sur
            le radar / densités joueur : total de saison ; sur le radar club :
            moyenne par match. Accueil : tops buteurs des 5 ligues.
          </dd>
        </div>
        <div>
          <dt>Passes décisives</dt>
          <dd>
            Assistances comptabilisées. Comparées au xA pour voir si le joueur
            « surperforme » ou sous-performe ses occasions de passe. Accueil :
            tops passeurs.
          </dd>
        </div>
        <div>
          <dt>Passes clés</dt>
          <dd>
            Passes qui mènent à un tir (Understat). Complément du volume
            créatif, au-delà des seules décisives.
          </dd>
        </div>
        <div>
          <dt>Tirs / tirs cadrés</dt>
          <dd>
            Volume de tirs (fiches joueur, radar club, match joué). Les tirs
            cadrés apparaissent surtout dans l’analyse de rencontre (profil
            saison et bilan du match).
          </dd>
        </div>
        <div>
          <dt>Minutes / matchs</dt>
          <dd>
            Temps de jeu et matchs disputés. Sur le radar joueur, les minutes
            font partie du profil de saison.
          </dd>
        </div>
        <div>
          <dt>Cartons (jaunes / rouges)</dt>
          <dd>
            Totaux par saison sur la fiche joueur ; sur l’analyse de match,
            rythme de cartons (forme récente ou moyenne de saison) pour un
            scénario « cartons » (jaunes / rouges attendus).
          </dd>
        </div>
        <div>
          <dt>Dribbles</dt>
          <dd>
            Non disponibles : Understat ne fournit pas les dribbles. L’API le
            rappelle explicitement si un classement « dribbles » est demandé.
          </dd>
        </div>
      </dl>

      <h2 id="defense">Actions défensives</h2>
      <p>
        Bloc « Contribution défensive » sur la page joueur, quand la table
        existe : tacles, tacles réussis, interceptions, blocs, dégagements,
        duels (dont gagnés), recoveries, pressions, arrêts, xG des tirs subis.
      </p>
      <p class="mention-ldc">
        Couverture limitée : StatsBomb Open Data et/ou jeu Wyscout 2017-2018
        (licence CC BY). Les saisons récentes des 5 grands championnats n’y
        figurent en général pas — le message affiché sur la page le rappelle.
      </p>

      <h2 id="diagrammes">Radar et densités</h2>
      <dl class="liste-concepts">
        <div>
          <dt>Radar</dt>
          <dd>
            Profil multi-axes normalisé (0–1) par rapport à un plafond ou à la
            distribution du championnat. Joueur : buts, xG, passes D., xA, tirs,
            minutes. Club : buts/match, xG, tirs, forme (5 derniers), solidité,
            xG encaissés. Polygone pointillé = moyenne ligue (ou adversaire en
            comparaison).
          </dd>
        </div>
        <div>
          <dt>Densités</dt>
          <dd>
            Histogrammes par axe : où se situe le joueur ou le club dans la
            ligue (centile, « Top X % », rang approximatif). Le losange marque
            la moyenne ligue quand elle est connue.
          </dd>
        </div>
        <div>
          <dt>Forme (clubs)</dt>
          <dd>
            Points cumulés sur les 5 derniers matchs joués (victoire 3, nul 1,
            défaite 0), plafonnés à 15 sur le radar. Sur l’analyse de match :
            série V/N/D + buts pour/contre et cartons récents.
          </dd>
        </div>
        <div>
          <dt>Comparer</dt>
          <dd>
            Page <router-link to="/comparer">/comparer</router-link> : deux
            joueurs ou deux clubs sur les mêmes axes (radar + densités), comme
            vs moyenne ligue.
          </dd>
        </div>
      </dl>

      <h2 id="analyse">Analyse de match</h2>
      <p>
        Page <router-link to="/match">/match</router-link> — scénario
        statistique à partir de football.db (forme, xG, tirs, cartons). Pas un
        pronostic de paris.
      </p>
      <dl class="liste-concepts">
        <div>
          <dt>Modèle Poisson (buts indépendants)</dt>
          <dd>
            Grille de scores 0–8 buts → score le plus probable, probabilités
            1-N-2, « les deux marquent », plus de 2 buts. Les xG prévus domicile
            / extérieur alimentent le modèle.
          </dd>
        </div>
        <div>
          <dt>Scénarios détaillés</dt>
          <dd>
            Quatre lectures : rythme (ouvert / fermé / proche de la moyenne du
            championnat), les deux équipes marquent, volume de buts, cartons
            attendus. Récit en français + bilan « prévu vs réel » si le match
            est déjà joué.
          </dd>
        </div>
        <div>
          <dt>Forces / faiblesses</dt>
          <dd>
            Phrases automatiques quand xG, tirs cadrés ou cartons s’écartent
            d’environ ±15 % de la moyenne du championnat (même lieu).
          </dd>
        </div>
        <div>
          <dt>Lecture marché</dt>
          <dd>
            Si des cotes 1-N-2 sont disponibles côté serveur : affichage
            informatif à côté du modèle — toujours en lecture seule.
          </dd>
        </div>
      </dl>

      <h2 id="elo">Elo ClubElo</h2>
      <p>
        Note Elo des clubs via l’API publique
        <a href="https://clubelo.com" rel="noopener noreferrer" target="_blank">ClubElo</a>,
        avec cache. Affichée sur les pages club avec force relative et rang
        indicatif (pas un classement officiel de compétition).
      </p>
      <p class="mention-ldc">
        Indisponible ou dégradé si le réseau / ClubElo ne répond pas. Bouton
        « Réessayer » sur la fiche équipe. Ligue des champions : l’Elo n’alimente
        pas le classement interne de la compétition.
      </p>

      <h2 id="marche">Valeurs et transferts</h2>
      <p>
        Sur certaines fiches joueur : estimation de valeur de marché (euros),
        âge, pic éventuel, et historique de transferts (frais, clubs, dates).
      </p>
      <p class="mention-ldc">
        Données issues de dumps communautaires — pas une mise à jour live type
        Transfermarkt. La mention « dump / pas live » apparaît quand le bloc
        est présent.
      </p>

      <h2 id="cotes">Cotes marché</h2>
      <p>
        Page <router-link to="/cotes">/cotes</router-link> : cotes moyennes 1-N-2
        (et détail bookmakers si fourni) pour les matchs à venir, via The Odds
        API côté serveur.
      </p>
      <p class="mention-ldc">
        Informations uniquement — Stats Foot n’est pas un opérateur de paris et
        ne propose aucune prise de pari. Sans clé API configurée, la page
        l’indique clairement.
      </p>

      <h2 id="pronos">Pronostics communautaires</h2>
      <dl class="liste-concepts">
        <div>
          <dt>Pronos privés</dt>
          <dd>
            Score exact ou 1X2 avant coup d’envoi (compte 18+). Classement
            ludique : 3 pts score exact · 1 pt bon vainqueur (prono score) ·
            1 pt 1X2 correct — aucun gain monétaire.
          </dd>
        </div>
        <div>
          <dt>Commentaires &amp; ligues</dt>
          <dd>
            Discussions sur les pages d’analyse ; ligues privées entre amis.
            Opinions de la communauté, pas un conseil en paris.
          </dd>
        </div>
      </dl>
      <p>
        Détail légal :
        <router-link to="/conditions">Conditions d’utilisation</router-link>.
      </p>

      <h2 id="sources">Sources de données</h2>
      <ul>
        <li>
          <strong>Understat</strong> — stats joueurs / xG / xA des 5 grands
          championnats (buteurs, passeurs, fiches, matchs_xg).
        </li>
        <li>
          <strong>football-data.co.uk</strong> — résultats, calendriers et
          stats match (tirs, cartons, etc.) via les datasets du dépôt.
        </li>
        <li>
          <strong>openfootball</strong> — calendrier et scores (notamment Ligue
          des champions) ; heures en heure locale de compétition.
        </li>
        <li>
          <strong>ClubElo</strong> — Elo clubs (API HTTPS publique).
        </li>
        <li>
          <strong>StatsBomb Open Data / Wyscout 2017-2018</strong> — actions
          défensives historiques seulement.
        </li>
        <li>
          <strong>OpenML (historique)</strong> — buts joueur LDC pour certaines
          saisons anciennes (environ 2013–2021) ; les saisons récentes LDC n’ont
          souvent pas de stats joueur ici.
        </li>
        <li>
          <strong>Dumps valeur / transferts</strong> — estimations figées, pas
          live.
        </li>
        <li>
          <strong>The Odds API</strong> — cotes 1-N-2 en lecture seule quand une
          clé est configurée côté serveur.
        </li>
      </ul>
      <p class="mention-ldc">
        La couverture varie par compétition et saison : les messages « mention
        sources » sur les pages club / championnat / joueur font foi.
      </p>
    </article>
  </div>
</template>
