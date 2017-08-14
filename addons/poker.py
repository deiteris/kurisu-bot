from random import shuffle as rshuffle
from discord.ext import commands
from enum import Enum, auto
from collections import deque


class GameStatus(Enum):
    PENDING = auto()
    PREFLOP = auto()
    FLOP = auto()
    TURN = auto()
    RIVER = auto()


class PlayerStatus(Enum):
    WAITING = auto()
    CALLED = auto()
    CHECKED = auto()
    BET = auto()
    RAISED = auto()
    ALLIN = auto()
    THONKING = auto()
    FOLDED = auto()


class Card:

    value_names = (
        'none', 'none',
        ':two:', ':three:', ':four:', ':five:',
        ':six:', ':seven:', ':eight:', ':nine:',
        ':keycap_ten:', ':regional_indicator_j:',
        ':regional_indicator_q:', ':regional_indicator_k:',
        ':regional_indicator_a:'
    )

    suit_names = (
        ':clubs:', ':diamonds:',
        ':hearts:', ':spades:'
    )

    class Value(Enum):
        TWO = 2
        THREE = 3
        FOUR = 4
        FIVE = 5
        SIX = 6
        SEVEN = 7
        EIGHT = 8
        NINE = 9
        TEN = 10
        JACK = 11
        QUEEN = 12
        KING = 13
        ACE = 14

        def __str__(self):
            return Card.value_names[self.value]

    class Suit(Enum):
        CLUBS = 0
        DIAMONDS = 1
        HEARTS = 2
        SPADES = 3

        def __str__(self):
            return Card.suit_names[self.value]

    def __init__(self, value, suit):
        self.value = value
        self.suit = suit

    def __str__(self):
        return "{} of {}".format(self.value, self.suit)


class Deck:

    def __init__(self):

        self.deck = deque()

        for suit in Card.Suit:
            for value in Card.Value:
                self.deck.append(Card(value, suit))

    def draw(self, amount: int):
        cards = []
        for card in range(amount):
            cards.append(self.deck.pop())

        return cards

    def shuffle(self):
        rshuffle(self.deck)

    def get_card(self):
        return self.deck.popleft()


class Dealer:

    def __init__(self, players, table):
        self.deck = Deck()
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


# TODO: Players database
class Player:

    def __init__(self, player_id, user, status):
        self.id = player_id
        self.user = user
        self.status = status
        self.hand = []
        self.current_stake = 20
        self.balance = 5000  # TODO: Balance

    def add_balance(self, amount):
        self.balance += amount

    def withdraw_balance(self, amount):
        self.balance -= amount

    def set_status(self, status):
        self.status = status

    def set_current_stake(self, stake):
        self.current_stake = stake


class Table:

    def __init__(self):
        self.players = None
        self.deck = None
        self.dealer = None
        self.cards = []
        self.bank = 0

    def get_bank(self):
        return self.bank

    def add_bank(self, amount):
        self.bank += amount

    def set_players(self, players):
        self.players = players

    def set_dealer(self):
        self.dealer = Dealer(self.players, self)

    def get_dealer(self):
        return self.dealer


