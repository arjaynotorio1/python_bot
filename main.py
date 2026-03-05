import logging
import time
import schedule
import argparse
from datetime import datetime, date
from typing import Optional
import MetaTrader5 as mt5
from src.config.config import config
from src.mt5.connection import mt5_connection
from src.mt5.gold_data import gold_data_fetcher
from src.strategies.technical import TechnicalAnalysisStrategy, RSIMeanReversionStrategy, BBBreakoutStrategy
from src.strategies.trend import TrendFollowingStrategy, GoldenCrossStrategy, ADXTrendStrategy
from src.strategies.fundamental import FundamentalStrategy, NewsBasedStrategy, MacroTrendStrategy
from src.risk.position_sizing import position_sizing
from src.risk.stop_loss import stop_loss_tp
from src.risk.drawdown import daily_drawdown_tracker
from src.alerts.telegram import telegram_alerts
from src.alerts.email import email_alerts
from src.database.db_manager import db_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/trading_bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class GoldTradingBot:
    def __init__(self):
        self.running = False
        self.strategies = []
        self._initialize_strategies()
        
    def _initialize_strategies(self) -> None:
        self.strategies = [
            TechnicalAnalysisStrategy(),
            RSIMeanReversionStrategy(),
            BBBreakoutStrategy(),
            TrendFollowingStrategy(),
            GoldenCrossStrategy(),
            ADXTrendStrategy(),
            FundamentalStrategy(),
            NewsBasedStrategy(),
            MacroTrendStrategy()
        ]
        
        logger.info(f"Initialized {len(self.strategies)} strategies")
        
    def connect_to_mt5(self) -> bool:
        logger.info("Connecting to MetaTrader 5...")
        if not mt5_connection.connect():
            logger.error("Failed to connect to MT5")
            telegram_alerts.send_error_alert("Failed to connect to MT5", "Connection failed")
            email_alerts.send_error_alert("Failed to connect to MT5", "Connection failed")
            return False
        
        logger.info("Connected to MT5 successfully")
        return True
    
    def check_positions(self) -> None:
        positions = mt5_connection.get_positions()
        
        for position in positions:
            current_price = position['price_current']
            entry_price = position['price_open']
            sl = position['sl']
            tp = position['tp']
            
            if sl and tp:
                risk = abs(entry_price - sl)
                reward = abs(tp - entry_price)
                
                new_sl = stop_loss_tp.update_trailing_stop(
                    entry_price, current_price, sl, position['type']
                )
                
                if new_sl and new_sl != sl:
                    self._modify_position(position['ticket'], new_sl, tp)
    
    def _modify_position(self, ticket: int, sl: float, tp: float) -> bool:
        try:
            position = mt5.positions_get(ticket=ticket)
            if not position:
                return False
                
            position = position[0]
            
            request = {
                'action': mt5.TRADE_ACTION_SLTP,
                'position': ticket,
                'sl': sl,
                'tp': tp,
                'symbol': position.symbol,
                'volume': position.volume
            }
            
            result = mt5.order_send(request)
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Position {ticket} modified: SL={sl:.2f}, TP={tp:.2f}")
                return True
            else:
                logger.error(f"Failed to modify position {ticket}: {result.comment}")
                return False
                
        except Exception as e:
            logger.error(f"Error modifying position {ticket}: {e}")
            return False
    
    def execute_trade(self, signal, lot_size: float) -> Optional[int]:
        if not config.IS_LIVE or config.PAPER_TRADING:
            logger.info(f"Paper trading: Would execute {signal.signal_type} at {signal.entry_price:.2f}")
            return None
        
        symbol_info = mt5.symbol_info(config.GOLD.SYMBOL)
        if symbol_info is None:
            logger.error(f"Symbol {config.GOLD.SYMBOL} not found")
            return None
            
        if not symbol_info.visible:
            if not mt5.symbol_select(config.GOLD.SYMBOL, True):
                logger.error(f"Failed to select symbol {config.GOLD.SYMBOL}")
                return None
        
        point = symbol_info.point
        
        request = {
            'action': mt5.TRADE_ACTION_DEAL,
            'symbol': config.GOLD.SYMBOL,
            'volume': lot_size,
            'type': mt5.ORDER_TYPE_BUY if signal.signal_type == 'BUY' else mt5.ORDER_TYPE_SELL,
            'price': signal.entry_price,
            'sl': signal.stop_loss,
            'tp': signal.take_profit,
            'deviation': 20,
            'magic': 234000,
            'comment': f"{signal.signal_type} - {signal.reason}",
            'type_time': mt5.ORDER_TIME_GTC,
            'type_filling': mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order failed: {result.retcode} - {result.comment}")
            telegram_alerts.send_error_alert(f"Order failed: {result.retcode}", result.comment)
            return None
            
        logger.info(f"Order executed: Ticket {result.order}, {signal.signal_type} {lot_size} lots at {signal.entry_price:.2f}")
        
        db_manager.add_trade({
            'ticket': result.order,
            'symbol': config.GOLD.SYMBOL,
            'signal_type': signal.signal_type,
            'strategy': signal.signal_type.split()[0],
            'entry_price': signal.entry_price,
            'stop_loss': signal.stop_loss,
            'take_profit': signal.take_profit,
            'lot_size': lot_size,
            'entry_time': datetime.now(),
            'reason': signal.reason
        })
        
        telegram_alerts.send_trade_alert(
            signal.signal_type, signal.entry_price, signal.stop_loss,
            signal.take_profit, signal.signal_type.split()[0], signal.reason
        )
        
        return result.order
    
    def analyze_market(self) -> None:
        logger.info("Analyzing market...")
        
        data = gold_data_fetcher.get_candles(config.STRATEGY.TECHNICAL_TIMEFRAME, count=200)
        
        if data is None or len(data) == 0:
            logger.warning("No market data available")
            return
        
        data = gold_data_fetcher.calculate_indicators(data)
        
        current_price = data.iloc[-1]['close']
        
        positions = mt5_connection.get_positions()
        open_positions_count = len(positions)
        
        if open_positions_count >= config.RISK.MAX_POSITIONS:
            logger.info(f"Max positions reached ({config.RISK.MAX_POSITIONS})")
            return
        
        for strategy in self.strategies:
            signal = strategy.analyze(data)
            
            if signal:
                if daily_drawdown_tracker.is_trading_allowed() and position_sizing.can_open_position():
                    atr = data.iloc[-1]['atr'] if 'atr' in data.columns else None
                    
                    lot_size = position_sizing.calculate_lot_size(
                        signal.entry_price, signal.stop_loss
                    )
                    
                    ticket = self.execute_trade(signal, lot_size)
                    
                    if ticket:
                        daily_drawdown_tracker.add_trade(0)
                    
                    db_manager.add_signal(signal.to_dict())
    
    def update_account_info(self) -> None:
        account_info = mt5_connection.get_account_info()
        
        if account_info:
            balance = account_info['balance']
            equity = account_info['equity']
            
            daily_drawdown_tracker.update_balance(equity)
            position_sizing.update_balance(balance)
            
            positions = mt5_connection.get_positions()
            open_profit = sum(pos['profit'] for pos in positions)
            
            daily_stats = daily_drawdown_tracker.get_daily_stats()
            
            telegram_alerts.send_status_update(
                balance, equity, len(positions), daily_stats['daily_profit']
            )
    
    def send_daily_summary(self) -> None:
        logger.info("Sending daily summary...")
        
        daily_stats = daily_drawdown_tracker.get_daily_stats()
        account_info = mt5_connection.get_account_info()
        
        if account_info and daily_stats:
            telegram_alerts.send_daily_summary(
                date.today().strftime('%Y-%m-%d'),
                account_info['balance'],
                daily_stats['daily_profit'],
                daily_stats['trades_count'],
                daily_stats.get('win_rate', 0)
            )
            
            email_alerts.send_daily_summary(
                date.today().strftime('%Y-%m-%d'),
                account_info['balance'],
                daily_stats['daily_profit'],
                daily_stats['trades_count'],
                daily_stats.get('win_rate', 0)
            )
            
            db_manager.add_daily_stats(
                date.today().strftime('%Y-%m-%d'),
                daily_stats
            )
    
    def run_backtest(self, strategy_name: str = None, days: int = 30) -> None:
        logger.info("Running backtest...")
        
        from src.backtesting.backtester import backtest_engine
        
        data = gold_data_fetcher.download_historical_data(config.STRATEGY.TECHNICAL_TIMEFRAME, days)
        
        if data is None:
            logger.error("Failed to download historical data")
            return
        
        if strategy_name:
            strategy = next((s for s in self.strategies if s.name == strategy_name), self.strategies[0])
            backtest_engine.run_backtest(strategy, data)
        else:
            for strategy in self.strategies:
                backtest_engine.run_backtest(strategy, data)
    
    def run(self) -> None:
        logger.info("Starting Gold Trading Bot...")
        
        if not self.connect_to_mt5():
            return
        
        self.running = True
        
        schedule.every(1).minutes.do(self.check_positions)
        schedule.every(5).minutes.do(self.analyze_market)
        schedule.every(15).minutes.do(self.update_account_info)
        schedule.every().day.at("23:59").do(self.send_daily_summary)
        
        self.analyze_market()
        self.update_account_info()
        
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down bot...")
            self.running = False
        finally:
            self.shutdown()
    
    def shutdown(self) -> None:
        logger.info("Shutting down...")
        mt5_connection.disconnect()
        logger.info("Bot shutdown complete")


def main():
    parser = argparse.ArgumentParser(description='Gold Trading Bot')
    parser.add_argument('--mode', choices=['live', 'backtest', 'dashboard'], default='live',
                       help='Run mode: live trading, backtesting, or dashboard')
    parser.add_argument('--strategy', type=str, help='Strategy name for backtesting')
    parser.add_argument('--days', type=int, default=30, help='Days for backtesting')
    
    args = parser.parse_args()
    
    bot = GoldTradingBot()
    
    if args.mode == 'dashboard':
        logger.info("Starting dashboard mode...")
        from src.dashboard.app import dashboard
        dashboard.run()
    elif args.mode == 'backtest':
        logger.info(f"Starting backtest mode for {args.days} days...")
        bot.run_backtest(args.strategy, args.days)
    else:
        logger.info(f"Starting live trading mode ({'PAPER' if config.PAPER_TRADING else 'LIVE'})")
        bot.run()


if __name__ == '__main__':
    main()
