"""Service métier — forum (wrapper en migration)."""

from __future__ import annotations

from forum import assurer_tables_forum, routeur_forum

__all__ = ["assurer_tables_forum", "routeur_forum"]
