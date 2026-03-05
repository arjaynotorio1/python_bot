import pandas as pd
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta
from src.strategies.base import BaseStrategy, TradeSignal
from src.config.config import config

logger = logging.getLogger(__name__)


class FundamentalStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("Fundamental Analysis")
        self.economic_events = []
        self.last_update = None
        
    def min_candles(self) -> int:
        return 50
    
    def generate_signal(self, data: pd.DataFrame) -> Optional[TradeSignal]:
        latest = data.iloc[-1]
        current_price = latest['close']
        
        signals = self._get_fundamental_signals()
        
        if not signals:
            return None
            
        buy_score = 0
        sell_score = 0
        reasons = []
        
        for signal in signals:
            if signal['type'] == 'BUY':
                buy_score += signal['weight']
                reasons.append(signal['reason'])
            elif signal['type'] == 'SELL':
                sell_score += signal['weight']
                reasons.append(signal['reason'])
        
        if buy_score >= 2:
            confidence = min(buy_score / 3.0, 1.0)
            reason = f"Fundamental BUY signals: {', '.join(reasons)}"
            return self._create_signal('BUY', current_price, confidence, reason)
        elif sell_score >= 2:
            confidence = min(sell_score / 3.0, 1.0)
            reason = f"Fundamental SELL signals: {', '.join(reasons)}"
            return self._create_signal('SELL', current_price, confidence, reason)
            
        return None
    
    def _get_fundamental_signals(self) -> list:
        signals = []
        
        fed_rate_signal = self._check_fed_rate_expectation()
        if fed_rate_signal:
            signals.append(fed_rate_signal)
            
        inflation_signal = self._check_inflation_expectation()
        if inflation_signal:
            signals.append(inflation_signal)
            
        geopolitical_signal = self._check_geopolitical_risk()
        if geopolitical_signal:
            signals.append(geopolitical_signal)
            
        dollar_strength_signal = self._check_dollar_strength()
        if dollar_strength_signal:
            signals.append(dollar_strength_signal)
            
        return signals
    
    def _check_fed_rate_expectation(self) -> Optional[Dict]:
        signals = {
            'type': 'BUY',
            'weight': 1.0,
            'reason': 'Expected Fed rate cuts (positive for gold)'
        }
        return signals
    
    def _check_inflation_expectation(self) -> Optional[Dict]:
        signals = {
            'type': 'BUY',
            'weight': 1.0,
            'reason': 'Rising inflation expectations (positive for gold)'
        }
        return signals
    
    def _check_geopolitical_risk(self) -> Optional[Dict]:
        signals = {
            'type': 'BUY',
            'weight': 1.0,
            'reason': 'Geopolitical tensions (safe-haven demand for gold)'
        }
        return signals
    
    def _check_dollar_strength(self) -> Optional[Dict]:
        signals = {
            'type': 'BUY',
            'weight': 1.0,
            'reason': 'Weakening US dollar (positive for gold)'
        }
        return signals
    
    def _create_signal(self, signal_type: str, price: float,
                       confidence: float, reason: str) -> TradeSignal:
        atr = config.RISK.MIN_STOP_LOSS_PIPS * config.GOLD.POINT
        
        if signal_type == 'BUY':
            stop_loss = price - atr
            take_profit = price + (atr * config.RISK.RISK_REWARD_RATIO)
        else:
            stop_loss = price + atr
            take_profit = price - (atr * config.RISK.RISK_REWARD_RATIO)
        
        return TradeSignal(
            signal_type=signal_type,
            confidence=confidence,
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reason=reason,
            position_size=config.RISK.DEFAULT_LOT_SIZE
        )
    
    def validate_signal(self, signal: TradeSignal) -> bool:
        return signal.confidence >= 0.5
    
    def add_economic_event(self, event: Dict) -> None:
        self.economic_events.append(event)
        self.last_update = datetime.now()


class NewsBasedStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("News Based")
        self.news_sentiment = 0.0
        self.major_events = []
        
    def min_candles(self) -> int:
        return 50
    
    def generate_signal(self, data: pd.DataFrame) -> Optional[TradeSignal]:
        latest = data.iloc[-1]
        current_price = latest['close']
        
        if self.news_sentiment == 0:
            return None
            
        if self.news_sentiment > 0.6:
            confidence = min(self.news_sentiment, 1.0)
            reason = f"Positive news sentiment for gold: {self.news_sentiment:.2f}"
            return self._create_signal('BUY', current_price, confidence, reason)
        elif self.news_sentiment < -0.6:
            confidence = min(abs(self.news_sentiment), 1.0)
            reason = f"Negative news sentiment for gold: {self.news_sentiment:.2f}"
            return self._create_signal('SELL', current_price, confidence, reason)
            
        return None
    
    def _create_signal(self, signal_type: str, price: float,
                       confidence: float, reason: str) -> TradeSignal:
        atr = config.RISK.MIN_STOP_LOSS_PIPS * config.GOLD.POINT
        
        if signal_type == 'BUY':
            stop_loss = price - atr
            take_profit = price + (atr * config.RISK.RISK_REWARD_RATIO)
        else:
            stop_loss = price + atr
            take_profit = price - (atr * config.RISK.RISK_REWARD_RATIO)
        
        return TradeSignal(
            signal_type=signal_type,
            confidence=confidence,
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reason=reason,
            position_size=config.RISK.DEFAULT_LOT_SIZE
        )
    
    def validate_signal(self, signal: TradeSignal) -> bool:
        return signal.confidence >= 0.5
    
    def update_news_sentiment(self, sentiment: float) -> None:
        self.news_sentiment = sentiment
        logger.info(f"News sentiment updated: {sentiment:.2f}")
    
    def add_major_event(self, event: Dict) -> None:
        self.major_events.append({
            'event': event,
            'timestamp': datetime.now()
        })
        logger.info(f"Major event added: {event}")


class MacroTrendStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("Macro Trend")
        self.real_yields_trend = 0.0
        self.dollar_index_trend = 0.0
        
    def min_candles(self) -> int:
        return 50
    
    def generate_signal(self, data: pd.DataFrame) -> Optional[TradeSignal]:
        latest = data.iloc[-1]
        current_price = latest['close']
        
        signals = []
        
        if self.real_yields_trend < -0.3:
            signals.append({
                'type': 'BUY',
                'weight': 1.0,
                'reason': 'Declining real yields (positive for gold)'
            })
        elif self.real_yields_trend > 0.3:
            signals.append({
                'type': 'SELL',
                'weight': 1.0,
                'reason': 'Rising real yields (negative for gold)'
            })
        
        if self.dollar_index_trend < -0.3:
            signals.append({
                'type': 'BUY',
                'weight': 1.0,
                'reason': 'Weakening dollar (positive for gold)'
            })
        elif self.dollar_index_trend > 0.3:
            signals.append({
                'type': 'SELL',
                'weight': 1.0,
                'reason': 'Strengthening dollar (negative for gold)'
            })
        
        if not signals:
            return None
        
        buy_score = sum(s['weight'] for s in signals if s['type'] == 'BUY')
        sell_score = sum(s['weight'] for s in signals if s['type'] == 'SELL')
        
        if buy_score >= 1:
            confidence = min(buy_score / 2.0, 1.0)
            reasons = [s['reason'] for s in signals if s['type'] == 'BUY']
            reason = f"Macro BUY signals: {', '.join(reasons)}"
            return self._create_signal('BUY', current_price, confidence, reason)
        elif sell_score >= 1:
            confidence = min(sell_score / 2.0, 1.0)
            reasons = [s['reason'] for s in signals if s['type'] == 'SELL']
            reason = f"Macro SELL signals: {', '.join(reasons)}"
            return self._create_signal('SELL', current_price, confidence, reason)
            
        return None
    
    def _create_signal(self, signal_type: str, price: float,
                       confidence: float, reason: str) -> TradeSignal:
        atr = config.RISK.MIN_STOP_LOSS_PIPS * config.GOLD.POINT
        
        if signal_type == 'BUY':
            stop_loss = price - atr
            take_profit = price + (atr * config.RISK.RISK_REWARD_RATIO)
        else:
            stop_loss = price + atr
            take_profit = price - (atr * config.RISK.RISK_REWARD_RATIO)
        
        return TradeSignal(
            signal_type=signal_type,
            confidence=confidence,
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reason=reason,
            position_size=config.RISK.DEFAULT_LOT_SIZE
        )
    
    def validate_signal(self, signal: TradeSignal) -> bool:
        return signal.confidence >= 0.5
    
    def update_macro_data(self, real_yields: float, dollar_index: float) -> None:
        self.real_yields_trend = real_yields
        self.dollar_index_trend = dollar_index
        logger.info(f"Macro data updated: Real yields={real_yields:.2f}, DXY={dollar_index:.2f}")
