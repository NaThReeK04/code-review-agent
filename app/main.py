import os
import structlog
from fastapi import FastAPI, HTTPException, status, Request, Body, Response
from celery.result import AsyncResult
from app.celery_worker import celery_app, run_code_review_task
from app.models import (
    PRAnalysisRequest, 
    TaskResponse, 
    TaskResultResponse, 
    AnalysisResult
)
from app.logging_config import setup_logging

# Rate Limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Setup structured logging on startup
setup_logging()
logger = structlog.get_logger(__name__)

# Initialize Rate Limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100 per hour", "20 per minute"])

app = FastAPI(
    title="Autonomous Code Review Agent",
    description="An API to trigger AI-powered code reviews for GitHub PRs.",
    version="1.1.0" # Updated version
)

# Add limiter state and exception handler to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.on_event("startup")
def startup_event():
    logger.info("FastAPI application starting up...")

@app.on_event("shutdown")
def shutdown_event():
    logger.info("FastAPI application shutting down...")

@app.post("/analyze-pr", 
          response_model=TaskResponse, 
          status_code=status.HTTP_202_ACCEPTED,
          summary="Submit a PR for analysis")
@limiter.limit("10/minute") # Rate limit this endpoint
async def analyze_pr(pr_request: PRAnalysisRequest, request: Request): # Renamed arguments
    """
    ...
    """
    log = logger.bind(repo_url=pr_request.repo_url, pr_number=pr_request.pr_number) # Use pr_request
    try:
        log.info(f"Received request to analyze PR")
        task = run_code_review_task.delay(
            pr_request.repo_url, 
            pr_request.pr_number, 
            pr_request.github_token  # Use pr_request
        )
        log.info("Task queued", task_id=task.id)
        return TaskResponse(task_id=task.id, status="PENDING")
    except Exception as e:
        log.error("Failed to queue task", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue analysis task: {e}"
        )

# New endpoint for GitHub Webhooks
@app.post("/webhook/github",
          status_code=status.HTTP_202_ACCEPTED,
          summary="GitHub Webhook receiver for PR events")
@limiter.limit("30/minute") # Allow more webhooks
async def handle_github_webhook(request: Request, payload: dict = Body(...)): # Renamed argument
    """
    ...
    """
    event_type = request.headers.get("X-GitHub-Event") # Use request
    action = payload.get("action")
    
    log = logger.bind(event_type=event_type, action=action)

    if event_type != "pull_request":
        log.info("Ignoring webhook, not a pull_request event.")
        return {"status": "ignored", "reason": "Not a pull_request event"}

    if action not in ["opened", "synchronize"]:
        log.info("Ignoring PR action, not 'opened' or 'synchronize'.")
        return {"status": "ignored", "reason": f"Action '{action}' not supported"}

    try:
        pr_number = payload["pull_request"]["number"]
        repo_url = payload["repository"]["html_url"]
        
        # Use the server's GITHUB_TOKEN for webhook-triggered events
        server_github_token = os.getenv("GITHUB_TOKEN")
        if not server_github_token:
            log.warn("No GITHUB_TOKEN set on server. Webhook may fail on private repos.")
        
        log = log.bind(repo_url=repo_url, pr_number=pr_number)
        
        log.info("Webhook valid, queuing analysis task.")
        task = run_code_review_task.delay(
            repo_url, 
            pr_number, 
            server_github_token
        )
        log.info("Webhook task queued", task_id=task.id)
        
        return {"status": "queued", "task_id": task.id}

    except KeyError as e:
        log.error("Webhook payload missing required keys", missing_key=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook payload missing required data: {e}"
        )
    except Exception as e:
        log.error("Failed to queue webhook task", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue analysis task: {e}"
        )


@app.get("/status/{task_id}", 
         response_model=TaskResponse,
         summary="Check the status of an analysis task")
async def get_status(task_id: str):
    """
    Checks the status of a previously submitted analysis task.
    """
    try:
        task_result = AsyncResult(task_id, app=celery_app)
        return TaskResponse(task_id=task_id, status=task_result.state)
    except Exception as e:
        logger.error("Error checking task status", task_id=task_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving task status."
        )

@app.get("/results/{task_id}", 
         response_model=TaskResultResponse,
         summary="Retrieve the results of a completed analysis")
async def get_results(task_id: str):
    """
    Retrieves the results of a completed analysis task.
    If the task is not complete, it returns the current status.
    """
    log = logger.bind(task_id=task_id)
    try:
        task_result = AsyncResult(task_id, app=celery_app)
        
        if task_result.state == "SUCCESS":
            log.info("Task success, returning results.")
            analysis_data = task_result.result
            return TaskResultResponse(
                task_id=task_id,
                status="COMPLETED",
                results=AnalysisResult.model_validate(analysis_data)
            )
        elif task_result.state == "FAILURE":
            log.warn("Task failed, returning error.")
            error_info = task_result.result.get('error', 'Unknown error')
            return TaskResultResponse(
                task_id=task_id,
                status="FAILED",
                error=str(error_info)
            )
        else:
            log.info("Task not yet complete", status=task_result.state)
            return TaskResultResponse(
                task_id=task_id,
                status=task_result.state
            )
    except Exception as e:
        log.error("Error retrieving task results", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving task results."
        )

@app.get("/", summary="Health Check")
async def root():
    """A simple health check endpoint."""
    return {"status": "ok", "message": "Code Review Agent API is. running."}