import discord
import asyncio
import utils
from discord.ext import commands


class Mod:
    """
    Moderation commands (owner/mod only)
    """

    # Construct
    def __init__(self, bot):
        self.bot = bot
        self.tasks_storage = {}
        print('Addon "{}" loaded'.format(self.__class__.__name__))

    # Send message
    async def send(self, msg):
        await self.bot.say(msg)

    async def set_permissions(self, ctx, member, access):
        # Create empty PermissionOverwrite object and update values
        overwrites_text = discord.PermissionOverwrite()
        overwrites_text.update(send_messages=access, send_tts_messages=access, add_reactions=access)

        try:
            await self.bot.server_voice_state(member, mute=False if access is None else True)
        except discord.Forbidden as e:
            print("Failed to mute user. Reason: {}".format(e))

        for channel in ctx.message.server.channels:
            if channel.type is channel.type.text:
                # Set perms for each channel
                await self.bot.edit_channel_permissions(channel, member, overwrites_text)

    async def unmute_timer(self, ctx, member, time: int):
        try:
            await asyncio.sleep(time)

            # Reset permissions
            await self.set_permissions(ctx, member, None)

            # Remove muted member from storage
            del self.tasks_storage[member.name]

            print("Member {} has been unmuted.".format(member.name))

        except asyncio.CancelledError:
            del self.tasks_storage[member.name]

    # Commands
    @commands.command(pass_context=True, name="mute-t")
    async def mute_t(self, ctx, user: str, time: int):
        """Mute for specific time"""

        if ctx.message.author.id != self.bot.config['owner']:
            await self.send("Access denied.")
            return

        # Check for permission before proceed
        bot = ctx.message.server.get_member(self.bot.user.id)
        bot_permissions = bot.server_permissions

        if not bot_permissions.manage_roles:
            await self.send("I'm not able to manage permissions without `Manage Roles` permission")
            return
        elif not bot_permissions.mute_members:
            await self.send("I'm not able to mute voice without `Mute Members` permission")

        members = utils.get_members(ctx, user)

        # We want to mute specific member, so limit this to one to avoid wrong member
        if len(members) > 1:
            await self.bot.say("There are too many results. Please be more specific.\n\nHere is a list with suggestions:\n" + "\n".join(members))
            return

        member = await utils.get_member(self.bot, ctx, user, members)

        if member is None:
            return

        # Set permissions
        await self.set_permissions(ctx, member, False)

        # Set unmute timer
        # TODO: Store and reinitilize timers after restart
        unmute_timer = self.bot.loop.create_task(self.unmute_timer(ctx, member, time))
        self.tasks_storage.update({member.name: unmute_timer})

        if time >= 60:
            await self.send("Member {0} has been muted for {1[0]} minutes and {1[1]} seconds".format(member.name, divmod(time, 60)))
        else:
            await self.send("Member {} has been muted for {} seconds".format(member.name, time))

    @commands.command(pass_context=True)
    async def mute(self, ctx, user: str):
        """Permanent mute command"""

        if ctx.message.author.id != self.bot.config['owner']:
            await self.send("Access denied.")
            return

        # Check for permission before proceed
        bot = ctx.message.server.get_member(self.bot.user.id)
        bot_permissions = bot.server_permissions

        if not bot_permissions.manage_roles:
            await self.send("I'm not able to manage permissions without `Manage Roles` permission")
            return

        members = utils.get_members(ctx, user)

        # We want to mute specific member, so limit this to one to avoid wrong member
        if len(members) > 1:
            await self.bot.say("There are too many results. Please be more specific.\n\nHere is a list with suggestions:\n" + "\n".join(members))
            return

        member = await utils.get_member(self.bot, ctx, user, members)

        if member is None:
            return

        # Set permissions
        await self.set_permissions(ctx, member, False)

        await self.send("Member {} has been muted permanently".format(member.name))

    @commands.command(pass_context=True)
    async def unmute(self, ctx, user: str):
        """Unmute command"""

        if ctx.message.author.id != self.bot.config['owner']:
            await self.send("Access denied.")
            return

        # Check for permission before proceed
        bot = ctx.message.server.get_member(self.bot.user.id)
        bot_permissions = bot.server_permissions

        if not bot_permissions.manage_roles:
            await self.send("I'm not able to manage permissions without `Manage Roles` permission")
            return

        members = utils.get_members(ctx, user)

        # We want to mute specific member, so limit this to one to avoid wrong member
        if len(members) > 1:
            await self.bot.say("There are too many results. Please be more specific.\n\nHere is a list with suggestions:\n" + "\n".join(members))
            return

        member = await utils.get_member(self.bot, ctx, user, members)

        if member is None:
            return

        # Reset permissions
        await self.set_permissions(ctx, member, None)

        # Remove mute task for a member and remove him from storage
        if member.name in self.tasks_storage:
            self.tasks_storage[member.name].cancel()

        await self.bot.send_message(ctx.message.channel, "Member {} has been unmuted by command.".format(member.name))


def setup(bot):
    bot.add_cog(Mod(bot))
