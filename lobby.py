from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import Collection, Generic, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field
from typing_extensions import Annotated

lobbies = {}


class CardNotInPlayerHandError(Exception):
    pass


class PlayerNotDealerError(Exception):
    pass


class PlayerNotOwnerError(Exception):
    pass


# class State(Enum):
#     MOVE = "move"
#     JUDGING = "judging"
#     PENDING_START = "pending start"
#     FINISHED = "finished"


class LobbyObserver:
    def owner_changed(self, player: Player):
        pass

    def player_disconnected(self, player: Player):
        pass

    def player_joined(self, player: Player):
        pass

    def player_left(self, player: Player):
        pass

    def player_connected(self, player: Player):
        pass

    def game_started(self, player: Player):
        pass

    def turn_started(
        self,
        setup: SetupCard,
        turn_duration: int | None,
        lead: Player,
        turn_count: int,
        card: PunchlineCard | None = None,
    ):
        pass

    def player_ready(self, player: Player):
        pass

    def table_card_opened(self, card_on_table: CardOnTable):
        pass

    def turn_ended(self, winner: Player, card: PunchlineCard):
        pass

    def all_players_ready(self):
        pass

    def game_finished(self, winner: Player):
        pass


@dataclass
class SetupCard:
    id: int
    text: str
    case: str
    starts_with_punchline: bool


@dataclass
class PunchlineCard:
    id: int
    text: list[tuple[str, list[str]]]


class Profile(BaseModel):
    name: str
    emoji: str
    background_color: str


class Player:
    observer: LobbyObserver
    uuid: str
    hand: list[PunchlineCard]
    score: int = 0
    profile: Profile
    is_ready = False
    is_connected: bool = False

    def __init__(self, profile: Profile) -> None:
        self.profile = profile
        self.hand = []
        self.uuid = uuid4().hex
        self.observer = LobbyObserver()

    def set_connected(self) -> None:
        self.is_connected = True

    def set_disconnected(self) -> None:
        self.observer = LobbyObserver()
        self.is_connected = False

    def add_punchline_card(self, card: PunchlineCard):
        self.hand.append(card)

    def __repr__(self) -> str:
        return f"Player({self.profile.name})"


class CardOnTable:
    card: PunchlineCard
    player: Player
    is_open: bool = False

    def __init__(self, card: PunchlineCard, player: Player) -> None:
        self.card = card
        self.player = player


AnyCard = TypeVar("AnyCard", bound=SetupCard | PunchlineCard)


class Deck(Generic[AnyCard]):
    def __init__(self, cards: list[AnyCard]) -> None:
        self.cards = cards
        self._dump = []
        self._shuffle()
        self.mapping = {card.id: card for card in cards}

    def get_card_by_uuid(self, card_id):
        return self.mapping[card_id]

    def _shuffle(self):
        random.shuffle(self.cards)

    def get_card(self) -> AnyCard:
        if not self.cards:
            self.cards, self._dump = self._dump, []
            self._shuffle()

        return self.cards.pop()

    def dump(self, cards: list[AnyCard]) -> None:
        self._dump.extend(cards)


class LobbySettings(BaseModel):
    turn_duration: int | None = 20
    winner_score: int | None = 10
    finish_delay: int | None = 5


class State:
    lobby: Lobby

    def choose_punchline_card(self, player: Player, card: PunchlineCard):
        raise Exception(
            f"method `choose_punchline_card` not expected in state {type(self).__name__}"
        )

    def open_punchline_card(self, player: Player, card_on_table: CardOnTable) -> None:
        raise Exception(
            f"method `open_punchline_card` not expected in state {type(self).__name__}"
        )

    def start_turn(self):
        raise Exception(
            f"method `pick_turn_winner` not expected in state {type(self).__name__}"
        )

    def pick_turn_winner(self, card: PunchlineCard):
        raise Exception(
            f"method `pick_turn_winner` not expected in state {type(self).__name__}"
        )

    def continue_game(self, player: Player) -> None:
        raise Exception(
            f"method `continue_game` not expected in state {type(self).__name__}"
        )


class Gathering(State):
    def start_game(self, player: Player, lobby_settings: LobbySettings) -> None:
        if player is not self.lobby.owner:
            raise PlayerNotOwnerError

        self.lobby.settings = lobby_settings
        for pl in self.lobby.all_players:
            for _ in range(self.lobby.HAND_SIZE):
                pl.add_punchline_card(self.lobby.punchlines.get_card())
            pl.observer.game_started(pl)

        self.start_turn()

    def start_turn(self):
        new_setup = self.lobby.setups.get_card()
        self.lobby.turn_count += 1
        self.lobby.transit_to(Turns(new_setup))
        for pl in self.lobby.all_players:
            pl.observer.turn_started(
                setup=new_setup,
                turn_duration=self.lobby.settings.turn_duration,
                lead=self.lobby.lead,
                turn_count=self.lobby.turn_count,
            )


class Turns(State):
    def __init__(self, setup: SetupCard):
        self.setup = setup

    def choose_punchline_card(self, player: Player, card: PunchlineCard) -> None:
        if card not in player.hand:
            raise CardNotInPlayerHandError

        self.lobby.table.append(CardOnTable(card=card, player=player))
        player.hand.remove(card)

        for pl in self.lobby.all_players:
            pl.observer.player_ready(player)

        if len(self.lobby.table) == len(self.lobby.players):
            self.lobby.transit_to(Judgement(self.setup))
            for pl in self.lobby.all_players:
                pl.observer.all_players_ready()


