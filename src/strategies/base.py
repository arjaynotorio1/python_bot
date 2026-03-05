from abc import ABC, abstractmethod
from typing import Dict, Optional, List
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TradeSignal:
    def __init__(self, signal_type: str, confidence: float, 
                 entry_price: float, stop_loss: Optional[float] = None,
                 take_profit: Optional[float] = None, 
                 reason: str = "", position_size: float = 0.01):
        self.signal_type = signal_type  # 'BUY' or 'SELL'
        self.confidence = confidence    # 0.0 to 1.0
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.reason = reason
        self.position_size = position_size
        self.timestamp = datetime.now()
    
    def __repr__(self):
        return (f"TradeSignal(type={self.signal_type}, confidence={self.confidence:.2f}, "
                f"entry={self.entry_price}, sl={self.stop_loss}, tp={self.take_profit})")
    
    def to_dict(self) -> Dict:
        return {
            'signal_type': self.signal_type,
            'confidence': self.confidence,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'reason': self.reason,
            'position_size': self.position_size,
            'timestamp': self.timestamp.isoformat()
        }


class BaseStrategy(ABC):
    def __init__(self, name: str):
        self.name = name
        self.enabled = True
        self.last_signal = None
        self.trade_count = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        
    @abstractmethod
    def generate_signal(self, data: pd.DataFrame) -> Optional[TradeSignal]:
        pass
    
    @abstractmethod
    def validate_signal(self, signal: TradeSignal) -> bool:
        pass
    
    def analyze(self, data: pd.DataFrame) -> Optional[TradeSignal]:
        if not self.enabled:
            logger.debug(f"Strategy {self.name} is disabled")
            return None
            
        if data is None or len(data) < self.min_candles():
            logger.warning(f"Insufficient data for strategy {self.name}")
            return None
            
        try:
            signal = self.generate_signal(data)
            
            if signal and self.validate_signal(signal):
                self.last_signal = signal
                logger.info(f"{self.name} generated {signal.signal_type} signal: {signal.reason}")
                return signal
            elif signal:
                logger.debug(f"Signal from {self.name} failed validation")
                
            return None
        except Exception as e:
            logger.error(f"Error in strategy {self.name}: {e}")
            return None
    
    @abstractmethod
    def min_candles(self) -> int:
        pass
    
    def update_performance(self, profit: float) -> None:
        self.trade_count += 1
        self.total_profit += profit
        
        if profit > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
            
    def get_performance_stats(self) -> Dict:
        win_rate = self.winning_trades / self.trade_count if self.trade_count > 0 else 0.0
        avg_profit = self.total_profit / self.trade_count if self.trade_count > 0 else 0.0
        
        return {
            'name': self.name,
            'enabled': self.enabled,
            'trade_count': self.trade_count,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'total_profit': self.total_profit,
            'avg_profit': avg_profit
        }
    
    def enable(self) -> None:
        self.enabled = True
        logger.info(f"Strategy {self.name} enabled")
    
    def disable(self) -> None:
        self.enabled = False
        logger.info(f"Strategy {self.name} disabled")
    
    def reset(self) -> None:
        self.last_signal = None
        self.trade_count = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        logger.info(f"Strategy {self.name} reset")
