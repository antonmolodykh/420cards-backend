from __future__ import annotations

import asyncio
import random
from asyncio import Task
from dataclasses import dataclass
from typing import Generic, TypeVar
from uuid import uuid4

from pydantic import BaseModel

lobbies = {}


class CardNotInPlayerHandError(Exception):
    pass


class PlayerNotLeadError(Exception):
    pass


class PlayerNotOwnerError(Exception):
    pass


class NotAllCardsOpenedError(Exception):
    pass


class UnknownPlayerError(Exception):
    pass


class PlayerAlreadyReadyError(Exception):
    pass


class ScoreTooLowError(Exception):
    pass


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

    def welcome(self):
        pass

    def hand_refreshed(self, new_hand: list[PunchlineCard]) -> None:
        pass

    def player_score_changed(self, player: Player) -> None:
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


class Player:
    observer: LobbyObserver
    lobby: Lobby
    uuid: str
    hand: list[PunchlineCard]
    score: int = 0
    profile: Profile
    token: str
    is_ready = False
    is_connected: bool = False

    def __init__(self, profile: Profile, token: str) -> None:
        self.profile = profile
        self.token = token
        self.hand = []
        self.uuid = uuid4().hex
        self.observer = LobbyObserver()

    def connect(self, observer: LobbyObserver) -> None:
        self.lobby.connect(self)
        self.is_connected = True
        self.observer = observer
        observer.welcome()

    def disconnect(self) -> None:
        self.observer = LobbyObserver()
        self.is_connected = False
        self.lobby.disconnect(self)

    def add_punchline_card(self, card: PunchlineCard):
        self.hand.append(card)

    def start_game(
        self,
        settings: LobbySettings,
        setups: Deck[SetupCard],
        punchlines: Deck[PunchlineCard],
    ) -> None:
        self.lobby.state.start_game(
            player=self,
            lobby_settings=settings,
            setups=setups,
            punchlines=punchlines,
        )

    def refresh_hand(self) -> None:
        self.lobby.state.refresh_hand(self)

    def make_turn(self, card: PunchlineCard) -> CardOnTable:
        self.lobby.state.make_turn(self, card)
        return self.lobby.get_card_from_table(card)

    def open_table_card(self, card_on_table: CardOnTable) -> None:
        self.lobby.state.open_table_card(self, card_on_table)

    def pick_turn_winner(self, card: PunchlineCard) -> None:
        self.lobby.state.pick_turn_winner(self, card)

    def continue_game(self) -> None:
        self.lobby.state.continue_game(self)

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
    turn_duration: int | None = None
    winning_score: int
    finish_delay: int = 5
    start_turn_delay: int = 5


class State:
    lobby: Lobby

    def remove_player(self, player: Player) -> None:
        pass

    def make_turn(self, player: Player, card: PunchlineCard) -> None:
        raise Exception(
            f"method `make_turn` not expected in state {type(self).__name__}"
        )

    def open_table_card(self, player: Player, card_on_table: CardOnTable) -> None:
        raise Exception(
            f"method `open_punchline_card` not expected in state {type(self).__name__}"
        )

    def start_turn(self):
        raise Exception(
            f"method `start_turn` not expected in state {type(self).__name__}"
        )

    def pick_turn_winner(self, player: Player, card: PunchlineCard):
        raise Exception(
            f"method `pick_turn_winner` not expected in state {type(self).__name__}"
        )

    def continue_game(self, player: Player) -> None:
        raise Exception(
            f"method `continue_game` not expected in state {type(self).__name__}"
        )

    def end_turn(self):
        raise Exception(
            f"method `end_turn` not expected in state {type(self).__name__}"
        )

    def refresh_hand(self, player: Player):
        raise Exception(
            f"method `refresh_hand` not expected in state {type(self).__name__}"
        )


class Gathering(State):
    def start_game(
        self,
        player: Player,
        lobby_settings: LobbySettings,
        setups: Deck[SetupCard],
        punchlines: Deck[PunchlineCard],
    ) -> None:
        if player is not self.lobby.owner:
            raise PlayerNotOwnerError

        self.lobby.setups = setups
        self.lobby.punchlines = punchlines

        self.lobby.settings = lobby_settings
        for pl in self.lobby.all_players:
            for _ in range(self.lobby.HAND_SIZE):
                pl.add_punchline_card(self.lobby.punchlines.get_card())
            pl.observer.game_started(pl)

        self.lobby.start_turn()


