import pytest

from lobby import Lobby


@pytest.mark.usefixtures("state_gathering")
def test_transit_gathering_to_turns(lobby: Lobby) -> None:
    lobby.state.start_turn()
    isinstance(lobby.state, Turns)
