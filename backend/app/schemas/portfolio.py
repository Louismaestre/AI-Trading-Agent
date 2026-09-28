"""API shapes for simulated portfolios."""

import datetime
from decimal import Decimal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.models import OrderSide, OrderStatus
from app.services.portfolio_service import DEFAULT_CAPITAL


class CreatePortfolioRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    initial_capital: Decimal = Field(default=DEFAULT_CAPITAL, gt=0)


class PlaceOrderRequest(BaseModel):
    ticker: str
    side: OrderSide
    quantity: int = Field(ge=1)
    # Defaults to now when omitted; pass a past instant to fill against stored bars.
    decision_at: AwareDatetime | None = None
    execute_at: AwareDatetime | None = None


class ExecuteOrdersRequest(BaseModel):
    at: AwareDatetime | None = None


class PositionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    quantity: int
    average_cost: Decimal
    market_price: Decimal
    value: Decimal


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    side: OrderSide
    quantity: int
    status: OrderStatus
    decision_at: datetime.datetime
    executed_at: datetime.datetime | None
    execution_price: Decimal | None
    fees: Decimal | None
    rejection_reason: str | None


class PortfolioResponse(BaseModel):
    id: int
    name: str
    initial_capital: Decimal
    cash: Decimal
    market_value: Decimal
    total_value: Decimal
    positions: list[PositionResponse]
