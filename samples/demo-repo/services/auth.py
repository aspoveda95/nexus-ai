"""Ejemplo de módulo Python para pruebas de ingesta RAG."""


def verify_token(token: str) -> bool:
    """Validación trivial solo para demostración."""
    return bool(token) and token.startswith("nexus-")


class AuthService:
    """Servicio de autenticación de ejemplo."""

    def __init__(self, issuer: str) -> None:
        self._issuer: str = issuer

    def issuer(self) -> str:
        return self._issuer