class Turns(State):
    def __init__(self, setup: SetupCard, timer: Task):
        self.setup = setup
        self.timer = timer

    def remove_player(self, player: Player) -> None:
        self.try_end_turn()

    def make_turn(self, player: Player, card: PunchlineCard) -> None:
        self.put_card_on_table(player, card)
        self.try_end_turn()

    def try_end_turn(self) -> None:
        for pl in self.lobby.players:
            if pl.is_connected and not pl.is_ready:
                return

        self.timer.cancel()
        self.end_turn()

    def end_turn(self):
        for player in self.lobby.players:
            if player.is_connected and not player.is_ready:
                self.put_card_on_table(player, random.choice(player.hand))

        random.shuffle(self.lobby.table)
        for pl in self.lobby.all_players:
            pl.observer.all_players_ready()

        if self.lobby.lead:
            self.lobby.transit_to(Judgement(self.setup))
        else:
            # self.lobby.transit_to(Voting(self.setup))
            # TODO: make turn, return table
            raise NotImplementedError

    def put_card_on_table(self, player: Player, card: PunchlineCard) -> None:
        if card not in player.hand:
            raise CardNotInPlayerHandError

        if prev_card := self.lobby.card_on_table_of(player):
            self.lobby.table.remove(prev_card)
            player.hand.append(prev_card.card)

        self.lobby.table.append(CardOnTable(card=card, player=player))
        player.hand.remove(card)
        player.is_ready = True
        for pl in self.lobby.all_players:
            pl.observer.player_ready(player)

    def refresh_hand(self, player: Player) -> None:
        if player.is_ready:
            raise PlayerAlreadyReadyError()

        new_hand = [
            self.lobby.punchlines.get_card() for _ in range(self.lobby.HAND_SIZE)
        ]
        self.lobby.punchlines.dump(player.hand)
        player.hand = new_hand

        if player.score < 0:
            raise ScoreTooLowError()
        player.score -= 1

        player.observer.hand_refreshed(new_hand)
        for pl in self.lobby.all_players:
            pl.observer.player_score_changed(player)


class Judgement(State):
    winner: Player | None

    def __init__(self, setup: SetupCard):
        self.setup = setup
        self.winner = None

    def remove_player(self, player: Player) -> None:
        if player is self.lobby.lead:
            self.start_voting()

    def start_voting(self):
        # self.lobby.transit_to(Voting(self.setup))
        # TODO: make turn, dump table
        raise NotImplementedError

    def open_table_card(self, player: Player, card_on_table: CardOnTable) -> None:
        if self.lobby.lead is not player:
            raise PlayerNotLeadError

        card_on_table.is_open = True
        for pl in self.lobby.all_players:
            pl.observer.table_card_opened(card_on_table)

    def pick_turn_winner(self, player, card) -> None:
        if player is not self.lobby.lead:
            raise PlayerNotLeadError

        for card_on_table in self.lobby.table:
            if not card_on_table.is_open:
                raise NotAllCardsOpenedError

        card_on_table = self.lobby.get_card_from_table(card=card)
        card_on_table.player.score += 1

        self.winner = card_on_table.player

        for pl in self.lobby.all_players:
            pl.observer.turn_ended(card_on_table.player, card)

        self.lobby.punchlines.dump(
            [card_on_table.card for card_on_table in self.lobby.table]
        )
        self.lobby.table = []

        async def finish_game(winner: Player):
            await asyncio.sleep(self.lobby.settings.finish_delay)
            self.finish_game(winner)

        if not self.lobby.is_game_endless:
            for pl in self.lobby.players:
                if pl.score == self.lobby.settings.winning_score:
                    asyncio.create_task(finish_game(pl))
                    return

        async def start_turn():
            await asyncio.sleep(self.lobby.settings.start_turn_delay)
            self.start_turn()

        asyncio.create_task(start_turn())

    def start_turn(self):
        self.lobby.setups.dump([self.setup])
        self.lobby.start_turn()

    def finish_game(self, winner: Player):
        for pl in self.lobby.all_players:
            pl.observer.game_finished(winner)

        self.lobby.transit_to(Finished(winner, self.setup))


class Finished(State):
    def __init__(self, winner: Player, setup: SetupCard):
        self.setup = setup
        self.winner = winner

    def start_turn(self):
        self.lobby.setups.dump([self.setup])
        self.lobby.start_turn()

    def continue_game(self, player: Player) -> None:
        if player is not self.lobby.owner:
            raise PlayerNotOwnerError

        self.lobby.is_game_endless = True
        self.start_turn()

    def start_game(
        self,
        player: Player,
        lobby_settings: LobbySettings,
        setups: Deck[SetupCard],
        punchlines: Deck[PunchlineCard],
    ) -> None:
        self.lobby.table.clear()
        self.lobby.turn_count = 0

        for pl in self.lobby.all_players:
            pl.hand.clear()
            pl.score = 0

        self.lobby.transit_to(Gathering())
        player.start_game(lobby_settings, setups, punchlines)


