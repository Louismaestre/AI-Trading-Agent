import datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import DailyPrice, Instrument

DAY = datetime.date(2026, 9, 24)


def _instrument(session: Session) -> Instrument:
    instrument = Instrument(ticker="MC.PA", name="LVMH")
    session.add(instrument)
    session.commit()
    return instrument


def _price(instrument: Instrument, day: datetime.date = DAY) -> DailyPrice:
    return DailyPrice(
        instrument_id=instrument.id,
        date=day,
        open=Decimal("600.1000"),
        high=Decimal("612.5000"),
        low=Decimal("598.0000"),
        close=Decimal("610.2500"),
        volume=3_000_000_000,
    )


def test_insert_and_read_daily_price(db_session: Session) -> None:
    instrument = _instrument(db_session)
    db_session.add(_price(instrument))
    db_session.commit()

    price = db_session.scalars(select(DailyPrice)).one()

    assert price.date == DAY
    assert price.close == Decimal("610.2500")
    assert price.volume == 3_000_000_000


def test_one_bar_per_instrument_and_day(db_session: Session) -> None:
    instrument = _instrument(db_session)
    db_session.add(_price(instrument))
    db_session.commit()

    db_session.add(_price(instrument))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_same_instrument_can_have_several_days(db_session: Session) -> None:
    instrument = _instrument(db_session)
    db_session.add_all([_price(instrument), _price(instrument, DAY + datetime.timedelta(days=1))])
    db_session.commit()

    assert db_session.scalar(select(func.count()).select_from(DailyPrice)) == 2


def test_price_requires_existing_instrument(db_session: Session) -> None:
    db_session.add(_price(Instrument(id=999_999, ticker="X", name="Ghost")))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_deleting_instrument_deletes_its_prices(db_session: Session) -> None:
    instrument = _instrument(db_session)
    db_session.add(_price(instrument))
    db_session.commit()

    db_session.delete(instrument)
    db_session.commit()

    assert db_session.scalar(select(func.count()).select_from(DailyPrice)) == 0
