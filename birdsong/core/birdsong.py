from __future__ import annotations

import discord
import logging
import typing

from birdsong.core import builtins
from birdsong.core import custom
from birdsong.core import database
from birdsong.core import files
from birdsong.core import utils

if typing.TYPE_CHECKING:
    from birdsong.core import birdsong


class Birdsong(discord.Client):
    """
    An enhanced Discord client that holds handles to various extra managers
    such as AssetManager and DataManager.
    """

    # BIRDSONG MEMBERS

    def __init__(self, base: dict = {}, birdsong: dict = {}) -> None:
        """
        Configures birdsong.
        """
        # Superclass initialization.
        intents = discord.Intents.all()
        super().__init__(
            intents=intents,
            **utils.prepare_kwargs(super(Birdsong, self).__init__, base),
        )

        # Birdsong initialization.
        utils.call_prepared(self.configure, kwargs=birdsong)

    def configure(
        self,
        *,
        client_token: str,
        prefix: str,
        admin: dict,
        database: dict,
        paths: dict,
    ):
        """
        Passes along each configuration bundle to its subhandler.
        """
        self.prefix: str = prefix
        self.logger: logging.Logger = discord.client._log
        self.client_token: str = client_token

        utils.call_prepared(self.configure_admin, kwargs=admin)
        utils.call_prepared(self.configure_database, kwargs=database)
        utils.call_prepared(self.configure_managers, kwargs=paths)

    def configure_admin(
        self,
        *,
        admins: list[int] = [],
        owner: int = 0,
    ):
        """
        Configures the bot's most basic attributes.
        """
        self.admins: list[int] = admins
        self.owner: int = owner

    def configure_database(
        self, *, hostname: str = "", username: str = "", password: str = ""
    ):
        """
        Configures options for the database and creates a handle.
        """
        self.dbmanager: database.DataManager = database.DataManager(
            self, hostname, username, password
        )

    def configure_managers(
        self, *, asset_path: str = "", commands_path: str = "", store_path: str = ""
    ):
        """
        Configures managers for various types of program flows.
        """
        self.assetmanager: files.AssetManager = files.AssetManager(
            self, asset_path, store_path
        )
        self.builtins: builtins.Builtins = builtins.Builtins(self)
        self.ccmanager: custom.CCManager = custom.CCManager(self, commands_path)

    def tweet_tweet(self) -> typing.NoReturn:
        """
        Runs the discord client loop.
        """
        self.run(self.client_token)

    # RELEVANT DISCORD EVENTS

    async def on_message(self, message: discord.Message):
        """
        Handles an incoming message by listing each custom command that satisfies
        the current context and executing them.
        """
        await self.ccmanager.execute_all(context=message)
