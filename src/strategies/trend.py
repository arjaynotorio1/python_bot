import pandas as pd
import logging
from typing import Optional
from src.strategies.base import BaseStrategy, TradeSignal
from src.config.config import config

logger = logging.getLogger(__name__)


class TrendFollowingStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("Trend Following")
        
    def min_candles(self) -> int:
        return config.STRATEGY.EMA_LONG + 10
    
    def generate_signal(self, data: pd.DataFrame) -> Optional[TradeSignal]:
        latest = data.iloc[-1]
        previous = data.iloc[-1]
        
        if pd.isna(latest['ema_fast']) or pd.isna(latest['ema_slow']) or pd.isna(latest['ema_long']):
            return None
            
        current_price = latest['close']
        
        strong_uptrend = (latest['ema_fast'] > latest['ema_slow'] > latest['ema_long'] and
                         previous['ema_fast'] > previous['ema_slow'] > previous['ema_long'])
        strong_downtrend = (latest['ema_fast'] < latest['ema_slow'] < latest['ema_long'] and
                           previous['ema_fast'] < previous['ema_slow'] < previous['ema_long'])
        
        if strong_uptrend:
            if current_price <= latest['ema_slow']:
                confidence = 0.8
                reason = "Pullback to EMA slow in strong uptrend"
                return self._create_signal('BUY', current_price, confidence, reason)
            elif pd.notna(latest['atr']):
                atr = latest['atr']
                if current_price <= latest['ema_slow'] + atr:
                    confidence = 0.6
                    reason = "Pullback within 1 ATR of EMA slow in uptrend"
                    return self._create_signal('BUY', current_price, confidence, reason)
                    
        if strong_downtrend:
            if current_price >= latest['ema_slow']:
                confidence = 0.8
                reason = "Pullback to EMA slow in strong downtrend"
                return self._create_signal('SELL', current_price, confidence, reason)
            elif pd.notna(latest['atr']):
                atr = latest['atr']
                if current_price >= latest['ema_slow'] - atr:
                    confidence = 0.6
                    reason = "Pullback within 1 ATR of EMA slow in downtrend"
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


class GoldenCrossStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("Golden Cross")
        
    def min_candles(self) -> int:
        return config.STRATEGY.EMA_LONG + 10
    
    def generate_signal(self, data: pd.DataFrame) -> Optional[TradeSignal]:
        if len(data) < 2:
            return None
            
        latest = data.iloc[-1]
        previous = data.iloc[-2]
        
        if pd.isna(latest['ema_fast']) or pd.isna(latest['ema_long']):
            return None
            
        if pd.isna(previous['ema_fast']) or pd.isna(previous['ema_long']):
            return None
            
        current_price = latest['close']
        
        golden_cross = (latest['ema_fast'] > latest['ema_long'] and 
                       previous['ema_fast'] <= previous['ema_long'])
        
        death_cross = (latest['ema_fast'] < latest['ema_long'] and 
                      previous['ema_fast'] >= previous['ema_long'])
        
        if golden_cross:
            confidence = 0.85
            reason = "Golden cross detected (fast EMA crossed above long EMA)"
            return self._create_signal('BUY', current_price, confidence, reason)
        elif death_cross:
            confidence = 0.85
            reason = "Death cross detected (fast EMA crossed below long EMA)"
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
        return True


class ADXTrendStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("ADX Trend")
        
    def min_candles(self) -> int:
        return config.STRATEGY.ADX_PERIOD + config.STRATEGY.EMA_SLOW + 10
    
    def generate_signal(self, data: pd.DataFrame) -> Optional[TradeSignal]:
        latest = data.iloc[-1]
        
        if pd.isna(latest['adx']) or pd.isna(latest['ema_fast']) or pd.isna(latest['ema_slow']):
            return None
            
        if latest['adx'] < config.STRATEGY.ADX_THRESHOLD:
            return None
            
        current_price = latest['close']
        
        trend_strength = (latest['adx'] - config.STRATEGY.ADX_THRESHOLD) / (50 - config.STRATEGY.ADX_THRESHOLD)
        trend_strength = min(trend_strength, 1.0)
        
        if latest['ema_fast'] > latest['ema_slow']:
            if current_price <= latest['ema_slow']:
                confidence = 0.5 + (trend_strength * 0.3)
                reason = f"Strong uptrend (ADX: {latest['adx']:.2f}), pullback to EMA slow"
                return self._create_signal('BUY', current_price, confidence, reason)
        elif latest['ema_fast'] < latest['ema_slow']:
            if current_price >= latest['ema_slow']:
                confidence = 0.5 + (trend_strength * 0.3)
                reason = f"Strong downtrend (ADX: {latest['adx']:.2f}), pullback to EMA slow"
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
        return signal.confidence >= 0.6
