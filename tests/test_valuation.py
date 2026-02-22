import numpy as np
import pandas as pd
import pytest

from fantasybaseball.valuation import add_auction_values


class TestAddAuctionValues:
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

    def test_auction_values_computed(self, sample_data):
        bat, pit, roster, salary = sample_data
        bat_result, pit_result = add_auction_values(bat, pit, roster, salary)

        assert "AuctionValue" in bat_result.columns
        assert "ContractValue" in bat_result.columns
        assert "AuctionValue" in pit_result.columns

    def test_positive_par_gets_higher_value(self, sample_data):
        bat, pit, roster, salary = sample_data
        bat_result, _ = add_auction_values(bat, pit, roster, salary)

        # Player with PAR=50 should have higher value than PAR=30
        values = bat_result.sort_values("PAR", ascending=False)["AuctionValue"].tolist()
        assert values[0] > values[1]

    def test_contract_value_is_auction_minus_salary(self, sample_data):
        bat, pit, roster, salary = sample_data
        bat.loc[0, "Salary"] = 25.0
        bat_result, _ = add_auction_values(bat, pit, roster, salary)

        row = bat_result.iloc[0]
        assert row["ContractValue"] == pytest.approx(row["AuctionValue"] - 25.0)

    def test_no_rostered_players(self, sample_data):
        bat, pit, roster, salary = sample_data
        bat_result, pit_result = add_auction_values(bat, pit, roster, salary, rostered_players=None)

        # All values should be numeric (not NaN for known sources)
        assert bat_result["AuctionValue"].notna().all()
        assert pit_result["AuctionValue"].notna().all()
