import discord
import asyncio
from addons import utils
from discord.ext import commands


class Mod:
    """
    Moderation commands (owner/mod only)
    """

    # Construct
    def __init__(self, bot):
        self.bot = bot
        self.timers_storage = bot.unmute_timers
        self.checks = utils.PermissionChecks(bot)
        print('Addon "{}" loaded'.format(self.__class__.__name__))

    # Send message
    async def send(self, msg):
        await self.bot.say(msg)

    async def set_permissions(self, msg, member, access):
        # Create empty PermissionOverwrite object and update values
        overwrites_text = discord.PermissionOverwrite()
        overwrites_text.update(send_messages=access, send_tts_messages=access, add_reactions=access)

        try:
            await self.bot.server_voice_state(member, mute=False if access is None else True)
        except discord.Forbidden as e:
            print("Failed to mute user. Reason: {}".format(e))

        for channel in msg.server.channels:
            if channel.type is channel.type.text:
                # Set perms for each channel
                try:
                    await self.bot.edit_channel_permissions(channel, member, overwrites_text)
                except discord.Forbidden as e:
                    print("Failed to change permissions in {} channel. Reason: {}".format(channel, e))

    async def unmute_timer(self, msg, member, time: int):
        try:
            await asyncio.sleep(time)

            # Reset permissions
            await self.set_permissions(msg, member, None)

            # Remove muted member from storage
            del self.timers_storage[msg.server.id][member.name]

            print("Member {} has been unmuted.".format(member.name))

        except asyncio.CancelledError:
            del self.timers_storage[msg.server.id][member.name]

    # Commands
    @commands.command(pass_context=True, name="mute-t")
    async def mute_t(self, ctx, user: str, time: int):
        """Mute for specific time"""

        if not await self.checks.check_perms(ctx.message, 2):
            return

        # Check for permission before proceed
        bot = ctx.message.server.get_member(self.bot.user.id)
        bot_permissions = bot.server_permissions

        if not bot_permissions.manage_roles:
            await self.send("I'm not able to manage permissions without `Manage Roles` permission.")
            return
        elif not bot_permissions.mute_members:
            await self.send("I'm not able to mute voice without `Mute Members` permission.")

        members = utils.get_members(ctx.message, user)

        # We want to mute specific member, so limit this to one to avoid wrong member
        if len(members) > 1:
            await self.bot.say("There are too many results. Please be more specific.\n\n"
                               "Here is a list with suggestions:\n"
                               "{}".format("\n".join(members)))
            return

        member = await utils.get_member(self.bot, ctx.message, user, members)

        if member is None:
            return

        # Set permissions
        await self.set_permissions(ctx.message, member, False)

        # Set unmute timer
        # TODO: Store and reinitilize timers after restart
        unmute_timer = self.bot.loop.create_task(self.unmute_timer(ctx.message, member, time))
        self.timers_storage[ctx.message.server.id].update({member.name: unmute_timer})

        if time >= 60:
            await self.send("Member {0} has been muted for {1[0]} minutes and {1[1]} seconds".format(member.name, divmod(time, 60)))
        else:
            await self.send("Member {} has been muted for {} seconds".format(member.name, time))

    @commands.command(pass_context=True)
    async def mute(self, ctx, user: str):
        """Permanent mute command"""

        if not await self.checks.check_perms(ctx.message, 2):
            return

        # Check for permission before proceed
        bot = ctx.message.server.get_member(self.bot.user.id)
        bot_permissions = bot.server_permissions

        if not bot_permissions.manage_roles:
            await self.send("I'm not able to manage permissions without `Manage Roles` permission.")
            return

        members = utils.get_members(ctx.message, user)

        # We want to mute specific member, so limit this to one to avoid wrong member
        if len(members) > 1:
            await self.bot.say("There are too many results. Please be more specific.\n\n"
                               "Here is a list with suggestions:\n"
                               "{}".format("\n".join(members)))
            return

        member = await utils.get_member(self.bot, ctx.message, user, members)

        if member is None:
            return

        # Set permissions
        await self.set_permissions(ctx.message, member, False)

        await self.send("Member {} has been muted permanently".format(member.name))

    @commands.command(pass_context=True)
    async def unmute(self, ctx, user: str):
        """Unmute command"""

        if not await self.checks.check_perms(ctx.message, 2):
            return

        # Check for permission before proceed
        bot = ctx.message.server.get_member(self.bot.user.id)
        bot_permissions = bot.server_permissions

        if not bot_permissions.manage_roles:
            await self.send("I'm not able to manage permissions without `Manage Roles` permission.")
            return

        members = utils.get_members(ctx.message, user)

        # We want to mute specific member, so limit this to one to avoid wrong member
        if len(members) > 1:
            await self.bot.say("There are too many results. Please be more specific.\n\n"
                               "Here is a list with suggestions:\n"
                               "{}".format("\n".join(members)))
            return

        member = await utils.get_member(self.bot, ctx.message, user, members)

        if member is None:
            return

        # Reset permissions
        await self.set_permissions(ctx.message, member, None)

        # Remove mute task for a member and remove him from storage
        if member.name in self.timers_storage[ctx.message.server.id]:
            self.timers_storage[ctx.message.server.id][member.name].cancel()

        await self.bot.send_message(ctx.message.channel, "Member {} has been unmuted by command.".format(member.name))


def setup(bot):
    bot.add_cog(Mod(bot))
