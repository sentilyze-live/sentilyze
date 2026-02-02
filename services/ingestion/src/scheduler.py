"""APScheduler-based collection scheduler."""

import asyncio
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from sentilyze_core import get_logger, get_settings
from sentilyze_core.logging import get_logger
from sentilyze_core.exceptions import CircuitBreakerOpen, ExternalServiceError

if TYPE_CHECKING:
    from ..publisher import EventPublisher
    from ..config import IngestionSettings

logger = get_logger(__name__)
settings: "IngestionSettings" = get_settings()

# Circuit breaker configuration
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 5
CIRCUIT_BREAKER_RESET_TIMEOUT_SECONDS = 300  # 5 minutes


class CircuitBreaker:
    """Simple circuit breaker for collection jobs."""
    
    def __init__(self, threshold: int = CIRCUIT_BREAKER_FAILURE_THRESHOLD, reset_timeout: int = CIRCUIT_BREAKER_RESET_TIMEOUT_SECONDS) -> None:
        self.threshold = threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.is_open = False
    
    def record_failure(self) -> bool:
        """Record a failure and return True if circuit should open."""
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)
        
        if self.failure_count >= self.threshold:
            self.is_open = True
            return True
        return False
    
    def record_success(self) -> None:
        """Record a success and reset if appropriate."""
        if self.is_open:
            # Check if enough time has passed to attempt reset
            if self.last_failure_time:
                elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
                if elapsed > self.reset_timeout:
                    self._reset()
        else:
            # Reset on success if below threshold
            if self.failure_count > 0:
                self.failure_count = max(0, self.failure_count - 1)
    
    def _reset(self) -> None:
        """Reset the circuit breaker."""
        self.failure_count = 0
        self.is_open = False
        self.last_failure_time = None
        logger.info("Circuit breaker reset")


