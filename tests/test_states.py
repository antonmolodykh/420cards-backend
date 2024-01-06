import asyncio

from lobby import (
    CardOnTable,
    Deck,
    Finished,
    Judgement,
    Lobby,
    Player,
    PunchlineCard,
    SetupCard,
    Turns,
)


async def test_transit_gathering_to_turns(lobby: Lobby) -> None:
    lobby.state.start_turn()
    isinstance(lobby.state, Turns)


async def test_transit_turns_to_judgement(
    lobby: Lobby,
    anton: Player,
    punchline_deck: Deck[PunchlineCard],
    setup_deck: Deck[SetupCard],
) -> None:
    setup_card = setup_deck.get_card()
    lobby.add_player(anton)
    punchline_card = punchline_deck.get_card()
    anton.add_punchline_card(punchline_card)
    lobby.transit_to(Turns(setup_card, 1))
    lobby.state.make_turn(anton, punchline_card)
    await asyncio.sleep(0.01)
    assert isinstance(lobby.state, Judgement)
    assert lobby.state.setup is setup_card


async def test_transit_judgement_to_turns(
    lobby: Lobby,
    anton: Player,
    punchline_deck: Deck[PunchlineCard],
    setup_deck: Deck[SetupCard],
) -> None:
    setup_card = setup_deck.get_card()
    next_setup_card = setup_deck.cards[-1]
    lobby.add_player(anton)
    lobby.transit_to(Judgement(setup_card))
    lobby.state.start_turn()
    assert isinstance(lobby.state, Turns)
    assert lobby.state.setup is next_setup_card


async def test_transit_judgement_to_finished(
    lobby: Lobby,
    egor: Player,
    anton: Player,
    punchline_deck: Deck[PunchlineCard],
    setup_deck: Deck[SetupCard],
) -> None:
    setup_card = setup_deck.get_card()
    lobby.add_player(egor)
    lobby.add_player(anton)
    lobby.settings.winning_score = 1
    lobby.settings.finish_delay = 0
    lobby.transit_to(Judgement(setup_card))
    punchline_card = punchline_deck.get_card()
    lobby.table.append(CardOnTable(punchline_card, anton))
    lobby.state.open_punchline_card(egor, lobby.get_card_from_table(punchline_card))
    lobby.state.pick_turn_winner(egor, punchline_card)
    await asyncio.sleep(0.01)
    assert isinstance(lobby.state, Finished)


async def test_transit_finished_to_turns(
    lobby: Lobby,
    egor: Player,
    anton: Player,
) -> None:
    lobby.add_player(anton)
    lobby.transit_to(Finished(anton, lobby.setups.get_card()))
    punchline_card = lobby.punchlines.get_card()
    lobby.table.append(CardOnTable(punchline_card, anton))
    next_setup_card = lobby.setups.cards[-1]

    lobby.state.continue_game(egor)

    assert isinstance(lobby.state, Turns)
    assert lobby.lead == anton
    assert lobby.state.setup == next_setup_card
