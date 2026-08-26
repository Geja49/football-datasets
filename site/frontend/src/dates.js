export const MOIS = [
  "janvier",
  "février",
  "mars",
  "avril",
  "mai",
  "juin",
  "juillet",
  "août",
  "septembre",
  "octobre",
  "novembre",
  "décembre",
];

export function aujourdhuiIso() {
  const maintenant = new Date();
  const mois = String(maintenant.getMonth() + 1).padStart(2, "0");
  const jour = String(maintenant.getDate()).padStart(2, "0");
  return `${maintenant.getFullYear()}-${mois}-${jour}`;
}

export function formaterDate(iso) {
  if (!iso || iso.length < 10) return iso || "";
  const jour = Number(iso.slice(8, 10));
  const mois = Number(iso.slice(5, 7));
  const annee = iso.slice(0, 4);
  if (!mois || mois < 1 || mois > 12) return iso;
  return `${jour} ${MOIS[mois - 1]} ${annee}`;
}

/** Instant UTC ISO → Date locale du navigateur. */
function instantLocal(commenceAt) {
  if (!commenceAt) return null;
  const instant = new Date(commenceAt);
  return Number.isNaN(instant.getTime()) ? null : instant;
}

/** Heure affichée dans le fuseau de l'ordinateur. */
export function formaterHeureLocale(match, options = {}) {
  const { joue = match && match.joue, videSiJoue = false } = options;
  if (joue && videSiJoue) return "";
  if (joue && !(match && match.heure) && !(match && match.commence_at)) {
    return "FT";
  }
  const instant = instantLocal(match && match.commence_at);
  if (instant) {
    return instant.toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
    });
  }
  if (match && match.heure) return match.heure;
  return joue ? "FT" : "—";
}

/** Date affichée (peut changer de jour selon le fuseau local). */
export function formaterDateLocale(match) {
  const instant = instantLocal(match && match.commence_at);
  if (instant) {
    const mois = String(instant.getMonth() + 1).padStart(2, "0");
    const jour = String(instant.getDate()).padStart(2, "0");
    return formaterDate(
      `${instant.getFullYear()}-${mois}-${jour}`
    );
  }
  return formaterDate(match && match.date);
}

/** Clé jour locale pour regrouper les matchs. */
export function cleJourLocale(match) {
  const instant = instantLocal(match && match.commence_at);
  if (instant) {
    const mois = String(instant.getMonth() + 1).padStart(2, "0");
    const jour = String(instant.getDate()).padStart(2, "0");
    return `${instant.getFullYear()}-${mois}-${jour}`;
  }
  return (match && match.date) || "";
}

export function titreMois(iso) {
  if (!iso || iso.length < 7) return "";
  const mois = Number(iso.slice(5, 7));
  const annee = iso.slice(0, 4);
  if (!mois || mois < 1 || mois > 12) return iso.slice(0, 7);
  const nom = MOIS[mois - 1];
  return `${nom.charAt(0).toUpperCase()}${nom.slice(1)} ${annee}`;
}

export function cleMois(iso) {
  return (iso || "").slice(0, 7);
}
