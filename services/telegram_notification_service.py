import httpx
import logging
from datetime import datetime
from typing import Optional
from config import settings

logger = logging.getLogger(__name__)


class TelegramNotificationService:
    """
    Service for sending Telegram notifications to admin.
    Completely isolated - failures won't affect main application flow.
    """
    
    @staticmethod
    async def send_message(message: str) -> bool:
        """
        Send a message to admin's Telegram chat.
        
        Args:
            message: Text message to send
            
        Returns:
            bool: True if sent successfully, False otherwise (never raises)
        """
        # Check if notifications are enabled
        if not settings.TELEGRAM_NOTIFICATIONS_ENABLED:
            logger.debug("Telegram notifications are disabled")
            return False
        
        # Check if credentials are configured
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
            logger.warning("Telegram bot credentials not configured")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            
            payload = {
                "chat_id": settings.TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML"  # Allows basic formatting
            }
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=payload)
                
                if response.status_code == 200:
                    logger.info("Telegram notification sent successfully")
                    return True
                else:
                    logger.warning(f"Telegram API error: {response.status_code} - {response.text}")
                    return False
                    
        except httpx.TimeoutException:
            logger.warning("Telegram notification timeout (non-critical)")
            return False
        except Exception as e:
            logger.warning(f"Failed to send Telegram notification (non-critical): {e}")
            return False
    
    @staticmethod
    async def notify_preview_created(
        preview_token: str,
        child_name: str,
        book_title: str,
        book_gender: str
    ) -> None:
        """
        Notify admin when a new preview is created.
        Non-blocking - runs in background, never raises exceptions.
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        message = f"""
🎨 <b>New Preview Created!</b>

👶 <b>Child:</b> {child_name}
📖 <b>Book:</b> {book_title} ({book_gender})
🔑 <b>Token:</b> <code>{preview_token}</code>
⏰ <b>Time:</b> {timestamp}

Check admin dashboard for details.
        """.strip()
        
        await TelegramNotificationService.send_message(message)
    
    @staticmethod
    async def notify_order_created(
        order_number: str,
        child_name: str,
        customer_name: str,
        book_title: str,
        total_amount: float,
        display_currency: str
    ) -> None:
        """
        Notify admin when a new order is placed.
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        message = f"""
🎉 <b>New Order Placed!</b>

📦 <b>Order #:</b> <code>{order_number}</code>
👶 <b>Child:</b> {child_name}
👤 <b>Customer:</b> {customer_name}
📖 <b>Book:</b> {book_title}
💰 <b>Amount:</b> {total_amount} {display_currency}
⏰ <b>Time:</b> {timestamp}

Check admin dashboard to process.
        """.strip()
        
        await TelegramNotificationService.send_message(message)
