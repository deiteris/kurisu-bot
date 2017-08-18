# TODO LIST
# TODO: Proper prize distribution and banks
# TODO: Clean up, refactor and sort the code
# TODO: Describe all commands and add more info upon completion
# FEATURE: Hand evaluation assist?
# FEATURE: Money transfer?
# FEATURE: Game initiator, on ready start, or stay as is?

# Deuces library is used for poker hand evaluation
# https://github.com/worldveil/deuces

import deuces
import sqlite3
import asyncio
import discord
from discord.ext import commands
from enum import Enum, auto
from collections import deque


class GameStatus(Enum):
    PENDING = auto()
    PREFLOP = auto()
    FLOP = auto()
    TURN = auto()
    RIVER = auto()
    ENDGAME = auto()

    def next(self):
        return GameStatus(self.value + 1)


class PlayerStatus(Enum):
    WAITING = auto()
    CALLED = auto()
    CHECKED = auto()
    BET = auto()
    RAISED = auto()
    ALLIN = auto()
    THONKING = auto()
    FOLDED = auto()


class Dealer:

    def __init__(self, players, table):
        self.deck = deuces.Deck()
        self.players = players
        self.table = table

    def distribute_cards(self):
        for player in self.players:
            player.hand.extend(self.deck.draw(2))

    def place_cards(self):
        if len(self.table.cards) >= 3:
            self.table.cards.extend(self.deck.draw(1))
        else:
            self.table.cards.extend(self.deck.draw(3))


class Player:

    def __init__(self, player_id, user, status, balance):
        self.id = player_id
        self.user = user
        self.status = status
        self.hand = []
        self.current_stake = 0
        self.total_stake = 0
        self.balance = balance

    def add_balance(self, amount):
        self.balance += amount

    def withdraw_balance(self, amount):
        self.balance -= amount

    def set_status(self, status):
        self.status = status

    def set_current_stake(self, stake):
        self.total_stake += stake
        self.current_stake = stake

    def __str__(self):
        return str(self.user)


class Table:

    def __init__(self, players):
        self.players = players
        self.dealer = Dealer(self.players, self)
        self.cards = []
        # TODO: Probably separate banks for different rounds are needed
        self.bank = 0

        # Distribute cards right after table was created
        self.dealer.distribute_cards()

    def add_bank(self, amount):
        self.bank += amount

    def set_players(self, players):
        self.players = players

    def get_dealer(self):
        return self.dealer


