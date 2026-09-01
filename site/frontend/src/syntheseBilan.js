import {
  estMarcheCarton,
  libelleTypeMarche,
} from "./libellesMarches.js";

const SEUIL_PRIVILEGIER_DEFAUT = 70;
const SEUIL_EVITER_DEFAUT = 50;
const ECHANTILLON_FAIBLE_DEFAUT = 3;

/** Échappe le texte pour un rendu HTML sûr (contenu généré côté app uniquement). */
export function echapperHtml(texte) {
  return String(texte)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Met en évidence un fragment de la synthèse. */
export function accentuer(texte, classe = "synthese-accent") {
  return `<strong class="${classe}">${echapperHtml(texte)}</strong>`;
}

/** Joint des libellés en français : « A », « A et B », « A, B et C ». */
export function joindreLibelles(elements) {
  const liste = elements.filter(Boolean);
  if (liste.length === 0) return "";
  const cit = (libelle) => `« ${accentuer(libelle)} »`;
  if (liste.length === 1) return cit(liste[0]);
  if (liste.length === 2) return `${cit(liste[0])} et ${cit(liste[1])}`;
  const debut = liste
    .slice(0, -1)
    .map(cit)
    .join(", ");
  return `${debut} et ${cit(liste.at(-1))}`;
}

function formaterTaux(taux) {
  if (taux == null) return null;
  const texte = Number.isInteger(taux) ? String(taux) : String(taux).replace(".", ",");
  return accentuer(`${texte} %`);
}

function marchesJuges(parMarche) {
  return Object.entries(parMarche || {})
    .filter(([type]) => !estMarcheCarton(type))
    .map(([type, stats]) => ({
      type,
      libelle: libelleTypeMarche(type),
      vrais: stats.vrais ?? 0,
      total: stats.total ?? 0,
      hit_rate: stats.hit_rate,
    }))
    .filter((m) => m.total > 0 && m.hit_rate != null)
    .sort((a, b) => b.hit_rate - a.hit_rate || b.total - a.total);
}

function championnatsJuges(parChampionnat) {
  return Object.entries(parChampionnat || {})
    .map(([nom, stats]) => ({
      nom,
      vrais: stats.vrais ?? 0,
      total: stats.total ?? 0,
      hit_rate: stats.hit_rate,
    }))
    .filter((c) => c.total > 0 && c.hit_rate != null)
    .sort((a, b) => b.hit_rate - a.hit_rate || b.total - a.total);
}

function nuanceEchantillon(total, seuilFaible) {
  if (total <= 1) return " (échantillon très faible)";
  if (total < seuilFaible) return " (échantillon faible)";
  return "";
}

function decrireMarche(marche, seuilFaible) {
  const pronos = accentuer(
    `${marche.total} prono${marche.total > 1 ? "s" : ""}`,
  );
  return `${accentuer(marche.libelle)} (${formaterTaux(marche.hit_rate)}, ${pronos}${nuanceEchantillon(marche.total, seuilFaible)})`;
}

function formaterComptagePronos(nb) {
  return accentuer(
    `${nb} marché${nb > 1 ? "s" : ""} figé${nb > 1 ? "s" : ""}`,
  );
}

function formaterBilanJuges(nbVrais, nbJuges) {
  return accentuer(
    `${nbVrais} correct${nbVrais > 1 ? "s" : ""} sur ${nbJuges} jugé${nbJuges > 1 ? "s" : ""}`,
  );
}

/**
 * Construit une synthèse lisible du bilan weekend Solo (HTML sûr pour v-html).
 * @returns {{ paragrapheBilan: string, paragrapheRecommandation: string } | null}
 */
export function construireSyntheseBilan(
  bilan,
  {
    seuilPrivilegier = SEUIL_PRIVILEGIER_DEFAUT,
    seuilEviter = SEUIL_EVITER_DEFAUT,
    echantillonFaible = ECHANTILLON_FAIBLE_DEFAUT,
  } = {},
) {
  if (!bilan) return null;

  const seuil = bilan.seuil_probabilite ?? seuilPrivilegier;
  const libelleWeekend = bilan.weekend?.libelle || "ce weekend";
  const marches = marchesJuges(bilan.par_marche);
  const championnats = championnatsJuges(bilan.par_championnat);

  if (bilan.nb_juges === 0) {
    const paragrapheBilan =
      bilan.nb_pronos === 0
        ? `Aucun marché figé à ${accentuer(`${seuil} %`)} ou plus pour ${accentuer(libelleWeekend)}. Impossible de dresser un bilan tant que des pronos n’ont pas été figés puis jugés.`
        : `${formaterComptagePronos(bilan.nb_pronos)} à ${accentuer(`${seuil} %`)} ou plus pour ${accentuer(libelleWeekend)}, mais aucun n’a encore été jugé. Revenez après l’exécution du script de jugement.`;

    return {
      paragrapheBilan,
      paragrapheRecommandation:
        "Sans verdicts sur ce weekend, aucune recommandation par type de marché n’est possible pour l’instant.",
    };
  }

  const tauxGlobal = formaterTaux(bilan.hit_rate);
  const intro = `Sur ${accentuer(libelleWeekend)}, les pronos figés à ${accentuer(`${seuil} %`)} ou plus affichent un taux de réussite de ${tauxGlobal} (${formaterBilanJuges(bilan.nb_vrais, bilan.nb_juges)}`;

  const complementPronos =
    bilan.nb_pronos > bilan.nb_juges
      ? `, sur ${accentuer(`${bilan.nb_pronos} marché${bilan.nb_pronos > 1 ? "s" : ""} figé${bilan.nb_pronos > 1 ? "s" : ""} au total`)}`
      : "";

  let paragrapheBilan = `${intro}${complementPronos}).`;

  if (marches.length) {
    const meilleurs = marches.filter((m) => m.hit_rate >= seuilPrivilegier);
    const pires = marches.filter((m) => m.hit_rate < seuilEviter);
    const moyens = marches.filter(
      (m) => m.hit_rate >= seuilEviter && m.hit_rate < seuilPrivilegier,
    );

    const parties = [];

    if (meilleurs.length) {
      const noms = joindreLibelles(meilleurs.map((m) => m.libelle));
      parties.push(
        `${meilleurs.length > 1 ? "Les marchés" : "Le marché"} ${noms} ${meilleurs.length > 1 ? "ont" : "a"} le mieux tenu (${meilleurs.map((m) => formaterTaux(m.hit_rate)).join(", ")})`,
      );
    }

    if (pires.length) {
      const noms = joindreLibelles(pires.map((m) => m.libelle));
      parties.push(
        `${pires.length > 1 ? "les marchés" : "le marché"} ${noms} ${pires.length > 1 ? "ont" : "a"} été plus difficile${pires.length > 1 ? "s" : ""} (${pires.map((m) => formaterTaux(m.hit_rate)).join(", ")})`,
      );
    } else if (moyens.length && !meilleurs.length) {
      const noms = joindreLibelles(moyens.slice(0, 2).map((m) => m.libelle));
      parties.push(
        `aucun type de marché n’a dépassé ${accentuer(`${seuilPrivilegier} %`)} de réussite ; les moins décevants restent ${noms}`,
      );
    }

    if (parties.length) {
      paragrapheBilan += ` ${parties[0].charAt(0).toUpperCase()}${parties[0].slice(1)}`;
      if (parties.length > 1) {
        paragrapheBilan += `, tandis que ${parties[1]}`;
      }
      paragrapheBilan += ".";
    }
  }

  if (championnats.length >= 2) {
    const meilleur = championnats[0];
    const pire = championnats.at(-1);
    if (
      meilleur.nom !== pire.nom &&
      meilleur.hit_rate - pire.hit_rate >= 15 &&
      meilleur.total >= echantillonFaible &&
      pire.total >= echantillonFaible
    ) {
      paragrapheBilan += ` Par championnat, ${accentuer(meilleur.nom)} (${formaterTaux(meilleur.hit_rate)}) a mieux répondu que ${accentuer(pire.nom)} (${formaterTaux(pire.hit_rate)}).`;
    }
  }

  const aPrivilegier = marches.filter((m) => m.hit_rate >= seuilPrivilegier);
  const aEviter = marches.filter((m) => m.hit_rate < seuilEviter);
  const prudence = marches.filter(
    (m) => m.hit_rate >= seuilEviter && m.hit_rate < seuilPrivilegier,
  );

  const recoParties = [];

  if (aPrivilegier.length) {
    const liste = aPrivilegier.map((m) => decrireMarche(m, echantillonFaible)).join(", ");
    recoParties.push(
      `pour le prochain weekend, les types de paris qui ont le mieux fonctionné sont ${liste}`,
    );
  }

  if (aEviter.length) {
    const liste = aEviter.map((m) => decrireMarche(m, echantillonFaible)).join(", ");
    recoParties.push(
      `${aPrivilegier.length ? "en revanche, " : ""}${accentuer("misez avec prudence", "synthese-accent-prudence")} sur ${liste}`,
    );
  }

  if (!aPrivilegier.length && !aEviter.length && prudence.length) {
    const liste = prudence.map((m) => decrireMarche(m, echantillonFaible)).join(", ");
    recoParties.push(
      `aucun marché n’a atteint ${accentuer(`${seuilPrivilegier} %`)} de réussite : restez sélectif, notamment sur ${liste}`,
    );
  }

  if (!recoParties.length && marches.length === 1) {
    const seul = marches[0];
    recoParties.push(
      `un seul type de marché a été jugé (${decrireMarche(seul, echantillonFaible)}) : base trop limitée pour une recommandation fiable`,
    );
  }

  let paragrapheRecommandation = recoParties.length
    ? `${recoParties[0].charAt(0).toUpperCase()}${recoParties[0].slice(1)}`
    : "Le bilan ne permet pas encore de distinguer clairement les marchés à privilégier ou à éviter.";

  if (recoParties.length > 1) {
    paragrapheRecommandation += ` ; ${recoParties[1]}`;
  }

  paragrapheRecommandation +=
    ". Ces indications s’appuient uniquement sur le bilan du weekend passé et ne préjugent pas des matchs à venir.";

  return { paragrapheBilan, paragrapheRecommandation };
}
