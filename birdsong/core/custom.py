from __future__ import annotations

import discord
import enum
import importlib.util
import pathlib
import re
import typing
import yaml

from birdsong.core import utils

if typing.TYPE_CHECKING:
    from birdsong.core import birdsong


CCActionsType = typing.Callable[
    [any, discord.Message, str, list[str]], typing.Awaitable[any]
]


class CCTriggerType(enum.Enum):
    """
    A trigger type for a custom command.
    """

    CCTriggerNone = 0  # Default.
    CCTriggerCommand = 1  # Commands.
    CCTriggerContains = 2  # Substring matching.
    CCTriggerExact = 3
    CCTriggerRegex = 4  # Regular expressions.

    @classmethod
    def from_string(cls, cmdtype: str) -> CCTriggerType:
        match cmdtype:
            case "command":
                return CCTriggerType.CCTriggerCommand
            case "contains":
                return CCTriggerType.CCTriggerContains
            case "exact":
                return CCTriggerType.CCTriggerExact
            case "regex":
                return CCTriggerType.CCTriggerRegex
            case _:
                return CCTriggerType.CCTriggerNone


class CustomCommand:
    """
    A model that represents a custom command.
    """

    def __init__(
        self,
        *,
        path: pathlib.Path,
        trigger: str,
        cmdtype: CCTriggerType,
        actions: CCActionsType,
        require: dict[str, list[str]],
    ) -> None:
        """
        Creates an empty custom command.
        """
        self.path: pathlib.Path = path
        self.actions: CCActionsType = actions
        self.cmdtype: CCTriggerType = cmdtype
        self.require: dict[str, set[str]] = {k: set(v) for k, v in require.items()}
        self.trigger: str = trigger

    def check_trigger(self, cmd: str) -> bool:
        """
        Determines whether the given command fragment satisfies the trigger.
        """
        match self.cmdtype:
            case CCTriggerType.CCTriggerCommand:
                return self.trigger == cmd.lower()
            case CCTriggerType.CCTriggerContains:
                return re.search(self.trigger.lower(), cmd.lower())
            case CCTriggerType.CCTriggerExact:
                return re.match(self.trigger, cmd)
            case CCTriggerType.CCTriggerRegex:
                return re.search(self.trigger, cmd)

    def check_requirements(self, requirements: dict[str, str | set[str]]) -> bool:
        """
        Determines whether the function's requirements are satisfied.
        """
        in_channel = self.require_channel(requirements.get("channel", ""))
        in_category = self.require_category(requirements.get("category", ""))
        has_a_role = self.require_a_role(requirements.get("roles", set()))

        return all([in_channel, in_category, has_a_role])

    def require_channel(self, current_channel: str) -> bool:
        """
        Determines if the current channel is one of the required channels.
        """
        if "channels" not in self.require:
            return True

        return current_channel in self.require["channels"]

    def require_category(self, current_category: str) -> bool:
        """
        Determines if the current category is one of the required categories.
        """
        if "categories" not in self.require:
            return True

        return current_category in self.require["categories"]

    def require_a_role(self, member_roles: set[str]) -> bool:
        """
        Determines if the member has at least one required role.
        """
        if "roles" not in self.require:
            return True

        return member_roles & self.require["roles"]


