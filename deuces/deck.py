from random import shuffle
from deuces.card import Card
from collections import deque


class Deck:
    """
    Class representing a deck. The first time we create, we seed the static
    deck with the list of unique card integers. Each object instantiated simply
    makes a copy of this object and shuffles it.
    """

    def __init__(self):

        self.deck = deque()

        for rank in Card.STR_RANKS:
            for suit, val in Card.CHAR_SUIT_TO_INT_SUIT.items():
                self.deck.append(Card.new(rank + suit))

        shuffle(self.deck)

    def draw(self, amount: int):
        return [self.get_card() for _ in range(amount)]

    def get_card(self):
        return self.deck.popleft()