class GameDirector:

    def __init__(self, bot, db_funcs, channel, status):
        self.channel = channel
        self.status = status
        self.bot = bot
        self.db_funcs = db_funcs
        self.table = None
        self.turn_timer = None
        self.players = []
        self.rotation = deque()
        self.highest_stake = 40
        self.turn_counter = 0
        self.evaluator = deuces.Evaluator()

    # Game functions
    def create_table(self):
        self.table = Table(self.players)

    def process_stake(self, player, amount, stake, status):

        player.withdraw_balance(amount)
        self.table.add_bank(amount)

        self.db_funcs.write_player_data(player)

        player.set_current_stake(stake)

        player.set_status(status)

    async def make_check(self, player):

        player.set_status(PlayerStatus.CHECKED)

        await self.get_next_player()

    async def make_fold(self, player):

        player.set_status(PlayerStatus.FOLDED)

        self.rotation.remove(player)

        await self.get_next_player()

    async def make_call(self, player):

        if self.highest_stake == 0:
            await self.make_check(player)
            return

        if player.balance < self.highest_stake:
            await self.bot.send_message(self.channel, "You don't have enough money to make call.")
            return

        amount_difference = self.highest_stake - player.current_stake

        self.process_stake(player, amount_difference, self.highest_stake, PlayerStatus.CALLED)

        await self.get_next_player()

    async def make_bet(self, player, amount):

        if player.balance < amount or self.highest_stake != 0:
            await self.bot.send_message(self.channel, "You don't have enough money to make bet or use \"k.raise\" to increase stake.")
            return

        self.highest_stake = amount

        self.process_stake(player, amount, amount, PlayerStatus.BET)

        await self.get_next_player()

    async def make_raise(self, player, amount):

        # (Highest Stake - Player Current Stake) + amount
        # (100 - 20) + 100 = 180 = PROFIT
        raise_amount = (self.highest_stake - player.current_stake) + amount

        if player.balance < raise_amount:
            await self.bot.send_message(self.channel, "You don't have enough money to raise stake.")
            return

        self.highest_stake = raise_amount

        amount_difference = raise_amount - player.current_stake

        self.process_stake(player, amount_difference, raise_amount, PlayerStatus.RAISED)

        await self.get_next_player()

    async def make_all_in(self, player):

        if player.balance == 0:
            await self.bot.send_message(self.channel, "You don't have enough money to go all in.")
            return

        player_stake = player.balance + player.current_stake

        if player_stake > self.highest_stake:
            self.highest_stake = player_stake

        # In case of emergency - swap values
        if player.balance > player.current_stake:
            amount_difference = player.balance - player.current_stake
        else:
            amount_difference = player.current_stake - player.balance

        self.process_stake(player, amount_difference, player_stake, PlayerStatus.ALLIN)

        await self.get_next_player()

    def take_blind(self, player):
        player.withdraw_balance(20)
        player.set_current_stake(20)
        self.table.add_bank(20)

        self.db_funcs.write_player_data(player)

    def set_players(self):
        # TODO: Make rotation order according to rules
        # Check if player has balance equal to 0 at game start and remove him
        for player in self.players:
            if player.balance < 100:
                self.players.remove(player)
            else:
                self.take_blind(player)
        # Copy players array to rotation
        self.rotation = deque(self.players)

    def add_player(self, player):

        balance = self.db_funcs.load_player_data(player)[3]

        self.players.append(Player(player.id, player, PlayerStatus.WAITING, balance))

    def get_player(self, author):
        for player in self.players:
            if author.id in player.id:
                return player

        return None

    async def remove_player(self, player):

        self.players.remove(player)

        # Variables are uninitialized if game is not in process
        if self.status is not GameStatus.PENDING:
            # player.set_status(PlayerStatus.FOLDED)
            self.rotation.remove(player)
            # If rotation doesn't contain players - the table will be destroyed
            if player.status is PlayerStatus.THONKING and len(self.rotation) >= 1:
                await self.get_next_player()

    def set_status(self, status):
        self.status = status

    async def turn_timer_task(self, player):
        try:
            # 20 seconds of inactivity
            while self.turn_counter < 90:
                self.turn_counter += 1
                await asyncio.sleep(1)
            else:
                # Don't forger to reset counter
                self.turn_counter = 0

                await self.bot.send_message(self.channel, "{} has been removed from table due to inactivity".format(str(player)))
                await self.remove_player(player)
        except asyncio.CancelledError:
            # And after task cancelling too
            self.turn_counter = 0

    async def get_table_info(self):

        embeded = discord.Embed(title='Table Info', description="Channel: {}".format(self.channel.name), color=0xEE8700)
        embeded.add_field(name="Total players:", value=str(len(self.players)), inline=True)
        embeded.add_field(name="Game status:", value=self.status.name, inline=False)
        if self.table is not None:
            embeded.add_field(name="Table bank:", value="${}".format(self.table.bank), inline=False)
        for player in self.players:
            embeded.add_field(name=player, value="Balance: ${}\nStatus: {}".format(player.balance, player.status.name), inline=True)

        await self.bot.send_message(self.channel, embed=embeded)

    async def get_next_player(self):

        # Cancel timer
        if self.turn_timer is not None:
            self.turn_timer.cancel()

        # Get next round
        await self.get_next_round()

        # Avoid errors after setting GameStatus to PENDING
        if self.status is GameStatus.PENDING:
            return

        # Move out player
        player = self.rotation.popleft()

        # Put him in the end of rotation
        self.rotation.append(player)

        # Set turn timer
        self.turn_timer = self.bot.loop.create_task(self.turn_timer_task(player))

        # Set player status
        player.set_status(PlayerStatus.THONKING)

        await self.bot.send_message(self.channel, "{}'s turn.\nCurrent table bank is: ${}".format(player.user.mention, self.table.bank))

    async def set_next_round(self, status):

        for player in self.rotation:
            # Reset states and nullify current stakes
            player.set_status(PlayerStatus.WAITING)
            player.set_current_stake(0)
            self.highest_stake = 0

        self.set_status(status)
        self.table.get_dealer().place_cards()

        cards = [deuces.Card.int_to_pretty_str(card) for card in self.table.cards]

        await self.bot.send_message(self.channel, "Cards on table:\n{}".format("\n".join(cards)))

    def reset_game(self):
        # Reset stakes and hands
        for player in self.players:
            player.hand = []
            player.set_current_stake(0)
            player.total_stake = 0
            player.set_status(PlayerStatus.WAITING)

        # Reset rotation
        self.rotation = deque()

        # Nullify timer task
        self.turn_timer = None

        # Reset initial highest stake
        self.highest_stake = 40

        # Burn the table
        self.table = None

    async def get_next_round(self):

        # Before we check for next round we need to make sure it's necessary
        if len(self.rotation) == 1:
            last_player = self.rotation.popleft()
            last_player.add_balance(self.table.bank)

            self.db_funcs.write_player_data(last_player)

            # Reset status
            self.set_status(GameStatus.PENDING)

            # Reset game
            self.reset_game()

            await self.bot.send_message(self.channel, "As the last man standing, {} wins and gets the bank!\n"
                                                      "Type \"k.start\" to start game again.".format(last_player.user.mention))
            return

        is_new_round = True

        for player in self.rotation:
            # We need to check if all stakes are equal to the highest one.
            # Except the case when player went all-in.
            if player.current_stake < self.highest_stake and player.balance != 0:
                player.set_status(PlayerStatus.WAITING)

            # And if we found player who is waiting and has non-zero balance - continue current round.
            if player.status is PlayerStatus.WAITING:
                is_new_round = False

        # If all players made their moves - proceed to next round
        if is_new_round:

            # Get next status
            next_status = self.status.next()

            # Set it if it's not end of the game
            if next_status is not GameStatus.ENDGAME:
                await self.set_next_round(next_status)
            else:
                # Update game status
                self.set_status(GameStatus.PENDING)

                # TODO: Prize distribution (when banks are finished)

                winners = []
                players_cards = ""

                # NOTE: Lower value - higher rank
                best_rank = 7463  # Set rank lower than lowest possible hand (7462)

                for player in self.rotation:
                    rank = self.evaluator.evaluate(player.hand, self.table.cards)

                    print("{}'s hand rank: {}".format(player, rank))

                    cards = [deuces.Card.int_to_pretty_str(card) for card in player.hand]
                    players_cards += "{}'s hand: {}\n".format(player, " and ".join(cards))

                    # Detect winner
                    if rank == best_rank:
                        winners.append(player)
                        best_rank = rank
                    elif rank < best_rank:
                        winners = [player]
                        best_rank = rank

                rank_class = self.evaluator.get_rank_class(best_rank)
                class_string = self.evaluator.class_to_string(rank_class)

                if len(winners) == 1:
                    msg = "The winner is {} with {}.\n{}\nEnd of game. Type \"k.start\" to start game again.".format(
                        winners[0].user.mention, class_string, players_cards
                    )
                    # Give bank to winner
                    winners[0].add_balance(self.table.bank)
                    self.db_funcs.write_player_data(winners[0])
                else:
                    msg = "Players {} are tied for the win with {}.\n{}\nEnd of game. Type \"k.start\" to start game again.".format(
                        ", ".join(map(str, winners)), class_string, players_cards
                    )
                    # Return players' stakes
                    for winner in winners:
                        winner.add_balance(winner.total_stake)
                        self.db_funcs.write_player_data(winner)

                # Reset game
                self.reset_game()

                await self.bot.send_message(self.channel, msg)


