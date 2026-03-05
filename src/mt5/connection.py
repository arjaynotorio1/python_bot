import MetaTrader5 as mt5
import logging
from typing import Optional, Tuple
from datetime import datetime
from src.config.config import config

logger = logging.getLogger(__name__)


class MT5Connection:
    def __init__(self):
        self._initialized = False
        self._connected = False
        self._account_info = None
        
    def initialize(self) -> bool:
        if self._initialized:
            logger.warning("MT5 already initialized")
            return True
            
        try:
            if config.MT5.PATH:
                mt5.initialize(path=config.MT5.PATH)
            else:
                mt5.initialize()
            
            self._initialized = True
            logger.info("MT5 initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize MT5: {e}")
            return False
    
    def login(self) -> bool:
        if not self._initialized:
            logger.error("MT5 not initialized")
            return False
            
        try:
            if config.MT5.LOGIN and config.MT5.PASSWORD and config.MT5.SERVER:
                authorized = mt5.login(
                    login=int(config.MT5.LOGIN),
                    password=config.MT5.PASSWORD,
                    server=config.MT5.SERVER
                )
                
                if not authorized:
                    logger.error(f"Login failed: {mt5.last_error()}")
                    return False
                
                self._connected = True
                logger.info(f"Logged in successfully to account {config.MT5.LOGIN}")
                return True
            else:
                logger.warning("MT5 credentials not configured, using current connection")
                self._connected = True
                return True
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    def connect(self) -> bool:
        if not self.initialize():
            return False
            
        if not self.login():
            return False
            
        self._account_info = mt5.account_info()
        if self._account_info:
            logger.info(f"Connected to account: {self._account_info.login}")
            return True
        
        logger.error("Failed to get account info")
        return False
    
    def disconnect(self) -> None:
        if self._connected:
            mt5.shutdown()
            self._connected = False
            self._initialized = False
            logger.info("Disconnected from MT5")
    
    def is_connected(self) -> bool:
        if not self._connected:
            return False
            
        account_info = mt5.account_info()
        return account_info is not None
    
    def get_account_info(self) -> Optional[dict]:
        if not self.is_connected():
            return None
            
        account_info = mt5.account_info()
        if not account_info:
            return None
            
        return {
            'login': account_info.login,
            'balance': account_info.balance,
            'equity': account_info.equity,
            'margin': account_info.margin,
            'margin_free': account_info.margin_free,
            'margin_level': account_info.margin_level,
            'profit': account_info.profit,
            'currency': account_info.currency
        }
    
    def get_positions(self) -> list:
        if not self.is_connected():
            return []
            
        positions = mt5.positions_get(symbol=config.GOLD.SYMBOL)
        if positions is None:
            return []
            
        return [{
            'ticket': pos.ticket,
            'symbol': pos.symbol,
            'type': 'BUY' if pos.type == 0 else 'SELL',
            'volume': pos.volume,
            'price_open': pos.price_open,
            'sl': pos.sl,
            'tp': pos.tp,
            'price_current': pos.price_current,
            'profit': pos.profit,
            'comment': pos.comment,
            'time': datetime.fromtimestamp(pos.time)
        } for pos in positions]
    
    def get_orders(self) -> list:
        if not self.is_connected():
            return []
            
        orders = mt5.orders_get(symbol=config.GOLD.SYMBOL)
        if orders is None:
            return []
            
        return [{
            'ticket': order.ticket,
            'symbol': order.symbol,
            'type': 'BUY' if order.type == 0 else 'SELL',
            'volume': order.volume,
            'price_open': order.price_open,
            'sl': order.sl,
            'tp': order.tp,
            'comment': order.comment,
            'time': datetime.fromtimestamp(order.time_setup)
        } for order in orders]
    
    def get_history(self, from_date: datetime, to_date: datetime) -> list:
        if not self.is_connected():
            return []
            
        history = mt5.history_deals_get(from_date, to_date)
        if history is None:
            return []
            
        return [{
            'ticket': deal.ticket,
            'symbol': deal.symbol,
            'type': 'BUY' if deal.type == 0 else 'SELL',
            'volume': deal.volume,
            'price': deal.price,
            'profit': deal.profit,
            'commission': deal.commission,
            'swap': deal.swap,
            'time': datetime.fromtimestamp(deal.time),
            'comment': deal.comment
        } for deal in history]
    
    def check_connection(self) -> bool:
        return self.is_connected()
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


mt5_connection = MT5Connection()
