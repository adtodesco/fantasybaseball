import pytest

from fantasybaseball.model import Position
from fantasybaseball.replacement import _calculate_replacement_level_ranks


class TestCalculateReplacementLevelRanks:
    def test_simple_roster_no_bench(self):
        """Basic roster without bench or flex positions."""
        roster = {"teams": 10, "positions": {"C": 1, "1B": 1, "SS": 1}}
        result = _calculate_replacement_level_ranks(roster, include_bench=False)

        assert result[Position.C] == 10.0
        assert result[Position.FiB] == 10.0
        assert result[Position.SS] == 10.0

    def test_bench_distributes_proportionally(self):
        """Bench spots distribute proportionally across positions."""
        roster = {"teams": 10, "positions": {"C": 1, "OF": 3, "bench": 4}}
        result = _calculate_replacement_level_ranks(roster, include_bench=True)

        # 4 starters total, bench=4
        # C gets 1/4 * 4 = 1 bench spot -> 2 total * 10 teams = 20
        assert result[Position.C] == 20.0
        # OF gets 3/4 * 4 = 3 bench spots -> 6 total * 10 teams = 60
        assert result[Position.OF] == 60.0

    def test_exclude_bench(self):
        """When include_bench=False, bench spots are ignored."""
        roster = {"teams": 10, "positions": {"C": 1, "OF": 3, "bench": 4}}
        result = _calculate_replacement_level_ranks(roster, include_bench=False)

        assert result[Position.C] == 10.0
        assert result[Position.OF] == 30.0

    def test_flex_positions_distribute(self):
        """UTIL/CI/MI spots distribute to their eligible positions."""
        roster = {"teams": 10, "positions": {"1B": 1, "3B": 1, "CI": 2}}
        result = _calculate_replacement_level_ranks(roster, include_bench=False)

        # CI=2 distributes to 1B and 3B: each gets +2/2 = +1
        assert result[Position.FiB] == 20.0  # (1+1) * 10
        assert result[Position.ThB] == 20.0  # (1+1) * 10
        assert Position.CI not in result

    def test_mi_flex_distribution(self):
        """MI distributes to 2B and SS."""
        roster = {"teams": 12, "positions": {"2B": 1, "SS": 1, "MI": 1}}
        result = _calculate_replacement_level_ranks(roster, include_bench=False)

        # MI=1 distributes: each gets +0.5
        assert result[Position.SeB] == pytest.approx(18.0)  # (1+0.5) * 12
        assert result[Position.SS] == pytest.approx(18.0)

    def test_team_count_as_list(self):
        """Teams can be a list of team names instead of an int."""
        roster = {"teams": ["Team A", "Team B", "Team C"], "positions": {"C": 1}}
        result = _calculate_replacement_level_ranks(roster, include_bench=False)

        assert result[Position.C] == 3.0

    def test_thedoo_roster(self):
        """Integration test with thedoo league roster."""
        roster = {
            "teams": 14,
            "positions": {"C": 1, "1B": 1, "2B": 1, "SS": 1, "3B": 1, "CI": 1, "MI": 1, "OF": 5, "UTIL": 1, "P": 9, "bench": 13},
        }
        result = _calculate_replacement_level_ranks(roster, include_bench=True)

        # Verify all flex positions resolved
        assert Position.CI not in result
        assert Position.MI not in result
        assert Position.UTIL not in result
        # Verify P exists (non-flex)
        assert Position.P in result
