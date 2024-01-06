import asyncio
from unittest.mock import ANY, Mock, call

import pytest

from lobby import (
    CardNotInPlayerHandError,
    Deck,
    Judgement,
    Lobby,
    LobbySettings,
    NotAllCardsOpenedError,
    Player,
    PlayerNotDealerError,
    PlayerNotOwnerError,
    PunchlineCard,
    SetupCard,
    Turns,
)


@pytest.mark.usefixtures("egor_connected")
async def test_lobby_start_game_set_owner_as_lead(
    lobby: Lobby,
    egor: Player,
    setup_deck: Deck[SetupCard],
    punchline_deck: Deck[PunchlineCard],
    lobby_settings: LobbySettings,
) -> None:
    # FIXME: Думаю, при старте игры можно определить лида, причем поставить лидом овнера
    #   ведь именно он запускает игру, и он точно подключен
    lobby.state.start_game(
        egor,
        lobby_settings,
        setup_deck,
        punchline_deck,
    )
    assert lobby.lead is egor


@pytest.mark.usefixtures("egor_connected", "anton_connected", "game_started")
async def test_lobby_make_turn(
    lobby: Lobby, egor: Player, anton: Player, observer: Mock
) -> None:
    # FIXME: turn_duration вообще-то nullable, но это не учитывается
    #  при запуске таймера
    punchline_card = anton.hand[0]
    lobby.state.make_turn(anton, punchline_card)

    card_on_table = lobby.get_card_from_table(punchline_card)
    assert card_on_table.card is punchline_card
    assert card_on_table.player is anton
    assert not card_on_table.is_open
    assert punchline_card not in anton.hand

    expected_events = [
        call.egor.player_ready(anton),
        call.anton.player_ready(anton),
    ]
    observer.assert_has_calls(expected_events, any_order=True)


@pytest.mark.usefixtures("egor_connected", "anton_connected", "game_started")
def test_lobby_make_turn_card_not_in_player_hand(
    lobby: Lobby, egor: Player, anton: Player, punchline_deck: Deck[PunchlineCard]
) -> None:
    punchline_card = egor.hand[0]
    with pytest.raises(CardNotInPlayerHandError):
        lobby.state.make_turn(anton, punchline_card)


@pytest.mark.usefixtures("egor_connected", "anton_connected", "game_started")
def test_open_punchline_card(
    lobby: Lobby, egor: Player, anton: Player, observer: Mock
) -> None:
    punchline_card = anton.hand[0]
    lobby.state.make_turn(anton, punchline_card)

    assert isinstance(lobby.state, Judgement)
    card_on_table = lobby.get_card_from_table(punchline_card)
    lobby.state.open_punchline_card(egor, card_on_table)
    assert card_on_table.is_open

    expected_events = [
        call.egor.table_card_opened(card_on_table),
    ]
    observer.assert_has_calls(expected_events)


@pytest.mark.usefixtures("egor_connected", "anton_joined", "game_started")
def test_open_punchline_card_member_not_lead(
    lobby: Lobby, egor: Player, anton: Player
) -> None:
    punchline_card = anton.hand[0]
    lobby.state.make_turn(anton, punchline_card)

    # TODO: Use `Lead` instead of `Dealer`
    with pytest.raises(PlayerNotDealerError):
        assert isinstance(lobby.state, Judgement)
        lobby.state.open_punchline_card(
            anton, lobby.get_card_from_table(punchline_card)
        )


@pytest.mark.usefixtures("egor_connected", "anton_connected", "game_started")
def test_lobby_all_players_ready(
    lobby: Lobby, egor: Player, anton: Player, observer: Mock
) -> None:
    lobby.state.make_turn(anton, anton.hand[0])
    assert isinstance(lobby.state, Judgement)

    expected_events = [
        call.egor.all_players_ready(),
        call.anton.all_players_ready(),
    ]
    observer.assert_has_calls(expected_events, any_order=True)


@pytest.mark.usefixtures("egor_connected", "anton_connected", "game_started")
def test_lobby_lead_open_punchline_card(
    lobby: Lobby,
    egor: Player,
    anton: Player,
    punchline_deck: Deck[PunchlineCard],
    observer,
) -> None:
    punchline_card = anton.hand[0]
    # TODO: Будет чище, если make_turn будет возвращать CardOnTable
    lobby.state.make_turn(anton, punchline_card)
    card_on_table = lobby.get_card_from_table(punchline_card)

    assert isinstance(lobby.state, Judgement)
    lobby.state.open_punchline_card(egor, card_on_table)
    expected_events = [
        call.egor.table_card_opened(card_on_table),
    ]
    observer.assert_has_calls(expected_events)