class DBFunctions:

    def __init__(self, db):
        self.db = db

    def add_player(self, player: discord.Member):
        try:
            # User ID, name, balance, win count
            record = (player.id, str(player), 5000, 0)
            self.db.execute("INSERT INTO poker_players(user_id, name, balance, win_count) VALUES (?,?,?,?)", record)
            self.db.commit()
        except sqlite3.Error as e:
            print(type(e).__name__)

    def write_player_data(self, player: Player):
        try:
            # NOTE: Uses Player type, other functions use discord.Member type
            record = (player, player.balance, player.user.id)
            self.db.execute("UPDATE poker_players SET name=?, balance=? WHERE user_id=?", record)
            self.db.commit()
        except sqlite3.Error as e:
            print(type(e).__name__)

    # This function name means that we will collect more data (win count f.e.)
    def load_player_data(self, player: discord.Member):

        self.check_for_player(player)

        cursor = self.db.cursor()
        try:
            cursor.execute("SELECT * FROM poker_players WHERE user_id=?", (player.id,))
            data = cursor.fetchone()
            cursor.close()
            # [0] - id, [1] - user_id, [2] - username
            # [3] - balance, [4] - win count
            return data
        except sqlite3.Error as e:
            print(type(e).__name__)

    def check_for_player(self, user: discord.Member):
        cursor = self.db.cursor()
        try:
            cursor.execute("SELECT * FROM poker_players WHERE user_id=?", (user.id,))
            player = cursor.fetchone()
            if not player:
                self.add_player(user)
        except sqlite3.Error as e:
            print(type(e).__name__)

    # Combines both types, discord.Member and Player
    def give_money(self, player):

        self.check_for_player(player)

        try:
            # TODO: Give random amount in certain range?
            money_to_give = 1000
            next_day = 24 * 60 * 60
            record = ()

            if type(player) is Player:
                player.balance += money_to_give
                record = (player, player.balance, next_day, player.user.id)
            elif type(player) is discord.Member:
                player_balance = self.load_player_data(player)[3]
                player_balance += money_to_give
                record = (str(player), player_balance, next_day, player.id)

            self.db.execute("UPDATE poker_players SET name=?, balance=?, next_claim_time=strftime('%s','now') + ? WHERE user_id=?", record)
            self.db.commit()
        except sqlite3.Error as e:
            print(type(e).__name__)


