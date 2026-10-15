from config.settings import config_yaml
from database.models import OrderSide

class IndianTaxCalculator:
    """
    Calculates exact Indian brokerage and regulatory charges for equity trading.
    Matches the business logic requirements exactly.
    """
    
    @staticmethod
    def calculate_charges(side: OrderSide, price: float, quantity: int, is_intraday: bool = True) -> dict:
        turnover = price * quantity
        
        # 1. Brokerage: Flat ₹20 per executed order (or 0.03%, whichever is lower)
        flat_fee = config_yaml['brokerage']['flat_fee']
        percentage_cap = config_yaml['brokerage']['percentage_cap'] * turnover
        brokerage = min(flat_fee, percentage_cap)
        
        # 2. STT (Securities Transaction Tax)
        # 0.025% on delivery or 0.025% on intraday sell-side
        stt = 0.0
        if is_intraday:
            if side == OrderSide.SELL:
                stt = round(turnover * 0.00025, 2)
        else:
            # Delivery (applies to both buy and sell sides)
            stt = round(turnover * 0.00025, 2)

        # 3. Exchange Turnover Fee (NSE): 0.00297%
        exchange_charges = round(turnover * 0.0000297, 2)
        
        # 4. SEBI Turnover Charges: ₹10 per crore (0.0001%)
        sebi_charges = round(turnover * 0.000001, 2)
        
        # 5. GST: 18% applied on (Brokerage + Exchange fees + SEBI Charges)
        gst = round(0.18 * (brokerage + exchange_charges + sebi_charges), 2)
        
        # 6. Stamp Duty: 0.003% on buy-side orders
        stamp_duty = 0.0
        if side == OrderSide.BUY:
            stamp_duty = round(turnover * 0.00003, 2)
            
        total_tax = round(brokerage + stt + exchange_charges + sebi_charges + gst + stamp_duty, 2)
        
        return {
            "brokerage": brokerage,
            "stt": stt,
            "exchange_charges": exchange_charges,
            "sebi_charges": sebi_charges,
            "gst": gst,
            "stamp_duty": stamp_duty,
            "total_tax": total_tax
        }
