import { reactive } from "vue";

export const extraNavigation = reactive({
  championnat: "",
  equipe: "",
  saison: "",
});

export function definirExtraNavigation(valeurs) {
  extraNavigation.championnat = valeurs.championnat || "";
  extraNavigation.equipe = valeurs.equipe || "";
  extraNavigation.saison = valeurs.saison || "";
}

export function viderExtraNavigation() {
  extraNavigation.championnat = "";
  extraNavigation.equipe = "";
  extraNavigation.saison = "";
}

export function lireContexteRoute(route) {
  return {
    championnat:
      route.params.championnat ||
      route.query.championnat ||
      extraNavigation.championnat ||
      "",
    equipe: route.params.equipe || extraNavigation.equipe || "",
    saison: route.query.saison || extraNavigation.saison || "",
    joueur: route.params.joueur || "",
  };
}
