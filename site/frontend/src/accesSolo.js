/**
 * Accès aux pages Solo (pronos weekend) et futures analyses liées.
 * Admin OU super utilisateur — pas un utilisateur simple.
 *
 * @param {{ est_admin?: boolean, super_utilisateur?: boolean } | null | undefined} utilisateur
 * @returns {boolean}
 */
export function aAccesSolo(utilisateur) {
  if (!utilisateur) return false;
  return Boolean(utilisateur.est_admin || utilisateur.super_utilisateur);
}
