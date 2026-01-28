from config import settings


def calculate_display_price(base_price_sar: float, currency: str) -> float:
    """Calculate price in target currency with adjustments"""
    config = settings.PRICING_CONFIG.get(currency, settings.PRICING_CONFIG["SAR"])
    adjusted_price = base_price_sar + config["adjustment"]
    calculated_price = adjusted_price * config["rate"]
    
    # Only round to nearest 100 for non-SAR currencies (large numbers)
    if currency != "SAR":
        rounded_price = round(calculated_price / 100) * 100
        return float(rounded_price)
    else:
        return round(calculated_price, 2)  # Keep SAR with 2 decimals

