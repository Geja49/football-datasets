/** Utilitaires avatars prédéfinis (fichiers statiques /avatars/*). */

const EXTENSION_PAR_DEFAUT = "svg";

/** Identifiants dont le fichier est en PNG (pack légendes découpé). */
const AVATARS_PNG = new Set([
  ...Array.from({ length: 18 }, (_, i) => `avatar-legende-${String(i + 1).padStart(2, "0")}`),
  ...Array.from({ length: 50 }, (_, i) => `avatar-legende-b-${String(i + 1).padStart(2, "0")}`),
]);

const COULEURS_INITIALES = [
  "#0f766e",
  "#1d4ed8",
  "#b91c1c",
  "#b45309",
  "#7c3aed",
  "#be185d",
  "#0369a1",
  "#15803d",
];

export function extensionAvatar(avatarId) {
  if (!avatarId) return EXTENSION_PAR_DEFAUT;
  return AVATARS_PNG.has(avatarId) ? "png" : EXTENSION_PAR_DEFAUT;
}

export function urlAvatar(avatarId) {
  if (!avatarId) return "";
  const ext = extensionAvatar(avatarId);
  return `/avatars/${encodeURIComponent(avatarId)}.${ext}`;
}

export function initialesDepuisPseudo(pseudo) {
  const texte = (pseudo || "").trim();
  if (!texte) return "?";
  const parties = texte.split(/[\s._-]+/).filter(Boolean);
  if (parties.length >= 2) {
    return (parties[0][0] + parties[1][0]).toUpperCase();
  }
  return texte.slice(0, 2).toUpperCase();
}

export function couleurInitiales(pseudo) {
  let somme = 0;
  const texte = (pseudo || "user").toLowerCase();
  for (let i = 0; i < texte.length; i += 1) {
    somme += texte.charCodeAt(i);
  }
  return COULEURS_INITIALES[somme % COULEURS_INITIALES.length];
}