@pytest.mark.usefixtures("egor_connected", "anton_connected", "game_started")
async def test_pick_turn_winner(
    lobby: Lobby,
    egor: Player,
    anton: Player,
    punchline_deck: Deck[PunchlineCard],
    observer,
) -> None:
    punchline_card = anton.hand[0]
    lobby.state.make_turn(anton, punchline_card)
    card_on_table = lobby.get_card_from_table(punchline_card)
    lobby.state.open_punchline_card(egor, card_on_table)

    # TODO: Будет чище, если принимать CardOnTable
    lobby.state.pick_turn_winner(egor, card_on_table.card)

    assert anton.score == 1

    expected_events = [
        call.egor.turn_ended(anton, punchline_card),
        call.anton.turn_ended(anton, punchline_card),
    ]
    observer.assert_has_calls(expected_events)


@pytest.mark.usefixtures("egor_connected", "anton_connected", "game_started")
async def test_pick_turn_winner_not_all_cards_opened(
    lobby: Lobby, egor: Player, anton: Player
) -> None:
    punchline_card = anton.hand[0]
    lobby.state.make_turn(anton, punchline_card)

    with pytest.raises(NotAllCardsOpenedError):
        lobby.state.pick_turn_winner(egor, punchline_card)


@pytest.mark.usefixtures("egor_connected")
def test_player_joined(lobby: Lobby, yura: Player, observer: Mock) -> None:
    lobby.add_player(yura)

    expected_events = [
        call.egor.player_joined(yura),
    ]
    observer.assert_has_calls(expected_events)


@pytest.mark.usefixtures("egor_connected", "yura_joined")
def test_player_connected(lobby: Lobby, yura: Player, observer: Mock) -> None:
    lobby.set_connected(yura)

    expected_events = [
        call.egor.player_connected(yura),
    ]
    observer.assert_has_calls(expected_events)


@pytest.mark.usefixtures("egor_connected", "yura_connected")
def test_player_disconnected(lobby: Lobby, yura: Player, observer: Mock) -> None:
    lobby.set_disconnected(yura)

    expected_events = [
        call.egor.player_disconnected(yura),
    ]
    observer.assert_has_calls(expected_events)


@pytest.mark.usefixtures("egor_connected", "yura_connected")
async def test_start_game(
    lobby: Lobby,
    egor: Player,
    yura: Player,
    observer: Mock,
    setup_deck: Deck[SetupCard],
    punchline_deck: Deck[PunchlineCard],
    lobby_settings: LobbySettings,
) -> None:
    lobby.state.start_game(egor, lobby_settings, setup_deck, punchline_deck)
    assert isinstance(lobby.state, Turns)
    expected_events = [
        call.game_started(egor),
        call.turn_started(
            setup=lobby.state.setup,
            turn_duration=lobby_settings.turn_duration,
            lead=egor,
            turn_count=1,
        ),
    ]
    observer.egor.assert_has_calls(expected_events)
    expected_events = [
        call.game_started(yura),
        call.turn_started(
            setup=lobby.state.setup,
            turn_duration=lobby_settings.turn_duration,
            lead=egor,
            turn_count=1,
        ),
    ]
    observer.yura.assert_has_calls(expected_events)


@pytest.mark.usefixtures("egor_connected", "yura_connected")
def test_start_game_player_not_owner_error(
    lobby: Lobby,
    yura: Player,
    observer: Mock,
    lobby_settings: LobbySettings,
    setup_deck: Deck[SetupCard],
    punchline_deck: Deck[PunchlineCard],
) -> None:
    with pytest.raises(PlayerNotOwnerError):
        lobby.state.start_game(yura, lobby_settings, setup_deck, punchline_deck)

    observer.egor.game_started.assert_not_called()
    observer.yura.game_started.assert_not_called()


@pytest.mark.usefixtures("egor_connected", "yura_connected", "game_started")
async def test_finish_game(
    lobby: Lobby, egor: Player, yura: Player, observer: Mock
) -> None:
    punchline_card = yura.hand[0]
    lobby.state.make_turn(yura, punchline_card)
    card_on_table = lobby.get_card_from_table(punchline_card)
    lobby.state.open_punchline_card(egor, card_on_table)
    lobby.state.pick_turn_winner(egor, punchline_card)
    await asyncio.sleep(0.01)

    expected_events = [
        call.egor.game_finished(yura),
        call.yura.game_finished(yura),
    ]
    observer.assert_has_calls(expected_events)


