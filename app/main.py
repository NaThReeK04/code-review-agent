import os
import structlog
from fastapi import FastAPI, HTTPException, status, Request, Body
from celery.result import AsyncResult
from app.celery_worker import celery_app, run_code_review_task
from app.models import (
    PRAnalysisRequest, 
    TaskResponse, 
    TaskResultResponse, 
    AnalysisResult
)
from app.logging_config import setup_logging
# [NEW] Import DB init function
from app.database import init_db

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

setup_logging()
logger = structlog.get_logger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=["100 per hour", "20 per minute"])

app = FastAPI(
    title="Autonomous Code Review Agent",
    description="An API to trigger AI-powered code reviews for GitHub PRs.",
    version="1.1.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.on_event("startup")
def startup_event():
    logger.info("FastAPI application starting up...")
    try:
        init_db() # [NEW] Create MySQL tables
        logger.info("Database tables created successfully.")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))

@app.on_event("shutdown")
def shutdown_event():
    logger.info("FastAPI application shutting down...")

@app.post("/analyze-pr", 
          response_model=TaskResponse, 
          status_code=status.HTTP_202_ACCEPTED,
          summary="Submit a PR for analysis")
@limiter.limit("10/minute")
async def analyze_pr(pr_request: PRAnalysisRequest, request: Request):
    log = logger.bind(repo_url=pr_request.repo_url, pr_number=pr_request.pr_number)
    try:
        log.info(f"Received request to analyze PR")
        task = run_code_review_task.delay(
            pr_request.repo_url, 
            pr_request.pr_number, 
            pr_request.github_token
        )
        log.info("Task queued", task_id=task.id)
        return TaskResponse(task_id=task.id, status="PENDING")
    except Exception as e:
        log.error("Failed to queue task", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue analysis task: {e}"
        )

@app.post("/webhook/github",
          status_code=status.HTTP_202_ACCEPTED,
          summary="GitHub Webhook receiver for PR events")
@limiter.limit("30/minute")
async def handle_github_webhook(request: Request, payload: dict = Body(...)):
    event_type = request.headers.get("X-GitHub-Event")
    action = payload.get("action")
    
    log = logger.bind(event_type=event_type, action=action)

    if event_type != "pull_request":
        return {"status": "ignored", "reason": "Not a pull_request event"}

    if action not in ["opened", "synchronize"]:
        return {"status": "ignored", "reason": f"Action '{action}' not supported"}

    try:
        pr_number = payload["pull_request"]["number"]
        repo_url = payload["repository"]["html_url"]
        
        server_github_token = os.getenv("GITHUB_TOKEN")
        
        task = run_code_review_task.delay(
            repo_url, 
            pr_number, 
            server_github_token
        )
        return {"status": "queued", "task_id": task.id}

    except Exception as e:
        log.error("Failed to queue webhook task", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{task_id}", response_model=TaskResponse)
async def get_status(task_id: str):
    try:
        task_result = AsyncResult(task_id, app=celery_app)
        return TaskResponse(task_id=task_id, status=task_result.state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/results/{task_id}", response_model=TaskResultResponse)
async def get_results(task_id: str):
    log = logger.bind(task_id=task_id)
    try:
        task_result = AsyncResult(task_id, app=celery_app)
        
        if task_result.state == "SUCCESS":
            analysis_data = task_result.result
            return TaskResultResponse(
                task_id=task_id,
                status="COMPLETED",
                results=AnalysisResult.model_validate(analysis_data)
            )
        elif task_result.state == "FAILURE":
            return TaskResultResponse(task_id=task_id, status="FAILED", error=str(task_result.result))
        else:
            return TaskResultResponse(task_id=task_id, status=task_result.state)
    except Exception as e:
        log.error("Error retrieving results", error=str(e))
        raise HTTPException(status_code=500, detail="Error retrieving results")

@app.get("/")
async def root():
    return {"status": "ok", "message": "Code Review Agent API is running with MySQL."}