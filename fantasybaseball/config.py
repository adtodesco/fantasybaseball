from dataclasses import dataclass, field


@dataclass
class ScoringConfig:
    bat: dict[str, float] = field(default_factory=dict)
    pit: dict[str, float] = field(default_factory=dict)

    def __getitem__(self, key):
        return getattr(self, key)


@dataclass
class RosterConfig:
    teams: int = 12
    positions: dict[str, int] = field(default_factory=dict)
    minors: int = 0

    def __getitem__(self, key):
        return getattr(self, key)


@dataclass
class SalaryConfig:
    cap: int = 260
    minimum: int = 1
    minors_pct: float = 0.0

    def __getitem__(self, key):
        return getattr(self, key)


@dataclass
class LeagueConfig:
    name: str = ""
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    roster: RosterConfig = field(default_factory=RosterConfig)
    salary: SalaryConfig = field(default_factory=SalaryConfig)

    def __getitem__(self, key):
        return getattr(self, key)

    def __contains__(self, key):
        return hasattr(self, key) and bool(getattr(self, key))

    def get(self, key, default=None):
        try:
            val = getattr(self, key)
            return val if val else default
        except AttributeError:
            return default


def _normalize_scoring_keys(scoring_dict):
    """Accept both 'bat'/'pit' and 'batting'/'pitching' as scoring keys."""
    normalized = {}
    for key, value in scoring_dict.items():
        if key == "batting":
            normalized["bat"] = value
        elif key == "pitching":
            normalized["pit"] = value
        else:
            normalized[key] = value
    return normalized


def load_league_config(yaml_dict):
    """Parse a league YAML dict into a typed LeagueConfig.

    Validates required fields and normalizes scoring keys.
    """
    if not isinstance(yaml_dict, dict):
        raise ValueError("League config must be a dictionary")

    name = yaml_dict.get("name", "")

    # Scoring
    scoring_raw = yaml_dict.get("scoring", {})
    if not scoring_raw:
        raise ValueError("League config must include 'scoring' section")
    scoring_raw = _normalize_scoring_keys(scoring_raw)
    if "bat" not in scoring_raw:
        raise ValueError("League scoring must include batting rules ('bat' or 'batting')")
    if "pit" not in scoring_raw:
        raise ValueError("League scoring must include pitching rules ('pit' or 'pitching')")
    scoring = ScoringConfig(
        bat={k: float(v) for k, v in scoring_raw["bat"].items()},
        pit={k: float(v) for k, v in scoring_raw["pit"].items()},
    )

    # Roster (optional)
    roster = RosterConfig()
    roster_raw = yaml_dict.get("roster")
    if roster_raw:
        teams = roster_raw.get("teams", 12)
        if isinstance(teams, list):
            teams_count = len(teams)
        else:
            teams_count = int(teams)
        positions = {k: int(v) for k, v in roster_raw.get("positions", {}).items()}
        if not positions:
            raise ValueError("League roster must include 'positions'")
        minors = int(roster_raw.get("minors", 0))
        roster = RosterConfig(teams=teams_count, positions=positions, minors=minors)

    # Salary (optional)
    salary = SalaryConfig()
    salary_raw = yaml_dict.get("salary")
    if salary_raw:
        salary = SalaryConfig(
            cap=int(salary_raw.get("cap", 260)),
            minimum=int(salary_raw.get("minimum", 1)),
            minors_pct=float(salary_raw.get("minors_pct", 0.0)),
        )

    return LeagueConfig(name=name, scoring=scoring, roster=roster, salary=salary)
