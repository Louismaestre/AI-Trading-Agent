from app.universe import UNIVERSE, tradable_tickers


def test_tickers_are_unique() -> None:
    tickers = [entry.ticker for entry in UNIVERSE]

    assert len(tickers) == len(set(tickers))


def test_isins_are_unique_and_well_formed() -> None:
    isins = [entry.isin for entry in UNIVERSE if entry.isin is not None]

    assert len(isins) == len(set(isins))
    for isin in isins:
        assert len(isin) == 12, isin
        assert isin[:2].isalpha(), isin


def test_benchmark_index_is_included() -> None:
    assert "^FCHI" in {entry.ticker for entry in UNIVERSE}


def test_tradable_tickers_exclude_the_index() -> None:
    tickers = tradable_tickers()
    assert "^FCHI" not in tickers
    assert "MC.PA" in tickers
