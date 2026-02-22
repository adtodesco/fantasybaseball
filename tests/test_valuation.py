import numpy as np
import pandas as pd
import pytest

from fantasybaseball.valuation import calculate_auction_values, calculate_available_budget


class TestCalculateAuctionValues:
    @pytest.fixture
    def sample_data(self):
        bat = pd.DataFrame(
            {
                "ProjectionSource": ["steamer", "steamer", "steamer"],
                "MlbamId": [1, 2, 3],
                "FangraphsId": [101, 102, 103],
                "PAR": [50.0, 30.0, -10.0],
                "Salary": [0.0, 0.0, 0.0],
            }
        )
        pit = pd.DataFrame(
            {
                "ProjectionSource": ["steamer", "steamer"],
                "MlbamId": [4, 5],
                "FangraphsId": [104, 105],
                "PAR": [40.0, 20.0],
                "Salary": [0.0, 0.0],
            }
        )
        roster = {"teams": 10, "positions": {"C": 1, "P": 1, "bench": 1}}
        salary = {"cap": 260, "minimum": 1}
        return bat, pit, roster, salary

    def test_returns_series(self, sample_data):
        bat, pit, roster, salary = sample_data
        bat_values, pit_values = calculate_auction_values(bat, pit, roster, salary)

        assert isinstance(bat_values, pd.Series)
        assert isinstance(pit_values, pd.Series)
        assert len(bat_values) == len(bat)
        assert len(pit_values) == len(pit)

    def test_values_are_numeric(self, sample_data):
        bat, pit, roster, salary = sample_data
        bat_values, pit_values = calculate_auction_values(bat, pit, roster, salary)

        assert bat_values.notna().all()
        assert pit_values.notna().all()

    def test_positive_par_gets_higher_value(self, sample_data):
        bat, pit, roster, salary = sample_data
        bat_values, _ = calculate_auction_values(bat, pit, roster, salary)

        # Player with PAR=50 should have higher value than PAR=30
        values = bat_values.tolist()
        assert values[0] > values[1]

    def test_power_factor_1_equals_default(self, sample_data):
        bat, pit, roster, salary = sample_data
        bat_default, pit_default = calculate_auction_values(bat, pit, roster, salary)
        bat_power1, pit_power1 = calculate_auction_values(bat, pit, roster, salary, power_factor=1.0)

        assert bat_default.values == pytest.approx(bat_power1.values)
        assert pit_default.values == pytest.approx(pit_power1.values)

    def test_power_factor_amplifies_top_players(self, sample_data):
        bat, pit, roster, salary = sample_data
        bat_linear, _ = calculate_auction_values(bat, pit, roster, salary)
        bat_curved, _ = calculate_auction_values(bat, pit, roster, salary, power_factor=1.5)

        # Top PAR player (PAR=50) should get more with curved
        assert bat_curved.iloc[0] > bat_linear.iloc[0]

        # Lowest positive PAR player (PAR=30) should get less with curved
        assert bat_curved.iloc[1] < bat_linear.iloc[1]

    def test_negative_par_gets_minimum_salary(self, sample_data):
        bat, pit, roster, salary = sample_data
        bat_values, _ = calculate_auction_values(bat, pit, roster, salary)

        # Player with PAR=-10 should get minimum_salary (PAR clipped to 0)
        assert bat_values.iloc[2] == pytest.approx(salary["minimum"])

    def test_total_auction_value_override(self, sample_data):
        bat, pit, roster, salary = sample_data
        bat_default, pit_default = calculate_auction_values(bat, pit, roster, salary)
        # Double the available budget
        bat_double, pit_double = calculate_auction_values(
            bat, pit, roster, salary, total_auction_value=2 * (10 * 260 - 30 * 1)
        )

        # Values above minimum should roughly double (minus the minimum_salary base)
        for default, doubled in [(bat_default, bat_double), (pit_default, pit_double)]:
            above_min_default = default - salary["minimum"]
            above_min_doubled = doubled - salary["minimum"]
            ratio = above_min_doubled / above_min_default.replace(0, np.nan)
            assert ratio.dropna().values == pytest.approx([2.0] * len(ratio.dropna()), rel=1e-6)

    def test_pool_mask_excludes_players_from_par_pool(self, sample_data):
        bat, pit, roster, salary = sample_data

        # Default: all players in pool
        bat_all, pit_all = calculate_auction_values(bat, pit, roster, salary)

        # Exclude the top batter (PAR=50) from the pool
        bat_mask = pd.Series([False, True, True], index=bat.index)
        pit_mask = pd.Series([True, True], index=pit.index)
        bat_partial, pit_partial = calculate_auction_values(
            bat, pit, roster, salary, bat_pool_mask=bat_mask, pit_pool_mask=pit_mask
        )

        # Remaining pool players should get higher $/PAR since total PAR is smaller
        # The second batter (PAR=30, in pool) should get a higher value
        assert bat_partial.iloc[1] > bat_all.iloc[1]

    def test_pool_mask_still_values_all_players(self, sample_data):
        bat, pit, roster, salary = sample_data

        bat_mask = pd.Series([False, True, True], index=bat.index)
        pit_mask = pd.Series([True, True], index=pit.index)
        bat_values, pit_values = calculate_auction_values(
            bat, pit, roster, salary, bat_pool_mask=bat_mask, pit_pool_mask=pit_mask
        )

        # All players still get values (even those outside the pool)
        assert len(bat_values) == len(bat)
        assert len(pit_values) == len(pit)
        assert bat_values.notna().all()
        assert pit_values.notna().all()


    def test_minors_pct_reduces_player_value_budget(self, sample_data):
        bat, pit, roster, salary = sample_data
        # Default: no minors_pct
        bat_default, pit_default = calculate_auction_values(bat, pit, roster, salary)

        # With 20% minors_pct — effective cap is 80% of 260 = 208
        salary_with_minors = {"cap": 260, "minimum": 1, "minors_pct": 0.20}
        bat_minors, pit_minors = calculate_auction_values(bat, pit, roster, salary_with_minors)

        # Total budget is lower, so values for positive-PAR players should be lower
        assert bat_minors.iloc[0] < bat_default.iloc[0]
        assert pit_minors.iloc[0] < pit_default.iloc[0]

    def test_minors_pct_zero_matches_default(self, sample_data):
        bat, pit, roster, salary = sample_data
        salary_explicit = {"cap": 260, "minimum": 1, "minors_pct": 0.0}
        bat_default, pit_default = calculate_auction_values(bat, pit, roster, salary)
        bat_explicit, pit_explicit = calculate_auction_values(bat, pit, roster, salary_explicit)

        assert bat_default.values == pytest.approx(bat_explicit.values)
        assert pit_default.values == pytest.approx(pit_explicit.values)