class Poker:
    """
    Poker game commands
    """

    def __init__(self, bot):
        self.bot = bot
        self.db_funcs = DBFunctions(bot.db)
        self.games = {}

    def get_game(self, server, channel):

        if server.id not in self.games or channel.id not in self.games[server.id]:
            return None

        return self.games[server.id][channel.id]

    # Don't allow player to participate in multiple games
    def player_lookup(self, player):

        for server, channel in self.games.items():
            for game in channel.values():
                if game.get_player(player):
                    return True

        return False

    # General actions
    @commands.command(pass_context=True, no_pm=True)
    async def poker(self, ctx):
        """
        Initializes poker game.
        For more information about game rules, please, check:
        http://www.pokerlistings.com/poker-rules-texas-holdem
        """

        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        game = self.get_game(server, channel)

        if game:
            await self.bot.say("There's an ongoing game! Type \"k.join\" to join the table!")
            return

        # The only case when we need to check if there a games - when we're creating new game
        if len(self.games) > 0:
            lookup_result = self.player_lookup(author)

            if lookup_result:
                await self.bot.say("You're not allowed to play in more than one game!")
                return

        player_balance = self.db_funcs.load_player_data(author)[3]

        if player_balance < 100:
            await self.bot.say("You don't have enough money to participate in game.")
            return

        game = GameDirector(self.bot, self.db_funcs, channel, GameStatus.PENDING)
        game.add_player(author)

        if server.id not in self.games:
            self.games.update({server.id: {}})

        self.games[server.id].update({channel.id: game})

        await self.bot.say("{} has initiated new game! ┬─┬﻿ ノ( ゜-゜ノ)\nType \"k.join\" to join table "
                           "and type \"k.start\" once everyone is ready!".format(author.name))

    @commands.command(pass_context=True, no_pm=True)
    async def join(self, ctx):
        """
        Join game.
        """

        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        game = self.get_game(server, channel)

        if not game:
            await self.bot.say("There're no ongoing games. Start new by typing \"k.poker\"!")
            return

        player = game.get_player(author)

        if player:
            await self.bot.say("You're participating in this game!")
            return

        # Since we're checking if there're any games before join
        # There's no possibility that games will be equal to zero
        lookup_result = self.player_lookup(author)

        if lookup_result:
            await self.bot.say("You're not allowed to play in more than one game!")
            return

        player_balance = self.db_funcs.load_player_data(author)[3]

        if player_balance < 100:
            await self.bot.say("You don't have enough money to participate in game.")
            return
        elif len(game.players) == 10:
            await self.bot.say("Table limit is 10 people.")
            return

        game.add_player(author)

        await self.bot.say("{} has joined the game!".format(author.name))

    @commands.command(pass_context=True, no_pm=True)
    async def leave(self, ctx):
        """
        Leave game.
        """

        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        game = self.get_game(server, channel)

        if not game:
            await self.bot.say("There're no ongoing games. Start new by typing \"k.poker\"!")
            return

        player = game.get_player(author)

        if not player:
            await self.bot.say("You're not participating in this game!")
            return

        await game.remove_player(player)

        await self.bot.say("You've left the game.")

        if not game.players:
            del self.games[server.id][channel.id]
            await self.bot.say("Table is empty! (╯°-°）╯︵ ┻━┻:fire:")

    @commands.command(pass_context=True, no_pm=False)
    async def claim(self, ctx):
        """
        Adds money to your balance in amount of $1000.
        You can claim prize only once in a day.
        """

        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel
        cursor = self.bot.db.cursor()

        cursor.execute("SELECT * FROM poker_players WHERE next_claim_time > strftime('%s','now') and user_id=?", (author.id,))
        result = cursor.fetchone()
        cursor.close()

        if result:
            await self.bot.say("You have already claimed your daily prize today!")
            return

        game = self.get_game(server, channel)

        if game:
            # Update balance in game and database
            player = game.get_player(author)
            if player:
                self.db_funcs.give_money(player)
        else:
            # Update balance only in database (and create record if it doesn't exist)
            self.db_funcs.give_money(author)

        await self.bot.say("You have successfully claimed daily prize!")

    @commands.command(pass_context=True, no_pm=False, aliases=['bal'])
    async def balance(self, ctx):
        """
        Shows balance.
        """

        author = ctx.message.author

        player_balance = self.db_funcs.load_player_data(author)[3]
        await self.bot.say("Your balance is ${}".format(player_balance))

    @commands.command(pass_context=True, no_pm=True)
    async def start(self, ctx):
        """
        Start game.
        """

        server = ctx.message.server
        channel = ctx.message.channel

        game = self.get_game(server, channel)

        if not game:
            await self.bot.say("There're no ongoing games. Start new by typing \"k.poker\"!")
            return
        elif game.status is not GameStatus.PENDING:
            await self.bot.say("The game is in process.")
            return
        elif len(game.players) <= 1:
            await self.bot.say("You can't start game alone.")
            return

        game.create_table()
        game.set_status(GameStatus.PREFLOP)
        game.set_players()

        for player in game.players:
            cards = [deuces.Card.int_to_pretty_str(card) for card in player.hand]
            await self.bot.send_message(player.user, "Your cards are: {}".format(" and ".join(cards)))

        await self.bot.say("Setting up the table and starting the game!\n")

        await game.get_next_player()

    # Game actions
    @commands.command(pass_context=True, no_pm=True)
    async def check(self, ctx):
        """
        Pass the action to next player, but keep cards.
        """

        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        game = self.get_game(server, channel)

        if not game:
            await self.bot.say("There're no ongoing games. Start new by typing \"k.poker\"!")
            return

        player = game.get_player(author)

        if not player:
            await self.bot.say("You're not playing in this game!")
            return
        elif game.status is GameStatus.PENDING:
            await self.bot.say("Game is not running.")
            return
        elif player.status is not PlayerStatus.THONKING:
            await self.bot.say("You can't make any actions!")
            return
        elif game.status is GameStatus.PREFLOP:
            await self.bot.say("You can't check during pre-flop round.")
            return

        await game.make_check(player)

    @commands.command(pass_context=True, no_pm=True, name='table-info')
    async def table_info(self, ctx):
        """
        Shows information about current game.
        """

        server = ctx.message.server
        channel = ctx.message.channel

        game = self.get_game(server, channel)

        if not game:
            await self.bot.say("There're no ongoing games. Start new by typing \"k.poker\"!")
            return

        await game.get_table_info()

    @commands.command(pass_context=True, no_pm=True)
    async def call(self, ctx):
        """
        Match the amount that has been put in by another player.
        """

        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        game = self.get_game(server, channel)

        if not game:
            await self.bot.say("There're no ongoing games. Start new by typing \"k.poker\"!")
            return

        player = game.get_player(author)

        if not player:
            await self.bot.say("You're not playing in this game!")
            return
        elif game.status is GameStatus.PENDING:
            await self.bot.say("Game is not running.")
            return
        elif player.status is not PlayerStatus.THONKING:
            await self.bot.say("You can't make any actions!")
            return

        await game.make_call(player)

    @commands.command(pass_context=True, no_pm=True)
    async def bet(self, ctx, amount: int):
        """
        Open round with stake.
        """

        if amount < 0:
            return

        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        game = self.get_game(server, channel)

        if not game:
            await self.bot.say("There're no ongoing games. Start new by typing \"k.poker\"!")
            return

        player = game.get_player(author)

        if not player:
            await self.bot.say("You're not playing in this game!")
            return
        elif game.status is GameStatus.PENDING:
            await self.bot.say("Game is not running.")
            return
        elif player.status is not PlayerStatus.THONKING:
            await self.bot.say("You can't make any actions!")
            return
        elif game.status is GameStatus.PREFLOP:
            await self.bot.say("You can't bet during pre-flop round.")
            return

        await game.make_bet(player, amount)

    @commands.command(pass_context=True, no_pm=True, name='raise')
    async def raise_stake(self, ctx, amount: int):
        """
        Increase the amount of current stake ON given amount.
        """

        if amount < 0:
            return

        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        game = self.get_game(server, channel)

        if not game:
            await self.bot.say("There're no ongoing games. Start new by typing \"k.poker\"!")
            return

        player = game.get_player(author)

        if not player:
            await self.bot.say("You're not playing in this game!")
            return
        elif game.status is GameStatus.PENDING:
            await self.bot.say("Game is not running.")
            return
        elif player.status is not PlayerStatus.THONKING:
            await self.bot.say("You can't make any actions!")
            return

        await game.make_raise(player, amount)

    @commands.command(pass_context=True, no_pm=True, name='all-in')
    async def all_in(self, ctx):
        """
        Bet all available money.
        """

        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        game = self.get_game(server, channel)

        if not game:
            await self.bot.say("There're no ongoing games. Start new by typing \"k.poker\"!")
            return

        player = game.get_player(author)

        if not player:
            await self.bot.say("You're not playing in this game!")
            return
        elif game.status is GameStatus.PENDING:
            await self.bot.say("Game is not running.")
            return
        elif player.status is not PlayerStatus.THONKING:
            await self.bot.say("You can't make any actions!")
            return

        await game.make_all_in(player)

    @commands.command(pass_context=True, no_pm=True)
    async def fold(self, ctx):
        """
        Drop cards and pass action to next player.
        """

        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        game = self.get_game(server, channel)

        if not game:
            await self.bot.say("There're no ongoing games. Start new by typing \"k.poker\"!")
            return

        player = game.get_player(author)

        if not player:
            await self.bot.say("You're not playing in this game!")
            return
        elif game.status is GameStatus.PENDING:
            await self.bot.say("Game is not running.")
            return
        elif player.status is not PlayerStatus.THONKING:
            await self.bot.say("You can't make any actions!")
            return

        await game.make_fold(player)


def setup(bot):
    bot.add_cog(Poker(bot))
