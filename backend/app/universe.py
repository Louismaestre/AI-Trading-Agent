"""Investment universe: the stocks the agents are allowed to trade, plus the CAC 40 benchmark."""

from dataclasses import dataclass


@dataclass(frozen=True)
class UniverseEntry:
    ticker: str
    name: str
    isin: str | None
    sector: str


UNIVERSE: list[UniverseEntry] = [
    UniverseEntry(ticker="MC.PA", name="LVMH", isin="FR0000121014", sector="Luxury"),
    UniverseEntry(ticker="OR.PA", name="L'Oréal", isin="FR0000120321", sector="Consumer goods"),
    UniverseEntry(ticker="TTE.PA", name="TotalEnergies", isin="FR0000120271", sector="Energy"),
    UniverseEntry(ticker="SAN.PA", name="Sanofi", isin="FR0000120578", sector="Healthcare"),
    UniverseEntry(ticker="AIR.PA", name="Airbus", isin="NL0000235190", sector="Aerospace"),
    UniverseEntry(ticker="BNP.PA", name="BNP Paribas", isin="FR0000131104", sector="Banking"),
    UniverseEntry(
        ticker="SU.PA", name="Schneider Electric", isin="FR0000121972", sector="Industrials"
    ),
    UniverseEntry(ticker="AI.PA", name="Air Liquide", isin="FR0000120073", sector="Chemicals"),
    UniverseEntry(ticker="CAP.PA", name="Capgemini", isin="FR0000125338", sector="Technology"),
    UniverseEntry(ticker="DG.PA", name="Vinci", isin="FR0000125486", sector="Construction"),
    # Benchmark index, not traded by the agents.
    UniverseEntry(ticker="^FCHI", name="CAC 40", isin="FR0003500008", sector="Index"),
]
