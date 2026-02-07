# Database operations for orders
from database import Database
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from schemas.requests import CreateOrderRequest
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
        order_request: CreateOrderRequest,
        total_amount: float
    ) -> Dict[str, Any]:
        """Create new order record"""
        order_number = await OrderRepository.generate_order_number()
        
        query = """
            INSERT INTO orders (
                book_id, preview_id, order_number, child_name,
                customer_name, customer_email, customer_phone,
                shipping_address, shipping_country, national_address_code,
                total_amount, display_currency, display_amount,
                payment_status, payment_method, order_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 'cod', 'received')
        """
        
        async with Database.connection() as conn:
            cursor = await conn.execute(
                query,
                (
                    book_id, preview_id, order_number, child_name,
                    order_request.customer_name, 
                    order_request.customer_email, 
                    order_request.customer_phone,
                    order_request.shipping_address, 
                    order_request.shipping_country, 
                    order_request.national_address_code,
                    total_amount,
                    order_request.display_currency, 
                    order_request.display_amount,   
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
    @staticmethod
    async def get_all_orders(since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get all orders with optional time filter"""
        if since:
            query = """
                SELECT o.*, b.title as book_title, b.gender as book_gender,
                    p.preview_token, p.child_name as preview_child_name
                FROM orders o
                LEFT JOIN books b ON o.book_id = b.id
                LEFT JOIN previews p ON o.preview_id = p.id
                WHERE o.created_at >= ?
                ORDER BY o.created_at DESC
            """
            results = await Database.fetch_all(query, (since.isoformat(),))
        else:
            query = """
                SELECT o.*, b.title as book_title, b.gender as book_gender,
                    p.preview_token, p.child_name as preview_child_name
                FROM orders o
                LEFT JOIN books b ON o.book_id = b.id
                LEFT JOIN previews p ON o.preview_id = p.id
                ORDER BY o.created_at DESC
            """
            results = await Database.fetch_all(query)
        
        return results
