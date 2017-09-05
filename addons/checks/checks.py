from discord.ext import commands
from addons.checks import errors


def is_access_allowed(required_level: int):
    return commands.check(lambda ctx: check_perms(ctx, required_level))


def check_perms(ctx, required_level: int):
    """
    Checks if user has permission to use command and returns boolean.
    Owner which is provided in config is a bot superuser
    since no one will be having access to special commands except owner by default.

    Bot access system uses levels. If role in database record is greater or equal to required level - access
    will be granted.

    Required_level explicitly passed to check_perms in command (currently manually).

    Access levels for commands are in progress...

    :param ctx: Context
    :param required_level: Required role level
    :return: Bool
    """

    msg = ctx.message
    bot = ctx.bot

    if msg.author.id == bot.config['owner']:
        return True

    if msg.author.roles:
        for role in msg.author.roles:
            # NOTE: Roles can have similar names. Not sure if it is bad.
            if role.id in bot.access_roles[msg.server.id] \
                    and bot.access_roles[msg.server.id][role.id] >= required_level:
                return True

    raise errors.AccessDenied