@pytest.mark.usefixtures("egor_connected", "yura_connected", "game_started")
async def test_continue_game(
    lobby: Lobby, egor: Player, yura: Player, observer: Mock
) -> None:
    punchline_card = yura.hand[0]
    lobby.state.make_turn(yura, punchline_card)
    card_on_table = lobby.get_card_from_table(punchline_card)
    lobby.state.open_punchline_card(egor, card_on_table)
    lobby.state.pick_turn_winner(egor, punchline_card)
    await asyncio.sleep(0.01)

    lobby.state.continue_game(egor)

    assert isinstance(lobby.state, Turns)

    expected_events = [
        call.egor.turn_started(
            setup=lobby.state.setup,
            turn_duration=lobby.settings.turn_duration,
            lead=yura,
            turn_count=2,
        ),
        call.yura.turn_started(
            setup=lobby.state.setup,
            turn_duration=lobby.settings.turn_duration,
            lead=yura,
            turn_count=2,
            card=ANY,
        ),
    ]
    observer.assert_has_calls(expected_events, any_order=True)


@pytest.mark.usefixtures("egor_connected", "yura_connected", "game_started")
async def test_continue_game_player_not_owner_error(
    lobby: Lobby, egor: Player, yura: Player, observer: Mock
) -> None:
    punchline_card = yura.hand[0]
    lobby.state.make_turn(yura, punchline_card)
    card_on_table = lobby.get_card_from_table(punchline_card)
    lobby.state.open_punchline_card(egor, card_on_table)
    lobby.state.pick_turn_winner(egor, punchline_card)
    await asyncio.sleep(0.01)

    with pytest.raises(PlayerNotOwnerError):
        lobby.state.continue_game(yura)


@pytest.mark.usefixtures("egor_connected", "yura_connected", "game_started")
async def test_continue_game_no_more_winner(
    lobby: Lobby,
    egor: Player,
    yura: Player,
    observer: Mock,
    lobby_settings: LobbySettings,
) -> None:
    egor.score = lobby_settings.winning_score - 1
    yura.score = lobby_settings.winning_score - 1
    punchline_card = yura.hand[0]
    lobby.state.make_turn(yura, punchline_card)
    card_on_table = lobby.get_card_from_table(punchline_card)
    lobby.state.open_punchline_card(egor, card_on_table)
    lobby.state.pick_turn_winner(egor, punchline_card)
    await asyncio.sleep(0.01)
    lobby.state.continue_game(egor)
    assert isinstance(lobby.state, Turns)
    punchline_card = egor.hand[0]
    lobby.state.make_turn(egor, punchline_card)
    card_on_table = lobby.get_card_from_table(punchline_card)
    lobby.state.open_punchline_card(yura, card_on_table)
    lobby.state.pick_turn_winner(yura, punchline_card)
    # TODO: Захардкоженный таймер мешает быстро тестировать
    await asyncio.sleep(5.01)
    assert egor.score == lobby_settings.winning_score
    assert isinstance(lobby.state, Turns)


@pytest.mark.usefixtures("egor_connected", "yura_connected", "game_started")
async def test_start_game_after_finish(
    lobby: Lobby,
    egor: Player,
    yura: Player,
    observer: Mock,
    lobby_settings: LobbySettings,
    setup_deck: Deck[SetupCard],
    punchline_deck: Deck[PunchlineCard],
) -> None:
    punchline_card = yura.hand[0]
    lobby.state.make_turn(yura, punchline_card)
    card_on_table = lobby.get_card_from_table(punchline_card)
    lobby.state.open_punchline_card(egor, card_on_table)
    lobby.state.pick_turn_winner(egor, punchline_card)
    await asyncio.sleep(0.01)
    lobby.state.start_game(
        egor,
        lobby_settings.model_copy(update={"turn_duration": 10}),
        setup_deck,
        punchline_deck,
    )

    assert isinstance(lobby.state, Turns)

    expected_events = [
        call.game_started(egor),
        call.turn_started(
            setup=lobby.state.setup,
            turn_duration=10,
            lead=egor,
            turn_count=1,
        ),
    ]
    observer.egor.assert_has_calls(expected_events)
    expected_events = [
        call.game_started(yura),
        call.turn_started(
            setup=lobby.state.setup,
            turn_duration=10,
            lead=egor,
            turn_count=1,
        ),
    ]
    observer.yura.assert_has_calls(expected_events)
