import os
import redis
import json
import structlog
from celery import Celery, Task
from dotenv import load_dotenv
from typing import Optional

from app.logging_config import setup_logging
# Import DB tools
from app.database import SessionLocal, ReviewRecord 

setup_logging()
load_dotenv()

celery_broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
celery_result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    "tasks",
    broker=celery_broker_url,
    backend=celery_result_backend
)

celery_app.conf.update(
    task_track_started=True,
    broker_connection_retry_on_startup=True
)

from app.github_client import fetch_pr_diff, fetch_pr_head_sha
from app.agent import CodeReviewAgent

logger = structlog.get_logger(__name__)

class ReviewTask(Task):
    _agent = None
    _cache = None
    
    @property
    def cache(self) -> redis.Redis:
        if self._cache is None:
            try:
                self._cache = redis.Redis.from_url(
                    os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0"),
                    decode_responses=True
                )
                self._cache.ping()
            except Exception as e:
                logger.error("Failed to init cache", error=str(e))
                self._cache = None
        return self._cache

    @property
    def agent(self) -> CodeReviewAgent:
        if self._agent is None:
            try:
                self._agent = CodeReviewAgent()
            except Exception as e:
                logger.error("Failed to init Agent", error=str(e))
                self._agent = None
        return self._agent

@celery_app.task(bind=True, base=ReviewTask, name="run_code_review_task")
def run_code_review_task(self: ReviewTask, repo_url: str, pr_number: int, github_token: Optional[str] = None) -> dict:
    task_id = self.request.id
    log = logger.bind(task_id=task_id, repo_url=repo_url, pr_number=pr_number)
    
    try:
        log.info(f"Task started")
        self.update_state(state='PROCESSING', meta={'step': 'Fetching SHA'})

        if self.cache is None:
             raise RuntimeError("Cache client failed to initialize.")
             
        sha = fetch_pr_head_sha(repo_url, pr_number, github_token)
        cache_key = f"review_cache:{repo_url}:{pr_number}:{sha}"
        
        # Check Cache
        cached_result = self.cache.get(cache_key)
        if cached_result:
            log.info("Cache hit.")
            return json.loads(cached_result)

        log.info("Cache miss. Analyzing.")
        
        self.update_state(state='PROCESSING', meta={'step': 'Fetching diff'})
        diff_text = fetch_pr_diff(repo_url, pr_number, github_token)
        
        if not diff_text:
            raise ValueError("No diff content found.")
        
        self.update_state(state='PROCESSING', meta={'step': 'Analyzing diff'})
        if self.agent is None:
             raise RuntimeError("AI Agent failed to initialize.")
             
        # Run AI
        analysis_result = self.agent.review_code_diff(diff_text)
        result_json = analysis_result.model_dump()
        
        # Save to Redis Cache
        self.cache.set(cache_key, json.dumps(result_json), ex=86400) 

        # Save to MySQL Database
        db = SessionLocal()
        try:
            existing = db.query(ReviewRecord).filter(ReviewRecord.task_id == task_id).first()
            if not existing:
                new_record = ReviewRecord(
                    task_id=task_id,
                    repo_url=repo_url,
                    pr_number=pr_number,
                    status="SUCCESS",
                    ai_result=result_json
                )
                db.add(new_record)
                db.commit()
                log.info("Result saved to MySQL.")
        except Exception as e:
            log.error("Failed to save to MySQL", error=str(e))
            db.rollback()
        finally:
            db.close()
        
        return result_json

    except Exception as e:
        log.error("Task failed", error=str(e), exc_info=True)
        # Simply raise the exception. Celery handles the state update to FAILURE automatically.
        raise e