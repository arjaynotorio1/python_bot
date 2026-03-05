import pandas as pd
import logging
from typing import Optional
from src.strategies.base import BaseStrategy, TradeSignal
from src.config.config import config

logger = logging.getLogger(__name__)


class TechnicalAnalysisStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("Technical Analysis")
        
    def min_candles(self) -> int:
        return max(
            config.STRATEGY.RSI_PERIOD,
            config.STRATEGY.MACD_SLOW,
            config.STRATEGY.EMA_LONG,
            config.STRATEGY.BB_PERIOD,
            config.STRATEGY.ADX_PERIOD
        ) + 10
    
    def generate_signal(self, data: pd.DataFrame) -> Optional[TradeSignal]:
        latest = data.iloc[-1]
        previous = data.iloc[-2]
        
        current_price = latest['close']
        
        buy_signals = []
        sell_signals = []
        
        if pd.isna(latest['rsi']):
            return None
            
        if latest['rsi'] < config.STRATEGY.RSI_OVERSOLD:
            buy_signals.append("RSI oversold")
        elif latest['rsi'] > config.STRATEGY.RSI_OVERBOUGHT:
            sell_signals.append("RSI overbought")
            
        if pd.notna(latest['macd']) and pd.notna(previous['macd']):
            if latest['macd'] > latest['macd_signal'] and previous['macd'] <= previous['macd_signal']:
                buy_signals.append("MACD bullish crossover")
            elif latest['macd'] < latest['macd_signal'] and previous['macd'] >= previous['macd_signal']:
                sell_signals.append("MACD bearish crossover")
                
        if pd.notna(latest['ema_fast']) and pd.notna(latest['ema_slow']):
            if latest['ema_fast'] > latest['ema_slow'] and previous['ema_fast'] <= previous['ema_slow']:
                buy_signals.append("EMA fast above slow")
            elif latest['ema_fast'] < latest['ema_slow'] and previous['ema_fast'] >= previous['ema_slow']:
                sell_signals.append("EMA fast below slow")
                
        if pd.notna(latest['bb_lower']) and pd.notna(latest['bb_upper']):
            if latest['close'] < latest['bb_lower']:
                buy_signals.append("Price below lower BB")
            elif latest['close'] > latest['bb_upper']:
                sell_signals.append("Price above upper BB")
                
        if pd.notna(latest['adx']) and latest['adx'] > config.STRATEGY.ADX_THRESHOLD:
            if pd.notna(latest['ema_fast']) and pd.notna(latest['ema_long']):
                if latest['ema_fast'] > latest['ema_long'] and previous['ema_fast'] <= previous['ema_long']:
                    buy_signals.append("Golden cross")
                elif latest['ema_fast'] < latest['ema_long'] and previous['ema_fast'] >= previous['ema_long']:
                    sell_signals.append("Death cross")
        
        buy_score = len(buy_signals)
        sell_score = len(sell_signals)
        
        if buy_score >= 2:
            confidence = min(buy_score / 4.0, 1.0)
            reason = f"Buy signals: {', '.join(buy_signals)}"
            return self._create_signal('BUY', current_price, confidence, reason)
        elif sell_score >= 2:
            confidence = min(sell_score / 4.0, 1.0)
            reason = f"Sell signals: {', '.join(sell_signals)}"
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
        if signal.confidence < 0.3:
            return False
            
        if signal.stop_loss and signal.take_profit:
            risk = abs(signal.entry_price - signal.stop_loss)
            reward = abs(signal.take_profit - signal.entry_price)
            
            if reward < risk * config.RISK.RISK_REWARD_RATIO:
                return False
                
        return True


class RSIMeanReversionStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("RSI Mean Reversion")
        
    def min_candles(self) -> int:
        return config.STRATEGY.RSI_PERIOD + 10
    
    def generate_signal(self, data: pd.DataFrame) -> Optional[TradeSignal]:
        latest = data.iloc[-1]
        
        if pd.isna(latest['rsi']):
            return None
            
        current_price = latest['close']
        
        if latest['rsi'] < config.STRATEGY.RSI_OVERSOLD:
            confidence = (config.STRATEGY.RSI_OVERSOLD - latest['rsi']) / (config.STRATEGY.RSI_OVERSOLD - 20)
            confidence = min(confidence, 1.0)
            reason = f"RSI oversold at {latest['rsi']:.2f}"
            return self._create_signal('BUY', current_price, confidence, reason)
        elif latest['rsi'] > config.STRATEGY.RSI_OVERBOUGHT:
            confidence = (latest['rsi'] - config.STRATEGY.RSI_OVERBOUGHT) / (80 - config.STRATEGY.RSI_OVERBOUGHT)
            confidence = min(confidence, 1.0)
            reason = f"RSI overbought at {latest['rsi']:.2f}"
            return self._create_signal('SELL', current_price, confidence, reason)
            
        return None
    
    def _create_signal(self, signal_type: str, price: float,
                       confidence: float, reason: str) -> TradeSignal:
        atr = config.RISK.MIN_STOP_LOSS_PIPS * config.GOLD.POINT
        
        if signal_type == 'BUY':
            stop_loss = price - atr
            take_profit = price + (atr * 1.5)
        else:
            stop_loss = price + atr
            take_profit = price - (atr * 1.5)
        
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
        return signal.confidence >= 0.3


class BBBreakoutStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("Bollinger Band Breakout")
        
    def min_candles(self) -> int:
        return config.STRATEGY.BB_PERIOD + 10
    
    def generate_signal(self, data: pd.DataFrame) -> Optional[TradeSignal]:
        latest = data.iloc[-1]
        previous = data.iloc[-2]
        
        if pd.isna(latest['bb_upper']) or pd.isna(latest['bb_lower']):
            return None
            
        current_price = latest['close']
        
        if latest['close'] > latest['bb_upper'] and previous['close'] <= previous['bb_upper']:
            confidence = 0.7
            reason = "Price broke above upper Bollinger Band"
            return self._create_signal('BUY', current_price, confidence, reason)
        elif latest['close'] < latest['bb_lower'] and previous['close'] >= previous['bb_lower']:
            confidence = 0.7
            reason = "Price broke below lower Bollinger Band"
            return self._create_signal('SELL', current_price, confidence, reason)
            
        return None
    
    def _create_signal(self, signal_type: str, price: float,
                       confidence: float, reason: str) -> TradeSignal:
        atr = config.RISK.MIN_STOP_LOSS_PIPS * config.GOLD.POINT
        
        if signal_type == 'BUY':
            stop_loss = price - atr
            take_profit = price + (atr * 2.0)
        else:
            stop_loss = price + atr
            take_profit = price - (atr * 2.0)
        
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
