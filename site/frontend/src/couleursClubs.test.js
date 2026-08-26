import { describe, expect, it } from "vitest";
import {
  couleursPourClub,
  estPageEquipe,
  paletteClub,
  resoudrePaletteClub,
  variablesCssClub,
} from "./couleursClubs.js";

describe("couleursPourClub", () => {
  it("trouve Barcelona", () => {
    const palette = couleursPourClub("Barcelona");
    expect(palette).not.toBeNull();
    expect(palette.accent).toBe("#A50044");
  });

  it("trouve Paris Saint Germain et l’alias PSG", () => {
    const direct = couleursPourClub("Paris Saint Germain");
    const alias = couleursPourClub("PSG");
    expect(direct).not.toBeNull();
    expect(alias?.accent).toBe(direct?.accent);
  });

  it("trouve Manchester City", () => {
    const palette = couleursPourClub("Manchester City");
    expect(palette).not.toBeNull();
    expect(palette.accent).toBe("#6CABDD");
  });

  it("renvoie null pour un club inconnu", () => {
    expect(couleursPourClub("Club Inexistant FC")).toBeNull();
  });
});

describe("paletteClub", () => {
  it("garde un fond sombre dans le dégradé hero", () => {
    const palette = paletteClub("#C8102E", "#00B2A9");
    expect(palette.hero).toMatch(/linear-gradient/);
    expect(palette.bandeau.toLowerCase()).not.toBe("#c8102e");
  });
});

describe("estPageEquipe", () => {
  it("détecte la fiche club", () => {
    expect(
      estPageEquipe({
        path: "/championnat/La%20Liga/equipe/Barcelona",
        params: { equipe: "Barcelona" },
      }),
    ).toBe(true);
  });

  it("ignore la page analyser", () => {
    expect(
      estPageEquipe({
        path: "/championnat/La%20Liga/equipe/Barcelona/analyser",
        params: { equipe: "Barcelona" },
      }),
    ).toBe(false);
  });
});

describe("resoudrePaletteClub", () => {
  it("trouve via alias API", () => {
    const palette = resoudrePaletteClub("Club Inconnu", "PSG");
    expect(palette?.accent).toBe(couleursPourClub("Paris Saint Germain")?.accent);
  });
});

describe("variablesCssClub", () => {
  it("expose les variables attendues", () => {
    const vars = variablesCssClub(couleursPourClub("Liverpool"));
    expect(vars).toMatchObject({
      "--accent": "#C8102E",
      "--hero": expect.stringMatching(/linear-gradient/),
    });
  });
});
