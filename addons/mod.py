from discord.ext import commands
import discord


class Mod:
    """
    Moderation commands (owner/mod only)
    """

    # Construct
    def __init__(self, bot):
        self.bot = bot
        print('Addon "{}" loaded'.format(self.__class__.__name__))

    # Send message
    async def send(self, msg):
        await self.bot.say(msg)

    def get_members(self, ctx, name):
        members = []

        for mem in ctx.message.server.members:
            # Limit number of results
            if name.lower() in mem.name.lower() and len(members) < 5:
                members.append(mem.name + "#" + mem.discriminator)

        return members

    async def get_member(self, ctx, name, members):
        if name.startswith("<@"):
            name = name.strip('<@?!#$%^&*>')
            member = ctx.message.server.get_member(name)
            return member
        else:
            if members:
                member = ctx.message.server.get_member_named(members[0])
                return member
            else:
                await self.send("No members were found and I don't have any clue who's that.")
                return

    @commands.command(pass_context=True)
    async def mute(self, ctx, user: str):
        """Mute command"""

        if ctx.message.author.id != self.bot.config['owner']:
            await self.send("Access denied.")
            return

        # Check for permission before proceed
        bot = ctx.message.server.get_member(self.bot.user.id)
        bot_permissions = bot.server_permissions

        if not bot_permissions.manage_roles:
            await self.send("I'm not able to manage permissions without `Manage Roles` permission")
            return

        members = self.get_members(ctx, user)

        if len(members) > 4:
            await self.bot.say("There are too many results. Please be more specific.\n\nHere is a list with suggestions:\n" + "\n".join(members))
            return

        member = await self.get_member(ctx, user, members)

        # Create empty PermissionOverwrite object and update values
        overwrites = discord.PermissionOverwrite()
        overwrites.update(send_messages=False, send_tts_messages=False, add_reactions=False)

        # TODO: Global mute/unmute might be a little bit overkill
        # TODO: Not so fast, but 100% effective
        for channel in ctx.message.server.channels:
            # We need only text channels
            if channel.type is channel.type.text:
                # Set perms for each channel
                await self.bot.edit_channel_permissions(channel, member, overwrites)

        await self.send("Member {} has been muted".format(member.name))

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

        members = self.get_members(ctx, user)

        if len(members) > 4:
            await self.bot.say("There are too many results. Please be more specific.\n\nHere is a list with suggestions:\n" + "\n".join(members))
            return

        member = await self.get_member(ctx, user, members)

        # Create empty PermissionOverwrite object and update values
        overwrites = discord.PermissionOverwrite()
        overwrites.update(send_messages=None, send_tts_messages=None, add_reactions=None)

        # TODO: Global mute/unmute might be a little bit overkill
        # TODO: Not so fast, but 100% effective
        for channel in ctx.message.server.channels:
            # We need only text channels
            if channel.type is channel.type.text:
                # Set perms for each channel
                await self.bot.edit_channel_permissions(channel, member, overwrites)

        await self.send("Member {} has been unmuted".format(member.name))


def setup(bot):
    bot.add_cog(Mod(bot))
