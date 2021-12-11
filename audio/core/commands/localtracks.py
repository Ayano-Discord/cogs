# Future Imports
from __future__ import annotations

# Standard Library Imports
from pathlib import Path
from typing import MutableMapping
import contextlib
import logging
import math

# Dependency Imports
from redbot.core import commands
from redbot.core.i18n import Translator
from redbot.core.utils._dpy_menus_utils import dpymenu
from redbot.core.utils.menus import close_menu, menu, next_page, prev_page
import discord

# Music Imports
from ...audio_dataclasses import LocalPath, Query
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Audio.cog.Commands.local_track")
_ = Translator("Audio", Path(__file__))


class LocalTrackCommands(MixinMeta, metaclass=CompositeMetaClass):
    pass