class Judgement(State):
    winner: Player | None

    def __init__(self, setup: SetupCard):
        self.setup = setup
        self.winner = None

    def open_punchline_card(self, player: Player, card_on_table: CardOnTable) -> None:
        if self.lobby.lead is not player:
            raise PlayerNotDealerError

        card_on_table.is_open = True
        for pl in self.lobby.all_players:
            pl.observer.table_card_opened(card_on_table)

    def pick_turn_winner(self, card) -> None:
        # TODO: проверять что только лид это может
        card_on_table = self.lobby.get_card_from_table(card=card)
        card_on_table.player.score += 1

        self.winner = card_on_table.player

        for pl in self.lobby.all_players:
            pl.observer.turn_ended(card_on_table.player, card)

        self.lobby.punchlines.dump(
            [card_in_table.card for card_in_table in self.lobby.table]
        )
        self.lobby.table = []

        async def finish_game(winner: Player):
            await asyncio.sleep(self.lobby.settings.finish_delay)
            self.finish_game(winner)

        for pl in self.lobby.players:
            if pl.score == self.lobby.settings.winner_score:
                asyncio.create_task(finish_game(pl))
                return

        async def start_turn():
            await asyncio.sleep(5)
            self.start_turn()

        asyncio.create_task(start_turn())

    def start_turn(self):
        previous_lead = self.lobby.lead
        self.lobby.change_lead()
        self.lobby.setups.dump([self.setup])

        new_setup = self.lobby.setups.get_card()
        self.lobby.turn_count += 1
        self.lobby.transit_to(Turns(new_setup))
        for pl in self.lobby.all_players_except(previous_lead):
            new_card = self.lobby.punchlines.get_card()
            pl.add_punchline_card(new_card)
            pl.observer.turn_started(
                setup=new_setup,
                turn_duration=self.lobby.settings.turn_duration,
                lead=self.lobby.lead,
                card=new_card,
                turn_count=self.lobby.turn_count,
            )
        previous_lead.observer.turn_started(
            setup=new_setup,
            turn_duration=self.lobby.settings.turn_duration,
            lead=self.lobby.lead,
            turn_count=self.lobby.turn_count,
        )

    def finish_game(self, winner: Player):
        for pl in self.lobby.all_players:
            pl.observer.game_finished(winner)

        self.lobby.transit_to(Finished(winner))


class Finished(State):
    def __init__(self, winner: Player):
        self.winner = winner

    def start_turn(self):
        previous_lead = self.lobby.lead
        self.lobby.change_lead()
        self.lobby.setups.dump([self.setup])

        new_setup = self.lobby.setups.get_card()
        self.lobby.turn_count += 1
        self.lobby.transit_to(Turns(new_setup))
        for pl in self.lobby.all_players_except(previous_lead):
            new_card = self.lobby.punchlines.get_card()
            pl.add_punchline_card(new_card)
            pl.observer.turn_started(
                setup=new_setup,
                turn_duration=self.lobby.settings.turn_duration,
                lead=self.lobby.lead,
                card=new_card,
                turn_count=self.lobby.turn_count,
            )
        previous_lead.observer.turn_started(
            setup=new_setup,
            turn_duration=self.lobby.settings.turn_duration,
            lead=self.lobby.lead,
            turn_count=self.lobby.turn_count,
        )

    def continue_game(self, player: Player) -> None:
        if player is not self.lobby.owner:
            raise PlayerNotOwnerError

        self.start_turn()


class Lobby:
    uid: uuid4
    players: list[Player]
    lead: Player
    owner: Player | None
    table: list[CardOnTable]
    punchlines: Deck[PunchlineCard]
    setups: Deck[SetupCard]
    observer: LobbyObserver
    settings: LobbySettings
    turn_count: int

    HAND_SIZE = 10

    def __init__(
        self,
        players: Collection[Player],
        lead: Player,
        owner: Player,
        setups: Deck[SetupCard],
        punchlines: Deck[PunchlineCard],
        state: Gathering,
    ) -> None:
        self.players = list(players)
        self.lead = lead
        self.owner = owner
        self.table = []
        self.uid = uuid4()
        self.punchlines = punchlines
        self.setups = setups
        self.settings = LobbySettings()
        self.state = state
        self.state.lobby = self
        self.turn_count = 0

    @property
    def all_players(self):
        return [self.lead, *self.players]

    def all_players_except(self, player: Player):
        return [p for p in self.all_players if p is not player]

    def get_selected_card(self, player: Player) -> PunchlineCard | None:
        for card_on_tabel in self.table:
            if card_on_tabel.player is player:
                return card_on_tabel.card
        return None

    def change_owner(self) -> None:
        self.owner = None
        for player in self.players:
            if player.is_connected:
                self.owner = player

    def transit_to(self, new_state: State) -> None:
        self.state = new_state
        self.state.lobby = self

    def change_lead(self) -> None:
        self.players.append(self.lead)
        self.lead = self.players.pop(0)

    def get_card_from_table(self, card) -> CardOnTable:
        for card_on_table in self.table:
            if card is card_on_table.card:
                return card_on_table
        raise NotImplemented

    def set_connected(self, player: Player):
        player.set_connected()
        if not self.owner:
            self.owner = player
        for pl in self.all_players_except(player):
            pl.observer.player_connected(player)

    def set_disconnected(self, player: Player):
        was_owner = False

        player.set_disconnected()
        if player is self.owner:
            was_owner = True
            self.change_owner()

        for pl in self.all_players_except(player):
            pl.observer.player_disconnected(player)
            if was_owner:
                pl.observer.owner_changed(player)
        # обработать если осталось менее 2 игроков

    def add_player(self, player: Player):
        for pl in self.all_players:
            pl.observer.player_joined(player)
        self.players.append(player)

    # def remove_player(self, player: Player):
    #     for pl in self._all_players_except(player):
    #         pl.observer.player_left(player)
    #     self.players.remove(player)
