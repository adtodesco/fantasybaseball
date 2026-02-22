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


class TestCalculateAvailableBudget:
    def test_basic_budget_calculation(self):
        bat = pd.DataFrame({
            "ProjectionSource": ["steamer", "steamer"],
            "MlbamId": [1, 2],
            "Salary": [25.0, 0.0],
        })
        pit = pd.DataFrame({
            "ProjectionSource": ["steamer"],
            "MlbamId": [3],
            "Salary": [15.0],
        })
        roster = {"teams": 10, "positions": {"C": 1, "P": 1, "bench": 1}}
        salary = {"cap": 260, "minimum": 1}

        signed_bat = pd.Series([True, False], index=bat.index)
        signed_pit = pd.Series([True], index=pit.index)

        budget = calculate_available_budget(bat, pit, roster, salary, signed_bat, signed_pit)

        # total_budget = 10 * 260 = 2600
        # signed_salary = 25 + 15 = 40
        # signed_count = 2
        # remaining_spots = 30 - 2 = 28
        # available = 2600 - 40 - 28 * 1 = 2532
        assert budget == pytest.approx(2532.0)

    def test_deduplicates_across_projection_sources(self):
        # Same player appears in two projection sources for batting
        bat = pd.DataFrame({
            "ProjectionSource": ["steamer", "zips"],
            "MlbamId": [1, 1],
            "Salary": [25.0, 25.0],
        })
        pit = pd.DataFrame({
            "ProjectionSource": ["steamer"],
            "MlbamId": [3],
            "Salary": [15.0],
        })
        roster = {"teams": 10, "positions": {"C": 1, "P": 1, "bench": 1}}
        salary = {"cap": 260, "minimum": 1}

        signed_bat = pd.Series([True, True], index=bat.index)
        signed_pit = pd.Series([True], index=pit.index)

        budget = calculate_available_budget(bat, pit, roster, salary, signed_bat, signed_pit)

        # Should only count MlbamId=1 once: salary = 25 + 15 = 40, count = 2
        # remaining = 30 - 2 = 28
        # available = 2600 - 40 - 28 = 2532
        assert budget == pytest.approx(2532.0)

    def test_deduplicates_two_way_players(self):
        # Same player in both bat and pit projections
        bat = pd.DataFrame({
            "ProjectionSource": ["steamer"],
            "MlbamId": [1],
            "Salary": [50.0],
        })
        pit = pd.DataFrame({
            "ProjectionSource": ["steamer"],
            "MlbamId": [1],
            "Salary": [50.0],
        })
        roster = {"teams": 10, "positions": {"C": 1, "P": 1, "bench": 1}}
        salary = {"cap": 260, "minimum": 1}

        signed_bat = pd.Series([True], index=bat.index)
        signed_pit = pd.Series([True], index=pit.index)

        budget = calculate_available_budget(bat, pit, roster, salary, signed_bat, signed_pit)

        # Only one signed player (MlbamId=1), salary=50
        # remaining = 30 - 1 = 29
        # available = 2600 - 50 - 29 = 2521
        assert budget == pytest.approx(2521.0)

    def test_no_signed_players(self):
        bat = pd.DataFrame({
            "ProjectionSource": ["steamer"],
            "MlbamId": [1],
            "Salary": [0.0],
        })
        pit = pd.DataFrame({
            "ProjectionSource": ["steamer"],
            "MlbamId": [2],
            "Salary": [0.0],
        })
        roster = {"teams": 10, "positions": {"C": 1, "P": 1, "bench": 1}}
        salary = {"cap": 260, "minimum": 1}

        signed_bat = pd.Series([False], index=bat.index)
        signed_pit = pd.Series([False], index=pit.index)

        budget = calculate_available_budget(bat, pit, roster, salary, signed_bat, signed_pit)

        # No signed players: same as full budget minus min salary reserve
        # available = 2600 - 0 - 30*1 = 2570
        assert budget == pytest.approx(2570.0)
