import pytest
import pandas as pd

from fantasybaseball.scoring import calculate_score_vector
from fantasybaseball.model import StatCategory


class TestCalculateScoreVector:
    def test_direct_stat_mapping(self):
        """Stats that appear directly in stat_cols get their scoring weight."""
        stat_cols = ["HR", "R", "RBI", "BB", "SO"]
        scoring = {"bat": {"HR": 4, "R": 1, "RBI": 1, "BB": 1, "SO": -0.5}}
        result = calculate_score_vector(StatCategory.BATTING, stat_cols, scoring)

        assert result["HR"] == 4.0
        assert result["R"] == 1.0
        assert result["SO"] == -0.5

    def test_stat_proxies_batting(self):
        """TB proxy should distribute across H, 2B, 3B, HR."""
        stat_cols = ["H", "2B", "3B", "HR", "AB"]
        scoring = {"bat": {"TB": 1}}
        result = calculate_score_vector(StatCategory.BATTING, stat_cols, scoring, use_stat_proxies=True)

        # TB proxy: H*1 + 2B*1 + 3B*2 + HR*3
        assert result["H"] == 1.0
        assert result["2B"] == 1.0
        assert result["3B"] == 2.0
        assert result["HR"] == 3.0

    def test_stat_proxies_pitching(self):
        """QS proxy should use GS * 0.37."""
        stat_cols = ["IP", "GS", "SV", "ER", "SO", "BB"]
        scoring = {"pit": {"QS": 5}}
        result = calculate_score_vector(StatCategory.PITCHING, stat_cols, scoring, use_stat_proxies=True)

        # QS proxy: GS * 0.37, so coefficient = 0.37 * 5 = 1.85
        assert result["GS"] == pytest.approx(1.85)

    def test_no_proxies_when_disabled(self):
        """Without proxies, missing stats are silently skipped."""
        stat_cols = ["H", "2B", "3B", "HR"]
        scoring = {"bat": {"TB": 1}}
        result = calculate_score_vector(StatCategory.BATTING, stat_cols, scoring, use_stat_proxies=False)

        # TB is not in stat_cols and proxies are off, so all coefficients stay 0
        assert all(v == 0.0 for v in result.values)

    def test_combined_direct_and_proxy(self):
        """Direct stats and proxy stats combine correctly."""
        stat_cols = ["H", "2B", "3B", "HR", "R", "BB"]
        scoring = {"bat": {"TB": 1, "R": 1, "BB": 1}}
        result = calculate_score_vector(StatCategory.BATTING, stat_cols, scoring, use_stat_proxies=True)

        assert result["R"] == 1.0
        assert result["BB"] == 1.0
        assert result["HR"] == 3.0  # From TB proxy

    def test_invalid_stat_category_raises(self):
        with pytest.raises((TypeError, ValueError)):
            calculate_score_vector("invalid", [], {})

    def test_returns_series_with_correct_index(self):
        stat_cols = ["HR", "R"]
        scoring = {"bat": {"HR": 4}}
        result = calculate_score_vector(StatCategory.BATTING, stat_cols, scoring)
        assert isinstance(result, pd.Series)
        assert list(result.index) == stat_cols
