import MetaTrader5 as mt5
import pandas as pd
import pandas_ta as ta
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from src.config.config import config, TimeFrame

logger = logging.getLogger(__name__)


class GoldDataFetcher:
    def __init__(self):
        self.symbol = config.GOLD.SYMBOL
        self.timeframe_map = {
            TimeFrame.M1: mt5.TIMEFRAME_M1,
            TimeFrame.M5: mt5.TIMEFRAME_M5,
            TimeFrame.M15: mt5.TIMEFRAME_M15,
            TimeFrame.M30: mt5.TIMEFRAME_M30,
            TimeFrame.H1: mt5.TIMEFRAME_H1,
            TimeFrame.H4: mt5.TIMEFRAME_H4,
            TimeFrame.D1: mt5.TIMEFRAME_D1,
            TimeFrame.W1: mt5.TIMEFRAME_W1
        }
        
    def get_mt5_timeframe(self, timeframe: TimeFrame) -> int:
        return self.timeframe_map.get(timeframe, mt5.TIMEFRAME_H1)
    
    def get_current_price(self) -> Optional[Dict[str, float]]:
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            logger.error(f"Failed to get tick data for {self.symbol}")
            return None
            
        return {
            'bid': tick.bid,
            'ask': tick.ask,
            'spread': tick.ask - tick.bid,
            'time': datetime.fromtimestamp(tick.time)
        }
    
    def get_candles(self, timeframe: TimeFrame, count: int = 100) -> Optional[pd.DataFrame]:
        mt5_timeframe = self.get_mt5_timeframe(timeframe)
        
        utc_from = datetime.now() - timedelta(minutes=500)
        candles = mt5.copy_rates_from(self.symbol, mt5_timeframe, utc_from, count)
        
        if candles is None or len(candles) == 0:
            logger.error(f"Failed to get candles for {self.symbol}")
            return None
            
        df = pd.DataFrame(candles)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        
        return df
    
    def get_candles_range(self, timeframe: TimeFrame, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        mt5_timeframe = self.get_mt5_timeframe(timeframe)
        
        candles = mt5.copy_rates_range(self.symbol, mt5_timeframe, start_date, end_date)
        
        if candles is None or len(candles) == 0:
            logger.error(f"Failed to get candles for {self.symbol} in range")
            return None
            
        df = pd.DataFrame(candles)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        
        return df
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or len(df) == 0:
            return df
            
        df = df.copy()
        
        df['rsi'] = ta.rsi(df['close'], length=config.STRATEGY.RSI_PERIOD)
        df['rsi_upper'] = config.STRATEGY.RSI_OVERBOUGHT
        df['rsi_lower'] = config.STRATEGY.RSI_OVERSOLD
        
        macd = ta.macd(df['close'], fast=config.STRATEGY.MACD_FAST, 
                       slow=config.STRATEGY.MACD_SLOW, signal=config.STRATEGY.MACD_SIGNAL)
        df['macd'] = macd[f'MACD_{config.STRATEGY.MACD_FAST}_{config.STRATEGY.MACD_SLOW}_{config.STRATEGY.MACD_SIGNAL}']
        df['macd_signal'] = macd[f'MACDs_{config.STRATEGY.MACD_FAST}_{config.STRATEGY.MACD_SLOW}_{config.STRATEGY.MACD_SIGNAL}']
        df['macd_hist'] = macd[f'MACDh_{config.STRATEGY.MACD_FAST}_{config.STRATEGY.MACD_SLOW}_{config.STRATEGY.MACD_SIGNAL}']
        
        df['ema_fast'] = ta.ema(df['close'], length=config.STRATEGY.EMA_FAST)
        df['ema_slow'] = ta.ema(df['close'], length=config.STRATEGY.EMA_SLOW)
        df['ema_long'] = ta.ema(df['close'], length=config.STRATEGY.EMA_LONG)
        
        bb = ta.bbands(df['close'], length=config.STRATEGY.BB_PERIOD, std=config.STRATEGY.BB_STD)
        df['bb_upper'] = bb[f'BBU_{config.STRATEGY.BB_PERIOD}_{config.STRATEGY.BB_STD}']
        df['bb_middle'] = bb[f'BBM_{config.STRATEGY.BB_PERIOD}_{config.STRATEGY.BB_STD}']
        df['bb_lower'] = bb[f'BBL_{config.STRATEGY.BB_PERIOD}_{config.STRATEGY.BB_STD}']
        df['bb_width'] = df['bb_upper'] - df['bb_lower']
        
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=config.STRATEGY.ATR_PERIOD)
        
        df['adx'] = ta.adx(df['high'], df['low'], df['close'], length=config.STRATEGY.ADX_PERIOD)[f'ADX_{config.STRATEGY.ADX_PERIOD}']
        df['adx_threshold'] = config.STRATEGY.ADX_THRESHOLD
        
        return df
    
    def get_latest_candle(self, timeframe: TimeFrame) -> Optional[Dict]:
        df = self.get_candles(timeframe, count=1)
        if df is None or len(df) == 0:
            return None
            
        latest = df.iloc[-1]
        return {
            'time': latest.name,
            'open': latest['open'],
            'high': latest['high'],
            'low': latest['low'],
            'close': latest['close'],
            'volume': latest['tick_volume']
        }
    
    def get_tick_data(self) -> Optional[pd.DataFrame]:
        ticks = mt5.copy_ticks_from(self.symbol, datetime.now(), mt5.COPY_TICKS_ALL, 1000)
        
        if ticks is None or len(ticks) == 0:
            logger.error(f"Failed to get tick data for {self.symbol}")
            return None
            
        df = pd.DataFrame(ticks)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        
        return df
    
    def download_historical_data(self, timeframe: TimeFrame, days: int = 365) -> Optional[pd.DataFrame]:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        df = self.get_candles_range(timeframe, start_date, end_date)
        
        if df is not None:
            file_path = f"data/xauusd/XAUUSD_{timeframe.value}_{days}days.csv"
            df.to_csv(file_path)
            logger.info(f"Downloaded {len(df)} candles to {file_path}")
            
        return df
    
    def get_signal_strength(self, df: pd.DataFrame) -> Dict[str, float]:
        if df is None or len(df) < 2:
            return {'buy': 0, 'sell': 0}
            
        latest = df.iloc[-1]
        previous = df.iloc[-2]
        
        buy_signals = 0
        sell_signals = 0
        
        if latest['rsi'] < config.STRATEGY.RSI_OVERSOLD:
            buy_signals += 1
        elif latest['rsi'] > config.STRATEGY.RSI_OVERBOUGHT:
            sell_signals += 1
            
        if latest['macd'] > latest['macd_signal'] and previous['macd'] <= previous['macd_signal']:
            buy_signals += 1
        elif latest['macd'] < latest['macd_signal'] and previous['macd'] >= previous['macd_signal']:
            sell_signals += 1
            
        if latest['ema_fast'] > latest['ema_slow']:
            buy_signals += 1
        else:
            sell_signals += 1
            
        if latest['close'] < latest['bb_lower']:
            buy_signals += 1
        elif latest['close'] > latest['bb_upper']:
            sell_signals += 1
            
        if latest['adx'] > config.STRATEGY.ADX_THRESHOLD:
            if latest['ema_fast'] > latest['ema_long']:
                buy_signals += 1
            else:
                sell_signals += 1
                
        total_signals = buy_signals + sell_signals
        if total_signals > 0:
            return {
                'buy': buy_signals / total_signals,
                'sell': sell_signals / total_signals
            }
        
        return {'buy': 0, 'sell': 0}
    
    def get_support_resistance(self, df: pd.DataFrame, lookback: int = 20) -> Dict[str, List[float]]:
        if df is None or len(df) < lookback:
            return {'support': [], 'resistance': []}
            
        recent = df.tail(lookback)
        
        highs = recent['high'].values
        lows = recent['low'].values
        
        resistance_levels = []
        support_levels = []
        
        for i in range(2, len(highs) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
               highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                resistance_levels.append(highs[i])
                
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
               lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                support_levels.append(lows[i])
                
        resistance_levels.sort(reverse=True)
        support_levels.sort()
        
        return {
            'support': support_levels[:3],
            'resistance': resistance_levels[:3]
        }


gold_data_fetcher = GoldDataFetcher()
