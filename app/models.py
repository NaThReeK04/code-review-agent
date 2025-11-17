from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# --- API Input/Output Models ---

class PRAnalysisRequest(BaseModel):
    """Request model for POST /analyze-pr"""
    repo_url: str = Field(..., example="https://github.com/user/repo")
    pr_number: int = Field(..., example=123)
    github_token: Optional[str] = None

class TaskResponse(BaseModel):
    """Response model for /analyze-pr and /status"""
    task_id: str
    status: str

# --- AI Agent Output Models ---
# These models define the structured JSON we want from the LLM

class AnalysisIssue(BaseModel):
    """A single issue found in the code."""
    type: Literal["style", "bug", "performance", "best_practice", "security", "other"] = Field(..., description="The category of the issue.")
    line: int = Field(..., description="The line number where the issue occurs.")
    description: str = Field(..., description="A brief description of the issue.")
    suggestion: str = Field(..., description="A concrete suggestion for how to fix the issue.")

class FileReview(BaseModel):
    """A review for a single file."""
    file_path: str = Field(..., description="The full path of the file being reviewed.")
    issues: List[AnalysisIssue] = Field(..., description="A list of issues found in this file.")

class AnalysisSummary(BaseModel):
    """A high-level summary of the review."""
    total_files_reviewed: int
    total_issues_found: int
    critical_issues: int = Field(..., description="Count of 'bug' or 'security' issues.")
    overview: str = Field(..., description="A brief, high-level summary of the code review.")


class AnalysisResult(BaseModel):
    """
    The final, structured output of the code review.
    This is the model the LLM will be asked to fill.
    """
    files: List[FileReview]
    summary: AnalysisSummary

# --- API Result Model ---

class TaskResultResponse(BaseModel):
    """Response model for GET /results/<task_id>"""
    task_id: str
    status: str
    results: Optional[AnalysisResult] = None
    error: Optional[str] = None