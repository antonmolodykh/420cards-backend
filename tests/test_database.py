from typing import AsyncGenerator

import pytest
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from dao import CardsDAO
from db import create_engine, create_tables_if_not_exist
from lobby import PunchlineCard, SetupCard
from models import Punchline, Setup, metadata


@pytest.fixture
async def async_session() -> async_sessionmaker:
    engine = create_engine()
    async with engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)
    await create_tables_if_not_exist(engine)
    return async_sessionmaker(engine)


@pytest.fixture
async def session(
    async_session: async_sessionmaker,
) -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


@pytest.fixture
def cards_dao(async_session: async_sessionmaker) -> CardsDAO:
    return CardsDAO(async_session)


@pytest.fixture
async def punchline_card(session: AsyncSession) -> None:
    await session.execute(insert(Punchline).values(variants=[("value", ["variant"])]))
    await session.commit()


@pytest.fixture
async def setup_card(session: AsyncSession) -> None:
    await session.execute(
        insert(Setup).values(variant="variant", starts_with_punchline=True, text="text")
    )
    await session.commit()


@pytest.mark.usefixtures("punchline_card")
async def test_insert_punchline_card(session: AsyncSession) -> None:
    ((punchline_card,),) = await session.execute(select(Punchline))
    assert isinstance(punchline_card, Punchline)


@pytest.mark.usefixtures("setup_card")
async def test_insert_setup_card(session: AsyncSession) -> None:
    ((setup_card,),) = await session.execute(select(Setup))
    assert isinstance(setup_card, Setup)


@pytest.mark.usefixtures("setup_card")
async def test_get_setups(cards_dao: CardsDAO) -> None:
    deck = await cards_dao.get_setups("123")
    assert isinstance(deck.get_card(), SetupCard)


@pytest.mark.usefixtures("punchline_card")
async def test_get_punchlines(cards_dao: CardsDAO) -> None:
    deck = await cards_dao.get_punchlines("123")
    assert isinstance(deck.get_card(), PunchlineCard)
