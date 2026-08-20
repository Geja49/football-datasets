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
