from redbot.core import commands
from redbot.core.bot import Red


class HibikiRPC:
    """RPC server handlers for the hibiki's api to get special things from the bot.

    This class contains the basic RPC functions, that don't belong to any other cog"""

    def __init__(self, cog: commands.Cog):
        self.cog: commands.Cog = cog
        self.bot: Red = cog.bot

        # Initialize RPC handlers
        self.bot.register_rpc_handler(self.bot_stats)
        self.bot.register_rpc_handler(self.user_profile_rpg)
        self.bot.register_rpc_handler(self.get_auth_token)

    
    async def bot_stats(self):
        """
        Returns the bot's stats.

        This function is called by the RPC server to get the bot's stats.
        """
        uptime = 