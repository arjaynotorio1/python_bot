import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional
from datetime import datetime
from src.strategies.base import BaseStrategy, TradeSignal
from src.config.config import config

logger = logging.getLogger(__name__)


class BacktestEngine:
    def __init__(self):
        self.initial_balance = config.BACKTEST.INITIAL_BALANCE
        self.commission = config.BACKTEST.COMMISSION
        self.slippage = config.BACKTEST.SLIPPAGE
        
    def run_backtest(self, strategy: BaseStrategy, data: pd.DataFrame, 
                     initial_balance: float = None) -> Dict:
        if initial_balance:
            self.initial_balance = initial_balance
            
        balance = self.initial_balance
        equity_curve = [balance]
        trades = []
        positions = []
        
        for i in range(len(data)):
            if i < strategy.min_candles():
                equity_curve.append(balance)
                continue
                
            current_candle = data.iloc[i]
            lookback_data = data.iloc[:i+1].copy()
            lookback_data = self._add_indicators(lookback_data)
            
            signal = strategy.generate_signal(lookback_data)
            
            if signal:
                trade_result = self._execute_trade(signal, current_candle, balance)
                if trade_result:
                    trades.append(trade_result)
                    balance = trade_result['final_balance']
                    positions.append(trade_result)
            
            equity_curve.append(balance)
            
        stats = self._calculate_stats(equity_curve, trades)
        stats['trades'] = trades
        
        logger.info(f"Backtest completed for {strategy.name}")
        logger.info(f"Total return: {stats['total_return']:.2%}")
        logger.info(f"Win rate: {stats['win_rate']:.2%}")
        logger.info(f"Sharpe ratio: {stats['sharpe_ratio']:.2f}")
        
        return stats
    
    def _add_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        data = data.copy()
        
        data['rsi'] = self._calculate_rsi(data['close'], config.STRATEGY.RSI_PERIOD)
        data['ema_fast'] = self._calculate_ema(data['close'], config.STRATEGY.EMA_FAST)
        data['ema_slow'] = self._calculate_ema(data['close'], config.STRATEGY.EMA_SLOW)
        data['ema_long'] = self._calculate_ema(data['close'], config.STRATEGY.EMA_LONG)
        data['atr'] = self._calculate_atr(data['high'], data['low'], data['close'], 
                                          config.STRATEGY.ATR_PERIOD)
        
        bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(
            data['close'], config.STRATEGY.BB_PERIOD, config.STRATEGY.BB_STD
        )
        data['bb_upper'] = bb_upper
        data['bb_middle'] = bb_middle
        data['bb_lower'] = bb_lower
        
        return data
    
    def _execute_trade(self, signal: TradeSignal, candle: pd.Series, 
                       balance: float) -> Optional[Dict]:
        entry_price = signal.entry_price
        stop_loss = signal.stop_loss
        take_profit = signal.take_profit
        lot_size = signal.position_size
        
        slippage_adjustment = self.slippage * config.GOLD.POINT
        
        if signal.signal_type == 'BUY':
            entry_price += slippage_adjustment
            if stop_loss:
                stop_loss += slippage_adjustment
            if take_profit:
                take_profit += slippage_adjustment
        else:
            entry_price -= slippage_adjustment
            if stop_loss:
                stop_loss -= slippage_adjustment
            if take_profit:
                take_profit -= slippage_adjustment
        
        profit = 0.0
        exit_price = None
        exit_reason = ""
        
        high = candle['high']
        low = candle['low']
        
        if signal.signal_type == 'BUY':
            if low <= stop_loss <= high:
                exit_price = stop_loss
                exit_reason = "Stop loss hit"
            elif high >= take_profit:
                exit_price = take_profit
                exit_reason = "Take profit hit"
            else:
                exit_price = candle['close']
                exit_reason = "End of candle"
                
            profit = (exit_price - entry_price) * lot_size * 100
        else:
            if high >= stop_loss >= low:
                exit_price = stop_loss
                exit_reason = "Stop loss hit"
            elif low <= take_profit:
                exit_price = take_profit
                exit_reason = "Take profit hit"
            else:
                exit_price = candle['close']
                exit_reason = "End of candle"
                
            profit = (entry_price - exit_price) * lot_size * 100
        
        profit -= self.commission
        final_balance = balance + profit
        
        return {
            'signal': signal.to_dict(),
            'entry_price': entry_price,
            'exit_price': exit_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'lot_size': lot_size,
            'profit': profit,
            'initial_balance': balance,
            'final_balance': final_balance,
            'exit_reason': exit_reason,
            'candle': candle.name
        }
    
    def _calculate_stats(self, equity_curve: List[float], trades: List[Dict]) -> Dict:
        final_balance = equity_curve[-1]
        total_return = (final_balance - self.initial_balance) / self.initial_balance
        
        returns = np.diff(equity_curve) / np.array(equity_curve[:-1])
        returns = returns[~np.isnan(returns)]
        
        if len(returns) > 0:
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        else:
            sharpe_ratio = 0.0
            
        max_drawdown = self._calculate_max_drawdown(equity_curve)
        
        if trades:
            winning_trades = [t for t in trades if t['profit'] > 0]
            losing_trades = [t for t in trades if t['profit'] <= 0]
            
            win_rate = len(winning_trades) / len(trades)
            
            avg_win = np.mean([t['profit'] for t in winning_trades]) if winning_trades else 0
            avg_loss = np.mean([t['profit'] for t in losing_trades]) if losing_trades else 0
            
            profit_factor = sum([t['profit'] for t in winning_trades]) / \
                           abs(sum([t['profit'] for t in losing_trades])) if losing_trades else 0
        else:
            win_rate = 0.0
            avg_win = 0.0
            avg_loss = 0.0
            profit_factor = 0.0
            
        return {
            'initial_balance': self.initial_balance,
            'final_balance': final_balance,
            'total_return': total_return,
            'total_profit': final_balance - self.initial_balance,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'total_trades': len(trades),
            'winning_trades': len([t for t in trades if t['profit'] > 0]),
            'losing_trades': len([t for t in trades if t['profit'] <= 0]),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor
        }
    
    def _calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        peak = equity_curve[0]
        max_dd = 0.0
        
        for value in equity_curve:
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
            
        return max_dd
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        return prices.ewm(span=period, adjust=False).mean()
    
    def _calculate_atr(self, high: pd.Series, low: pd.Series, 
                       close: pd.Series, period: int) -> pd.Series:
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int, 
                                   std_dev: float) -> tuple:
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        middle_band = sma
        lower_band = sma - (std * std_dev)
        
        return upper_band, middle_band, lower_band
    
    def optimize_parameters(self, strategy: BaseStrategy, data: pd.DataFrame,
                           param_ranges: Dict) -> Dict:
        results = []
        
        for params in self._generate_parameter_combinations(param_ranges):
            strategy.__dict__.update(params)
            
            stats = self.run_backtest(strategy, data)
            results.append({
                'params': params,
                'stats': stats
            })
        
        best_result = max(results, key=lambda x: x['stats']['total_return'])
        
        logger.info(f"Best parameters: {best_result['params']}")
        logger.info(f"Best return: {best_result['stats']['total_return']:.2%}")
        
        return best_result
    
    def _generate_parameter_combinations(self, param_ranges: Dict) -> List[Dict]:
        import itertools
        
        keys = list(param_ranges.keys())
        values = list(param_ranges.values())
        
        combinations = []
        for combination in itertools.product(*values):
            combinations.append(dict(zip(keys, combination)))
            
        return combinations


backtest_engine = BacktestEngine()
