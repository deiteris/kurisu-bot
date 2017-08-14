import sqlite3

# These methods are static since they're used in different addons
async def db_check(bot, msg, cursor, table: str):
    """
    This function is coroutine.
    
    Checks if table exists.
    
    :param bot: Bot instance
    :param msg: Message
    :param cursor: Database cursor
    :param table: Table name
    :return: Bool
    """

    try:
        cursor.execute('SELECT 1 FROM {}'.format(table))
        return True
    except sqlite3.Error:
        await bot.send_message(msg.channel, "Table {} is not initialized.\n\n"
                                            "Hint: Use `Kurisu, db init` to perform database initialization.".format(table))
        cursor.close()
        return False


async def get_members(bot, msg, name: str):
    """
    This function is coroutine.
    
    Gets server member/members.
    Returns array of members in "Username#Discriminator" format/
    First member of this array (members[0]) should be passed to server.get_member_named() method.
    Members array can be used for similar results outputting.
    
    :param bot: Bot instance
    :param msg: Message
    :param name: Member name
    :return: Array
    """

    members = []

    # Search for a member by mention
    # First check if it's mention
    if name.startswith('<@'):
        print("Mention has been passed. Looking for the member...")
        name = name.strip('<@?!#$%^&*>')
        mem = msg.server.get_member(name)
        print("Member {} found!".format(mem.name))
        members.append(mem.name + '#' + mem.discriminator)
        return members
    else:
        # Search for a member with specific discriminator
        # Since username cannot contain hash we can safely split it
        if '#' in name:
            print("Name with discriminator has been passed. Looking for the member...")
            name_parts = name.split('#')
            for mem in msg.server.members:
                if name_parts[0].lower() in mem.name.lower() and name_parts[1] in mem.discriminator:
                    print("Member {} found!".format(mem.name))
                    members.append(mem.name + '#' + mem.discriminator)
                    # Since there can be only one specific member with this discriminator
                    # we can return members right after we found him
                    return members

        # Search for a member by username
        for mem in msg.server.members:
            # Limit number of results
            if name.lower() in mem.name.lower() and len(members) < 5:
                members.append(mem.name + '#' + mem.discriminator)

        # Search for a member by nickname
        # If we didn't find any members, then there is possibility that it's a nickname
        if not members:
            print("Members weren't found. Checking if it's a nickname...")
            for mem in msg.server.members:
                # Limit number of results & check if member has a nick and compare with input
                if mem.nick and name.lower() in mem.nick.lower() and len(members) < 5:
                    members.append(mem.name + '#' + mem.discriminator)

        # If no members this time, then return None and error message else - return members
        if not members:
            print("No members were found")
            await bot.send_message(msg.channel, "No members were found and I don't have any clue who that is.")
            return None
        else:
            if len(members) > 4:
                await bot.say("There are too many results. Please be more specific.\n\n"
                                   "Here is a list with suggestions:\n"
                                   "{}".format("\n".join(members)))
                return None
            else:
                return members


class PermissionChecks:

    def __init__(self, bot):
        self.bot = bot

    async def check_perms(self, msg, required_level: int):
        """
        This function is coroutine.
        
        Checks if user has permission to use command and returns boolean.
        Owner which is provided in config is a bot superuser 
        since no one will be having access to special commands except owner by default.
        
        Bot access system uses levels. If role in database record is greater or equal to required level - access 
        will be granted.

        Required_level explicitly passed to check_perms in command (currently manually).

        Access levels for commands are in progress...

        :param msg: Message
        :param required_level: Required role level
        :return: Bool
        """

        if msg.author.id == self.bot.config['owner']:
            return True

        for role in msg.author.roles:
            # NOTE: Roles can have similar names. Not sure if it is bad.
            if role.name.lower() in self.bot.access_roles[msg.server.id] \
                    and self.bot.access_roles[msg.server.id][role.name.lower()] >= required_level:
                return True

        await self.bot.say("Access denied.")
        return False


# Dummy cog
class Utils:

    # Construct
    def __init__(self):
        print('Addon "{}" loaded'.format(self.__class__.__name__))


def setup(bot):
    bot.add_cog(Utils())