class TestCalculateAvailableBudget:
    def test_basic_budget_calculation(self):
        league_export = pd.DataFrame({
            "Status": ["Signed", "FA", "Signed"],
            "Salary": [25.0, 0.0, 15.0],
        })
        roster = {"teams": 10, "positions": {"C": 1, "P": 1, "bench": 1}}
        salary = {"cap": 260, "minimum": 1}

        budget = calculate_available_budget(roster, salary, league_export)

        # total_budget = 10 * 260 = 2600
        # signed_salary = 25 + 15 = 40
        # signed_count = 2
        # remaining_spots = 30 - 2 = 28
        # available = 2600 - 40 - 28 * 1 = 2532
        assert budget == pytest.approx(2532.0)

    def test_fa_players_not_counted_as_signed(self):
        league_export = pd.DataFrame({
            "Status": ["Signed", "FA", None],
            "Salary": [25.0, 10.0, 5.0],
        })
        roster = {"teams": 10, "positions": {"C": 1, "P": 1, "bench": 1}}
        salary = {"cap": 260, "minimum": 1}

        budget = calculate_available_budget(roster, salary, league_export)

        # Only first player is signed: salary=25, count=1
        # remaining = 30 - 1 = 29
        # available = 2600 - 25 - 29 = 2546
        assert budget == pytest.approx(2546.0)

    def test_minors_roster_spots_expand_total(self):
        league_export = pd.DataFrame({
            "Status": ["Signed", "FA", "Signed"],
            "Salary": [25.0, 0.0, 15.0],
        })
        roster = {"teams": 10, "positions": {"C": 1, "P": 1, "bench": 1}, "minors": 5}
        salary = {"cap": 260, "minimum": 1}

        budget = calculate_available_budget(roster, salary, league_export)

        # total_roster_spots = 10 * (3 + 5) = 80
        # signed_salary = 25 + 15 = 40, signed_count = 2
        # remaining_spots = 80 - 2 = 78
        # available = 2600 - 40 - 78 * 1 = 2482
        assert budget == pytest.approx(2482.0)

    def test_includes_players_without_projections(self):
        # Minor leaguers in export but with no projections should still be counted
        league_export = pd.DataFrame({
            "Status": ["Signed", "Signed", "Signed", "FA"],
            "Salary": [25.0, 15.0, 8.0, 0.0],
        })
        roster = {"teams": 10, "positions": {"C": 1, "P": 1, "bench": 1}}
        salary = {"cap": 260, "minimum": 1}

        budget = calculate_available_budget(roster, salary, league_export)

        # signed_salary = 25 + 15 + 8 = 48, signed_count = 3
        # remaining = 30 - 3 = 27
        # available = 2600 - 48 - 27 = 2525
        assert budget == pytest.approx(2525.0)

    def test_no_signed_players(self):
        league_export = pd.DataFrame({
            "Status": ["FA", "FA"],
            "Salary": [0.0, 0.0],
        })
        roster = {"teams": 10, "positions": {"C": 1, "P": 1, "bench": 1}}
        salary = {"cap": 260, "minimum": 1}

        budget = calculate_available_budget(roster, salary, league_export)

        # No signed players: same as full budget minus min salary reserve
        # available = 2600 - 0 - 30*1 = 2570
        assert budget == pytest.approx(2570.0)
