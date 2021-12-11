# -*- coding: utf-8 -*-
# Future Imports
from __future__ import annotations

# Music Imports
from .reporter import Reporter


def setup(bot):
    bot.add_cog(Reporter(bot))
