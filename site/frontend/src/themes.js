export function nomTheme(route) {
  return route.params.championnat || route.query.championnat || "accueil";
}

export function appliquerTheme(nom) {
  document.documentElement.dataset.theme = nom || "accueil";
}
