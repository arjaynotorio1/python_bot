import sqlite3
import logging
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
from src.config.config import config

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DATABASE.PATH
        self._ensure_db_directory()
        self._initialize_database()
        
    def _ensure_db_directory(self) -> None:
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
        
    def _initialize_database(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket INTEGER UNIQUE,
                    symbol TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    lot_size REAL NOT NULL,
                    profit REAL,
                    commission REAL DEFAULT 0,
                    entry_time TIMESTAMP NOT NULL,
                    exit_time TIMESTAMP,
                    status TEXT NOT NULL DEFAULT 'open',
                    exit_reason TEXT,
                    reason TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE NOT NULL,
                    start_balance REAL NOT NULL,
                    end_balance REAL NOT NULL,
                    daily_profit REAL NOT NULL,
                    trades_count INTEGER NOT NULL,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    max_drawdown REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name TEXT UNIQUE NOT NULL,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    total_profit REAL DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    avg_profit REAL DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL,
                    take_profit REAL,
                    reason TEXT,
                    position_size REAL,
                    executed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_stats(date)
            """)
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    def add_trade(self, trade: Dict) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades (
                    ticket, symbol, signal_type, strategy, entry_price,
                    stop_loss, take_profit, lot_size, entry_time, status, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.get('ticket'),
                trade.get('symbol', config.GOLD.SYMBOL),
                trade.get('signal_type'),
                trade.get('strategy'),
                trade.get('entry_price'),
                trade.get('stop_loss'),
                trade.get('take_profit'),
                trade.get('lot_size'),
                trade.get('entry_time', datetime.now()),
                trade.get('status', 'open'),
                trade.get('reason', '')
            ))
            
            conn.commit()
            trade_id = cursor.lastrowid
            logger.info(f"Trade added: ID {trade_id}, {trade.get('signal_type')} at {trade.get('entry_price')}")
            return trade_id
    
    def close_trade(self, ticket: int, exit_price: float, profit: float,
                    exit_reason: str = "") -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE trades SET
                    exit_price = ?,
                    profit = ?,
                    exit_time = ?,
                    status = 'closed',
                    exit_reason = ?
                WHERE ticket = ?
            """, (exit_price, profit, datetime.now(), exit_reason, ticket))
            
            conn.commit()
            if cursor.rowcount > 0:
                logger.info(f"Trade {ticket} closed: ${profit:.2f}")
                return True
            return False
    
    def get_open_trades(self) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trades WHERE status = 'open' ORDER BY entry_time DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_trade_history(self, limit: int = 100) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trades WHERE status = 'closed' 
                ORDER BY exit_time DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_trade_by_ticket(self, ticket: int) -> Optional[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trades WHERE ticket = ?", (ticket,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def add_signal(self, signal: Dict) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO signals (
                    strategy, signal_type, confidence, entry_price,
                    stop_loss, take_profit, reason, position_size
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal.get('strategy'),
                signal.get('signal_type'),
                signal.get('confidence'),
                signal.get('entry_price'),
                signal.get('stop_loss'),
                signal.get('take_profit'),
                signal.get('reason', ''),
                signal.get('position_size', 0.01)
            ))
            
            conn.commit()
            signal_id = cursor.lastrowid
            logger.debug(f"Signal added: ID {signal_id}")
            return signal_id
    
    def update_strategy_performance(self, strategy_name: str, profit: float) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM strategy_performance WHERE strategy_name = ?
            """, (strategy_name,))
            result = cursor.fetchone()
            
            if result:
                data = dict(result)
                total_trades = data['total_trades'] + 1
                winning_trades = data['winning_trades'] + (1 if profit > 0 else 0)
                losing_trades = data['losing_trades'] + (1 if profit <= 0 else 0)
                total_profit = data['total_profit'] + profit
                win_rate = winning_trades / total_trades if total_trades > 0 else 0
                avg_profit = total_profit / total_trades if total_trades > 0 else 0
                
                cursor.execute("""
                    UPDATE strategy_performance SET
                        total_trades = ?,
                        winning_trades = ?,
                        losing_trades = ?,
                        total_profit = ?,
                        win_rate = ?,
                        avg_profit = ?,
                        last_updated = ?
                    WHERE strategy_name = ?
                """, (total_trades, winning_trades, losing_trades, total_profit,
                     win_rate, avg_profit, datetime.now(), strategy_name))
            else:
                winning_trades = 1 if profit > 0 else 0
                losing_trades = 1 if profit <= 0 else 0
                win_rate = 1.0 if profit > 0 else 0.0
                
                cursor.execute("""
                    INSERT INTO strategy_performance (
                        strategy_name, total_trades, winning_trades, losing_trades,
                        total_profit, win_rate, avg_profit
                    ) VALUES (?, 1, ?, ?, ?, ?, ?)
                """, (strategy_name, winning_trades, losing_trades, profit,
                     win_rate, profit))
            
            conn.commit()
    
    def get_strategy_performance(self, strategy_name: str = None) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if strategy_name:
                cursor.execute("""
                    SELECT * FROM strategy_performance WHERE strategy_name = ?
                """, (strategy_name,))
            else:
                cursor.execute("""
                    SELECT * FROM strategy_performance ORDER BY total_profit DESC
                """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def add_daily_stats(self, date: str, stats: Dict) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO daily_stats (
                    date, start_balance, end_balance, daily_profit,
                    trades_count, winning_trades, losing_trades,
                    win_rate, max_drawdown
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                date,
                stats.get('start_balance', 0),
                stats.get('end_balance', 0),
                stats.get('daily_profit', 0),
                stats.get('trades_count', 0),
                stats.get('winning_trades', 0),
                stats.get('losing_trades', 0),
                stats.get('win_rate', 0),
                stats.get('max_drawdown', 0)
            ))
            
            conn.commit()
            logger.info(f"Daily stats added for {date}")
    
    def get_daily_stats(self, date: str = None) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if date:
                cursor.execute("""
                    SELECT * FROM daily_stats WHERE date = ?
                """, (date,))
            else:
                cursor.execute("""
                    SELECT * FROM daily_stats ORDER BY date DESC LIMIT 30
                """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_portfolio_summary(self) -> Dict:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN profit <= 0 THEN 1 ELSE 0 END) as losing_trades,
                    SUM(profit) as total_profit,
                    AVG(profit) as avg_profit,
                    AVG(CASE WHEN status = 'closed' THEN profit END) as avg_closed_profit
                FROM trades WHERE status = 'closed'
            """)
            
            result = cursor.fetchone()
            return dict(result) if result else {}
    
    def cleanup_old_data(self, days: int = 90) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
            
            cursor.execute("""
                DELETE FROM signals WHERE created_at < ?
            """, (cutoff_date,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            logger.info(f"Cleaned up {deleted_count} old signal records")
            return deleted_count


db_manager = DatabaseManager()
