from unittest.mock import Mock

import pytest
from config import config

from lobby import (
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
    # TODO: I want to control the "hand size"
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
def observer() -> Mock:
    return Mock(LobbyObserver)


@pytest.fixture
def egor() -> Player:
    return Player(
        profile=Profile(name="egor", emoji="🍎", background_color="#ff0000"),
    )


@pytest.fixture
def anton() -> Player:
    return Player(
        profile=Profile(name="anton", emoji="🍎", background_color="#ff0000"),
    )


@pytest.fixture
def yura() -> Player:
    return Player(
        profile=Profile(name="yura", emoji="🍎", background_color="#ff0000"),
    )


@pytest.fixture
def state_gathering() -> Gathering:
    return Gathering()


@pytest.fixture
def lobby_settings() -> LobbySettings:
    return LobbySettings(turn_duration=None, winning_score=1, finish_delay=0)


@pytest.fixture
def lobby(
    egor: Player,
    setup_deck: Deck[SetupCard],
    punchline_deck: Deck[PunchlineCard],
    observer: Mock,
    state_gathering: Gathering,
    lobby_settings: LobbySettings,
) -> Lobby:
    lobby = Lobby(
        settings=lobby_settings,
        players=[],
        state=state_gathering,
        # TODO: state gathering determines the setups and punchlines
        # Move?
        setups=setup_deck,
        punchlines=punchline_deck,
    )
    # TODO: Почему лобби создается без owner?
    lobby.owner = egor
    return lobby


@pytest.fixture
def egor_joined(lobby: Lobby, egor: Player) -> None:
    lobby.add_player(egor)


@pytest.fixture
def egor_connected(
    egor_joined: None, lobby: Lobby, egor: Player, observer: Mock
) -> None:
    player_mock = Mock(LobbyObserver)
    observer.attach_mock(player_mock, "egor")
    egor.observer = player_mock
    lobby.set_connected(egor)


@pytest.fixture
def anton_joined(lobby: Lobby, anton: Player) -> None:
    lobby.add_player(anton)


@pytest.fixture
def anton_connected(
    anton_joined: None, lobby: Lobby, anton: Player, observer: Mock
) -> None:
    player_mock = Mock(LobbyObserver)
    observer.attach_mock(player_mock, "anton")
    anton.observer = player_mock
    lobby.set_connected(anton)


@pytest.fixture
def yura_joined(lobby: Lobby, yura: Player) -> None:
    lobby.add_player(yura)


@pytest.fixture
def yura_connected(
    yura_joined: None, lobby: Lobby, yura: Player, observer: Mock
) -> None:
    player_mock = Mock(LobbyObserver)
    observer.attach_mock(player_mock, "yura")
    yura.observer = player_mock
    lobby.set_connected(yura)


@pytest.fixture
async def game_started(
    lobby: Lobby,
    egor: Player,
    setup_deck: Deck[SetupCard],
    punchline_deck: Deck[PunchlineCard],
    lobby_settings: LobbySettings,
) -> None:
    lobby.state.start_game(
        egor,
        lobby_settings,
        setup_deck,
        punchline_deck,
    )