class Lobby:
    uid: uuid4
    players: list[Player]
    lead: Player | None
    owner: Player
    table: list[CardOnTable]
    grave: set[Player]
    punchlines: Deck[PunchlineCard]
    setups: Deck[SetupCard]
    observer: LobbyObserver
    settings: LobbySettings
    turn_count: int
    is_game_endless: bool = False

    HAND_SIZE = 10

    def __init__(
        self,
        settings: LobbySettings,
        owner: Player,
        setups: Deck[SetupCard],
        punchlines: Deck[PunchlineCard],
        state: Gathering,
    ) -> None:
        self.players = []
        self.lead = None
        self.owner = owner
        self.table = []
        self.grave = set()
        self.uid = uuid4()
        self.punchlines = punchlines
        self.setups = setups
        self.settings = settings
        self.state = state
        self.state.lobby = self
        self.turn_count = 0

    @property
    def all_players(self):
        if not self.lead:
            return self.players
        return [self.lead, *self.players]

    def all_players_except(self, player: Player):
        return [p for p in self.all_players if p is not player]

    def card_on_table_of(self, player: Player) -> CardOnTable | None:
        for card_on_tabel in self.table:
            if card_on_tabel.player is player:
                return card_on_tabel
        return None

    def change_owner(self) -> None:
        # TODO: Что делать, если не осталось игроков?
        self.owner = None  # это поле не nullable
        for player in self.all_players:
            if player.is_connected:
                self.owner = player
                return

    def transit_to(self, new_state: State) -> None:
        # TODO: Исправить, стейты зависят от лобби но могут оказаться без него
        # Также лобби не доступно в конструкторах стейтов
        self.state = new_state
        self.state.lobby = self

    def change_lead(self) -> None:
        # TODO: можем на дисконектнутого смениться?
        # TODO: Выбирать, нужен ли лид по режиму игры
        if self.lead:
            self.players.append(self.lead)
        # TODO: Что делать в ситуации, когда не осталось игроков?
        self.lead = self.players.pop(0)

    def start_turn(self):
        self.change_lead()
        new_setup = self.setups.get_card()
        self.turn_count += 1

        async def turn_timer() -> None:
            if turn_duration := self.settings.turn_duration:
                await asyncio.sleep(turn_duration)
                self.state.end_turn()

        self.transit_to(Turns(new_setup, asyncio.create_task(turn_timer())))

        for pl in self.all_players:
            pl.is_ready = False
            if len(pl.hand) != self.HAND_SIZE:
                new_card = self.punchlines.get_card()
                pl.add_punchline_card(new_card)
                pl.observer.turn_started(
                    setup=new_setup,
                    turn_duration=self.settings.turn_duration,
                    lead=self.lead,
                    card=new_card,
                    turn_count=self.turn_count,
                )
            else:
                pl.observer.turn_started(
                    setup=new_setup,
                    turn_duration=self.settings.turn_duration,
                    lead=self.lead,
                    turn_count=self.turn_count,
                )

    def get_card_from_table(self, card) -> CardOnTable:
        for card_on_table in self.table:
            if card is card_on_table.card:
                return card_on_table
        raise NotImplementedError

    def connect(self, player: Player) -> None:
        if player not in self.all_players:
            if player not in self.grave:
                raise UnknownPlayerError()

            self.grave.remove(player)
            self.add_player(player)

        if not isinstance(self.state, Gathering):
            while len(player.hand) < self.HAND_SIZE:
                player.add_punchline_card(self.punchlines.get_card())

        for pl in self.all_players_except(player):
            pl.observer.player_connected(player)

    def disconnect(self, player: Player) -> None:
        for pl in self.all_players_except(player):
            pl.observer.player_disconnected(player)

    def add_player(self, player: Player):
        self.players.append(player)
        player.lobby = self

        for pl in self.all_players:
            pl.observer.player_joined(player)

    def remove_player(self, player: Player) -> None:
        if player is self.lead:
            self.lead = None
            # TODO: make turn, return table

        if player in self.players:
            self.players.remove(player)

        if player is self.owner:
            self.change_owner()
            for pl in self.all_players_except(player):
                pl.observer.owner_changed(self.owner)

        self.grave.add(player)

        for card_on_table in self.table:
            if card_on_table.player is player:
                self.punchlines.dump([card_on_table.card])
                # TODO: Если сбросить карту игрока, то надо как-то оповестить
                #   остальных, что эту карту надо убрать со стола
                self.table.remove(card_on_table)
                print(f"Card is dumped and removed from the table. table={self.table}")
                break

        for pl in self.all_players_except(player):
            pl.observer.player_left(player)
        print(f"Removed. self.lead={self.lead}, self.players={self.players}")
        self.state.remove_player(player)
