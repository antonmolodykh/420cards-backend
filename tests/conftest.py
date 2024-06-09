from unittest.mock import Mock

import pytest
from config import config

from cardsagainst import (
    Deck,
    Gathering,
    Lobby,
    LobbyObserver,
    LobbySettings,
    Player,
    Profile,
    PunchlineCard,
    SetupCard,
)


@pytest.fixture(scope="session", autouse=True)
def set_test_environment() -> None:
    config.configure(FORCE_ENV_FOR_DYNACONF="test")


@pytest.fixture
def setup_deck_size() -> int:
    return 10


@pytest.fixture
def setup_deck(setup_deck_size: int) -> Deck[SetupCard]:
    return Deck(
        cards=[
            SetupCard(id=i + 1, text="", case="", starts_with_punchline=False)
            for i in range(setup_deck_size)
        ]
    )


@pytest.fixture
def punchline_deck_size() -> int:
    return 100


@pytest.fixture
def punchline_deck(punchline_deck_size: int) -> Deck[PunchlineCard]:
    return Deck(
        cards=[
            PunchlineCard(id=i + 1, text=[("a", ["b"])])
            for i in range(punchline_deck_size)
        ]
    )


@pytest.fixture
def outbox() -> Mock:
    return Mock(LobbyObserver)


@pytest.fixture
def egor() -> Player:
    return Player(profile=Profile(name="egor", emoji="🍎"), token="egor-token")


@pytest.fixture
def anton() -> Player:
    return Player(profile=Profile(name="anton", emoji="🍎"), token="anton-token")


@pytest.fixture
def yura() -> Player:
    return Player(profile=Profile(name="yura", emoji="🍎"), token="yura-token")


@pytest.fixture
def state_gathering() -> Gathering:
    return Gathering()


@pytest.fixture
def lobby_settings() -> LobbySettings:
    return LobbySettings(
        turn_duration=None,
        winning_score=1,
        finish_delay=0,
        start_turn_delay=0,
    )


@pytest.fixture
def lobby(  # TODO: Переименовать в лобби егора, чтобы было понятно, что он owner
    egor: Player,
    outbox: Mock,
    state_gathering: Gathering,
) -> Lobby:
    return Lobby(
        owner=egor,
        state=state_gathering,
    )


@pytest.fixture
def egor_joined(lobby: Lobby, egor: Player) -> None:
    lobby.add_player(egor)


@pytest.fixture
def egor_connected(egor_joined: None, lobby: Lobby, egor: Player, outbox: Mock) -> None:
    player_mock = Mock(LobbyObserver)
    egor.connect(player_mock)
    outbox.attach_mock(player_mock, "egor")


@pytest.fixture
def anton_joined(lobby: Lobby, anton: Player) -> None:
    lobby.add_player(anton)


@pytest.fixture
def anton_connected(
    anton_joined: None, lobby: Lobby, anton: Player, outbox: Mock
) -> None:
    player_mock = Mock(LobbyObserver)
    anton.connect(player_mock)
    outbox.attach_mock(player_mock, "anton")


@pytest.fixture
def yura_joined(lobby: Lobby, yura: Player) -> None:
    lobby.add_player(yura)


@pytest.fixture
def yura_connected(yura_joined: None, lobby: Lobby, yura: Player, outbox: Mock) -> None:
    player_mock = Mock(LobbyObserver)
    yura.connect(player_mock)
    outbox.attach_mock(player_mock, "yura")


@pytest.fixture
async def game_started(
    lobby: Lobby,
    egor: Player,
    setup_deck: Deck[SetupCard],
    punchline_deck: Deck[PunchlineCard],
    lobby_settings: LobbySettings,
) -> None:
    egor.start_game(lobby_settings, setup_deck, punchline_deck)
