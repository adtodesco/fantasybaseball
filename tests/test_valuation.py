import numpy as np
import pandas as pd
import pytest

from fantasybaseball.valuation import calculate_auction_values


class TestCalculateAuctionValues:
    @pytest.fixture
    def sample_data(self):
        bat = pd.DataFrame({
            "ProjectionSource": ["steamer", "steamer", "steamer"],
            "MlbamId": [1, 2, 3],
            "FangraphsId": [101, 102, 103],
            "PAR": [50.0, 30.0, -10.0],
            "Salary": [0.0, 0.0, 0.0],
        })
        pit = pd.DataFrame({
            "ProjectionSource": ["steamer", "steamer"],
            "MlbamId": [4, 5],
            "FangraphsId": [104, 105],
            "PAR": [40.0, 20.0],
            "Salary": [0.0, 0.0],
        })
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
