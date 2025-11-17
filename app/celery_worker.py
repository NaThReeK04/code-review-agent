import os
import redis
import json
import structlog
from celery import Celery, Task
from dotenv import load_dotenv
from typing import Optional

# Load logging config *before* anything else
from app.logging_config import setup_logging
setup_logging()

# Load environment variables from .env file
load_dotenv()

# --- App Setup ---
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

# --- Agent & Tool Imports ---
from app.github_client import fetch_pr_diff, fetch_pr_head_sha
from app.agent import CodeReviewAgent

# Use structured logger
logger = structlog.get_logger(__name__)

# --- Task Definition ---

class ReviewTask(Task):
    """Custom Task class to hold the agent and cache client."""
    _agent = None
    _cache = None
    
    # Cache property
    @property
    def cache(self) -> redis.Redis:
        """Lazy-load the Redis cache client."""
        if self._cache is None:
            logger.info("Initializing Redis cache client for Celery worker...")
            try:
                self._cache = redis.Redis.from_url(
                    os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0"),
                    decode_responses=True # Decode keys/values from bytes
                )
                self._cache.ping()
                logger.info("Redis cache client initialized.")
            except Exception as e:
                logger.error("Failed to initialize Redis cache client", error=str(e), exc_info=True)
                self._cache = None
        return self._cache

    @property
    def agent(self) -> CodeReviewAgent:
        """Lazy-load the agent instance once per worker process."""
        if self._agent is None:
            logger.info("Initializing CodeReviewAgent for Celery worker...")
            try:
                self._agent = CodeReviewAgent()
                logger.info("CodeReviewAgent initialized successfully.")
            except Exception as e:
                logger.error("Failed to initialize CodeReviewAgent", error=str(e), exc_info=True)
                self._agent = None # Ensure it retries on next call if init failed
        return self._agent

@celery_app.task(bind=True, base=ReviewTask, name="run_code_review_task")
def run_code_review_task(self: ReviewTask, repo_url: str, pr_number: int, github_token: Optional[str] = None) -> dict:
    """
    Asynchronous task to run a complete code review.
    Now with caching.
    """
    task_id = self.request.id
    log = logger.bind(task_id=task_id, repo_url=repo_url, pr_number=pr_number)
    
    try:
        log.info(f"Task started: Review for {repo_url}/pull/{pr_number}")
        
        # 1. Update status
        self.update_state(state='PROCESSING', meta={'step': 'Fetching SHA'})

        # 2. Caching Logic: Get HEAD SHA
        if self.cache is None:
             raise RuntimeError("Cache client failed to initialize.")
             
        sha = fetch_pr_head_sha(repo_url, pr_number, github_token)
        cache_key = f"review_cache:{repo_url}:{pr_number}:{sha}"
        log = log.bind(sha=sha, cache_key=cache_key)
        
        # 3. Check cache
        cached_result = self.cache.get(cache_key)
        if cached_result:
            log.info("Cache hit. Returning cached result.")
            self.update_state(state='SUCCESS', meta={'step': 'Cached'})
            # Result is stored as JSON, so parse it
            return json.loads(cached_result)

        log.info("Cache miss. Proceeding with full analysis.")
        
        # 4. Update status & Fetch PR diff
        self.update_state(state='PROCESSING', meta={'step': 'Fetching diff'})
        diff_text = fetch_pr_diff(repo_url, pr_number, github_token)
        
        if not diff_text:
            log.warn("No diff content found.")
            raise ValueError("No diff content found. Nothing to review.")
        
        # 5. Update status & Run AI Agent
        self.update_state(state='PROCESSING', meta={'step': 'Analyzing diff'})
        if self.agent is None:
             raise RuntimeError("AI Agent failed to initialize.")
             
        analysis_result = self.agent.review_code_diff(diff_text)
        
        log.info("Analysis complete", issues_found=analysis_result.summary.total_issues_found)
        
        # 6. Store in cache and return
        serializable_result = analysis_result.model_dump()
        
        # Store as JSON string, set to expire in 24 hours
        self.cache.set(cache_key, json.dumps(serializable_result), ex=86400) 
        log.info("Result stored in cache.")
        
        return serializable_result

    except Exception as e:
        log.error("Task failed", error=str(e), exc_info=True)
        self.update_state(
            state='FAILURE',
            meta={
                'exc_type': type(e).__name__,
                'exc_message': str(e),
                'step': 'FAILED'
            }
        )
        return {"error": f"{type(e).__name__}: {str(e)}"}