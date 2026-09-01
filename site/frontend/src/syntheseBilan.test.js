import { describe, expect, it } from "vitest";
import {
  accentuer,
  construireSyntheseBilan,
  echapperHtml,
  joindreLibelles,
} from "./syntheseBilan.js";

describe("echapperHtml", () => {
  it("échappe les caractères HTML", () => {
    expect(echapperHtml("<script>")).toBe("&lt;script&gt;");
    expect(echapperHtml("A & B")).toBe("A &amp; B");
  });
});

describe("accentuer", () => {
  it("entoure le texte d’un strong avec la classe dédiée", () => {
    expect(accentuer("70 %")).toBe(
      '<strong class="synthese-accent">70 %</strong>',
    );
  });
});

describe("joindreLibelles", () => {
  it("formate une liste en français avec accentuation", () => {
    expect(joindreLibelles(["A"])).toBe(
      '« <strong class="synthese-accent">A</strong> »',
    );
    expect(joindreLibelles(["A", "B"])).toBe(
      '« <strong class="synthese-accent">A</strong> » et « <strong class="synthese-accent">B</strong> »',
    );
    expect(joindreLibelles(["A", "B", "C"])).toBe(
      '« <strong class="synthese-accent">A</strong> », « <strong class="synthese-accent">B</strong> » et « <strong class="synthese-accent">C</strong> »',
    );
  });
});

describe("construireSyntheseBilan", () => {
  const weekend = {
    libelle: "28–31 août 2026",
    date_debut: "2026-08-28",
    date_fin: "2026-08-31",
  };

  it("gère l’absence de verdicts", () => {
    const synthese = construireSyntheseBilan({
      weekend,
      seuil_probabilite: 70,
      nb_pronos: 5,
      nb_juges: 0,
      nb_vrais: 0,
      nb_faux: 0,
      hit_rate: null,
      par_marche: {},
      par_championnat: {},
      details: [],
    });
    expect(synthese.paragrapheBilan).toContain("aucun n’a encore été jugé");
    expect(synthese.paragrapheBilan).toContain(
      '<strong class="synthese-accent">28–31 août 2026</strong>',
    );
    expect(synthese.paragrapheBilan).toContain(
      '<strong class="synthese-accent">5 marchés figés</strong>',
    );
    expect(synthese.paragrapheRecommandation).toContain(
      "aucune recommandation",
    );
  });

  it("résume le bilan et recommande selon les hit-rates", () => {
    const synthese = construireSyntheseBilan({
      weekend,
      seuil_probabilite: 70,
      nb_pronos: 20,
      nb_juges: 15,
      nb_vrais: 11,
      nb_faux: 4,
      hit_rate: 73.3,
      par_marche: {
        victoire_1: { vrais: 8, total: 10, hit_rate: 80 },
        over_25: { vrais: 2, total: 5, hit_rate: 40 },
        btts: { vrais: 1, total: 1, hit_rate: 100 },
        cartons_15: { vrais: 0, total: 5, hit_rate: 0 },
      },
      par_championnat: {
        "La Liga": { vrais: 6, total: 8, hit_rate: 75 },
        "Ligue 1": { vrais: 2, total: 7, hit_rate: 28.6 },
      },
      details: [],
    });

    expect(synthese.paragrapheBilan).toContain(
      '<strong class="synthese-accent">73,3 %</strong>',
    );
    expect(synthese.paragrapheBilan).toContain(
      '<strong class="synthese-accent">11 corrects sur 15 jugés</strong>',
    );
    expect(synthese.paragrapheBilan).toContain(
      '<strong class="synthese-accent">20 marchés figés au total</strong>',
    );
    expect(synthese.paragrapheBilan).toContain("Victoire domicile");
    expect(synthese.paragrapheBilan).not.toContain("cartons");
    expect(synthese.paragrapheRecommandation).toContain("Victoire domicile");
    expect(synthese.paragrapheRecommandation).toContain("+2,5 buts");
    expect(synthese.paragrapheRecommandation).toContain(
      '<strong class="synthese-accent-prudence">misez avec prudence</strong>',
    );
    expect(synthese.paragrapheRecommandation).toContain("échantillon très faible");
    expect(synthese.paragrapheRecommandation).toContain(
      "ne préjugent pas des matchs à venir",
    );
  });

  it("nuance quand un seul marché est jugé", () => {
    const synthese = construireSyntheseBilan({
      weekend,
      seuil_probabilite: 70,
      nb_pronos: 1,
      nb_juges: 1,
      nb_vrais: 1,
      nb_faux: 0,
      hit_rate: 100,
      par_marche: {
        btts: { vrais: 1, total: 1, hit_rate: 100 },
      },
      par_championnat: {},
      details: [],
    });
    expect(synthese.paragrapheRecommandation).toContain("échantillon très faible");
    expect(synthese.paragrapheBilan).toContain(
      '<strong class="synthese-accent">100 %</strong>',
    );
  });
});
