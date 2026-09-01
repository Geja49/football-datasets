import { describe, expect, it } from "vitest";
import {
  estMarcheCarton,
  indiceTriMarche,
  libelleTypeMarche,
  palierHitRate,
} from "./libellesMarches.js";

describe("libelleTypeMarche", () => {
  it("traduit les clés BD", () => {
    expect(libelleTypeMarche("victoire_1")).toBe("Victoire domicile");
    expect(libelleTypeMarche("over_15")).toBe("+1,5 buts");
    expect(libelleTypeMarche("corners_over_95")).toBe("Corners +9,5");
  });

  it("préfère le libellé API s’il est fourni", () => {
    expect(libelleTypeMarche("victoire_1", "Victoire Barcelona")).toBe(
      "Victoire Barcelona",
    );
  });
});

describe("estMarcheCarton", () => {
  it("détecte les types cartons", () => {
    expect(estMarcheCarton("cartons_15")).toBe(true);
    expect(estMarcheCarton("victoire_1")).toBe(false);
  });
});

describe("palierHitRate", () => {
  it("classe selon le seuil", () => {
    expect(palierHitRate(80)).toBe("haute");
    expect(palierHitRate(70)).toBe("haute");
    expect(palierHitRate(55)).toBe("moyenne");
    expect(palierHitRate(40)).toBe("basse");
    expect(palierHitRate(null)).toBe("neutre");
  });
});

describe("indiceTriMarche", () => {
  it("place victoire avant over", () => {
    expect(indiceTriMarche("victoire_1")).toBeLessThan(indiceTriMarche("over_25"));
  });
});