class CCManager:
    """
    A manager for custom commands.
    """

    def __init__(self, bs_inst: birdsong.Birdsong, commands_path: str) -> None:
        """
        Configures the command manager.
        """
        self.birdsong = bs_inst
        self.commands: dict[str, CustomCommand] = {}
        self.commands_path = commands_path
        self.load_command_library()

    def build_command_line(
        self, content: str, type: CCTriggerType
    ) -> typing.Tuple[str, list[str]]:
        """
        Returns the command line that results from treating a message of an invocation of
        a command with the given command trigger type. Messages of type command return the
        prefixless first word in cmd and the rest of the message split into args. Messages
        of all match-based types return the entire content string in cmd and an empty list
        of args.
        """
        if type == CCTriggerType.CCTriggerNone:
            raise Exception("Cannot have a trigger of type None!")

        if type != CCTriggerType.CCTriggerCommand:
            return content, []
        else:
            self.birdsong.logger.debug("Content here: {}".format(content))
            fragments = content.split()
            args = [] if len(fragments) < 2 else fragments[1:]
            return fragments[0].removeprefix(self.birdsong.prefix), args

    def build_require_block(
        self, context: discord.Message
    ) -> dict[str, list[str] | set(str)]:
        """
        Parses the context into a dictionary of requirements.
        """
        return {
            "channel": context.channel.name,
            "category": context.channel.category.name if context.channel.category else "",
            "roles": set(map(lambda role: role.name, context.author.roles)),
        }

    async def execute_all(self, context: discord.Message):
        """
        Finds every matching command spec and executes them in sequence.
        """
        commands: list[CustomCommand] = self.find_commands(context=context)
        self.birdsong.logger.debug(
            "(id={}, content={}): Matched {} commands.".format(
                context.id, context.content, len(commands)
            )
        )
        delete = False

        for command in commands:
            cmd, args = self.build_command_line(
                content=context.content, type=command.cmdtype
            )
            if await command.actions(self.birdsong, context, cmd, args):
                delete = True

        if delete:
            await context.delete()

    def find_commands(self, context: discord.Message):
        """
        Returns a list of every custom command whose spec is satisfied by the context that is
        associated with the trigger message.
        """
        candidates = []
        for command in self.commands.values():
            cmd, _ = self.build_command_line(
                content=context.content, type=command.cmdtype
            )
            requirements = self.build_require_block(context=context)
            if command.check_trigger(cmd) and command.check_requirements(requirements):
                candidates.append(command)
        return candidates

    def load_cc_response(self, path: str, spec: pathlib.Path) -> CCActionsType:
        """
        Opens a python file at the given path, and loads the coroutine named action from it.
        """
        if path == "":
            return CCManager.no_such_action

        code_path: pathlib.Path = utils.resolve_path(path=path, relative=spec)

        import_spec = importlib.util.spec_from_file_location(code_path.stem, code_path)
        import_module = importlib.util.module_from_spec(import_spec)
        import_spec.loader.exec_module(import_module)

        return import_module.action

    def load_command_library(self):
        """
        Loads the command library from the commands path.
        """
        for path in pathlib.Path(self.commands_path).rglob("*.yaml"):
            if path in self.commands:
                continue

            with open(path, "r") as yaml_file:
                command_spec = yaml.load(yaml_file, yaml.CLoader)

            actions = self.load_cc_response(
                path=command_spec.get("actions", ""), spec=path
            )
            cmdtype = CCTriggerType.from_string(command_spec.get("cmdtype", ""))
            require = command_spec.get("require", {})
            trigger = command_spec.get("trigger", "")

            cc: CustomCommand = CustomCommand(
                path=path,
                actions=actions,
                cmdtype=cmdtype,
                require=require,
                trigger=trigger,
            )
            if self.validate_command(cc):
                self.commands.update({path: cc})

        self.birdsong.logger.info("Loaded {} commands.".format(len(self.commands)))

    @classmethod
    async def no_such_action(
        cls, birdsong: any, context: discord.Message, cmd: str, args: list[str]
    ) -> bool:
        """
        Does nothing.
        """
        return False

    def validate_command(self, command: CustomCommand) -> bool:
        """
        Determines whether the custom command is valid.
        """
        if command.trigger == "":
            self.birdsong.logger.warn(
                "Command has empty trigger. (defined at: {})".format(command.path)
            )
            return False

        if command.cmdtype == CCTriggerType.CCTriggerNone:
            self.birdsong.logger.warn(
                "Command has invalid cmdtype None. (defined at: {})".format(
                    command.path
                )
            )
            return False

        if utils.did_except(re.compile, command.trigger):
            self.birdsong.logger.warn(
                "Command has invalid trigger regex {}. (defined at: {})".format(
                    command.trigger, command.path
                )
            )
            return False

        return True
