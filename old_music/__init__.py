# Future Imports
from __future__ import annotations

# Standard Library Imports
from pathlib import Path
import getpass
import platform
import sys

# Dependency Imports
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
from redbot.core.utils import get_end_user_data_statement

# Music Imports
from .utils import copy_audio_db

# Dirty hack to made the cog always the downloaded lib and not the one that comes with Red.
if (
    getpass.getuser() == "Draper" and platform.system() == "Windows"
):  # Deving enviroment is annoying and I wanna have to avoid pushing untested changes upstream so i can validate audio
    _LIB = Path(r"C:\Users\Draper\PycharmProjects\Red-Lavalink")
else:
    _LIB = cog_data_path(None, raw_name="Downloader") / "lib"
sys.path.insert(0, str(_LIB))
# My Modded Imports
import lavalink  # noqa: F401 E402

_to_remove = [
    name
    for name in sys.modules
    if name == "lavalink" or name.startswith("lavalink.")
]
for _name in _to_remove:
    sys.modules.pop(_name, None)
# My Modded Imports
import lavalink  # noqa: F401 E402 F811

sys.path.pop(0)


# Music Imports
from .core import Music  # noqa: E402

__red_end_user_data_statement__ = get_end_user_data_statement(__file__)


async def setup(bot: Red):
    async with bot._config.packages() as curr_pkgs:
        if "audio" not in curr_pkgs[:1]:
            while "audio" in curr_pkgs:
                curr_pkgs.remove("audio")
            curr_pkgs.insert(0, "audio")
    copy_audio_db()
    cog = Music(bot)
    bot.add_cog(cog)
    cog.start_up_task()
