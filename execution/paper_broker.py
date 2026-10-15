import logging
from typing import Dict
from sqlalchemy.orm import Session
from database.models import Order, Trade, OrderStatus, OrderSide, OrderType
from execution.order_types import OrderCreate, Position
from execution.tax_calculator import IndianTaxCalculator

logger = logging.getLogger(__name__)

class PaperBroker:
    """
    Virtual paper broker simulating capital constraints, order matching,
    and portfolio management.
    """
    def __init__(self, initial_capital: float, db: Session):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.db = db
        self.positions: Dict[str, Position] = {}
        
    def submit_order(self, order_data: OrderCreate) -> Order:
        db_order = Order(
            symbol=order_data.symbol,
            order_type=order_data.order_type,
            side=order_data.side,
            quantity=order_data.quantity,
            price=order_data.price
        )
        self.db.add(db_order)
        self.db.commit()
        self.db.refresh(db_order)
        logger.info(f"Order submitted: {db_order.id} | {db_order.side.name} {db_order.quantity} {db_order.symbol}")
        return db_order

    def cancel_order(self, order_id: int) -> bool:
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if order and order.status == OrderStatus.PENDING:
            order.status = OrderStatus.CANCELLED
            self.db.commit()
            logger.info(f"Order {order_id} cancelled.")
            return True
        return False

    def process_tick(self, symbol: str, current_price: float):
        """
        Match pending orders against new market price ticks.
        """
        pending_orders = self.db.query(Order).filter(
            Order.symbol == symbol, 
            Order.status == OrderStatus.PENDING
        ).all()
        
        for order in pending_orders:
            if self._check_match(order, current_price):
                self._execute_order(order, current_price)
                
        # Update unrealized PnL for positions
        if symbol in self.positions:
            pos = self.positions[symbol]
            if pos.quantity > 0:
                pos.unrealized_pnl = (current_price - pos.average_price) * pos.quantity
            elif pos.quantity < 0:
                pos.unrealized_pnl = (pos.average_price - current_price) * abs(pos.quantity)

    def _check_match(self, order: Order, current_price: float) -> bool:
        if order.order_type == OrderType.MARKET:
            return True
        if order.side == OrderSide.BUY and current_price <= order.price:
            return True
        if order.side == OrderSide.SELL and current_price >= order.price:
            return True
        return False
        
    def _execute_order(self, order: Order, executed_price: float):
        # Calculate taxes
        taxes = IndianTaxCalculator.calculate_charges(
            side=order.side,
            price=executed_price,
            quantity=order.quantity,
            is_intraday=True # Defaulting to intraday for simplicity in paper broker
        )
        
        # Calculate capital impact
        turnover = executed_price * order.quantity
        if order.side == OrderSide.BUY:
            required_capital = turnover + taxes['total_tax']
            if self.current_capital < required_capital:
                order.status = OrderStatus.REJECTED
                self.db.commit()
                logger.warning(f"Order {order.id} rejected: Insufficient capital.")
                return
            self.current_capital -= required_capital
        else:
            self.current_capital += (turnover - taxes['total_tax'])
            
        # Record trade
        trade = Trade(
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=executed_price,
            **taxes
        )
        
        order.status = OrderStatus.EXECUTED
        self.db.add(trade)
        self.db.commit()
        
        # Update Positions
        self._update_position(order.symbol, order.side, order.quantity, executed_price)
        logger.info(f"Order {order.id} executed at {executed_price}. Taxes: {taxes['total_tax']}")

    def _update_position(self, symbol: str, side: OrderSide, quantity: int, price: float):
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol, quantity=0, average_price=0.0)
            
        pos = self.positions[symbol]
        
        if side == OrderSide.BUY:
            if pos.quantity >= 0:
                # Adding to long
                new_qty = pos.quantity + quantity
                pos.average_price = ((pos.quantity * pos.average_price) + (quantity * price)) / new_qty
                pos.quantity = new_qty
            else:
                # Covering short
                if quantity <= abs(pos.quantity):
                    realized = (pos.average_price - price) * quantity
                    pos.realized_pnl += realized
                    pos.quantity += quantity
                    if pos.quantity == 0:
                        pos.average_price = 0.0
                else:
                    realized = (pos.average_price - price) * abs(pos.quantity)
                    pos.realized_pnl += realized
                    pos.quantity += quantity
                    pos.average_price = price # Flipped to long
        else: # SELL
            if pos.quantity <= 0:
                # Adding to short
                new_qty = pos.quantity - quantity
                pos.average_price = ((abs(pos.quantity) * pos.average_price) + (quantity * price)) / abs(new_qty)
                pos.quantity = new_qty
            else:
                # Selling long
                if quantity <= pos.quantity:
                    realized = (price - pos.average_price) * quantity
                    pos.realized_pnl += realized
                    pos.quantity -= quantity
                    if pos.quantity == 0:
                        pos.average_price = 0.0
                else:
                    realized = (price - pos.average_price) * pos.quantity
                    pos.realized_pnl += realized
                    pos.quantity -= quantity
                    pos.average_price = price # Flipped to short
