from .api import HibikiAPI


def setup(bot):
    cog = HibikiAPI(bot)
    bot.add_cog(cog)