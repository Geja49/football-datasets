import { describe, expect, it } from "vitest";

const routesAttendues = [
  "/",
  "/match",
  "/mes-pronos",
  "/nos-pronos",
  "/classement-pronos",
  "/pronos-journee",
  "/ligues",
  "/ligue/:code",
  "/notifications",
  "/mon-profil",
  "/moderation",
  "/forum",
  "/forum/sujet/:id",
  "/forum/:championnat",
  "/connexion",
  "/conditions",
  "/glossaire",
  "/:pathMatch(.*)*",
];

describe("routeur — lazy loading Phase 4", () => {
  it("déclare les routes principales et le catch-all 404", async () => {
    const source = await import("node:fs/promises").then((fs) =>
      fs.readFile(new URL("./routeur.js", import.meta.url), "utf8"),
    );
    for (const chemin of routesAttendues) {
      expect(source).toContain(`"${chemin}"`);
    }
    expect(source).toContain("() => import(");
    expect(source).toContain("PageIntrouvable.vue");
  });
});
