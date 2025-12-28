import os
import aiosqlite
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from config import settings
import logging

logger = logging.getLogger(__name__)


class Database:
    _db_path: str = settings.DATABASE_URL
    
    @classmethod
    async def initialize(cls):
        """Initialize database and create tables if they don't exist"""
        # Ensure directory exists for SQLite file
        os.makedirs(os.path.dirname(cls._db_path), exist_ok=True)
        logger.info(f"Initializing database at: {cls._db_path}")
        
        # Configure SQLite for better concurrency
        async with cls.connection() as conn:
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA busy_timeout=5000")
            await conn.execute("PRAGMA synchronous=NORMAL")
            await conn.commit()
            logger.info("SQLite WAL mode enabled")
        
        await cls._create_tables()
    
    @classmethod
    async def close(cls):
        """Close database connections - placeholder for cleanup if needed"""
        logger.info("Database cleanup completed")
    
    @classmethod
    @asynccontextmanager
    async def connection(cls):
        """Context manager for database connections"""
        async with aiosqlite.connect(cls._db_path) as conn:
            conn.row_factory = aiosqlite.Row  # Enable dict-like access
            yield conn
    
    @classmethod
    async def execute(cls, query: str, params: tuple = None) -> None:
        """Execute a query without returning results"""
        async with cls.connection() as conn:
            await conn.execute(query, params or ())
            await conn.commit()
            logger.debug(f"Executed: {query[:100]}...")
    
    @classmethod
    async def execute_batch(cls, queries: List[tuple]) -> None:
        """
        Execute multiple different queries in a single connection/transaction.
        Each item in `queries` should be (query_str, params_tuple).
        """
        async with cls.connection() as conn:
            for query, params in queries:
                await conn.execute(query, params or ())
            await conn.commit()
            logger.debug(f"Executed batch of {len(queries)} queries")
    
    @classmethod
    async def fetch_one(cls, query: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        """Fetch a single row"""
        async with cls.connection() as conn:
            cursor = await conn.execute(query, params or ())
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    @classmethod
    async def fetch_all(cls, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Fetch multiple rows"""
        async with cls.connection() as conn:
            cursor = await conn.execute(query, params or ())
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    @classmethod
    async def execute_many(cls, query: str, params_list: List[tuple]) -> None:
        """Execute query multiple times with different parameters"""
        async with cls.connection() as conn:
            await conn.executemany(query, params_list)
            await conn.commit()
            logger.debug(f"Executed many ({len(params_list)} times): {query[:100]}...")
    
    @classmethod
    async def health_check(cls) -> bool:
        """Check if database is accessible"""
        try:
            async with cls.connection() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    @classmethod
    async def _create_tables(cls):
        """Create all database tables"""
        tables = [
            """
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                age_range TEXT,
                category TEXT,
                price REAL NOT NULL,
                template_path TEXT NOT NULL,
                character_count INTEGER NOT NULL,
                cover_image_path TEXT,
                preview_images TEXT,
                is_active INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS previews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                preview_token TEXT UNIQUE NOT NULL,
                original_photo_path TEXT NOT NULL,
                preview_pptx_path TEXT,
                preview_pdf_path TEXT,
                swapped_images_paths TEXT,
                preview_status TEXT DEFAULT 'processing',
                error_message TEXT,
                expires_at DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (book_id) REFERENCES books(id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                preview_id INTEGER,
                order_number TEXT UNIQUE NOT NULL,
                child_name TEXT NOT NULL,
                child_age INTEGER,
                customer_name TEXT NOT NULL,
                customer_email TEXT NOT NULL,
                customer_phone TEXT,
                shipping_address TEXT,
                shipping_country TEXT,
                total_amount REAL NOT NULL,
                payment_status TEXT DEFAULT 'pending',
                payment_method TEXT,
                stripe_payment_id TEXT,
                order_status TEXT DEFAULT 'received',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (book_id) REFERENCES books(id),
                FOREIGN KEY (preview_id) REFERENCES previews(id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS generated_books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER UNIQUE NOT NULL,
                original_photo_path TEXT NOT NULL,
                swapped_images_paths TEXT,
                final_pptx_path TEXT,
                final_pdf_path TEXT,
                generation_status TEXT DEFAULT 'queued',
                characters_completed INTEGER DEFAULT 0,
                estimated_time_minutes INTEGER,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                processing_started_at DATETIME,
                processing_completed_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS generation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                generated_book_id INTEGER NOT NULL,
                step TEXT NOT NULL,
                status TEXT NOT NULL,
                api_provider TEXT,
                api_cost REAL,
                error_details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (generated_book_id) REFERENCES generated_books(id)
            );
            """
        ]
        
        async with cls.connection() as conn:
            # Create tables
            for table_sql in tables:
                await conn.execute(table_sql)
            
            await conn.commit()
            logger.info("All database tables created successfully")
