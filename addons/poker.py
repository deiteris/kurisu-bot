# Deuces library is used for poker hand evaluation
# https://github.com/worldveil/deuces

import sqlite3
import asyncio
import discord
from random import randint
from addons import utils
from addons import deuces
from operator import attrgetter
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
    # For debug purposes
    BLINDED = auto()
    CALLED = auto()
    CHECKED = auto()
    BET = auto()
    RAISED = auto()
    ALLIN = auto()
    THONKING = auto()
    FOLDED = auto()


class Dealer:

    def __init__(self, table):
        self.deck = deuces.Deck()
        self.players = table.players
        self.table = table

    def deal_cards(self):
        for player in self.players:
            player.hand.extend(self.deck.draw(2))

    def place_cards(self):
        if len(self.table.cards) >= 3:
            self.table.cards.extend(self.deck.draw(1))
        else:
            self.table.cards.extend(self.deck.draw(3))


class Player:

    def __init__(self, user, balance):
        self.id = user.id
        self.user = user
        self.status = PlayerStatus.WAITING
        self.hand = []
        self.current_stake = 0
        self.total_stake = 0
        self.balance = balance
        self.fold_position = 0

    def add_balance(self, amount):
        self.balance += amount

    def withdraw_balance(self, amount):
        self.balance -= amount

    def set_status(self, status):
        self.status = status

    def set_current_stake(self, stake):
        self.current_stake = stake

    def set_total_stake(self, stake):
        self.total_stake += stake

    def set_fold_position(self, position):
        self.fold_position = position

    def __str__(self):
        return str(self.user)


class Table:

    def __init__(self, players):
        self.players = players
        self.rotation = deque()
        self.dealer = Dealer(self)
        self.cards = []
        self.bank = 0

    def add_bank(self, amount):
        self.bank += amount

    def withdraw_bank(self, amount):
        self.bank -= amount

    def get_dealer(self):
        return self.dealer


