from __future__ import annotations

import discord
import typing

if typing.TYPE_CHECKING:
    from birdsong.core import birdsong


class Builtins:
    """
    A class that wraps all builtin Birdsong functionality into one point of reference.
    """

    SUCCESS = 1
    WARNING = 2
    ERROR = 3

    def __init__(self, bs_inst: birdsong.Birdsong) -> None:
        """
        Configures the builtins: this really just means to provide a reference to the bot.
        """
        self.birdsong = bs_inst

    def birdsong_admin(self, author: discord.User) -> bool:
        """
        Determines whether the given user is a bot administrator.
        """
        return self.birdsong.owner == author.id or author.id in self.birdsong.admins

    async def create_channel(
        self,
        context: discord.Message,
        name: str,
        type: discord.ChannelType,
        overwrites=None,
        duplicate=False,
    ) -> discord.abc.GuildChannel | None:
        """
        Creates a new channel.
        """
        guild = context.guild

        if not duplicate:
            channels: list[discord.abc.GuildChannel] = await guild.fetch_channels()
            if any(
                channel.name == name and channel.type == type for channel in channels
            ):
                return None

        kwargs = {}
        if overwrites:
            kwargs.update({"overwrites": overwrites})

        match type:
            case discord.ChannelType.category:
                return await guild.create_category(name, **kwargs)
            case discord.ChannelType.forum:
                return await guild.create_forum(name, **kwargs)
            case discord.ChannelType.text:
                return await guild.create_text_channel(name, **kwargs)
            case discord.ChannelType.voice:
                return await guild.create_voice_channel(name, **kwargs)

    async def find_channel(
        self, context: discord.Message, name: str, type: discord.ChannelType
    ) -> discord.abc.GuildChannel | None:
        """
        Finds a channel with the given name on the current guild if possible.
        """
        guild = context.guild

        for channel in await guild.fetch_channels():
            if channel.name == name and channel.type == type:
                return channel
        return None

    async def give_role(
        self, context: discord.Message, user: discord.Member, name: str
    ) -> bool:
        """
        Gives a role to a user by name and returns False if no such role was found.
        """
        guild = context.guild

        roles: list[discord.Role] = await guild.fetch_roles()
        matching: list[discord.Role] = [role for role in roles if role.name == name]
        if len(matching) > 0:
            await user.add_roles(*[matching])
            return True
        return False

    async def send_message(
        self,
        context: discord.Message,
        contents: list[dict],
        files: list[discord.File] = [],
        as_dm=False,
    ):
        """
        A nice wrapper for embed sending that handles multiple embeds and multiple files.
        """
        embeds = []
        for content in contents:
            embed = discord.Embed.from_dict(content)
            if "image" in content:
                embed.set_image(url=content["image"])
            embeds.append(embed)

        kwargs = {}
        kwargs.update({"embed": embeds[0]} if len(embeds) == 1 else {"embeds": embeds})
        kwargs.update({"file": files[0]} if len(files) == 1 else {"files": files})

        if as_dm:
            await context.author.send(**kwargs)
        else:
            await context.channel.send(**kwargs)

    def simple_embed_data(
        title: str = None,
        description: str = None,
        image: str = None,
        severity: int = None,
    ):
        """
        Creates a simple embed, with the severity in the description.
        """
        status_emote = {
            Builtins.SUCCESS: ":white_check_mark:",
            Builtins.WARNING: ":warning:",
            Builtins.ERROR: ":x:",
        }.get(severity, None)

        status_emote = "" if not status_emote else status_emote + " "

        content = {}

        if title:
            content.update({"title": title})
        if description:
            content.update({"description": status_emote + description})
        if image:
            content.update({"image": image})

        if content is not {}:
            return content

    async def take_role(
        self, context: discord.Message, user: discord.Member, name: str
    ) -> bool:
        """
        Takes roles from a user by name and returns False if no matching roles were found.
        """
        user.remove_roles(*[role for role in user.roles if role.name == name])
