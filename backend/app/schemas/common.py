"""Shared API types: money as minor units with a currency, and fixed-precision decimals.

Decimals are serialised as strings with a fixed number of places, so the API
returns the same text on SQLite and Postgres and clients never parse floats.
"""

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, PlainSerializer

from app.domain.money import Money


def _fixed(places: int) -> PlainSerializer:
    return PlainSerializer(lambda value: f"{value:.{places}f}", return_type=str)


Percent = Annotated[Decimal, _fixed(2)]
Ratio = Annotated[Decimal, _fixed(2)]
Fte = Annotated[Decimal, _fixed(2)]
OneDecimal = Annotated[Decimal, _fixed(1)]


class MoneyOut(BaseModel):
    amount_minor: int
    currency: str

    @classmethod
    def of(cls, money: Money) -> "MoneyOut":
        return cls(amount_minor=money.amount_minor, currency=money.currency)

    @classmethod
    def maybe(cls, money: Money | None) -> "MoneyOut | None":
        return cls.of(money) if money is not None else None


class PageOut[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int
