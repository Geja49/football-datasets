function mettreMajusculeDebutMot(mot) {
  if (!mot) return "";
  return mot.charAt(0).toLocaleUpperCase("fr") + mot.slice(1);
}

/** Affichage forum : première lettre de chaque mot (espaces / tirets). */
export function formaterPseudoAffichage(pseudo) {
  if (!pseudo) return "";
  return pseudo
    .trim()
    .split(/\s+/)
    .map((mot) => mot.split("-").map(mettreMajusculeDebutMot).join("-"))
    .join(" ");
}
