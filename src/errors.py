"""Exceptions métier."""


class PipelineError(Exception):
    """Erreur de base de la pipeline."""


class InvalidDataError(PipelineError):
    """Fichier / donnée ne respectant pas le format attendu (jamais retentée)."""


class TransientError(PipelineError):
    """Panne temporaire (réelle ou simulée) : l'opération peut être retentée."""