class GameDirector:

    def __init__(self, bot, channel, status):
        self.players = deque()
        self.rotation = deque()
        self.table = None
        self.channel = channel
        self.status = status
        self.highest_stake = 40
        self.current_player = None
        self.bot = bot

    def create_table(self):
        self.table = Table()

    def process_stake(self, player, amount, stake, status):
        player.withdraw_balance(amount)
        self.table.add_bank(amount)

        player.set_current_stake(stake)

        player.set_status(status)

    async def make_check(self, player):
        player.set_status(PlayerStatus.CHECKED)

        await self.get_next_player()

    async def make_call(self, player):

        if self.highest_stake == 0:
            await self.make_check(player)
            return True

        if player.balance < self.highest_stake:
            return False

        amount_difference = self.highest_stake - player.current_stake

        self.process_stake(player, amount_difference, self.highest_stake, PlayerStatus.CALLED)

        await self.get_next_player()

        return True

    async def make_bet(self, player, amount):

        if player.balance < amount or self.highest_stake != 0:
            return False

        self.highest_stake = amount

        self.process_stake(player, amount, amount, PlayerStatus.BET)

        await self.get_next_player()

        return True

    async def make_raise(self, player, amount):

        # (Highest Stake - Player Current Stake) + amount
        # (100 - 0) + 100 = 200 = PROFIT
        raise_amount = (self.highest_stake - player.current_stake) + amount

        # if self.highest_stake == 0:
        #    await self.make_bet(player, amount)
        #    return True

        if player.balance < raise_amount:
            return False

        self.highest_stake = raise_amount

        amount_difference = raise_amount - self.highest_stake

        self.process_stake(player, amount_difference, raise_amount, PlayerStatus.RAISED)

        await self.get_next_player()

        return True

    async def make_all_in(self, player):

        if player.balance == 0:
            return False

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

        return True

    async def make_fold(self, player):
        player.set_status(PlayerStatus.FOLDED)
        self.rotation.remove(player)

        await self.get_next_player()

        return True

    def take_blind(self):
        for player in self.players:
            player.withdraw_balance(20)
            player.set_current_stake(20)
            self.table.add_bank(20)

    def get_table_bank(self):
        return self.table.get_bank()

    def get_players(self):
        return self.players

    def set_players(self):
        # Copy players array to rotation
        self.rotation = deque(self.players)
        # TODO: Make rotation order according to rules
        self.table.set_players(self.rotation)

        self.current_player = self.rotation.popleft()
        self.rotation.append(self.current_player)
        self.current_player.set_status(PlayerStatus.THONKING)

    def add_player(self, player):
        self.players.append(player)

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
            if player is self.current_player:
                await self.get_next_player()
                # Gets dereferenced
                # self.table.players.remove(player)

    def set_status(self, status):
        self.status = status

    async def get_next_player(self):

        if not self.rotation:
            if not self.players:
                return
            money = self.get_table_bank() // len(self.players)
            print(money)
            for player in self.players:
                player.add_balance(money)
                player.hand = []
            self.set_status(GameStatus.PENDING)
            await self.bot.send_message(self.channel, "Everyone has folded. Table bank will be distributed among all players.\n"
                                                      "Type \"/start\" to start game again.")
            return
        elif len(self.rotation) == 1:
            last_player = self.rotation.popleft()
            for player in self.players:
                player.hand = []
            last_player.add_balance(self.get_table_bank())
            self.set_status(GameStatus.PENDING)
            await self.bot.send_message(self.channel, "As the last man standing, {} wins and gets the bank!\n"
                                                      "Type \"/start\" to start game again.".format(last_player.user.name))
            return

        # Get next round
        await self.get_next_round()

        # Move out player
        player = self.rotation.popleft()
        # If player has any other status than WAITING - pick next one
        if player.status is not PlayerStatus.WAITING:
            player = self.rotation.popleft()
        # Put him in the end of rotation
        self.rotation.append(player)
        # Set player status
        player.set_status(PlayerStatus.THONKING)

        self.current_player = player

    async def set_next_round(self, status):
        for player in self.rotation:
            # Reset states and nullify current stakes
            player.set_status(PlayerStatus.WAITING)
            player.set_current_stake(0)
            self.highest_stake = 0

        self.set_status(status)
        self.table.get_dealer().place_cards()

        cards = []
        for card in self.table.cards:
            cards.append(str(card))

        await self.bot.send_message(self.channel, "Cards on table:\n{}".format("\n".join(cards)))

    async def get_next_round(self):
        found = False

        for player in self.rotation:
            if player.current_stake < self.highest_stake:
                player.set_status(PlayerStatus.WAITING)
            if player.status is PlayerStatus.WAITING and player.balance != 0:
                found = True

        if not found:

            if self.status is GameStatus.PREFLOP:
                await self.set_next_round(GameStatus.FLOP)
            elif self.status is GameStatus.FLOP:
                await self.set_next_round(GameStatus.TURN)
            elif self.status is GameStatus.TURN:
                await self.set_next_round(GameStatus.RIVER)
            elif self.status is GameStatus.RIVER:

                # Update game status
                self.set_status(GameStatus.PENDING)

                # TODO: Combinations, comparison, prize distribution

                # Compile end game message
                msg = "Players' cards:\n"
                for player in self.rotation:
                    cards = []
                    for card in player.hand:
                        cards.append(str(card))
                    msg += "{}'s hand: {}\n".format(player.user.name, " and ".join(cards))
                    player.hand = []
                msg += "End of game. Type \"/start\" to start game again."

                # Reset rotation
                self.rotation = deque()

                await self.bot.send_message(self.channel, msg)


