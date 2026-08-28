"""Modèles de réponse standard pour endpoints critiques."""

from __future__ import annotations

from pydantic import BaseModel


class ReponseOk(BaseModel):
    ok: bool = True


class ReponseErreur(BaseModel):
    detail: str


class ReponseSignalement(BaseModel):
    ok: bool = True
