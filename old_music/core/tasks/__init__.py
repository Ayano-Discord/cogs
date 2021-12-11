# Future Imports
from __future__ import annotations

# Standard Library Imports
from abc import ABC
import logging

# Music Imports
from ..cog_utils import CompositeMetaClass
from .lavalink import LavalinkTasks
from .player import PlayerTasks
from .startup import StartUpTasks

log = logging.getLogger("red.cogs.Music.cog.Tasks")


class Tasks(
    LavalinkTasks, PlayerTasks, StartUpTasks, ABC, metaclass=CompositeMetaClass
):
    """Class joining all task subclasses"""
