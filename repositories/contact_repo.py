from database import Database
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
logger = logging.getLogger(__name__)


class ContactRepository:
    
    @staticmethod
    async def create_contact(
        preview_token: str, 
        book_id: int, 
        phone_number: str
    ) -> Optional[Dict[str, Any]]:
        """Save phone number contact for preview notification"""
        query = """
            INSERT INTO clients_contacts (preview_token, book_id, phone_number)
            VALUES (?, ?, ?)
        """
        await Database.execute(query, (preview_token, book_id, phone_number))
        logger.info(f"Saved phone contact for preview {preview_token}")
        
        # Return the saved contact
        return await Database.fetch_one(
            "SELECT * FROM clients_contacts  WHERE preview_token = ? AND phone_number = ? ORDER BY id DESC LIMIT 1",
            (preview_token, phone_number)
        )
    
    @staticmethod
    async def get_pending_contacts(preview_token: str) -> List[Dict[str, Any]]:
        """Get all contacts waiting for notification (message not sent yet)"""
        query = """
            SELECT * FROM clients_contacts
            WHERE preview_token = ? AND message_sent = 0
        """
        return await Database.fetch_all(query, (preview_token,))
    
    @staticmethod
    async def mark_message_sent(contact_id: int) -> None:
        """Mark message as sent"""
        query = "UPDATE clients_contacts SET message_sent = 1 WHERE id = ?"
        await Database.execute(query, (contact_id,))
        logger.info(f"Marked message as sent for contact {contact_id}")
    @staticmethod
    async def get_all_contacts(since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get all contacts with optional time filter"""
        if since:
            query = """
                SELECT c.*, b.title as book_title, p.child_name
                FROM clients_contacts c
                LEFT JOIN books b ON c.book_id = b.id
                LEFT JOIN previews p ON c.preview_token = p.preview_token
                WHERE c.submitted_at >= ?
                ORDER BY c.submitted_at DESC
            """
            results = await Database.fetch_all(query, (since.isoformat(),))
        else:
            query = """
                SELECT c.*, b.title as book_title, p.child_name
                FROM clients_contacts c
                LEFT JOIN books b ON c.book_id = b.id
                LEFT JOIN previews p ON c.preview_token = p.preview_token
                ORDER BY c.submitted_at DESC
            """
            results = await Database.fetch_all(query)
        
        return results
