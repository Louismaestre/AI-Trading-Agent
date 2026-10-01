"""Background jobs that drive live sessions. Not started in the test environment."""

import datetime
import logging
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_engine
from app.market_clock import ensure_aware, is_market_open, last_close, next_open
from app.models import LiveSession, LiveSessionStatus
from app.services.live_service import LiveService, cycle_slot
from app.services.news_service import NewsService

logger = logging.getLogger(__name__)

_CLOSE_DELAY = datetime.timedelta(minutes=5)
_CLOSE_WINDOW = datetime.timedelta(hours=3)

_scheduler: BackgroundScheduler | None = None
_in_flight: set[int] = set()
_lock = threading.Lock()


def next_trigger(now: datetime.datetime, interval_minutes: int) -> datetime.datetime:
    """Next analysis time after `now`: next slot if the market is open, otherwise next open."""
    now = ensure_aware(now)
    if is_market_open(now):
        following = cycle_slot(now, interval_minutes) + datetime.timedelta(minutes=interval_minutes)
        if is_market_open(following):
            return following
    return next_open(now)


def close_mark_at(now: datetime.datetime) -> datetime.datetime | None:
    """Close timestamp to mark, if `now` is shortly after the last bell. Else None."""
    now = ensure_aware(now)
    if is_market_open(now):
        return None
    close = last_close(now)
    if close + _CLOSE_DELAY <= now <= close + _CLOSE_WINDOW:
        return close
    return None


def try_acquire(session_id: int) -> bool:
    """True if this session is not already running a cycle."""
    with _lock:
        if session_id in _in_flight:
            return False
        _in_flight.add(session_id)
        return True


def release(session_id: int) -> None:
    with _lock:
        _in_flight.discard(session_id)


def tick_running_sessions(now: datetime.datetime | None = None) -> None:
    """Run one cycle for every RUNNING session that is not already in flight."""
    moment = now or datetime.datetime.now(datetime.UTC)
    for session_id in _session_ids(LiveSessionStatus.RUNNING):
        if not try_acquire(session_id):
            logger.info("Skip live session %s: a cycle is already running", session_id)
            continue
        try:
            with Session(get_engine()) as session:
                result = LiveService(session).run_cycle(session_id, moment)
                logger.info("Live session %s cycle: %s", session_id, result.reason)
        except Exception:
            logger.exception("Live session %s cycle failed", session_id)
        finally:
            release(session_id)


def tick_close_marks(now: datetime.datetime | None = None) -> None:
    """Shortly after the close, store a last mark-to-market for each active session."""
    moment = now or datetime.datetime.now(datetime.UTC)
    close = close_mark_at(moment)
    if close is None:
        return
    for session_id in _session_ids(LiveSessionStatus.RUNNING, LiveSessionStatus.PAUSED):
        try:
            with Session(get_engine()) as session:
                LiveService(session).mark_at_close(session_id, close)
        except Exception:
            logger.exception("Live session %s close mark failed", session_id)


def tick_news() -> None:
    """Pull recent headlines so the sentiment window is not empty on the next cycle."""
    try:
        with Session(get_engine()) as session:
            stored = NewsService(session).sync_universe()
            logger.info("News sync stored %s articles", stored)
    except Exception:
        logger.exception("News sync failed")


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        tick_running_sessions, "interval", minutes=1, id="live-cycles", max_instances=1
    )
    _scheduler.add_job(tick_close_marks, "interval", minutes=5, id="close-marks", max_instances=1)
    _scheduler.add_job(tick_news, "interval", hours=6, id="news-sync", max_instances=1)
    _scheduler.start()
    logger.info("Live scheduler started")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
    logger.info("Live scheduler stopped")


def _session_ids(*statuses: LiveSessionStatus) -> list[int]:
    with Session(get_engine()) as session:
        statement = select(LiveSession.id).where(LiveSession.status.in_(statuses))
        return list(session.scalars(statement))
