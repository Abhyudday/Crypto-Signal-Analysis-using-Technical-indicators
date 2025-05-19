from enum import Enum, auto

class SignalType(Enum):
    BUY = 'BUY'
    SELL = 'SELL'
    HOLD = 'HOLD'

class ConfidenceLevel(Enum):
    HIGH = 'HIGH'
    MEDIUM = 'MEDIUM'
    NONE = 'NONE' 