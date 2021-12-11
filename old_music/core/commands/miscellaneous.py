# Future Imports
from __future__ import annotations

# Standard Library Imports
from abc import ABC
import logging

# Music Imports
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Music.cog.Commands.miscellaneous")


class MiscellaneousCommands(MixinMeta, ABC, metaclass=CompositeMetaClass):
    pass
