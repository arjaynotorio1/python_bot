import logging
from typing import Optional
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from src.config.config import config

logger = logging.getLogger(__name__)


class TelegramAlerts:
    def __init__(self):
        self.bot_token = config.TELEGRAM.BOT_TOKEN
        self.chat_id = config.TELEGRAM.CHAT_ID
        self.enabled = config.TELEGRAM.ENABLED
        self.bot = None
        
        if self.enabled and self.bot_token:
            try:
                self.bot = Bot(token=self.bot_token)
                logger.info("Telegram bot initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Telegram bot: {e}")
                self.enabled = False
    
    async def send_message(self, message: str) -> bool:
        if not self.enabled or not self.bot or not self.chat_id:
            logger.debug("Telegram alerts disabled or not configured")
            return False
            
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message)
            logger.info(f"Telegram message sent: {message[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    def send_trade_alert(self, signal_type: str, entry_price: float, 
                        stop_loss: float, take_profit: float, 
                        strategy: str, reason: str) -> bool:
        if not self.enabled:
            return False
            
        emoji = "🟢" if signal_type == "BUY" else "🔴"
        message = (
            f"{emoji} *NEW TRADE*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📊 *Strategy:* {strategy}\n"
            f"📈 *Signal:* {signal_type}\n"
            f"💰 *Entry:* ${entry_price:.2f}\n"
            f"🛑 *Stop Loss:* ${stop_loss:.2f}\n"
            f"🎯 *Take Profit:* ${take_profit:.2f}\n"
            f"ℹ️ *Reason:* {reason}\n"
        )
        
        import asyncio
        return asyncio.run(self.send_message(message))
    
    def send_position_closed(self, entry_price: float, exit_price: float,
                           profit: float, strategy: str, reason: str) -> bool:
        if not self.enabled:
            return False
            
        emoji = "✅" if profit > 0 else "❌"
        profit_percent = (profit / (entry_price * 100)) * 100
        message = (
            f"{emoji} *POSITION CLOSED*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📊 *Strategy:* {strategy}\n"
            f"💰 *Entry:* ${entry_price:.2f}\n"
            f"💰 *Exit:* ${exit_price:.2f}\n"
            f"💵 *Profit:* ${profit:.2f} ({profit_percent:.2f}%)\n"
            f"ℹ️ *Reason:* {reason}\n"
        )
        
        import asyncio
        return asyncio.run(self.send_message(message))
    
    def send_daily_summary(self, date: str, balance: float, profit: float,
                          trades_count: int, win_rate: float) -> bool:
        if not self.enabled:
            return False
            
        emoji = "🟢" if profit > 0 else "🔴"
        profit_percent = (profit / (balance - profit)) * 100 if balance != profit else 0
        message = (
            f"📊 *DAILY SUMMARY*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📅 *Date:* {date}\n"
            f"💰 *Balance:* ${balance:.2f}\n"
            f"💵 *Daily P&L:* ${profit:.2f} ({profit_percent:.2f}%)\n"
            f"📈 *Trades:* {trades_count}\n"
            f"✅ *Win Rate:* {win_rate:.2%}\n"
        )
        
        import asyncio
        return asyncio.run(self.send_message(message))
    
    def send_error_alert(self, error: str, context: str = "") -> bool:
        if not self.enabled:
            return False
            
        message = (
            f"⚠️ *ERROR ALERT*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"❌ *Error:* {error}\n"
            f"ℹ️ *Context:* {context}\n"
        )
        
        import asyncio
        return asyncio.run(self.send_message(message))
    
    def send_stop_loss_alert(self, position_type: str, entry_price: float,
                            exit_price: float, loss: float) -> bool:
        if not self.enabled:
            return False
            
        loss_percent = (loss / (entry_price * 100)) * 100
        message = (
            f"🛑 *STOP LOSS HIT*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📊 *Position:* {position_type}\n"
            f"💰 *Entry:* ${entry_price:.2f}\n"
            f"💰 *Exit:* ${exit_price:.2f}\n"
            f"❌ *Loss:* ${loss:.2f} ({loss_percent:.2f}%)\n"
        )
        
        import asyncio
        return asyncio.run(self.send_message(message))
    
    def send_take_profit_alert(self, position_type: str, entry_price: float,
                              exit_price: float, profit: float) -> bool:
        if not self.enabled:
            return False
            
        profit_percent = (profit / (entry_price * 100)) * 100
        message = (
            f"🎯 *TAKE PROFIT HIT*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📊 *Position:* {position_type}\n"
            f"💰 *Entry:* ${entry_price:.2f}\n"
            f"💰 *Exit:* ${exit_price:.2f}\n"
            f"✅ *Profit:* ${profit:.2f} ({profit_percent:.2f}%)\n"
        )
        
        import asyncio
        return asyncio.run(self.send_message(message))
    
    def send_risk_alert(self, alert_type: str, value: float, limit: float) -> bool:
        if not self.enabled:
            return False
            
        message = (
            f"⚠️ *RISK ALERT*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🚨 *Type:* {alert_type}\n"
            f"📊 *Value:* {value:.2%}\n"
            f"🎚️ *Limit:* {limit:.2%}\n"
        )
        
        import asyncio
        return asyncio.run(self.send_message(message))
    
    def send_status_update(self, balance: float, equity: float, 
                           open_positions: int, daily_profit: float) -> bool:
        if not self.enabled:
            return False
            
        emoji = "🟢" if daily_profit > 0 else "🔴"
        message = (
            f"📊 *STATUS UPDATE*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 *Balance:* ${balance:.2f}\n"
            f"💵 *Equity:* ${equity:.2f}\n"
            f"📈 *Open Positions:* {open_positions}\n"
            f"💵 *Daily P&L:* {emoji} ${daily_profit:.2f}\n"
        )
        
        import asyncio
        return asyncio.run(self.send_message(message))


telegram_alerts = TelegramAlerts()
