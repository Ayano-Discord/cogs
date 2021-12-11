# Future Imports
from __future__ import annotations

# Dependency Imports
from redbot import VersionInfo

# Music Imports
from .hash import version

COMMIT = version

version_info = VersionInfo.from_json(
    {"major": 4, "minor": 1, "micro": 0, "releaselevel": "final", "serial": 2}
)


__version__ = f"{version_info}-{COMMIT}"