class Poker:
    """
    Poker game commands
    """

    def __init__(self, bot):
        self.bot = bot
        self.game = {}

    def get_game(self, server, channel):

        if len(self.game) == 0:
            return None

        if server.id in self.game:
            print('Found server!')
            print('Server: {}'.format(server.name))
        else:
            return None

        if channel.id in self.game[server.id]:
            print('Found channel!')
            print('Channel: {}'.format(channel.name))
        else:
            return None

        return self.game[server.id][channel.id]

    # General actions
    @commands.command(pass_context=True, no_pm=True)
    async def poker(self, ctx):
        """Initializes poker game"""

        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        game = self.get_game(server, channel)

        if game:
            await self.bot.say("There's ongoing game! Type \"/join\" to join the table!")
            return

        self.game.update({server.id: {channel.id: GameDirector(self.bot, channel, GameStatus.PENDING)}})

        print("Game created!")
        print("Game object: {}".format(self.game[server.id][channel.id]))

        self.game[server.id][channel.id].add_player(Player(author.id, author, PlayerStatus.WAITING))

        print("Players initiated!")
        print("Total players: {}".format(self.game[server.id][channel.id].players))

        await self.bot.say("{} has initiated new game! Type \"/join\" to join table!".format(author.name))

    @commands.command(pass_context=True, no_pm=True)
    async def join(self, ctx):
        """Join game"""

        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        game = self.get_game(server, channel)

        if not game:
            await self.bot.say("There're no ongoing games. Start new by typing \"/poker\"!")
            return

        player = game.get_player(author)

        if player:
            await self.bot.say("You're playing this game!")
            return

        if len(game.players) == 10:
            await self.bot.say("Table limit is 10 people.")
            return

        game.add_player(Player(author.id, author, PlayerStatus.WAITING))

        print("Players updated!")
        print("Total players: {}".format(self.game[server.id][channel.id].players))

        await self.bot.say("{} has joined the game!".format(author.name))

    @commands.command(pass_context=True, no_pm=True)
    async def leave(self, ctx):
        """Leave game"""

        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        game = self.get_game(server, channel)

        if not game:
            await self.bot.say("There're no ongoing games. Start new by typing \"/poker\"!")
            return

        player = game.get_player(author)

        if not player:
            await self.bot.say("You're not playing in this game!")
            return

        await game.remove_player(player)

        await self.bot.say("You've left the game.")

        if not game.players:
            del self.game[server.id][channel.id]
            await self.bot.say("Table is empty! (╯°□°）╯︵ ┻━┻")

    # TODO: Make players database
    @commands.command(pass_context=True, no_pm=True)
    async def balance(self, ctx):
        """Shows balance (WIP)"""

        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        game = self.get_game(server, channel)

        if not game:
            await self.bot.say("There're no ongoing games. Start new by typing \"/poker\"!")
            return

        player = game.get_player(author)

        if not player:
            await self.bot.say("You're not playing in this game!")
            return

        dm = server.get_member(author.id)
        await self.bot.send_message(dm, "Your current balance {}$".format(player.balance))

    @commands.command(pass_context=True, no_pm=True)
    async def start(self, ctx):
        """Start game"""

        server = ctx.message.server
        channel = ctx.message.channel

        game = self.get_game(server, channel)

        if not game:
            await self.bot.say("There're no ongoing games. Start new by typing \"/poker\"!")
            return

        if game.status is not GameStatus.PENDING:
            await self.bot.say("The game is in process.")
            return

        if len(game.get_players()) <= 1:
            await self.bot.say("You can't start game alone.")
            return

        game.create_table()
        game.set_status(GameStatus.PREFLOP)
        game.set_players()
        game.table.set_dealer()
        game.table.get_dealer().deck.shuffle()
        game.take_blind()
        game.table.get_dealer().distribute_cards()

        for player in game.players:
            cards = []
            for card in player.hand:
                cards.append(str(card))
            await self.bot.send_message(player.user, "Your cards are: {}".format(" and ".join(cards)))

        await self.bot.say("The game has started!\n{}'s turn\nCurrent table bank is: {}$".format(game.current_player.user.name, game.get_table_bank()))

    # Game actions
    @commands.command(pass_context=True, no_pm=True)
    async def check(self, ctx):

        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        game = self.get_game(server, channel)

        if not game:
            await self.bot.say("There're no ongoing games. Start new by typing \"/poker\"!")
            return

        player = game.get_player(author)

        if not player:
            await self.bot.say("You're not playing in this game!")
            return

        if player.status is PlayerStatus.WAITING or player.status is PlayerStatus.FOLDED:
            await self.bot.say("You can't make any actions!")
            return

        if game.status is GameStatus.PREFLOP:
            await self.bot.say("You can't check during pre-flop round.")
            return

        await game.make_check(player)

        await self.bot.say("{}'s turn.".format(game.current_player.user.name))

    @commands.command(pass_context=True, no_pm=True)
    async def call(self, ctx):

        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        game = self.get_game(server, channel)

        if not game:
            await self.bot.say("There're no ongoing games. Start new by typing \"/poker\"!")
            return

        player = game.get_player(author)

        if not player:
            await self.bot.say("You're not playing in this game!")
            return

        if player.status is PlayerStatus.WAITING or player.status is PlayerStatus.FOLDED:
            await self.bot.say("You can't make any actions!")
            return

        result = await game.make_call(player)

        if not result:
            await self.bot.say("You don't have enough money to make call.")
        else:
            await self.bot.say("{}'s turn.\nCurrent table bank is: {}$".format(game.current_player.user.name, game.get_table_bank()))

    @commands.command(pass_context=True, no_pm=True)
    async def bet(self, ctx, amount: int):

        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        game = self.get_game(server, channel)

        if not game:
            await self.bot.say("There're no ongoing games. Start new by typing \"/poker\"!")
            return

        player = game.get_player(author)

        if not player:
            await self.bot.say("You're not playing in this game!")
            return

        if player.status is PlayerStatus.WAITING or player.status is PlayerStatus.FOLDED:
            await self.bot.say("You can't make any actions!")
            return

        if game.status is GameStatus.PREFLOP:
            await self.bot.say("You can't bet during pre-flop round.")
            return

        result = await game.make_bet(player, amount)

        if not result:
            await self.bot.say("You don't have enough money to make bet or use \"/raise\" to increase stake.")
        else:
            await self.bot.say("{}'s turn.\nCurrent table bank is: {}$".format(game.current_player.user.name, game.get_table_bank()))

    @commands.command(pass_context=True, no_pm=True, name='raise')
    async def raise_stake(self, ctx, amount: int):

        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        game = self.get_game(server, channel)

        if not game:
            await self.bot.say("There're no ongoing games. Start new by typing \"/poker\"!")
            return

        player = game.get_player(author)

        if not player:
            await self.bot.say("You're not playing in this game!")
            return

        if player.status is PlayerStatus.WAITING or player.status is PlayerStatus.FOLDED:
            await self.bot.say("You can't make any actions!")
            return

        result = await game.make_raise(player, amount)

        if not result:
            await self.bot.say("You don't have enough money to raise stake.")
        else:
            await self.bot.say("{}'s turn.\nCurrent table bank is: {}$".format(game.current_player.user.name, game.get_table_bank()))

    @commands.command(pass_context=True, no_pm=True, name='all-in')
    async def all_in(self, ctx):

        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        game = self.get_game(server, channel)

        if not game:
            await self.bot.say("There're no ongoing games. Start new by typing \"/poker\"!")
            return

        player = game.get_player(author)

        if not player:
            await self.bot.say("You're not playing in this game!")
            return

        if player.status is PlayerStatus.WAITING or player.status is PlayerStatus.FOLDED:
            await self.bot.say("You can't make any actions!")
            return

        result = await game.make_all_in(player)

        if not result:
            await self.bot.say("You don't have enough money to go all in.")
        else:
            await self.bot.say("{}'s turn.\nCurrent table bank is: {}$".format(game.current_player.user.name, game.get_table_bank()))

    @commands.command(pass_context=True, no_pm=True)
    async def fold(self, ctx):

        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        game = self.get_game(server, channel)

        if not game:
            await self.bot.say("There're no ongoing games. Start new by typing \"/poker\"!")
            return

        player = game.get_player(author)

        if not player:
            await self.bot.say("You're not playing in this game!")
            return

        if player.status is PlayerStatus.WAITING or player.status is PlayerStatus.FOLDED:
            await self.bot.say("You can't make any actions!")
            return

        result = await game.make_fold(player)

        if not result:
            await self.bot.say("{}'s turn.".format(game.current_player.user.name))


def setup(bot):
    bot.add_cog(Poker(bot))
