from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from lobby import Deck, PunchlineCard, SetupCard
from models import Punchline, Setup


class CardsDAO:
    def __init__(self, async_session: async_sessionmaker):
        self.async_session = async_session

    async def get_setups(self, deck_id: str) -> Deck[SetupCard]:
        async with self.async_session() as session:
            result = await session.execute(select(Setup))

            return Deck(
                cards=[
                    SetupCard(
                        id=setup_card.id,
                        text=setup_card.text,
                        case=setup_card.variant,
                        starts_with_punchline=setup_card.starts_with_punchline,
                    )
                    for (setup_card,) in result.all()
                ]
            )

    async def get_punchlines(self, deck_id: str) -> Deck[PunchlineCard]:
        async with self.async_session() as session:
            result = await session.execute(select(Punchline))

            return Deck(
                cards=[
                    PunchlineCard(
                        id=punchline_card.id,
                        text=punchline_card.variants,
                    )
                    for (punchline_card,) in result.all()
                ]
            )