class GameDirector:

    def __init__(self, bot, db_funcs, channel):
        self.channel = channel
        self.status = GameStatus.PENDING
        self.bot = bot
        self.db_funcs = db_funcs
        self.table = None
        self.turn_timer = None
        self.pot_count = 0
        self.players = []
        self.round_highest_stake = 0
        self.turn_counter = 0
        self.fold_position = 0
        self.evaluator = deuces.Evaluator()

    # Game functions
    def create_table(self):
        self.table = Table(list(self.players))

    def process_stake(self, player: Player, amount: int, stake: int, status: PlayerStatus):

        print("-------------------------------")
        print("{} {}".format(str(player), status.name))
        print("Player balance: ${}".format(player.balance))
        print("Amount to withdraw and add to bank: ${}".format(amount))
        print("Player current stake: ${}".format(stake))

        player.withdraw_balance(amount)
        player.set_total_stake(amount)
        self.table.add_bank(amount)

        self.db_funcs.write_player_data(player)

        player.set_current_stake(stake)
        print("Player total stake: ${}".format(player.total_stake))
        print("-------------------------------")

        player.set_status(status)

    async def make_check(self, player: Player):

        if player.balance != 0 and player.current_stake < self.round_highest_stake:
            await self.bot.send_message(self.channel, "You're not allowed to check.")
            return

        player.set_status(PlayerStatus.CHECKED)

        await self.get_next_player()

    async def make_fold(self, player: Player):

        player.set_status(PlayerStatus.FOLDED)

        # Used for detection in side pots distribution
        self.fold_position += 1

        player.set_fold_position(self.fold_position)

        self.table.rotation.remove(player)

        await self.get_next_player()

    async def make_call(self, player: Player):

        if self.round_highest_stake == 0:
            await self.make_check(player)
            return

        if player.balance < self.round_highest_stake:
            await self.bot.send_message(self.channel, "You don't have enough money to make call.")
            return

        # Difference between stake to answer on and player's current stake
        amount_difference = self.round_highest_stake - player.current_stake

        self.process_stake(player, amount_difference, self.round_highest_stake, PlayerStatus.CALLED)

        await self.get_next_player()

    async def make_bet(self, player: Player, amount: int):

        if player.balance < amount:
            await self.bot.send_message(self.channel, "You don't have enough money to make bet.")
            return
        elif self.round_highest_stake != 0:
            await self.bot.send_message(self.channel, "You can't use bet. Use \"k.raise\" to raise stake.")
            return

        # Set initial round's highest stake
        self.round_highest_stake = amount

        self.process_stake(player, amount, amount, PlayerStatus.BET)

        await self.get_next_player()

    async def make_raise(self, player: Player, amount: int):

        # Raise ON amount more than round's highest stake
        raise_amount = self.round_highest_stake + amount

        if player.balance + player.current_stake < raise_amount:
            await self.bot.send_message(self.channel, "You don't have enough money to raise stake.")
            return

        # Raise is always higher than round's highest stake
        self.round_highest_stake = raise_amount

        # Difference between raised amount and current stake
        amount_difference = raise_amount - player.current_stake

        self.process_stake(player, amount_difference, raise_amount, PlayerStatus.RAISED)

        await self.get_next_player()

    async def make_all_in(self, player: Player):

        if player.balance == 0:
            await self.bot.send_message(self.channel, "You don't have money to go all in.")
            return

        # Player's stake in current round must be sum of player's balance and his current stake
        player_stake = player.balance + player.current_stake

        # If this stake is higher than round's highest stake - set new round's highest stake
        if player_stake > self.round_highest_stake:
            self.round_highest_stake = player_stake

        self.process_stake(player, player.balance, player_stake, PlayerStatus.ALLIN)

        await self.get_next_player()

    def take_blind(self, players):

        SMALL_BLIND = 20
        BIG_BLIND = SMALL_BLIND + 20

        self.round_highest_stake = BIG_BLIND

        self.process_stake(players[0], SMALL_BLIND, SMALL_BLIND, PlayerStatus.BLINDED)
        self.process_stake(players[1], BIG_BLIND, BIG_BLIND, PlayerStatus.BLINDED)

        self.db_funcs.write_player_data(players[0])
        self.db_funcs.write_player_data(players[1])

    def check_players(self):

        # Check if player has balance lower than $100 and remove him from the game
        for player in self.table.players:
            if player.balance < 100:
                self.players.remove(player)
                self.table.players.remove(player)

        self.take_blind(self.table.players)

        # Deal cards
        self.table.dealer.deal_cards()
        # Set rotation
        self.table.rotation = deque(self.table.players)

    def add_player(self, author: discord.Member):

        balance = self.db_funcs.load_player_data(author)[3]

        player = Player(author, balance)

        self.players.append(player)

    def get_player(self, author: discord.Member):
        for player in self.players:
            if author.id == player.id:
                return player

        return None

    async def remove_player(self, player: Player):

        # If there are no players - the table will be destroyed
        self.players.remove(player)

        # Variables are uninitialized if game is not in process
        if self.status is not GameStatus.PENDING:
            # Remove player from rotation, but let him be in table, since we need him in pots calculations
            self.table.rotation.remove(player)
            # If rotation contains only 1 player - get last player and end the game.
            if player.status is PlayerStatus.THONKING or len(self.table.rotation) == 1:
                player.set_status(PlayerStatus.FOLDED)
                await self.get_next_player()

    def give_money(self, player: Player, amount: int):
        # Take money from the table bank
        self.table.withdraw_bank(amount)
        # Give them to player
        player.add_balance(amount)

        self.db_funcs.write_player_data(player)

    def set_status(self, status: GameStatus):
        self.status = status

    async def turn_timer_task(self, player: Player):
        try:
            # 20 seconds of inactivity
            while self.turn_counter < 90:
                self.turn_counter += 1
                await asyncio.sleep(1)
            else:
                # Don't forget to reset counter
                self.turn_counter = 0
                await self.remove_player(player)
                await self.bot.send_message(self.channel, "{} has been removed from table due to inactivity".format(player.user.mention))
        except asyncio.CancelledError:
            # And after task cancelling too
            self.turn_counter = 0

    async def get_table_info(self):

        embeded = discord.Embed(title='Table Info', description="Channel: {}".format(self.channel.name), color=0xEE8700)
        embeded.add_field(name="Total players:", value="{}/10".format(str(len(self.players))), inline=True)
        embeded.add_field(name="Game status:", value=self.status.name, inline=False)
        if self.table is not None:
            embeded.add_field(name="Table bank:", value="${}".format(self.table.bank), inline=False)
        for player in self.players:
            embeded.add_field(name=str(player), value="Balance: ${}\nStatus: {}".format(player.balance, player.status.name), inline=True)

        await self.bot.send_message(self.channel, embed=embeded)

    def get_available_actions(self, player: Player):
        msg = ""

        if player.balance >= self.round_highest_stake != 0:
            msg += "Raise stake - k.raise <amount>\n"
            msg += "Call to ${} - k.call\n".format(self.round_highest_stake)
            msg += "Go all-in - k.all-in\n"
            msg += "Fold - k.fold\n"
        elif player.balance > self.round_highest_stake == 0:
            msg += "Bet money - k.bet <amount>\n"
            msg += "Check - k.check\n"
            msg += "Go all-in - k.all-in\n"
            msg += "Fold - k.fold\n"
        elif player.balance == 0:
            msg += "Check - k.check\n"
            msg += "Fold - k.fold\n"
        elif player.balance < self.round_highest_stake:
            msg += "Go all-in - k.all-in\n"
            msg += "Fold - k.fold\n"

        return msg

    async def get_next_player(self):

        # Cancel timer
        if self.turn_timer is not None:
            self.turn_timer.cancel()

        # Get next round
        await self.get_next_round(self.table.rotation)

        # Avoid errors after setting GameStatus to PENDING
        if self.status is GameStatus.PENDING:
            return

        # Move out player
        player = self.table.rotation.popleft()

        # Put him in the end of rotation
        self.table.rotation.append(player)

        # Set turn timer
        self.turn_timer = self.bot.loop.create_task(self.turn_timer_task(player))

        # Set player status
        player.set_status(PlayerStatus.THONKING)

        actions = self.get_available_actions(player)

        await self.bot.send_message(self.channel, "{}'s turn.\n\n"
                                                  "**Available actions:**\n{}\n"
                                                  "Current table bank is: ${}".format(player.user.mention, actions, self.table.bank))

    async def set_next_round(self, status: GameStatus):

        self.table.get_dealer().place_cards()

        for player in self.table.rotation:
            # Reset states and nullify current stakes
            player.set_status(PlayerStatus.WAITING)
            player.current_stake = 0
            self.round_highest_stake = 0

            # Evaluate player's hand and let him know about his current combination
            rank = self.evaluator.evaluate(player.hand, self.table.cards)
            rank_class = self.evaluator.get_rank_class(rank)
            class_string = self.evaluator.class_to_string(rank_class)

            await self.bot.send_message(player.user, "Current combination: **{}**".format(class_string))

        self.set_status(status)

        cards = [deuces.Card.int_to_pretty_str(card) for card in self.table.cards]

        await self.bot.send_message(self.channel, "Cards on table:\n{}".format("\n".join(cards)))

    def reset_game(self):
        # Reset status
        self.set_status(GameStatus.PENDING)

        # Reset statuses, stakes and hands
        for player in self.players:
            player.set_status(PlayerStatus.WAITING)
            player.hand = []
            player.current_stake = 0
            player.total_stake = 0
            player.fold_position = 0

        # Nullify timer task
        self.turn_timer = None

        # Reset initial highest stake
        self.round_highest_stake = 0

        # Reset pot count
        self.pot_count = 0

        # Reset fold position
        self.fold_position = 0

        # Burn the table
        self.table = None

    def find_winners(self, players: list, pot: int):

        winners = []

        # NOTE: Lower value - higher rank
        best_rank = 7463  # Set rank lower than lowest possible hand (7462)

        str_pot = "main pot with amount of ${}".format(pot) if self.pot_count == 0 else "side pot {} with amount of ${}".format(self.pot_count, pot)

        for player in players:

            if player.status is PlayerStatus.FOLDED:
                continue

            rank = self.evaluator.evaluate(player.hand, self.table.cards)

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
            msg = "Player {} wins {} with {}.\n".format(winners[0].user.mention, str_pot, class_string)
            # Give pot to winner
            self.give_money(winners[0], pot)
        else:
            msg = "Players {} are tied for {} with {}.\n".format(", ".join(map(str, winners)), str_pot, class_string)
            # Return winners' stakes + win amount
            for winner in winners:
                win_amount = pot // len(winners)
                self.give_money(winner, winner.total_stake + win_amount)
        self.pot_count += 1

        return msg

    def calculate_pots(self, players: list):

        if len(players) == 1:
            self.give_money(players[0], players[0].total_stake)
            if players[0].total_stake == 0:
                return "\n"
            else:
                return "${} were returned to {}\n".format(players[0].total_stake, players[0].user.mention)

        lowest_stake = players[0].total_stake

        pot = lowest_stake * len(players)

        msg = self.find_winners(players, pot)

        for player in players:
            player.total_stake -= lowest_stake

        del players[0]

        return msg

    async def get_next_round(self, rotation: deque):

        # Before we check for next round we need to make sure it's necessary
        if len(rotation) == 1:
            last_player = rotation.popleft()
            self.give_money(last_player, self.table.bank)

            # Reset game
            self.reset_game()

            await self.bot.send_message(self.channel, "As the last man standing, {} wins and gets the bank!\n"
                                                      "Type \"k.start\" to start game again.".format(last_player.user.mention))
            return

        is_new_round = True

        for player in rotation:
            # We need to check if all stakes are equal to the highest one.
            # Except the case when player went all-in.
            if player.current_stake < self.round_highest_stake and player.balance != 0:
                player.set_status(PlayerStatus.WAITING)

            # And if we found player who is waiting and has non-zero balance - continue current round.
            if player.status is PlayerStatus.WAITING:
                is_new_round = False
                break

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

                # Sort players by total stakes
                compare = attrgetter("total_stake")
                players = list(self.table.players)
                players.sort(key=compare, reverse=False)

                # Calculate pots and distribute money
                msg = [self.calculate_pots(players) for _ in range(len(self.table.players))]

                # Collect players' hands and compile message
                players_cards = ""
                for player in rotation:

                    if player.status is PlayerStatus.FOLDED:
                        continue

                    cards = [deuces.Card.int_to_pretty_str(card) for card in player.hand]
                    players_cards += "{}'s hand: {}\n".format(player, " and ".join(cards))

                # Reset game
                self.reset_game()

                await self.bot.send_message(self.channel, "{}\n"
                                                          "**Players' hands:**\n{}\n"
                                                          "End of game. Type \"k.start\" to start the game again.".format("".join(msg), players_cards))


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
            record = (str(player), player.balance, player.user.id)
            self.db.execute("UPDATE poker_players SET name=?, balance=? WHERE user_id=?", record)
            self.db.commit()
        except sqlite3.Error as e:
            print(type(e).__name__)

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
    def claim_money(self, player):

        if type(player) is discord.Member:
            self.check_for_player(player)

        try:
            roll = randint(0, 100)
            if roll > 85:
                money_to_give = 10000
            elif roll > 50:
                money_to_give = 5000
            else:
                money_to_give = 1000

            next_day = 24 * 60 * 60
            record = ()

            if type(player) is Player:
                player.balance += money_to_give
                record = (str(player), player.balance, next_day, player.user.id)
            elif type(player) is discord.Member:
                player_balance = self.load_player_data(player)[3]
                player_balance += money_to_give
                record = (str(player), player_balance, next_day, player.id)

            self.db.execute("UPDATE poker_players SET name=?, balance=?, next_claim_time=strftime('%s','now') + ? WHERE user_id=?", record)
            self.db.commit()
        except sqlite3.Error as e:
            print(type(e).__name__)

    def give_money(self, sender, recipient, amount: int):

        if type(sender) is discord.Member:
            self.check_for_player(sender)
        if type(recipient) is discord.Member:
            self.check_for_player(recipient)

        sender_balance = self.load_player_data(sender)[3]

        if sender_balance < amount:
            return False

        self.take_money(sender, amount)

        try:
            record = ()

            if type(recipient) is Player:
                recipient.balance += amount
                record = (str(recipient), recipient.balance, recipient.user.id)
            elif type(recipient) is discord.Member:
                player_balance = self.load_player_data(recipient)[3]
                player_balance += amount
                record = (str(recipient), player_balance, recipient.id)

            self.db.execute("UPDATE poker_players SET name=?, balance=? WHERE user_id=?", record)
            self.db.commit()
        except sqlite3.Error as e:
            print(type(e).__name__)

        return True

    def take_money(self, sender, amount: int):

        try:
            record = ()

            if type(sender) is Player:
                sender.balance -= amount
                record = (str(sender), sender.balance, sender.user.id)
            elif type(sender) is discord.Member:
                player_balance = self.load_player_data(sender)[3]
                player_balance -= amount
                record = (str(sender), player_balance, sender.id)

            self.db.execute("UPDATE poker_players SET name=?, balance=? WHERE user_id=?", record)
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

        if server.id not in self.games:
            self.games.update({server.id: {}})

        if channel.id not in self.games[server.id]:
            return None

        return self.games[server.id][channel.id]

    # Don't allow player to participate in multiple games
    def player_lookup(self, player: discord.Member):

        for server, channel in self.games.items():
            for game in channel.values():
                found_player = game.get_player(player)
                if found_player is not None:
                    return found_player

        return None

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

        lookup_result = self.player_lookup(author)

        if lookup_result:
            await self.bot.say("You're not allowed to play in more than one game!")
            return

        player_balance = self.db_funcs.load_player_data(author)[3]

        if player_balance < 100:
            await self.bot.say("You don't have enough money to participate in game.")
            return

        game = GameDirector(self.bot, self.db_funcs, channel)
        game.add_player(author)

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
        Adds money to your balance in range of $1000 to $10000.
        You can claim prize only once in a day.
        """

        author = ctx.message.author
        cursor = self.bot.db.cursor()

        cursor.execute("SELECT * FROM poker_players WHERE next_claim_time > strftime('%s','now') and user_id=?", (author.id,))
        result = cursor.fetchone()
        cursor.close()

        if result:
            await self.bot.say("You have already claimed your daily prize today!")
            return

        # Since we can use this command in any other channel - look up player
        player = self.player_lookup(author)

        requester = player if player else author

        self.db_funcs.claim_money(requester)

        await self.bot.say("You have successfully claimed daily prize!")

    @commands.command(pass_context=True, no_pm=False)
    async def transfer(self, ctx, name: str, amount: int):
        """
        Transfer money to other player
        """

        if amount <= 0:
            await self.bot.say("Invalid amount.")
            return

        author = ctx.message.author

        members = await utils.get_members(self.bot, ctx.message, name)

        if members is None:
            return

        member = ctx.message.server.get_member_named(members[0])

        if member == author:
            await self.bot.say("You can't transfer money to yourself.")
            return

        # Same as in 'claim' command - get games and find players in them
        player_sender = self.player_lookup(author)
        player_recipient = self.player_lookup(member)

        sender = player_sender if player_sender else author
        recipient = player_recipient if player_recipient else member

        result = self.db_funcs.give_money(sender, recipient, amount)

        if not result:
            await self.bot.say("You don't have enough money to transfer.")
            return

        await self.bot.say("You've successfully transferred ${} to {}".format(amount, member.name))

    @commands.command(pass_context=True, no_pm=False, aliases=['bal'])
    async def balance(self, ctx):
        """
        Shows balance.
        """

        author = ctx.message.author

        player_balance = self.db_funcs.load_player_data(author)[3]
        await self.bot.say("Your balance is ${}".format(player_balance))

    # TODO: Game initiator, on ready start, or stay as is?
    @commands.command(pass_context=True, no_pm=True)
    async def start(self, ctx):
        """
        Start game.
        """

        server = ctx.message.server
        channel = ctx.message.channel
        author = ctx.message.author

        game = self.get_game(server, channel)

        if not game:
            await self.bot.say("There're no ongoing games. Start new by typing \"k.poker\"!")
            return

        player = game.get_player(author)

        if not player:
            await self.bot.say("You're not participating in this game!")
            return
        elif game.status is not GameStatus.PENDING:
            await self.bot.say("The game is in process.")
            return
        elif len(game.players) <= 1:
            await self.bot.say("You can't start game alone.")
            return

        game.create_table()
        game.set_status(GameStatus.PREFLOP)
        game.check_players()

        for player in game.players:
            cards = [deuces.Card.int_to_pretty_str(card) for card in player.hand]
            await self.bot.send_message(player.user, "Your cards are: {}".format(" and ".join(cards)))

        await self.bot.say("Setting up the table and starting the game!\n")

        await game.get_next_player()

    # Game actions
    async def is_action_allowed(self, player, game):
        if not player:
            await self.bot.say("You're not participating in this game!")
            return
        elif game.status is GameStatus.PENDING:
            await self.bot.say("Game is not running.")
            return
        elif player.status is not PlayerStatus.THONKING:
            await self.bot.say("You can't make any actions!")
            return

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

        if not self.is_action_allowed(player, game):
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

        if not self.is_action_allowed(player, game):
            return

        await game.make_call(player)

    @commands.command(pass_context=True, no_pm=True)
    async def bet(self, ctx, amount: int):
        """
        Open round with stake.
        """

        if amount <= 0:
            await self.bot.say("Invalid amount.")
            return

        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        game = self.get_game(server, channel)

        if not game:
            await self.bot.say("There're no ongoing games. Start new by typing \"k.poker\"!")
            return

        player = game.get_player(author)

        if not self.is_action_allowed(player, game):
            return

        await game.make_bet(player, amount)

    @commands.command(pass_context=True, no_pm=True, name='raise')
    async def raise_stake(self, ctx, amount: int):
        """
        Increase the amount of current stake ON given amount.
        """

        if amount <= 0:
            await self.bot.say("Invalid amount.")
            return

        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        game = self.get_game(server, channel)

        if not game:
            await self.bot.say("There're no ongoing games. Start new by typing \"k.poker\"!")
            return

        player = game.get_player(author)

        if not self.is_action_allowed(player, game):
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

        if not self.is_action_allowed(player, game):
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

        if not self.is_action_allowed(player, game):
            return

        await game.make_fold(player)


def setup(bot):
    bot.add_cog(Poker(bot))
