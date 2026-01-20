# Database operations for orders
from database import Database
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class OrderRepository:
    
    @staticmethod
    async def generate_order_number() -> str:
        """
        Generate unique order number: KK-YYYYMMDD-XXXX
        Example: KK-20260115-0001
        """
        today = datetime.utcnow().strftime("%Y%m%d")
        
        # Get today's order count
        query = """
            SELECT COUNT(*) as count 
            FROM orders 
            WHERE order_number LIKE ?
        """
        result = await Database.fetch_one(query, (f"KK-{today}-%",))
        count = result['count'] + 1 if result else 1
        
        return f"KK-{today}-{count:04d}"
    
    @staticmethod
    async def create_order(
        book_id: int,
        preview_id: int,
        child_name: str,
        child_age: Optional[int],
        customer_name: str,
        customer_email: str,
        customer_phone: Optional[str],
        shipping_address: Optional[str],
        shipping_country: Optional[str],
        total_amount: float
    ) -> Dict[str, Any]:
        """Create new order record"""
        order_number = await OrderRepository.generate_order_number()
        
        query = """
            INSERT INTO orders (
                book_id, preview_id, order_number, child_name, child_age,
                customer_name, customer_email, customer_phone,
                shipping_address, shipping_country, total_amount,
                payment_status, order_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 'received')
        """
        
        async with Database.connection() as conn:
            cursor = await conn.execute(
                query,
                (
                    book_id, preview_id, order_number, child_name, child_age,
                    customer_name, customer_email, customer_phone,
                    shipping_address, shipping_country, total_amount
                )
            )
            await conn.commit()
            order_id = cursor.lastrowid
        
        logger.info(f"Order created: {order_number} (ID: {order_id})")
        
        return {
            'id': order_id,
            'order_number': order_number
        }
    
    @staticmethod
    async def get_by_order_number(order_number: str) -> Optional[Dict[str, Any]]:
        """Get order by order number"""
        query = "SELECT * FROM orders WHERE order_number = ?"
        return await Database.fetch_one(query, (order_number,))
    
    @staticmethod
    async def get_by_id(order_id: int) -> Optional[Dict[str, Any]]:
        """Get order by ID"""
        query = "SELECT * FROM orders WHERE id = ?"
        return await Database.fetch_one(query, (order_id,))
    
    @staticmethod
    async def update_payment_status(
        order_id: int,
        payment_status: str,
        stripe_payment_id: Optional[str] = None
    ):
        """Update payment status (for Stripe webhook later)"""
        query = """
            UPDATE orders 
            SET payment_status = ?,
                stripe_payment_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        
        await Database.execute(query, (payment_status, stripe_payment_id, order_id))
        logger.info(f"Order {order_id} payment status: {payment_status}")
    
    @staticmethod
    async def verify_email(order_number: str, email: str) -> bool:
        """Verify customer email for order"""
        query = """
            SELECT customer_email 
            FROM orders 
            WHERE order_number = ?
        """
        result = await Database.fetch_one(query, (order_number,))
        
        if not result:
            return False
        
        return result['customer_email'].lower() == email.lower()
