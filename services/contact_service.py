from twilio.rest import Client
from config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)


class ContactService:
    
    @staticmethod
    async def send_preview_ready_notification(
        to_number: str, 
        preview_token: str, 
        book_id: int
    ) -> dict:
        """
        Send SMS when preview is ready
        
        Args:
            to_number: Recipient phone number (e.g., '+966501234567')
            preview_token: Preview token for generating link
            book_id: Book ID for generating link
        
        Returns:
            dict: {"success": bool, "message_sid": str or "error": str}
        """
        
        # Generate shareable link
        preview_link = f"{settings.FRONTEND_BASE_URL}/books/{book_id}/preview?token={preview_token}"
        
        # Arabic message (same as before)
        message_body = (
            f"🎉 معاينة قصتك جاهزة!\n\n"
            f"اضغط هنا لمشاهدتها:\n{preview_link}\n\n"
            f"استمتع بمشاهدة القصة المخصصة لطفلك! 📖✨"
        )
        
        try:
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            
            message = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.messages.create(
                    body=message_body,
                    from_=settings.TWILIO_NUMBER_FROM,  
                    to=to_number  
                )
            )
            
            logger.info(f"SMS sent successfully to {to_number}: {message.sid}")
            return {"success": True, "message_sid": message.sid}
        except Exception as e:
            logger.error(f"SMS send error to {to_number}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def send_notifications_for_preview(preview_token: str, book_id: int) -> None:
        """
        Send notifications to all pending contacts for a completed preview
        This is called automatically when preview generation completes
        """
        from repositories.contact_repo import ContactRepository
        
        try:
            contacts = await ContactRepository.get_pending_contacts(preview_token)
            
            if not contacts:
                logger.info(f"No pending Contact notifications for {preview_token}")
                return
            
            logger.info(f"Sending {len(contacts)} SMS notifications for {preview_token}")
            
            for contact in contacts:
                result = await ContactService.send_preview_ready_notification(
                    to_number=contact["phone_number"],
                    preview_token=preview_token,
                    book_id=book_id
                )
                
                if result["success"]:
                    await ContactRepository.mark_message_sent(contact["id"])
                    logger.info(f"✅ Sent SMS to {contact['phone_number']}")
                else:
                    logger.error(f"❌ Failed to send SMS to {contact['phone_number']}: {result.get('error')}")
        
        except Exception as e:
            logger.error(f"Error sending SMS notifications for {preview_token}: {e}", exc_info=True)