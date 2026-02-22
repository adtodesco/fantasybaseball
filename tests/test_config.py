import pytest

from fantasybaseball.config import load_league_config, LeagueConfig, ScoringConfig


class TestLoadLeagueConfig:
    def test_basic_config(self):
        yaml = {
            "name": "test",
            "scoring": {
                "bat": {"HR": 4, "R": 1},
                "pit": {"SO": 1, "W": 5},
            },
        }
        config = load_league_config(yaml)

        assert isinstance(config, LeagueConfig)
        assert config.name == "test"
        assert config.scoring.bat["HR"] == 4.0
        assert config.scoring.pit["W"] == 5.0

    def test_normalizes_batting_pitching_keys(self):
        """Accepts 'batting'/'pitching' and normalizes to 'bat'/'pit'."""
        yaml = {
            "scoring": {
                "batting": {"HR": 4},
                "pitching": {"SO": 1},
            },
        }
        config = load_league_config(yaml)

        assert config.scoring.bat["HR"] == 4.0
        assert config.scoring.pit["SO"] == 1.0

    def test_full_config_with_roster_and_salary(self):
        yaml = {
            "name": "thedoo",
            "scoring": {"bat": {"HR": 4}, "pit": {"SO": 1}},
            "roster": {"teams": 14, "positions": {"C": 1, "OF": 5}},
            "salary": {"cap": 1026, "minimum": 11},
        }
        config = load_league_config(yaml)

        assert config.roster.teams == 14
        assert config.roster.positions["C"] == 1
        assert config.salary.cap == 1026
        assert config.salary.minimum == 11

    def test_missing_scoring_raises(self):
        with pytest.raises(ValueError, match="scoring"):
            load_league_config({"name": "bad"})

    def test_missing_bat_scoring_raises(self):
        with pytest.raises(ValueError, match="batting"):
            load_league_config({"scoring": {"pit": {"SO": 1}}})

    def test_missing_pit_scoring_raises(self):
        with pytest.raises(ValueError, match="pitching"):
            load_league_config({"scoring": {"bat": {"HR": 4}}})

    def test_non_dict_raises(self):
        with pytest.raises(ValueError, match="dictionary"):
            load_league_config("not a dict")

    def test_roster_without_positions_raises(self):
        with pytest.raises(ValueError, match="positions"):
            load_league_config(
                {
                    "scoring": {"bat": {"HR": 4}, "pit": {"SO": 1}},
                    "roster": {"teams": 10},
                }
            )

    def test_dict_access_works(self):
        """LeagueConfig supports dict-style access for backwards compat."""
        yaml = {
            "scoring": {"bat": {"HR": 4}, "pit": {"SO": 1}},
            "roster": {"teams": 10, "positions": {"C": 1}},
        }
        config = load_league_config(yaml)

        assert config["scoring"].bat["HR"] == 4.0
        assert config["roster"]["teams"] == 10

    def test_contains_check(self):
        """'in' operator works for checking sections."""
        yaml = {
            "scoring": {"bat": {"HR": 4}, "pit": {"SO": 1}},
            "roster": {"teams": 10, "positions": {"C": 1}},
            "salary": {"cap": 260, "minimum": 1},
        }
        config = load_league_config(yaml)

        assert "scoring" in config
        assert "roster" in config
        assert "salary" in config

    def test_teams_as_list(self):
        yaml = {
            "scoring": {"bat": {"HR": 4}, "pit": {"SO": 1}},
            "roster": {"teams": ["Team A", "Team B"], "positions": {"C": 1}},
        }
        config = load_league_config(yaml)
        assert config.roster.teams == 2

    def test_scoring_values_converted_to_float(self):
        yaml = {
            "scoring": {"bat": {"SO": -1}, "pit": {"IP": 3}},
        }
        config = load_league_config(yaml)
        assert isinstance(config.scoring.bat["SO"], float)
        assert config.scoring.bat["SO"] == -1.0
