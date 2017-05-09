import sqlite3

async def db_check(bot, ctx, cursor, table: str):
    """
    This function is coroutine.
    Checks if table exists.
    
    :param bot: Bot instance
    :param ctx: Context
    :param cursor: Database cursor
    :param table: Table name
    :return: Boolean: True or False
    """
    try:
        cursor.execute('SELECT 1 FROM {}'.format(table))
        return True
    except sqlite3.Error:
        await bot.send_message(ctx.message.channel, "Database is not initialized. Use `Kurisu, db init` to perform initialization.")
        cursor.close()
        return False


def get_members(ctx, name):
    """
    Gets all server members.
    Returns array of members which should be passed to get_member() method.
    Used for more intelligent search among server members.
    
    :param ctx: Context
    :param name: Member name
    :return: Array
    """
    members = []

    # Since username cannot contain hash we can safely split it
    if '#' in name:
        print("Name with discriminator has been passed. Looking for the member...")
        name_parts = name.split('#')
        for mem in ctx.message.server.members:
            if name_parts[0].lower() in mem.name.lower():
                print("Member {} found!".format(mem.name))
                members.append(mem.name + '#' + mem.discriminator)
                # Since there can be only one specific member with this discriminator
                # we can return members right after we found him
                return members

    # Search for members if there's
    for mem in ctx.message.server.members:
        # Limit number of results
        if name.lower() in mem.name.lower() and len(members) < 5:
            members.append(mem.name + '#' + mem.discriminator)

    # If we didn't find any members, then there is possibility that it's a nickname
    if not members:
        print("Members weren't found. Checking if it's a nickname...")
        for mem in ctx.message.server.members:
            # Limit number of results & check if member has a nick and compare with input
            if mem.nick and name.lower() in mem.nick.lower() and len(members) < 5:
                members.append(mem.name + '#' + mem.discriminator)
        print('Members with nickname was found!')

    return members


# TODO: Might be possible to combine it with get_members() method
async def get_member(bot, ctx, name, members):
    """
    This function is coroutine.
    Used to get member from user message.
    Returns member if found and None if not found.
    
    :param bot: Bot instance
    :param ctx: Context
    :param name: Member name
    :param members: Array of members
    :return: member or None
    """
    # Check if it's a mention
    if name.startswith('<@'):
        name = name.strip('<@?!#$%^&*>')
        member = ctx.message.server.get_member(name)
        return member
    else:
        if members:
            member = ctx.message.server.get_member_named(members[0])
            return member
        else:
            await bot.send_message(ctx.message.channel, "No members were found and I don't have any clue who that is.")
            return None
