"""Tests de validation Pydantic — entrées communauté rejetées si invalides."""

import pytest
from pydantic import ValidationError

from schemas.communaute import (
    CommentaireBody,
    InscriptionBody,
    PronosticBody,
    ReactionBody,
)


def test_inscription_rejette_champs_supplementaires():
    with pytest.raises(ValidationError) as erreur:
        InscriptionBody.model_validate(
            {
                "email": "test@exemple.fr",
                "pseudo": "Joueur1",
                "mot_de_passe": "motdepasse1",
                "age_18_plus": True,
                "cgu_acceptees": True,
                "admin": True,
            }
        )
    assert "admin" in str(erreur.value)


def test_inscription_rejette_email_invalide():
    with pytest.raises(ValidationError):
        InscriptionBody.model_validate(
            {
                "email": "pas-un-email",
                "pseudo": "Joueur1",
                "mot_de_passe": "motdepasse1",
            }
        )


def test_inscription_rejette_pseudo_trop_long():
    with pytest.raises(ValidationError):
        InscriptionBody.model_validate(
            {
                "email": "test@exemple.fr",
                "pseudo": "A" * 31,
                "mot_de_passe": "motdepasse1",
            }
        )


def test_commentaire_rejette_contenu_vide_apres_strip():
    with pytest.raises(ValidationError):
        CommentaireBody.model_validate(
            {
                "championnat": "Ligue 1",
                "saison": "2025-2026",
                "domicile": "PSG",
                "exterieur": "OM",
                "contenu": "   ",
            }
        )


def test_commentaire_accepte_chaine_xss_stockee_telle_quelle():
    """La validation ne filtre pas le HTML — stockage sûr via échappement front."""
    payload = CommentaireBody.model_validate(
        {
            "championnat": "Ligue 1",
            "saison": "2025-2026",
            "domicile": "PSG",
            "exterieur": "OM",
            "contenu": '<script>alert("xss")</script>',
        }
    )
    assert "<script>" in payload.contenu


def test_pronostic_score_exige_buts():
    with pytest.raises(ValidationError):
        PronosticBody.model_validate(
            {
                "championnat": "Ligue 1",
                "saison": "2025-2026",
                "domicile": "PSG",
                "exterieur": "OM",
                "type_pronostic": "score",
            }
        )


def test_pronostic_1x2_interdit_buts():
    with pytest.raises(ValidationError):
        PronosticBody.model_validate(
            {
                "championnat": "Ligue 1",
                "saison": "2025-2026",
                "domicile": "PSG",
                "exterieur": "OM",
                "type_pronostic": "1x2",
                "resultat_1x2": "1",
                "buts_domicile": 2,
            }
        )


def test_pronostic_equipes_identiques_refusees():
    with pytest.raises(ValidationError):
        PronosticBody.model_validate(
            {
                "championnat": "Ligue 1",
                "saison": "2025-2026",
                "domicile": "PSG",
                "exterieur": "PSG",
                "type_pronostic": "1x2",
                "resultat_1x2": "1",
            }
        )


def test_reaction_type_invalide_refuse():
    with pytest.raises(ValidationError):
        ReactionBody.model_validate({"type_reaction": "bombe"})


def test_pronostic_score_valide():
    prono = PronosticBody.model_validate(
        {
            "championnat": "Ligue 1",
            "saison": "2025-2026",
            "domicile": "PSG",
            "exterieur": "OM",
            "type_pronostic": "score",
            "buts_domicile": 2,
            "buts_exterieur": 1,
        }
    )
    assert prono.buts_domicile == 2
