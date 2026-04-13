#!/usr/bin/env python3
"""Django entrypoint for Nexus-AI api-core."""

import os
import sys
from typing import List


def main(argv: List[str] | None = None) -> None:
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nexus_api.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover - bootstrap guard
        raise ImportError(
            "No se pudo importar Django. ¿Está instalado y activo el virtualenv?"
        ) from exc
    execute_from_command_line(argv or sys.argv)


if __name__ == "__main__":
    main()
