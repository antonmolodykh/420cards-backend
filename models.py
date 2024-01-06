from sqlalchemy import Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    """Base model"""


metadata = Base.metadata


class Punchline(Base):
    __tablename__ = "punchlines"

    id: Mapped[int] = mapped_column(primary_key=True)
    variants: Mapped[list[tuple[str, list[str]]]] = mapped_column(JSONB, nullable=False)


class Setup(Base):
    __tablename__ = "setups"

    id: Mapped[int] = mapped_column(primary_key=True)
    variant: Mapped[str] = mapped_column(Text, nullable=False)
    starts_with_punchline: Mapped[bool] = mapped_column(Boolean, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
