from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum

@dataclass
class Snap:
    t: int = 0
    bar: int = 0
    o: float = 0.0
    c: float = 0.0
    h: float = 0.0
    l: float = 0.0
    lvl: float = 0.0

@dataclass
class Level:
    left: int
    right: int
    top: float
    bot: float
    col: Optional[str]
    txt: str
    kind: int
    dir: int
    active: bool = True
    deleted: bool = False
    stopReady: bool = False
    stopReadyBar: int = 0
    bornBar: int = 0
    anaStarted: bool = False
    anaActive: bool = False
    anaStartBar: int = 0
    anaWaitingConfirm: bool = False
    anaTargetPrice: Optional[float] = None
    anaLossPrice: Optional[float] = None

@dataclass
class FVGLevel:
    left: int
    right: int
    top: float
    bot: float
    bull: bool
    active: bool = True
    deleted: bool = False

@dataclass
class OBLevel:
    left: int
    right: int
    top: float
    bot: float
    bull: bool
    active: bool = True
    deleted: bool = False

class ISSStateEnum(Enum):
    NONE = 0
    BASE_TRACKING = 1
    BASE_CONFIRMED = 2
    FIRST_BREAK = 3
    CONFIRMED_ISS4 = 4

@dataclass
class StrategyState:
    """Persistent state of the strategy machine operating bar-by-bar."""
    trend: int = 0
    phase: int = 1

    runHigh: Snap = field(default_factory=Snap)
    runLow: Snap = field(default_factory=Snap)
    lastCH: Snap = field(default_factory=Snap)
    lastCL: Snap = field(default_factory=Snap)
    tjl1: Snap = field(default_factory=Snap)
    tjl2: Snap = field(default_factory=Snap)

    runHighSet: bool = False
    runLowSet: bool = False
    lastCHSet: bool = False
    lastCLSet: bool = False
    tjl1Set: bool = False

    # Bullish ISS State Variables
    bullIssState: int = 0
    bullIssBaseConfirmed: bool = False
    bullIssBaseLow: Optional[float] = None
    bullIssBaseLowBar: Optional[int] = None
    bullIssRunHigh: Optional[float] = None
    bullIssRunHighBar: Optional[int] = None
    bullIss1Level: Optional[float] = None
    bullIss1Bar: Optional[int] = None
    bullIss2Level: Optional[float] = None
    bullIss2Bar: Optional[int] = None
    bullIssAfterBreakRunHigh: Optional[float] = None
    bullIssAfterBreakRunHighBar: Optional[int] = None
    bullIssAfterBreakRunLow: Optional[float] = None
    bullIssAfterBreakRunLowBar: Optional[int] = None
    bullIssBosBars: List[int] = field(default_factory=list)
    bullIssBosLvls: List[float] = field(default_factory=list)

    # Bearish ISS State Variables
    bearIssState: int = 0
    bearIssBaseConfirmed: bool = False
    bearIssBaseHigh: Optional[float] = None
    bearIssBaseHighBar: Optional[int] = None
    bearIssRunLow: Optional[float] = None
    bearIssRunLowBar: Optional[int] = None
    bearIss1Level: Optional[float] = None
    bearIss1Bar: Optional[int] = None
    bearIss2Level: Optional[float] = None
    bearIss2Bar: Optional[int] = None
    bearIssAfterBreakRunLow: Optional[float] = None
    bearIssAfterBreakRunLowBar: Optional[int] = None
    bearIssAfterBreakRunHigh: Optional[float] = None
    bearIssAfterBreakRunHighBar: Optional[int] = None
    bearIssBosBars: List[int] = field(default_factory=list)
    bearIssBosLvls: List[float] = field(default_factory=list)

    # CHOCH & QML Tracking
    lastChochSide: int = 0
    issOrTjlSinceChoch: bool = False
    lastQmlLeft: Optional[int] = None
    lastQmlTop: Optional[float] = None
    lastQmlBot: Optional[float] = None

    # Persistent Collections
    levels: List[Level] = field(default_factory=list)
    fvgLevels: List[FVGLevel] = field(default_factory=list)
    obLevels: List[OBLevel] = field(default_factory=list)

    # Analyzer Statistics
    levelAnalyzerTests: List[int] = field(default_factory=lambda: [0] * 17)
    levelAnalyzerWins: List[int] = field(default_factory=lambda: [0] * 17)
    levelAnalyzerLosses: List[int] = field(default_factory=lambda: [0] * 17)

    startBarIndex: Optional[int] = None
