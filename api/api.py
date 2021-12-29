from redbot.core import commands, Config
from redbot.core.bot import Red


class HibikiAPI(commands.Cog):

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        self.config = Config.get_conf(self, identifier=473541068378341376)
        self.config.register_global(
            auth_tokens=[]
        )

    def initialize(self):