class CollectionScheduler:
    """Scheduler for periodic data collection from all enabled collectors."""

    def __init__(
        self,
        collectors: dict[str, Any],
        publisher: "EventPublisher",
    ) -> None:
        self.collectors = collectors
        self.publisher = publisher
        self.scheduler: AsyncIOScheduler | None = None
        self._running = False
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._total_failures: dict[str, int] = {}

    async def start(self) -> None:
        """Start the scheduler with configured intervals."""
        if self._running:
            return

        self.scheduler = AsyncIOScheduler()

        # Schedule Reddit collection
        if "reddit" in self.collectors and settings.enable_reddit_collector:
            self.scheduler.add_job(
                self._collect_reddit,
                IntervalTrigger(seconds=settings.scheduler_reddit_interval),
                id="reddit_collection",
                name="Reddit Collection",
                replace_existing=True,
            )
            logger.info(
                "Scheduled Reddit collection",
                interval_seconds=settings.scheduler_reddit_interval,
            )

        # Schedule RSS collection
        if "rss" in self.collectors and settings.enable_rss_collector:
            self.scheduler.add_job(
                self._collect_rss,
                IntervalTrigger(seconds=settings.scheduler_rss_interval),
                id="rss_collection",
                name="RSS Collection",
                replace_existing=True,
            )
            logger.info(
                "Scheduled RSS collection",
                interval_seconds=settings.scheduler_rss_interval,
            )

        # Schedule Binance collection (includes WebSocket)
        if "binance" in self.collectors and settings.enable_binance_collector:
            # REST API collection
            self.scheduler.add_job(
                self._collect_binance,
                IntervalTrigger(seconds=settings.scheduler_binance_interval),
                id="binance_collection",
                name="Binance REST Collection",
                replace_existing=True,
            )
            logger.info(
                "Scheduled Binance collection",
                interval_seconds=settings.scheduler_binance_interval,
            )

        # Schedule GoldAPI collection
        if "goldapi" in self.collectors and settings.enable_goldapi_collector:
            self.scheduler.add_job(
                self._collect_goldapi,
                IntervalTrigger(seconds=settings.scheduler_goldapi_interval),
                id="goldapi_collection",
                name="GoldAPI Collection",
                replace_existing=True,
            )
            logger.info(
                "Scheduled GoldAPI collection",
                interval_seconds=settings.scheduler_goldapi_interval,
            )

        # Schedule Finnhub collection
        if "finnhub" in self.collectors and settings.enable_finnhub_collector:
            self.scheduler.add_job(
                self._collect_finnhub,
                IntervalTrigger(seconds=settings.scheduler_finnhub_interval),
                id="finnhub_collection",
                name="Finnhub News Collection",
                replace_existing=True,
            )
            logger.info(
                "Scheduled Finnhub collection",
                interval_seconds=settings.scheduler_finnhub_interval,
            )

        # Schedule Turkish scrapers collection
        if "turkish_scrapers" in self.collectors and settings.enable_turkish_scrapers:
            self.scheduler.add_job(
                self._collect_turkish,
                IntervalTrigger(seconds=settings.scheduler_turkish_interval),
                id="turkish_collection",
                name="Turkish Scrapers Collection",
                replace_existing=True,
            )
            logger.info(
                "Scheduled Turkish scrapers collection",
                interval_seconds=settings.scheduler_turkish_interval,
            )

        self.scheduler.start()
        self._running = True
        logger.info("Collection scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler."""
        if self.scheduler and self._running:
            self.scheduler.shutdown(wait=True)
            self._running = False
            logger.info("Collection scheduler stopped")

    def _get_circuit_breaker(self, job_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for a job."""
        if job_name not in self._circuit_breakers:
            self._circuit_breakers[job_name] = CircuitBreaker()
            self._total_failures[job_name] = 0
        return self._circuit_breakers[job_name]

    async def _collect_reddit(self) -> None:
        """Trigger Reddit collection."""
        collector = self.collectors.get("reddit")
        if not collector:
            return
        
        job_name = "reddit"
        circuit = self._get_circuit_breaker(job_name)
        
        # Check if circuit is open
        if circuit.is_open:
            circuit.record_success()  # Try to reset
            if circuit.is_open:
                raise CircuitBreakerOpen(
                    f"Circuit breaker is open for {job_name} collector",
                    service=job_name
                )

        try:
            count = await collector.collect()
            circuit.record_success()
            logger.info(
                "Scheduled Reddit collection completed",
                collected=count,
            )
        except Exception as e:
            logger.error("Scheduled Reddit collection failed", error=str(e))
            self._total_failures[job_name] = self._total_failures.get(job_name, 0) + 1
            if circuit.record_failure():
                logger.critical(
                    "Circuit breaker opened for Reddit collector",
                    failures=circuit.failure_count,
                    total_failures=self._total_failures[job_name],
                )
            raise ExternalServiceError(f"Reddit collection failed: {e}", service=job_name) from e

    async def _collect_rss(self) -> None:
        """Trigger RSS collection."""
        collector = self.collectors.get("rss")
        if not collector:
            return
        
        job_name = "rss"
        circuit = self._get_circuit_breaker(job_name)
        
        if circuit.is_open:
            circuit.record_success()
            if circuit.is_open:
                raise CircuitBreakerOpen(f"Circuit breaker is open for {job_name} collector", service=job_name)

        try:
            count = await collector.collect()
            circuit.record_success()
            logger.info(
                "Scheduled RSS collection completed",
                collected=count,
            )
        except Exception as e:
            logger.error("Scheduled RSS collection failed", error=str(e))
            self._total_failures[job_name] = self._total_failures.get(job_name, 0) + 1
            if circuit.record_failure():
                logger.critical(
                    "Circuit breaker opened for RSS collector",
                    failures=circuit.failure_count,
                    total_failures=self._total_failures[job_name],
                )
            raise ExternalServiceError(f"RSS collection failed: {e}", service=job_name) from e

    async def _collect_binance(self) -> None:
        """Trigger Binance REST collection."""
        collector = self.collectors.get("binance")
        if not collector:
            return
        
        job_name = "binance"
        circuit = self._get_circuit_breaker(job_name)
        
        if circuit.is_open:
            circuit.record_success()
            if circuit.is_open:
                raise CircuitBreakerOpen(f"Circuit breaker is open for {job_name} collector", service=job_name)

        try:
            count = await collector.collect()
            circuit.record_success()
            logger.info(
                "Scheduled Binance collection completed",
                collected=count,
            )
        except Exception as e:
            logger.error("Scheduled Binance collection failed", error=str(e))
            self._total_failures[job_name] = self._total_failures.get(job_name, 0) + 1
            if circuit.record_failure():
                logger.critical(
                    "Circuit breaker opened for Binance collector",
                    failures=circuit.failure_count,
                    total_failures=self._total_failures[job_name],
                )
            raise ExternalServiceError(f"Binance collection failed: {e}", service=job_name) from e

    async def _collect_goldapi(self) -> None:
        """Trigger GoldAPI collection."""
        collector = self.collectors.get("goldapi")
        if not collector:
            return
        
        job_name = "goldapi"
        circuit = self._get_circuit_breaker(job_name)
        
        if circuit.is_open:
            circuit.record_success()
            if circuit.is_open:
                raise CircuitBreakerOpen(f"Circuit breaker is open for {job_name} collector", service=job_name)

        try:
            events = await collector.collect()
            message_ids = await collector.publish_events(events)
            circuit.record_success()
            logger.info(
                "Scheduled GoldAPI collection completed",
                collected=len(events),
                published=len(message_ids),
            )
        except Exception as e:
            logger.error("Scheduled GoldAPI collection failed", error=str(e))
            self._total_failures[job_name] = self._total_failures.get(job_name, 0) + 1
            if circuit.record_failure():
                logger.critical(
                    "Circuit breaker opened for GoldAPI collector",
                    failures=circuit.failure_count,
                    total_failures=self._total_failures[job_name],
                )
            raise ExternalServiceError(f"GoldAPI collection failed: {e}", service=job_name) from e

    async def _collect_finnhub(self) -> None:
        """Trigger Finnhub news collection."""
        collector = self.collectors.get("finnhub")
        if not collector:
            return
        
        job_name = "finnhub"
        circuit = self._get_circuit_breaker(job_name)
        
        if circuit.is_open:
            circuit.record_success()
            if circuit.is_open:
                raise CircuitBreakerOpen(f"Circuit breaker is open for {job_name} collector", service=job_name)

        try:
            events = await collector.collect()
            message_ids = await collector.publish_events(events)
            circuit.record_success()
            logger.info(
                "Scheduled Finnhub collection completed",
                collected=len(events),
                published=len(message_ids),
            )
        except Exception as e:
            logger.error("Scheduled Finnhub collection failed", error=str(e))
            self._total_failures[job_name] = self._total_failures.get(job_name, 0) + 1
            if circuit.record_failure():
                logger.critical(
                    "Circuit breaker opened for Finnhub collector",
                    failures=circuit.failure_count,
                    total_failures=self._total_failures[job_name],
                )
            raise ExternalServiceError(f"Finnhub collection failed: {e}", service=job_name) from e

    async def _collect_turkish(self) -> None:
        """Trigger Turkish scrapers collection."""
        collector = self.collectors.get("turkish_scrapers")
        if not collector:
            return
        
        job_name = "turkish_scrapers"
        circuit = self._get_circuit_breaker(job_name)
        
        if circuit.is_open:
            circuit.record_success()
            if circuit.is_open:
                raise CircuitBreakerOpen(f"Circuit breaker is open for {job_name} collector", service=job_name)

        try:
            events = await collector.collect_all()
            message_ids = await collector.publish_events(events)
            circuit.record_success()
            logger.info(
                "Scheduled Turkish scrapers collection completed",
                collected=len(events),
                published=len(message_ids),
            )
        except Exception as e:
            logger.error("Scheduled Turkish scrapers collection failed", error=str(e))
            self._total_failures[job_name] = self._total_failures.get(job_name, 0) + 1
            if circuit.record_failure():
                logger.critical(
                    "Circuit breaker opened for Turkish scrapers collector",
                    failures=circuit.failure_count,
                    total_failures=self._total_failures[job_name],
                )
            raise ExternalServiceError(f"Turkish scrapers collection failed: {e}", service=job_name) from e

    def get_job_status(self) -> dict:
        """Get status of scheduled jobs."""
        if not self.scheduler:
            return {"status": "not_running", "jobs": []}

        jobs = []
        for job in self.scheduler.get_jobs():
            circuit = self._circuit_breakers.get(job.id)
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "circuit_breaker": {
                    "is_open": circuit.is_open if circuit else False,
                    "failure_count": circuit.failure_count if circuit else 0,
                    "total_failures": self._total_failures.get(job.id, 0),
                } if circuit else None,
            })

        return {
            "status": "running" if self._running else "stopped",
            "jobs": jobs,
            "circuit_breakers_open": sum(1 for cb in self._circuit_breakers.values() if cb.is_open),
        }
