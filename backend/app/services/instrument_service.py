from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Instrument
from app.universe import UNIVERSE


class InstrumentService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def sync_universe(self) -> None:
        """Insert or update every UNIVERSE entry in the instruments table."""

        rows = [
            {
                "ticker": entry.ticker,
                "name": entry.name,
                "isin": entry.isin,
                "sector": entry.sector,
            }
            for entry in UNIVERSE
        ]

        statement = insert(Instrument).values(rows)
        statement = statement.on_conflict_do_update(
            index_elements=[Instrument.ticker],
            set_={
                "name": statement.excluded.name,
                "isin": statement.excluded.isin,
                "sector": statement.excluded.sector,
            },
        )
        self._session.execute(statement)
        self._session.commit()

    def list_instruments(self) -> list[Instrument]:
        """Return all instruments, sorted by ticker."""
        statement = select(Instrument).order_by(Instrument.ticker)
        return list(self._session.scalars(statement).all())
