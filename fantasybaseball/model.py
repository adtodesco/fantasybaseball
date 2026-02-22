from enum import Enum


class ProjectionSourceName(Enum):
    ATC = "atc"
    DEPTH_CHARTS = "fangraphsdc"
    OOPSY = "oopsy"
    STEAMER = "steamer"
    THE_BAT = "thebat"
    THE_BAT_X = "thebatx"
    ZIPS = "zips"
    ZIPSDC = "zipsdc"


class ProjectionSource:
    def __init__(self, name, ros=False):
        if isinstance(name, str):
            name = ProjectionSourceName(name)
        self.name = name
        self.ros = ros

    def __eq__(self, other):
        if isinstance(other, ProjectionSource):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other
        return NotImplemented

    def __hash__(self):
        return hash(self.value)

    @property
    def value(self):
        if not self.ros:
            return self.name.value
        if self.name == ProjectionSourceName.STEAMER:
            return f"{self.name.value}r"
        elif self.name == ProjectionSourceName.ATC:
            return f"r{self.name.value}dc"
        elif self.name == ProjectionSourceName.OOPSY:
            return f"r{self.name.value}dc"
        else:
            return f"r{self.name.value}"


class StatCategory(Enum):
    BATTING = "bat"
    PITCHING = "pit"


class Position(Enum):
    ALL = "ALL"
    C = "C"
    FiB = "1B"
    SeB = "2B"
    ThB = "3B"
    SS = "SS"
    MI = "MI"
    CI = "CI"
    LF = "LF"
    CF = "CF"
    RF = "RF"
    OF = "OF"
    DH = "DH"
    P = "P"
    SP = "SP"
    RP = "RP"
    UTIL = "UTIL"


class League(Enum):
    ALL = "ALL"
    AL = "AL"
    NL = "NL"


class Team(Enum):
    ALL = 0
    LAA = 1
    BAL = 2
    BOS = 3
    CHW = 4
    CLE = 5
    DET = 6
    KC = 7
    MIN = 8
    NYY = 9
    OAK = 10
    SEA = 11
    TB = 12
    TEX = 13
    TOR = 14
    ARI = 15
    ATL = 16
    CHC = 17
    CIN = 18
    COL = 19
    MIA = 20
    HOU = 21
    LAD = 22
    MIL = 23
    WAS = 24
    NYM = 25
    PHI = 26
    PIT = 27
    STL = 28
    SD = 29
    SF = 30


class Stat(Enum):
    AB = "AB"
    TB = "TB"
    Sng = "1B"
    Dbl = "2B"
    Trp = "3B"
    HR = "HR"
    R = "R"
    RBI = "RBI"
    BB = "BB"
    SO = "SO"
    SB = "SB"
    CS = "CS"
    GDP = "GDP"
    HBP = "HBP"
    CYC = "CYC"
    IP = "IP"
    ER = "ER"
    H = "H"
    HB = "HB"
    W = "W"
    L = "L"
    GS = "GS"
    QS = "QS"
    CG = "CG"
    SHO = "SHO"
    SV = "SV"
    HLD = "HLD"
    BS = "BS"
    PG = "PG"
