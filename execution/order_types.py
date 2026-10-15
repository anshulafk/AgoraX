from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from database.models import OrderSide, OrderType, OrderStatus

class OrderCreate(BaseModel):
    symbol: str
    order_type: OrderType
    side: OrderSide
    quantity: int = Field(gt=0)
    price: Optional[float] = None
    
    class Config:
        from_attributes = True

class OrderResponse(OrderCreate):
    id: int
    status: OrderStatus
    timestamp: datetime
    
    class Config:
        from_attributes = True

class Position(BaseModel):
    symbol: str
    quantity: int
    average_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
