from pathlib import Path

import pytest

from app.services.agent_service import llm_overrides
from app.services.experiment_service import (
    DuplicateExperimentIdError,
    ExperimentService,
    load_experiments,
)

DIR = Path(__file__).resolve().parents[2] / "config" / "experiments"


def test_every_experiment_file_matches_the_schema() -> None:
    configs = load_experiments(DIR)
    assert [item.id for item in configs] == ["E0", "E1", "E2", "E3", "E4", "E5", "E6"]
    assert all(item.question for item in configs)


def test_experiments_share_the_same_window() -> None:
    windows = {
        (item.start, item.end, item.initial_capital, item.decision_frequency)
        for item in load_experiments(DIR)
    }
    assert len(windows) == 1


def test_e1_is_technical_only_and_e5_adds_risk() -> None:
    by_id = {item.id: item for item in load_experiments(DIR)}
    assert by_id["E1"].graph.fundamental is False
    assert by_id["E1"].graph.debate_rounds == 0
    assert by_id["E1"].graph.risk is False
    assert by_id["E5"].graph.fundamental is True
    assert by_id["E5"].graph.sentiment is True
    assert by_id["E5"].graph.debate_rounds == 2
    assert by_id["E5"].graph.risk is True


def test_repeats_must_be_between_one_and_five(tmp_path: Path) -> None:
    service = ExperimentService(object(), directory=tmp_path)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="repeats"):
        service.start("E1", repeats=0)
    with pytest.raises(ValueError, match="repeats"):
        service.start("E1", repeats=6)


def test_llm_overrides_read_repeat_flags() -> None:
    assert llm_overrides({"temperature": 0.2, "cache": False}) == (0.2, False)
    assert llm_overrides({"model": "qwen3:8b"}) == (None, None)


def test_duplicate_ids_are_rejected(tmp_path: Path) -> None:
    (tmp_path / "a.yaml").write_text(
        "\n".join(
            [
                "id: E1",
                "name: one",
                "question: q",
                "start: 2026-01-02",
                "end: 2026-03-31",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "b.yaml").write_text(
        "\n".join(
            [
                "id: E1",
                "name: two",
                "question: q",
                "start: 2026-01-02",
                "end: 2026-03-31",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(DuplicateExperimentIdError):
        load_experiments(tmp_path)
