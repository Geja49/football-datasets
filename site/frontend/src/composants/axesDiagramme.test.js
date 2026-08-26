import { describe, expect, it } from "vitest";
import {
  axesComparaisonLigue,
  axesDepuisJoueur,
  histogrammeLocal,
  medianeListe,
  nombre,
  percentileDepuisScore,
  scoreMedianHistogramme,
  scoreRelatif,
  texteEcart,
  textePosition,
} from "./axesDiagramme.js";

describe("nombre", () => {
  it("convertit une valeur numérique", () => {
    expect(nombre("3.5")).toBe(3.5);
    expect(nombre(2)).toBe(2);
  });

  it("renvoie 0 pour une valeur invalide", () => {
    expect(nombre(null)).toBe(0);
    expect(nombre("abc")).toBe(0);
    expect(nombre(undefined)).toBe(0);
  });
});

describe("scoreRelatif", () => {
  it("borne le score entre 0 et 1", () => {
    expect(scoreRelatif(5, 10)).toBe(0.5);
    expect(scoreRelatif(20, 10)).toBe(1);
    expect(scoreRelatif(-1, 10)).toBe(0);
    expect(scoreRelatif(5, 0)).toBe(0);
  });
});

describe("histogrammeLocal", () => {
  it("répartit les valeurs dans des classes", () => {
    const histo = histogrammeLocal([0, 5, 9], 10, 5);
    expect(histo).toHaveLength(5);
    expect(histo.reduce((s, c) => s + c.n, 0)).toBe(3);
  });

  it("gère un plafond invalide", () => {
    expect(histogrammeLocal([1, 2], 0, 4)).toEqual([
      { n: 0 },
      { n: 0 },
      { n: 0 },
      { n: 0 },
    ]);
  });
});

describe("lecture densités", () => {
  const histo = [
    { n: 4 },
    { n: 6 },
    { n: 8 },
    { n: 2 },
  ];

  it("calcule une médiane dans la masse", () => {
    expect(scoreMedianHistogramme(histo)).toBeCloseTo(0.375, 3);
  });

  it("estime un percentile élevé pour un score fort", () => {
    expect(percentileDepuisScore(0.9, histo)).toBeGreaterThanOrEqual(80);
  });

  it("formule Top % ou rang lisible", () => {
    expect(textePosition(0.95, histo)).toMatch(/^Top \d+ %$/);
    expect(textePosition(0.4, histo)).toMatch(/^\d+e \/ \d+$/);
  });
});

describe("comparaison ligue", () => {
  it("calcule une médiane de liste", () => {
    expect(medianeListe([1, 2, 3])).toBe(2);
    expect(medianeListe([1, 2, 3, 4])).toBe(2.5);
  });

  it("formule un écart lisible", () => {
    expect(texteEcart(1.8, 1.4, { cle: "buts" })).toMatch(/\+0\.4 vs moyenne/);
    expect(texteEcart(1.8, 1.4, { cle: "buts" })).toMatch(/au-dessus/);
    expect(texteEcart(0.8, 1.4, { cle: "defense", inverser: true })).toMatch(/au-dessus/);
  });

  it("expose un polygone de comparaison quand scoreLigue est présent", () => {
    const axes = axesDepuisJoueur(
      { buts: 10, xg: 8, passes_decisives: 4, xa: 3, tirs: 40, minutes: 2000 },
      {
        axes: [
          { cle: "buts", plafond: 20, moyenne: 5, histogramme: histogrammeLocal([2, 5, 10], 20) },
          { cle: "xg", plafond: 15, moyenne: 4, histogramme: histogrammeLocal([2, 4, 8], 15) },
          {
            cle: "passes_decisives",
            plafond: 10,
            moyenne: 2,
            histogramme: histogrammeLocal([1, 2, 5], 10),
          },
          { cle: "xa", plafond: 8, moyenne: 1.5, histogramme: histogrammeLocal([1, 1.5, 3], 8) },
          { cle: "tirs", plafond: 80, moyenne: 20, histogramme: histogrammeLocal([10, 20, 40], 80) },
          {
            cle: "minutes",
            plafond: 3000,
            moyenne: 1500,
            histogramme: histogrammeLocal([900, 1500, 2700], 3000),
          },
        ],
      },
    );
    expect(axes[0].valeurLigue).toBe(5);
    expect(axes[0].scoreLigue).toBeCloseTo(0.25, 2);
    expect(axesComparaisonLigue(axes)).toHaveLength(6);
  });
});
