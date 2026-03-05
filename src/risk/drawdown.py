import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from src.config.config import config

logger = logging.getLogger(__name__)


class DailyDrawdownTracker:
    def __init__(self):
        self.max_daily_drawdown = config.RISK.MAX_DAILY_DRAWDOWN
        self.max_daily_trades = config.RISK.MAX_DAILY_TRADES
        
        self.daily_balance = {}
        self.daily_trades = {}
        self.daily_start_balance = {}
        self.daily_peak_balance = {}
        
        self.current_date = date.today()
        self.trading_halted = False
        self.halt_reason = ""
        
    def update_balance(self, current_balance: float) -> None:
        today = date.today()
        
        if today != self.current_date:
            self._new_day(today)
            
        if today not in self.daily_balance:
            self._initialize_day(today, current_balance)
            
        self.daily_balance[today] = current_balance
        
        peak = self.daily_peak_balance.get(today, current_balance)
        if current_balance > peak:
            self.daily_peak_balance[today] = current_balance
            
        drawdown = self._calculate_drawdown(today)
        
        if drawdown >= self.max_daily_drawdown:
            self._halt_trading(f"Daily drawdown limit reached: {drawdown:.2%}")
            
        logger.debug(f"Balance: ${current_balance:.2f}, Drawdown: {drawdown:.2%}")
        
    def add_trade(self, profit: float) -> None:
        today = date.today()
        
        if today != self.current_date:
            self._new_day(today)
            
        if today not in self.daily_trades:
            self.daily_trades[today] = []
            
        self.daily_trades[today].append({
            'profit': profit,
            'timestamp': datetime.now()
        })
        
        if len(self.daily_trades[today]) >= self.max_daily_trades:
            self._halt_trading(f"Daily trade limit reached: {self.max_daily_trades}")
            
        logger.info(f"Trade added: ${profit:.2f}. Daily trades: {len(self.daily_trades[today])}")
        
    def _new_day(self, new_date: date) -> None:
        logger.info(f"New trading day: {new_date}")
        self.current_date = new_date
        self.trading_halted = False
        self.halt_reason = ""
        
    def _initialize_day(self, trade_date: date, balance: float) -> None:
        self.daily_start_balance[trade_date] = balance
        self.daily_peak_balance[trade_date] = balance
        self.daily_trades[trade_date] = []
        
        logger.info(f"Initialized day {trade_date} with balance: ${balance:.2f}")
        
    def _calculate_drawdown(self, trade_date: date) -> float:
        if trade_date not in self.daily_balance or trade_date not in self.daily_peak_balance:
            return 0.0
            
        current = self.daily_balance[trade_date]
        peak = self.daily_peak_balance[trade_date]
        
        if peak == 0:
            return 0.0
            
        return (peak - current) / peak
        
    def _halt_trading(self, reason: str) -> None:
        if not self.trading_halted:
            self.trading_halted = True
            self.halt_reason = reason
            logger.warning(f"TRADING HALTED: {reason}")
            
    def is_trading_allowed(self) -> bool:
        return not self.trading_halted
        
    def get_daily_stats(self, trade_date: date = None) -> Dict:
        if trade_date is None:
            trade_date = date.today()
            
        if trade_date not in self.daily_balance:
            return {
                'date': trade_date,
                'start_balance': 0.0,
                'current_balance': 0.0,
                'peak_balance': 0.0,
                'daily_profit': 0.0,
                'daily_drawdown': 0.0,
                'trades_count': 0,
                'trading_allowed': True
            }
            
        start = self.daily_start_balance.get(trade_date, 0.0)
        current = self.daily_balance[trade_date]
        peak = self.daily_peak_balance.get(trade_date, 0.0)
        trades = self.daily_trades.get(trade_date, [])
        
        return {
            'date': trade_date,
            'start_balance': start,
            'current_balance': current,
            'peak_balance': peak,
            'daily_profit': current - start,
            'daily_drawdown': self._calculate_drawdown(trade_date),
            'trades_count': len(trades),
            'trading_allowed': not self.trading_halted,
            'halt_reason': self.halt_reason if self.trading_halted else ""
        }
        
    def get_trade_history(self, trade_date: date = None) -> List[Dict]:
        if trade_date is None:
            trade_date = date.today()
            
        return self.daily_trades.get(trade_date, [])
        
    def reset_day(self, trade_date: date = None) -> None:
        if trade_date is None:
            trade_date = date.today()
            
        if trade_date in self.daily_balance:
            del self.daily_balance[trade_date]
        if trade_date in self.daily_start_balance:
            del self.daily_start_balance[trade_date]
        if trade_date in self.daily_peak_balance:
            del self.daily_peak_balance[trade_date]
        if trade_date in self.daily_trades:
            del self.daily_trades[trade_date]
            
        self.trading_halted = False
        self.halt_reason = ""
        
        logger.info(f"Reset trading day: {trade_date}")
        
    def get_weekly_stats(self) -> Dict:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        
        week_profit = 0.0
        week_trades = 0
        max_drawdown = 0.0
        
        for i in range(7):
            check_date = week_start + timedelta(days=i)
            if check_date in self.daily_balance:
                stats = self.get_daily_stats(check_date)
                week_profit += stats['daily_profit']
                week_trades += stats['trades_count']
                max_drawdown = max(max_drawdown, stats['daily_drawdown'])
                
        return {
            'week_start': week_start,
            'week_end': today,
            'week_profit': week_profit,
            'week_trades': week_trades,
            'max_drawdown': max_drawdown
        }
        
    def get_all_time_stats(self) -> Dict:
        total_profit = 0.0
        total_trades = 0
        max_drawdown = 0.0
        
        for trade_date, trades in self.daily_trades.items():
            stats = self.get_daily_stats(trade_date)
            total_profit += stats['daily_profit']
            total_trades += stats['trades_count']
            max_drawdown = max(max_drawdown, stats['daily_drawdown'])
            
        return {
            'total_profit': total_profit,
            'total_trades': total_trades,
            'max_drawdown': max_drawdown,
            'trading_days': len(self.daily_trades)
        }


daily_drawdown_tracker = DailyDrawdownTracker()
