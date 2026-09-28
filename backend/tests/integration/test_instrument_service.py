from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Instrument
from app.services.instrument_service import InstrumentService
from app.universe import UNIVERSE


def _count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Instrument)) or 0


def test_sync_inserts_every_universe_entry(db_session: Session) -> None:
    InstrumentService(db_session).sync_universe()

    assert _count(db_session) == len(UNIVERSE)


def test_sync_is_idempotent(db_session: Session) -> None:
    service = InstrumentService(db_session)

    service.sync_universe()
    service.sync_universe()

    assert _count(db_session) == len(UNIVERSE)


def test_sync_restores_values_changed_in_database(db_session: Session) -> None:
    service = InstrumentService(db_session)
    service.sync_universe()
    lvmh = db_session.scalars(select(Instrument).where(Instrument.ticker == "MC.PA")).one()
    lvmh.name = "Wrong name"
    db_session.commit()

    service.sync_universe()

    db_session.refresh(lvmh)
    assert lvmh.name == "LVMH"


def test_list_instruments_is_sorted_by_ticker(db_session: Session) -> None:
    service = InstrumentService(db_session)
    service.sync_universe()

    tickers = [instrument.ticker for instrument in service.list_instruments()]
    # PostgreSQL's collation ignores punctuation ("^FCHI" sorts as "FCHI"), unlike Python's
    # sorted(), so only the stock tickers are compared.
    stocks = [ticker for ticker in tickers if not ticker.startswith("^")]

    assert stocks == sorted(stocks)
    assert len(tickers) == len(UNIVERSE)
