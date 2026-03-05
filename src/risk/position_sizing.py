import logging
from typing import Dict
from src.config.config import config

logger = logging.getLogger(__name__)


class PositionSizing:
    def __init__(self):
        self.account_balance = 10000.0
        self.risk_per_trade = config.RISK.RISK_PER_TRADE
        self.default_lot_size = config.RISK.DEFAULT_LOT_SIZE
        self.max_positions = config.RISK.MAX_POSITIONS
        self.current_positions = 0
        
    def update_balance(self, balance: float) -> None:
        self.account_balance = balance
        logger.info(f"Account balance updated: ${balance:.2f}")
        
    def update_positions_count(self, count: int) -> None:
        self.current_positions = count
        logger.debug(f"Current positions count: {count}")
        
    def calculate_lot_size(self, entry_price: float, stop_loss: float, 
                          risk_amount: float = None) -> float:
        if risk_amount is None:
            risk_amount = self.account_balance * self.risk_per_trade
            
        if stop_loss is None or entry_price is None:
            logger.warning("Missing stop loss or entry price, using default lot size")
            return self.default_lot_size
        
        risk_per_lot = abs(entry_price - stop_loss) * 100
        if risk_per_lot == 0:
            return self.default_lot_size
            
        lot_size = risk_amount / risk_per_lot
        
        lot_size = max(0.01, min(lot_size, 10.0))
        
        logger.debug(f"Calculated lot size: {lot_size:.2f} (risk: ${risk_amount:.2f})")
        return lot_size
    
    def calculate_fixed_fractional_lot_size(self, fraction: float = 0.02) -> float:
        risk_amount = self.account_balance * fraction
        assumed_stop_loss = 50.0 * config.GOLD.POINT
        assumed_risk_per_lot = assumed_stop_loss * 100
        
        lot_size = risk_amount / assumed_risk_per_lot if assumed_risk_per_lot > 0 else self.default_lot_size
        lot_size = max(0.01, min(lot_size, 10.0))
        
        logger.debug(f"Fixed fractional lot size: {lot_size:.2f}")
        return lot_size
    
    def calculate_kelly_lot_size(self, win_rate: float, avg_win: float, 
                                 avg_loss: float) -> float:
        if win_rate <= 0 or avg_loss == 0:
            return self.default_lot_size
            
        win_loss_ratio = avg_win / abs(avg_loss)
        kelly = win_rate - ((1 - win_rate) / win_loss_ratio)
        
        kelly = min(kelly, 0.25)
        
        if kelly < 0:
            kelly = 0.01
            
        lot_size = self.account_balance * kelly
        
        assumed_stop_loss = 50.0 * config.GOLD.POINT
        lot_size = lot_size / (assumed_stop_loss * 100) if assumed_stop_loss > 0 else self.default_lot_size
        lot_size = max(0.01, min(lot_size, 10.0))
        
        logger.debug(f"Kelly lot size: {lot_size:.2f} (Kelly: {kelly:.2%})")
        return lot_size
    
    def calculate_atr_based_lot_size(self, atr: float, atr_multiplier: float = 1.5) -> float:
        if atr is None or atr == 0:
            return self.default_lot_size
            
        volatility_adjustment = 1.0 / (atr * 100)
        base_lot_size = self.account_balance * self.risk_per_trade
        
        lot_size = base_lot_size * volatility_adjustment * atr_multiplier
        lot_size = max(0.01, min(lot_size, 10.0))
        
        logger.debug(f"ATR-based lot size: {lot_size:.2f} (ATR: {atr:.2f})")
        return lot_size
    
    def can_open_position(self) -> bool:
        if self.current_positions >= self.max_positions:
            logger.warning(f"Max positions reached ({self.max_positions})")
            return False
            
        return True
    
    def get_max_exposure(self) -> float:
        return self.account_balance * (1 - config.RISK.MAX_DAILY_DRAWDOWN)
    
    def get_available_margin(self) -> float:
        max_exposure = self.get_max_exposure()
        current_exposure = self.current_positions * self.default_lot_size * 1000
        available = max(0, max_exposure - current_exposure)
        
        logger.debug(f"Available margin: ${available:.2f}")
        return available


position_sizing = PositionSizing()
