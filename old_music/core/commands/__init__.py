# Future Imports
from __future__ import annotations

# Standard Library Imports
from abc import ABC

# Music Imports
from ..cog_utils import CompositeMetaClass
from .audioset import AudioSetCommands
from .controller import PlayerControllerCommands
from .equalizer import EqualizerCommands
from .filters import EffectsCommands
from .localtracks import LocalTrackCommands
from .lyrics import LyricsCommands
from .miscellaneous import MiscellaneousCommands
from .player import PlayerCommands
from .playlists import PlaylistCommands
from .queue import QueueCommands


class Commands(
    AudioSetCommands,
    PlayerControllerCommands,
    EqualizerCommands,
    EffectsCommands,
    LocalTrackCommands,
    LyricsCommands,
    MiscellaneousCommands,
    PlayerCommands,
    PlaylistCommands,
    QueueCommands,
    ABC,
    metaclass=CompositeMetaClass,
):
    """Class joining all command subclasses"""
