import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import AwareDatetime
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import Order
from app.schemas.portfolio import (
    CreatePortfolioRequest,
    ExecuteOrdersRequest,
    OrderResponse,
    PlaceOrderRequest,
    PortfolioResponse,
    PositionResponse,
)
from app.services.market_data_service import UnknownTickerError
from app.services.portfolio_service import PortfolioService, PortfolioView, UnknownPortfolioError

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


def get_portfolio_service(session: Annotated[Session, Depends(get_session)]) -> PortfolioService:
    return PortfolioService(session)


@router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
def create_portfolio(
    request: CreatePortfolioRequest,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> PortfolioResponse:
    portfolio = service.create(request.name, request.initial_capital)
    return _portfolio_response(service.snapshot(portfolio.id, datetime.datetime.now(datetime.UTC)))


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
def get_portfolio(
    portfolio_id: int,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    as_of: AwareDatetime | None = None,
) -> PortfolioResponse:
    try:
        view = service.snapshot(portfolio_id, as_of or datetime.datetime.now(datetime.UTC))
    except UnknownPortfolioError:
        raise _unknown_portfolio(portfolio_id) from None
    return _portfolio_response(view)


@router.get("/{portfolio_id}/orders", response_model=list[OrderResponse])
def list_orders(
    portfolio_id: int,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> list[OrderResponse]:
    try:
        return [_order_response(order) for order in service.list_orders(portfolio_id)]
    except UnknownPortfolioError:
        raise _unknown_portfolio(portfolio_id) from None


@router.post(
    "/{portfolio_id}/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def place_order(
    portfolio_id: int,
    request: PlaceOrderRequest,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> OrderResponse:
    now = datetime.datetime.now(datetime.UTC)
    try:
        order = service.place_order(
            portfolio_id,
            request.ticker,
            request.side,
            request.quantity,
            request.decision_at or now,
        )
        service.execute_pending_orders(portfolio_id, request.execute_at or now)
        return _order_response(service.get_order(portfolio_id, order.id))
    except UnknownPortfolioError:
        raise _unknown_portfolio(portfolio_id) from None
    except UnknownTickerError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown ticker: {request.ticker}"
        ) from None


@router.post("/{portfolio_id}/execute", response_model=list[OrderResponse])
def execute_orders(
    portfolio_id: int,
    request: ExecuteOrdersRequest,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> list[OrderResponse]:
    now = request.at or datetime.datetime.now(datetime.UTC)
    try:
        orders = service.execute_pending_orders(portfolio_id, now)
        return [_order_response(service.get_order(portfolio_id, order.id)) for order in orders]
    except UnknownPortfolioError:
        raise _unknown_portfolio(portfolio_id) from None


def _portfolio_response(view: PortfolioView) -> PortfolioResponse:
    portfolio = view.portfolio
    return PortfolioResponse(
        id=portfolio.id,
        name=portfolio.name,
        initial_capital=portfolio.initial_capital,
        cash=portfolio.cash,
        market_value=view.market_value,
        total_value=view.total_value,
        positions=[PositionResponse.model_validate(item) for item in view.positions],
    )


def _order_response(order: Order) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        ticker=order.instrument.ticker,
        side=order.side,
        quantity=order.quantity,
        status=order.status,
        decision_at=order.decision_at,
        executed_at=order.executed_at,
        execution_price=order.execution_price,
        fees=order.fees,
        rejection_reason=order.rejection_reason,
    )


def _unknown_portfolio(portfolio_id: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown portfolio: {portfolio_id}"
    )
