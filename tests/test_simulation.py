import random

import pytest

from raccoonbot_game.game import Game, GameResult
from raccoonbot_game.simulation import play_simulated_match, render_ascii, run_tournament


def test_ascii_board_shows_numbered_empty_cells() -> None:
    assert render_ascii(Game(), show_indices=True) == "1 2 3\n4 5 6\n7 8 9"


def test_simulated_match_always_finishes() -> None:
    record = play_simulated_match(rng=random.Random(12))
    assert record.result is not GameResult.IN_PROGRESS
    assert 5 <= len(record.actions) <= 16


def test_tournament_accounts_for_every_game() -> None:
    results = run_tournament(300, seed=2026)
    assert sum(results.values()) == 300
    assert results[GameResult.IN_PROGRESS] == 0


def test_tournament_rejects_non_positive_count() -> None:
    with pytest.raises(ValueError):
        run_tournament(0)
