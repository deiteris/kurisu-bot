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
        await bot.send_message(msg.channel, "Table {} is not initialized.\n\n Hint: Use `Kurisu, db init` to perform database initialization.")
        cursor.close()
        return False


def get_members(msg, name):
    """
    Gets all server members.
    Returns array of members which should be passed to get_member() method.
    Used for more intelligent search among server members.
    
    :param msg: Message
    :param name: Member name
    :return: Array
    """

    members = []

    # Since username cannot contain hash we can safely split it
    if '#' in name:
        print("Name with discriminator has been passed. Looking for the member...")
        name_parts = name.split('#')
        for mem in msg.server.members:
            if name_parts[0].lower() in mem.name.lower():
                print("Member {} found!".format(mem.name))
                members.append(mem.name + '#' + mem.discriminator)
                # Since there can be only one specific member with this discriminator
                # we can return members right after we found him
                return members

    # Search for members if there're
    for mem in msg.server.members:
        # Limit number of results
        if name.lower() in mem.name.lower() and len(members) < 5:
            members.append(mem.name + '#' + mem.discriminator)

    # If we didn't find any members, then there is possibility that it's a nickname
    if not members:
        print("Members weren't found. Checking if it's a nickname...")
        for mem in msg.server.members:
            # Limit number of results & check if member has a nick and compare with input
            if mem.nick and name.lower() in mem.nick.lower() and len(members) < 5:
                members.append(mem.name + '#' + mem.discriminator)

    return members


# TODO: Might be possible to combine it with get_members() method
async def get_member(bot, msg, name, members):
    """
    This function is coroutine.
    Used to get member from user message.
    Returns member if found and None if not found.
    
    :param bot: Bot instance
    :param msg: Message
    :param name: Member name
    :param members: Array of members
    :return: member or None
    """

    # Check if it's a mention
    if name.startswith('<@'):
        print("Mention has been passed. Looking for the member...")
        name = name.strip('<@?!#$%^&*>')
        member = msg.server.get_member(name)
        print("Member {} found!".format(member.name))
        return member
    else:
        if members:
            member = msg.server.get_member_named(members[0])
            return member
        else:
            await bot.send_message(msg.channel, "No members were found and I don't have any clue who that is.")
            return None


class PermissionChecks:

    def __init__(self, bot):
        self.bot = bot

    async def check_perms(self, msg, required_level: int):
        """
        Checks if user has permission to use command and returns boolean.
        Owner provided in config is a bot superuser since no one will be having access to special commands except owner by default.
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
