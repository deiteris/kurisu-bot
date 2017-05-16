import discord
import asyncio
import time
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

        # Open cursor and check for mutes in database
        cursor = self.bot.db.cursor()

        # Check for those members, who need to be unmuted now
        cursor.execute("SELECT * FROM mutes WHERE mute_time < strftime('%s','now')")
        to_unmute_now_data = cursor.fetchall()
        if to_unmute_now_data:
            unmute_tasks = []
            print("Users with expired mute found. Removing mutes...")
            for row in to_unmute_now_data:
                # row[0] - ID
                # row[1] - Member ID
                # row[2] - Member name
                # row[3] - Mute time
                # row[4] - server id
                for server in bot.servers:
                    if server.id == row[4]:
                        member = server.get_member(row[1])
                        # Since we can't use async in __init__ we we'll create Future task.
                        task = asyncio.ensure_future(self.set_permissions(server, member, None))
                        # Add task to array
                        unmute_tasks.append(task)
                        # Add callback so task get removed from array when it's done
                        task.add_done_callback(unmute_tasks.remove)
                        break
            # Remove members with expired mute from database
            self.bot.db.execute("DELETE FROM mutes WHERE mute_time < strftime('%s','now')")
            self.bot.db.commit()

        # Check for those members, who need to be unmuted later
        cursor.execute("SELECT * FROM mutes")
        to_unmute_later_data = cursor.fetchall()
        if to_unmute_later_data:
            print("Users with not expired mute found.")
            for row in to_unmute_later_data:
                # row[0] - ID
                # row[1] - Member ID
                # row[2] - Member name
                # row[3] - Mute time
                # row[4] - server id
                for server in bot.servers:
                    if server.id == row[4]:
                        member = server.get_member(row[1])
                        seconds_to_unmute = row[3] - time.time()
                        # Prevent creating multiple tasks on 'reload' command
                        if member.id not in self.timers_storage[server.id]:
                            print("Setting up timers...")
                            unmute_timer = self.bot.loop.create_task(self.unmute_timer(server, member, seconds_to_unmute))
                            self.timers_storage[server.id].update({member.id: unmute_timer})
        cursor.close()

    # Send message
    async def send(self, msg):
        await self.bot.say(msg)

    async def set_permissions(self, server, member, access):
        # Create empty PermissionOverwrite object and update values
        overwrites_text = discord.PermissionOverwrite()
        overwrites_text.update(send_messages=access, send_tts_messages=access, add_reactions=access)

        try:
            await self.bot.server_voice_state(member, mute=False if access is None else True)
        except discord.Forbidden as e:
            print("Failed to mute user. Reason: {}".format(e))

        print("Setting permissions for {} to: {}".format(member.name, str(access)))

        for channel in server.channels:
            if channel.type is channel.type.text:
                # Set perms for each channel
                try:
                    await self.bot.edit_channel_permissions(channel, member, overwrites_text)
                except discord.Forbidden as e:
                    print("Failed to change permissions in {} channel. Reason: {}".format(channel, e))

    async def unmute_timer(self, server, member, seconds: int):
        try:
            await asyncio.sleep(seconds)

            # Reset permissions
            await self.set_permissions(server, member, None)

            # Remove muted member from storage
            del self.timers_storage[server.id][member.id]

            db = self.bot.db
            values = (member.id, server.id)
            db.execute("DELETE FROM mutes WHERE member_id=? AND server_id=?", values)
            db.commit()

            print("Member {} has been unmuted.".format(member.name))

        except asyncio.CancelledError:
            del self.timers_storage[server.id][member.id]

    # Commands
    @commands.command(pass_context=True, name="mute-t")
    async def mute_t(self, ctx, user: str, seconds: int):
        """Mute for specific time"""

        msg = ctx.message
        server = ctx.message.server

        if not await self.checks.check_perms(msg, 2):
            return

        # Check for permission before proceed
        bot = server.get_member(self.bot.user.id)
        bot_permissions = bot.server_permissions

        if not bot_permissions.manage_roles:
            await self.send("I'm not able to manage permissions without `Manage Roles` permission.")
            return
        elif not bot_permissions.mute_members:
            await self.send("I'm not able to mute voice without `Mute Members` permission.")

        members = utils.get_members(msg, user)

        # We want to mute specific member, so limit this to one to avoid wrong member
        if len(members) > 1:
            await self.bot.say("There are too many results. Please be more specific.\n\n"
                               "Here is a list with suggestions:\n"
                               "{}".format("\n".join(members)))
            return

        member = await utils.get_member(self.bot, msg, user, members)

        if member is None:
            return

        if member.id in self.timers_storage[server.id]:
            await self.bot.say("This member is already muted!")
            return

        # Set permissions
        await self.set_permissions(server, member, False)

        # Set unmute timer
        unmute_timer = self.bot.loop.create_task(self.unmute_timer(server, member, seconds))
        self.timers_storage[server.id].update({member.id: unmute_timer})

        # Write muted member to database
        db = self.bot.db
        values = (member.id, member.name, seconds, server.id)
        db.execute("INSERT INTO mutes(member_id, member_name, mute_time, server_id) VALUES (?,?,strftime('%s','now') + ?,?)", values)
        db.commit()

        if seconds >= 60:
            await self.send("Member {0} has been muted for {1[0]} minutes and {1[1]} seconds".format(member.name, divmod(seconds, 60)))
        else:
            await self.send("Member {} has been muted for {} seconds".format(member.name, seconds))

    @commands.command(pass_context=True)
    async def mute(self, ctx, user: str):
        """Permanent mute command"""

        msg = ctx.message
        server = ctx.message.server

        if not await self.checks.check_perms(msg, 2):
            return

        # Check for permission before proceed
        bot = server.get_member(self.bot.user.id)
        bot_permissions = bot.server_permissions

        if not bot_permissions.manage_roles:
            await self.send("I'm not able to manage permissions without `Manage Roles` permission.")
            return

        members = utils.get_members(msg, user)

        # We want to mute specific member, so limit this to one to avoid wrong member
        if len(members) > 1:
            await self.bot.say("There are too many results. Please be more specific.\n\n"
                               "Here is a list with suggestions:\n"
                               "{}".format("\n".join(members)))
            return

        member = await utils.get_member(self.bot, msg, user, members)

        if member is None:
            return

        # If member is temporarily muted - just cancel current timer
        if member.id in self.timers_storage[server.id]:
            self.timers_storage[server.id][member.id].cancel()
            db = self.bot.db
            values = (member.id, server.id)
            db.execute("DELETE FROM mutes WHERE member_id=? AND server_id=?", values)
            db.commit()
        else:
            # Set permissions
            await self.set_permissions(server, member, False)

        await self.send("Member {} has been muted permanently".format(member.name))

    @commands.command(pass_context=True)
    async def unmute(self, ctx, user: str):
        """Unmute command"""

        msg = ctx.message
        server = ctx.message.server

        if not await self.checks.check_perms(msg, 2):
            return

        # Check for permission before proceed
        bot = server.get_member(self.bot.user.id)
        bot_permissions = bot.server_permissions

        if not bot_permissions.manage_roles:
            await self.send("I'm not able to manage permissions without `Manage Roles` permission.")
            return

        members = utils.get_members(msg, user)

        # We want to mute specific member, so limit this to one to avoid wrong member
        if len(members) > 1:
            await self.bot.say("There are too many results. Please be more specific.\n\n"
                               "Here is a list with suggestions:\n"
                               "{}".format("\n".join(members)))
            return

        member = await utils.get_member(self.bot, msg, user, members)

        if member is None:
            return

        # Reset permissions
        await self.set_permissions(server, member, None)

        # Remove mute task for a member and remove him from database
        if member.id in self.timers_storage[server.id]:
            self.timers_storage[server.id][member.id].cancel()
            db = self.bot.db
            values = (member.id, server.id)
            db.execute("DELETE FROM mutes WHERE member_id=? AND server_id=?", values)
            db.commit()

        await self.bot.send_message(msg.channel, "Member {} has been unmuted by command.".format(member.name))


def setup(bot):
    bot.add_cog(Mod(bot))
