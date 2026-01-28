# API endpoints for orders and full book generation
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse
from pathlib import Path
import logging

from repositories.order_repo import OrderRepository
from repositories.generated_book_repo import GeneratedBookRepository
from repositories.preview_repo import PreviewRepository
from repositories.book_repo import BookRepository
from services.full_book_generation_service import FullBookGenerationService
from schemas.requests import CreateOrderRequest
from schemas.responses import CreateOrderResponse, OrderStatusResponse
from utils.pricing import calculate_display_price

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/orders", response_model=CreateOrderResponse)
async def ep_create_order(
    request: CreateOrderRequest,
    background_tasks: BackgroundTasks
):
    """
    Create order from completed preview (without payment for MVP)
    Later: Add Stripe payment check here
    """
    try:
        # Validate preview exists and is completed
        preview = await PreviewRepository.get_by_token(request.preview_token)
        if not preview:
            raise HTTPException(status_code=404, detail="Preview not found")
        
        if preview['preview_status'] != 'completed':
            raise HTTPException(
                status_code=400,
                detail=f"Preview not ready (status: {preview['preview_status']})"
            )
        
        # Get book details
        book = await BookRepository.get_by_id(preview['book_id'])
        expected_display_amount = calculate_display_price(book.price, request.display_currency)
        if abs(request.display_amount - expected_display_amount) > 1:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid price. Expected {expected_display_amount} {request.display_currency}"
            )
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        # TODO: Add Stripe payment check here when ready
        # Example:
        # stripe_session = stripe.checkout.Session.create(...)
        # return {"stripe_checkout_url": stripe_session.url, "order_number": order_number}
        
      # Create order record
        order = await OrderRepository.create_order(
            book_id=book.id,
            preview_id=preview['id'],
            child_name=preview['child_name'],
            order_request=request,  # ← Just pass the request object
            total_amount=book.price
        )

        # Create generated book record
        await GeneratedBookRepository.create_generated_book(
            order_id=order['id'],
            original_photo_path=preview['original_photo_path']
        )
        
        # Start background generation (for MVP without payment)
        # Later: Move this to Stripe webhook handler
        background_tasks.add_task(
            FullBookGenerationService.generate_full_book,
            order_id=order['id'],
            preview_token=request.preview_token,
            child_name=preview['child_name']
        )
        
        logger.info(f"Order created: {order['order_number']}")
        
        return CreateOrderResponse(
        order_number=order['order_number'],
       total_amount=request.display_amount,
       currency=request.display_currency,
        message="سنتواصل معك عبر واتساب خلال الساعات القادمة لتأكيد الطلب"  # ← CHANGED
    )

        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating order: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create order")


@router.get("/orders/{order_number}/status", response_model=OrderStatusResponse)
async def get_order_status(
    order_number: str,
    email: str = Query(..., description="Customer email for verification")
):
    """Check order status and book generation progress"""
    try:
        # Get order (single DB call)
        order = await OrderRepository.get_by_order_number(order_number)
        if not order or order['customer_email'].lower() != email.lower():
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Get generation status
        generated_book = await GeneratedBookRepository.get_by_order_id(order['id'])
        if not generated_book:
            raise HTTPException(status_code=404, detail="Generation record not found")
        
        # Build PDF URL if completed
        final_pdf_url = None
        if generated_book['generation_status'] == 'completed':
            final_pdf_url = f"/api/orders/{order_number}/download"
        
        return OrderStatusResponse(
            order_number=order_number,
            order_status=order['order_status'],
            payment_status=order['payment_status'],
            generation_status=generated_book['generation_status'],
            characters_completed=generated_book['characters_completed'],
            estimated_time_minutes=generated_book['estimated_time_minutes'] or 0,
            final_pdf_url=final_pdf_url,
            error_message=generated_book.get('error_message')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching order status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch order status")


@router.get("/orders/{order_number}/download")
async def download_book(
    order_number: str,
    email: str = Query(..., description="Customer email for verification")
):
    """Download final personalized book PDF"""
    try:
        # Get order (single DB call)
        order = await OrderRepository.get_by_order_number(order_number)
        if not order or order['customer_email'].lower() != email.lower():
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Get generated book
        generated_book = await GeneratedBookRepository.get_by_order_id(order['id'])
        if not generated_book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        if generated_book['generation_status'] != 'completed':
            raise HTTPException(
                status_code=400,
                detail=f"Book not ready (status: {generated_book['generation_status']})"
            )
        
        # Get PDF path
        pdf_path = Path(generated_book['final_pdf_path'])
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail="PDF file not found")
        
        # Stream PDF
        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            filename=f"KhayalKids_{order_number}.pdf"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading book: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to download book")
