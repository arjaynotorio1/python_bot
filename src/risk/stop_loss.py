import logging
from typing import Tuple, Optional
from src.config.config import config

logger = logging.getLogger(__name__)


class StopLossTakeProfit:
    def __init__(self):
        self.min_sl_pips = config.RISK.MIN_STOP_LOSS_PIPS
        self.min_tp_pips = config.RISK.MIN_TAKE_PROFIT_PIPS
        self.risk_reward_ratio = config.RISK.RISK_REWARD_RATIO
        self.trailing_stop_pips = config.STRATEGY.TRAILING_STOP_PIPS
        
    def calculate_atr_based_sl(self, entry_price: float, atr: float, 
                              signal_type: str, atr_multiplier: float = 1.5) -> float:
        if signal_type == 'BUY':
            sl = entry_price - (atr * atr_multiplier)
        else:
            sl = entry_price + (atr * atr_multiplier)
            
        min_sl = self.min_sl_pips * config.GOLD.POINT
        if signal_type == 'BUY':
            sl = min(sl, entry_price - min_sl)
        else:
            sl = max(sl, entry_price + min_sl)
            
        logger.debug(f"ATR-based SL: {sl:.2f} (ATR: {atr:.2f})")
        return sl
    
    def calculate_fixed_pip_sl(self, entry_price: float, signal_type: str, 
                              pips: int = None) -> float:
        if pips is None:
            pips = self.min_sl_pips
            
        sl_distance = pips * config.GOLD.POINT
        
        if signal_type == 'BUY':
            sl = entry_price - sl_distance
        else:
            sl = entry_price + sl_distance
            
        logger.debug(f"Fixed pip SL: {sl:.2f} ({pips} pips)")
        return sl
    
    def calculate_support_resistance_sl(self, entry_price: float, signal_type: str,
                                      support: float = None, resistance: float = None) -> float:
        if signal_type == 'BUY':
            if support:
                sl = support - (self.min_sl_pips * config.GOLD.POINT)
            else:
                sl = self.calculate_fixed_pip_sl(entry_price, 'BUY')
        else:
            if resistance:
                sl = resistance + (self.min_sl_pips * config.GOLD.POINT)
            else:
                sl = self.calculate_fixed_pip_sl(entry_price, 'SELL')
                
        logger.debug(f"Support/Resistance SL: {sl:.2f}")
        return sl
    
    def calculate_trailing_stop(self, entry_price: float, current_price: float,
                               signal_type: str, trail_distance: int = None) -> float:
        if trail_distance is None:
            trail_distance = self.trailing_stop_pips
            
        trail_distance_pips = trail_distance * config.GOLD.POINT
        
        if signal_type == 'BUY':
            if current_price > entry_price + trail_distance_pips:
                sl = current_price - trail_distance_pips
            else:
                sl = entry_price - trail_distance_pips
        else:
            if current_price < entry_price - trail_distance_pips:
                sl = current_price + trail_distance_pips
            else:
                sl = entry_price + trail_distance_pips
                
        logger.debug(f"Trailing stop: {sl:.2f}")
        return sl
    
    def calculate_tp(self, entry_price: float, stop_loss: float, 
                    signal_type: str, risk_reward_ratio: float = None) -> float:
        if risk_reward_ratio is None:
            risk_reward_ratio = self.risk_reward_ratio
            
        risk_distance = abs(entry_price - stop_loss)
        tp_distance = risk_distance * risk_reward_ratio
        
        if signal_type == 'BUY':
            tp = entry_price + tp_distance
        else:
            tp = entry_price - tp_distance
            
        min_tp = self.min_tp_pips * config.GOLD.POINT
        if signal_type == 'BUY':
            tp = max(tp, entry_price + min_tp)
        else:
            tp = min(tp, entry_price - min_tp)
            
        logger.debug(f"Take profit: {tp:.2f} (R:R = {risk_reward_ratio:.1f})")
        return tp
    
    def calculate_sl_tp(self, entry_price: float, signal_type: str, 
                       atr: float = None, atr_multiplier: float = 1.5) -> Tuple[float, float]:
        if atr:
            sl = self.calculate_atr_based_sl(entry_price, atr, signal_type, atr_multiplier)
        else:
            sl = self.calculate_fixed_pip_sl(entry_price, signal_type)
            
        tp = self.calculate_tp(entry_price, sl, signal_type)
        
        return sl, tp
    
    def validate_sl_tp(self, entry_price: float, stop_loss: float, 
                       take_profit: float, signal_type: str) -> bool:
        if signal_type == 'BUY':
            if stop_loss >= entry_price:
                logger.warning("Stop loss must be below entry price for BUY")
                return False
            if take_profit <= entry_price:
                logger.warning("Take profit must be above entry price for BUY")
                return False
        else:
            if stop_loss <= entry_price:
                logger.warning("Stop loss must be above entry price for SELL")
                return False
            if take_profit >= entry_price:
                logger.warning("Take profit must be below entry price for SELL")
                return False
        
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        
        if reward < risk * self.risk_reward_ratio:
            logger.warning(f"Risk:Reward ratio ({reward/risk:.2f}) below minimum ({self.risk_reward_ratio:.2f})")
            return False
            
        return True
    
    def update_trailing_stop(self, current_price: float, entry_price: float,
                            existing_sl: float, signal_type: str) -> Optional[float]:
        if signal_type == 'BUY':
            new_sl = self.calculate_trailing_stop(entry_price, current_price, 'BUY')
            if new_sl > existing_sl:
                logger.info(f"Trailing stop updated: {existing_sl:.2f} -> {new_sl:.2f}")
                return new_sl
        else:
            new_sl = self.calculate_trailing_stop(entry_price, current_price, 'SELL')
            if new_sl < existing_sl:
                logger.info(f"Trailing stop updated: {existing_sl:.2f} -> {new_sl:.2f}")
                return new_sl
                
        return None
    
    def calculate_breakeven_sl(self, entry_price: float, current_price: float,
                               signal_type: str, trigger_pips: int = 20) -> Optional[float]:
        trigger_distance = trigger_pips * config.GOLD.POINT
        
        if signal_type == 'BUY':
            if current_price >= entry_price + trigger_distance:
                return entry_price
        else:
            if current_price <= entry_price - trigger_distance:
                return entry_price
                
        return None


stop_loss_tp = StopLossTakeProfit()
