# Future Imports
from __future__ import annotations

# Standard Library Imports
from operator import attrgetter
from typing import Any, AnyStr, Union
import inspect
import os

# Dependency Imports
import discord
import rich

# Music Imports
from .classes import CustomEmojis

VALID_JSON_TYPES = Union[str, int, bool, list, dict, None]

__all__ = (
    "button_from_json",
    "get_p",
    "get_custom_emoji",
    "read_file",
)


def button_from_json(
    json_obj: dict, *, cls: Any = discord.ui.Button
) -> discord.Button:
    """A function that returns a button from a JSON dictionary
    Parameters
    ----------
    json_obj : dict
        the json dictionary representing the button
    cls: Object
        The class to use for the button
    Returns
    -------
    discord.Button
        The button that was converted from the JSON
    """
    button = cls(
        label=json_obj.get("label", ""),
        style=json_obj.get("style", ""),
        disabled=json_obj.get("disabled", False),
        row=json_obj.get("row", 0),
    )
    if json_obj.get("emoji"):
        button.emoji = json_obj["emoji"]
    return button


def read_file(filepath: str, *args, **kwargs) -> AnyStr:
    """Reads a file and returns the content
    Parameters
    ----------
    filepath : str
        The path to the file to read
    Returns
    -------
    AnyStr
        the content of the file
    """
    with open(filepath, *args, **kwargs) as f:
        return f.read()


def get_custom_emoji(emoji: str) -> str:
    """Returns the custom emoji from the config if it exists
    Parameters
    ----------
    emoji : str
        the emoji to get
    Returns
    -------
    str
        The emoji that it got
    """
    emoji_config = CustomEmojis.from_json(
        read_file("/home/ubuntu/mine/aki/emojis.json")
    )
    return attrgetter(emoji)(emoji_config)


def get_p(
    progress: int,
    *,
    total=100,
    prefix="",
    suffix="",
    decimals=0,
    length=100,
    fill="█",
):
    """Use this to make a progress bar for
    Parameters
    ----------
    progress : int
        the current progress
    total : int, optional
        the total progress, by default 100
    prefix : str, optional
        the prefix to add in front of the progressbar, by default ""
    suffix : str, optional
        the suffix to add in front of the progressbar, by default ""
    decimals : int, optional
        the number of decimal places to display in the progressbar, by default 0
    length : int, optional
        the length of the progressbar, by default 100
    fill : str, optional
        the fill to add use the progressbar, by default "█"
    Returns
    -------
    str
        the progressbar
    """
    if progress is None:
        progress = 0
    else:
        progress = progress
    percent = ("{0:." + str(decimals) + "f}").format(100 * (progress / total))
    filled_length = int(length * progress // total)
    bar = fill * filled_length + "-" * (length - filled_length)
    return f"{prefix} |{bar}| {percent}% {suffix}"
