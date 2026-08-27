/**
 * Insère un emoji (ou texte) dans un champ à la position du curseur.
 * @param {HTMLInputElement|HTMLTextAreaElement|null} element
 * @param {string} valeurActuelle
 * @param {string} emoji
 * @returns {{ valeur: string, position: number }}
 */
export function insererEmojiDansChamp(element, valeurActuelle, emoji) {
  const texte = valeurActuelle ?? "";
  if (!element || typeof element.selectionStart !== "number") {
    const valeur = texte + emoji;
    return { valeur, position: valeur.length };
  }
  const debut = element.selectionStart;
  const fin = element.selectionEnd ?? debut;
  const valeur = texte.slice(0, debut) + emoji + texte.slice(fin);
  return { valeur, position: debut + emoji.length };
}
