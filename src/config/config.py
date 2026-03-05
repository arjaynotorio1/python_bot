import os
from dotenv import load_dotenv
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

load_dotenv()


class TradingMode(Enum):
    PAPER = "paper"
    LIVE = "live"


class TimeFrame(Enum):
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"
    W1 = "W1"


@dataclass
class GoldConfig:
    SYMBOL: str = "XAUUSD"
    POINT: float = 0.01
    DIGITS: int = 2
    TRADE_COMMISSION: float = 0.0
    SWAP_LONG: float = 0.0
    SWAP_SHORT: float = 0.0


@dataclass
class MT5Config:
    LOGIN: str = field(default="")
    PASSWORD: str = field(default="")
    SERVER: str = field(default="")
    PATH: str = field(default="")
    TIMEOUT: int = 60000
    
    def __post_init__(self):
        self.LOGIN = os.getenv("MT5_LOGIN", "")
        self.PASSWORD = os.getenv("MT5_PASSWORD", "")
        self.SERVER = os.getenv("MT5_SERVER", "")
        self.PATH = os.getenv("MT5_PATH", "")


@dataclass
class TelegramConfig:
    BOT_TOKEN: str = field(default="")
    CHAT_ID: str = field(default="")
    ENABLED: bool = False
    
    def __post_init__(self):
        self.BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
        self.ENABLED = bool(self.BOT_TOKEN and self.CHAT_ID)


@dataclass
class EmailConfig:
    FROM: str = field(default="")
    PASSWORD: str = field(default="")
    TO: str = field(default="")
    SMTP_SERVER: str = field(default="")
    SMTP_PORT: int = 587
    ENABLED: bool = False
    
    def __post_init__(self):
        self.FROM = os.getenv("EMAIL_FROM", "")
        self.PASSWORD = os.getenv("EMAIL_PASSWORD", "")
        self.TO = os.getenv("EMAIL_TO", self.FROM or "")
        self.SMTP_SERVER = os.getenv("SMTP_SERVER", "")
        self.SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
        self.ENABLED = bool(self.FROM and self.PASSWORD)


@dataclass
class RiskConfig:
    RISK_PER_TRADE: float = 0.02
    MAX_DAILY_DRAWDOWN: float = 0.05
    DEFAULT_LOT_SIZE: float = 0.01
    MAX_POSITIONS: int = 2
    MIN_STOP_LOSS_PIPS: int = 30
    MIN_TAKE_PROFIT_PIPS: int = 60
    RISK_REWARD_RATIO: float = 2.0
    MAX_DAILY_TRADES: int = 10
    
    def __post_init__(self):
        self.RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", 0.02))
        self.MAX_DAILY_DRAWDOWN = float(os.getenv("MAX_DAILY_DRAWDOWN", 0.05))
        self.DEFAULT_LOT_SIZE = float(os.getenv("DEFAULT_LOT_SIZE", 0.01))
        self.MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", 2))


@dataclass
class DatabaseConfig:
    PATH: str = "data/trading.db"
    
    def __post_init__(self):
        self.PATH = os.getenv("DB_PATH", "data/trading.db")


@dataclass
class StrategyConfig:
    TECHNICAL_TIMEFRAME: TimeFrame = TimeFrame.H1
    TREND_TIMEFRAME: TimeFrame = TimeFrame.H4
    RSI_PERIOD: int = 14
    RSI_OVERBOUGHT: float = 70.0
    RSI_OVERSOLD: float = 30.0
    MACD_FAST: int = 12
    MACD_SLOW: int = 26
    MACD_SIGNAL: int = 9
    EMA_FAST: int = 20
    EMA_SLOW: int = 50
    EMA_LONG: int = 200
    BB_PERIOD: int = 20
    BB_STD: float = 2.0
    ADX_PERIOD: int = 14
    ADX_THRESHOLD: float = 25.0
    ATR_PERIOD: int = 14
    TRAILING_STOP_PIPS: int = 20


@dataclass
class BacktestConfig:
    INITIAL_BALANCE: float = 10000.0
    START_DATE: Optional[str] = None
    END_DATE: Optional[str] = None
    COMMISSION: float = 0.0
    SLIPPAGE: float = 0.0


@dataclass
class DashboardConfig:
    HOST: str = "127.0.0.1"
    PORT: int = 8050
    DEBUG: bool = True
    REFRESH_INTERVAL: int = 5


class Config:
    GOLD = GoldConfig()
    MT5 = MT5Config()
    TELEGRAM = TelegramConfig()
    EMAIL = EmailConfig()
    RISK = RiskConfig()
    DATABASE = DatabaseConfig()
    STRATEGY = StrategyConfig()
    BACKTEST = BacktestConfig()
    DASHBOARD = DashboardConfig()
    
    @property
    def TRADING_MODE(self) -> TradingMode:
        mode = os.getenv("TRADING_MODE", "paper").lower()
        return TradingMode.LIVE if mode == "live" else TradingMode.PAPER
    
    @property
    def PAPER_TRADING(self) -> bool:
        return self.TRADING_MODE == TradingMode.PAPER
    
    @property
    def IS_LIVE(self) -> bool:
        return self.TRADING_MODE == TradingMode.LIVE
    
    def get_timeframes(self) -> List[TimeFrame]:
        return [TimeFrame.M5, TimeFrame.H1, TimeFrame.H4, TimeFrame.D1]


config = Config()
