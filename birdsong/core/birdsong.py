from __future__ import annotations

import discord
import importlib.util
import logging
import pathlib
import typing

from birdsong.core import builtins
from birdsong.core import custom
from birdsong.core import database
from birdsong.core import files
from birdsong.core import utils

if typing.TYPE_CHECKING:
    from birdsong.core import birdsong


class ModuleCollection(object):
    """
    Empty class on which birdsong sets modules as attributes.
    """

    pass


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
        default_roles: list[str],
        prefix: str,
        admin: dict,
        database: dict,
        logs: dict,
        paths: dict,
    ):
        """
        Passes along each configuration bundle to its subhandler.
        """
        self.client_token: str = client_token
        self.default_roles: list[str] = default_roles
        self.prefix: str = prefix

        utils.call_prepared(self.configure_logging, kwargs=logs)
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

    def configure_logging(self, *, level: int = 2):
        """
        Sets up birdsong's logger.
        """
        severity = {
            0: logging.ERROR,
            1: logging.WARN,
            2: logging.INFO,
            3: logging.DEBUG,
        }.get(level, logging.INFO)

        self.logger = logging.getLogger("birdsong")
        self.logger.setLevel(severity)

        self.handler = logging.StreamHandler()
        self.handler.setLevel(severity)
        self.logger.addHandler(self.handler)

        if utils.stream_supports_colour(self.handler.stream):
            self.formatter = utils.StreamFormatter()
        else:
            dt_fmt = "%Y-%m-%d %H:%M:%S"
            self.formatter = logging.Formatter(
                "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
            )
        self.handler.setFormatter(self.formatter)

    def configure_managers(
        self,
        *,
        asset_path: str = "",
        commands_path: str = "",
        modules_path: str = "",
        store_path: str = "",
    ):
        """
        Configures managers for various types of program flows.
        """
        self.assetmanager: files.AssetManager = files.AssetManager(
            self, asset_path, store_path
        )
        self.builtins: builtins.Builtins = builtins.Builtins(self)
        self.ccmanager: custom.CCManager = custom.CCManager(self, commands_path)
        self.configure_modules(modules_path=modules_path)

    def configure_modules(self, *, modules_path: str = ""):
        """
        Configures the modules path.
        """
        self.modules_path = modules_path
        self.modules = ModuleCollection()
        self.load_modules()

    def load_modules(self):
        """
        Loads "global" modules into the birdsong namespace, which can then be referenced by commands.
        """
        for module_file in pathlib.Path(self.modules_path).glob("*.py"):
            module_name = pathlib.Path(module_file).stem
            import_spec = importlib.util.spec_from_file_location(
                module_name, module_file
            )
            module = importlib.util.module_from_spec(import_spec)
            import_spec.loader.exec_module(module)
            setattr(self.modules, module_name, module)

        self.logger.info("loaded modules: {}".format(dir(self.modules)))

    def tweet_tweet(self) -> typing.NoReturn:
        """
        Runs the discord client loop.
        """
        self.run(self.client_token, log_handler=None)

    # RELEVANT DISCORD EVENTS

    async def on_message(self, message: discord.Message):
        """
        Handles an incoming message by listing each custom command that satisfies
        the current context and executing them.
        """
        if message.author.bot:
            return

        self.logger.debug(
            "from={}#{}, content={}".format(
                message.author.name, message.author.discriminator, message.content
            )
        )

        await self.ccmanager.execute_all(context=message)

    async def on_member_join(self, member: discord.Member):
        """
        Adds the default roles to a member when they join.
        """
        guild = member.guild
        matched = [role for role in guild.roles if role.name in self.default_roles]
        await member.add_roles(*matched)
