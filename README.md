# Autonomous AI Code Review Agent

An autonomous code review system that uses AI to analyze GitHub pull requests. It implements a goal-oriented agent that can:

- Fetch PR metadata and diffs from GitHub
- Plan and execute a multi-step review process
- Run asynchronously using Celery workers
- Expose a clean FastAPI HTTP API for developers
- Return structured, machine-readable feedback for each file and issue

**Tech stack:** FastAPI, Celery, Redis/PostgreSQL, LangChain/Agent framework, Ollama (llama3) or LLM API, Docker, pytest

---

## Features

### Async PR Analysis
Submit a PR for analysis and retrieve results using `task_id`.

### Goal-Oriented AI Agent
Reviews code for:
- Style & formatting issues
- Bugs
- Performance improvements
- Best-practice violations

### GitHub Integration
Securely fetches PR files and diffs using GitHub token.

### Structured Results
Each file contains issue lists with:
- Issue type
- Line number
- Description
- Fix suggestion

### Celery-Based Workers
Heavy code analysis runs asynchronously.

### Redis/PostgreSQL Storage
Stores task status, results, caching entries.

### Optional Caching
Avoid recomputing results for identical PRs.

### Structured Logging
JSON/logfmt logs for agent + API + workers.

### Docker Support
One-command startup using docker-compose.

### Webhook Ready
Works with GitHub PR webhooks (supports ngrok).

---

## Architecture Overview

**High-level flow:**

1. Client sends `POST /analyze-pr` with `repo_url`, `pr_number`, and optional `github_token`.
2. FastAPI creates a Celery task → returns a unique `task_id`.
3. Celery worker:
   - Fetches PR diff
   - Runs AI analysis
   - Stores output in Redis/PostgreSQL
   - Updates task status
4. Client queries:
   - `GET /status/{task_id}`
   - `GET /results/{task_id}`

---

## API Overview

### 1. POST /analyze-pr

Trigger analysis for a GitHub pull request.

**Request body:**

```json
{
  "repo_url": "https://github.com/user/repo",
  "pr_number": 123,
  "github_token": "optional_token"
}
```

**Response:**

```json
{
  "task_id": "abc123",
  "status": "pending"
}
```

### 2. GET /status/{task_id}

Check current status.

**Example response:**

```json
{
  "task_id": "abc123",
  "status": "processing",
  "updated_at": "2025-11-17T14:32:00Z"
}
```

**Possible statuses:**
- `pending`
- `processing`
- `completed`
- `failed`

### 3. GET /results/{task_id}

Returns structured code review output.

**Example:**

```json
{
  "task_id": "abc123",
  "status": "completed",
  "results": {
    "files": [
      {
        "name": "main.py",
        "issues": [
          {
            "type": "style",
            "line": 15,
            "description": "Line too long",
            "suggestion": "Break line into multiple lines"
          },
          {
            "type": "bug",
            "line": 23,
            "description": "Potential null pointer",
            "suggestion": "Add null check"
          }
        ]
      }
    ],
    "summary": {
      "total_files": 1,
      "total_issues": 2,
      "critical_issues": 1
    }
  }
}
```

**If still running:**

```json
{ "task_id": "abc123", "status": "processing" }
```

**If failed:**

```json
{
  "task_id": "abc123",
  "status": "failed",
  "error": "Error details here"
}
```

---

## Example Project Structure

```
code-review-agent/
├── app/
│   ├── main.py
│   ├── api/v1/routes.py
│   ├── core/config.py
│   ├── core/logging.py
│   ├── workers/celery_app.py
│   ├── workers/tasks.py
│   ├── services/github_client.py
│   ├── services/caching.py
│   ├── services/storage.py
│   ├── agent/model_client.py
│   ├── agent/reviewer.py
│   └── schemas/pr.py
├── tests/
│   ├── test_api.py
│   ├── test_agent.py
│   └── test_tasks.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## Prerequisites

- Python 3.8+
- Docker & Docker Compose
- Redis (if not using Docker)
- Ollama (for local llama3) or any LLM API key
- Ngrok (for webhook testing)

---

## Setup & Installation

### 1. Clone repo

```bash
git clone https://github.com/<your-username>/code-review-agent
cd code-review-agent
```

### 2. Pull Ollama model

```bash
ollama pull llama3
```

### 3. Create environment file

```bash
cp .env.example .env
```

**Example variables:**

```env
APP_PORT=8000
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
GITHUB_TOKEN=ghp_...
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3
```

---

## Running With Docker (Recommended)

**Start API + worker + Redis:**

```bash
docker-compose up --build
```

**Open documentation:**

```
http://localhost:8000/docs
```

**Stop:**

```bash
docker-compose down
```

---

## Running Locally Without Docker

**Start Redis:**

```bash
docker run -p 6379:6379 redis:7
```

**Install dependencies:**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Start FastAPI:**

```bash
uvicorn app.main:app --reload --port 8000
```

**Start Celery worker:**

```bash
celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

---

## Using ngrok + GitHub Webhooks (Bonus)

**Expose local API:**

```bash
ngrok http 8000
```

**Use forwarding URL in GitHub Webhook settings:**

- **Payload URL:** `https://<ngrok-id>.ngrok.io/webhook/github`
- **Content type:** `application/json`
- **Secret:** same as `GITHUB_WEBHOOK_SECRET`
- Select "Pull request" event.

---

## Example cURL Commands

**Trigger analysis:**

```bash
curl -X POST http://localhost:8000/analyze-pr \
  -H "Content-Type: application/json" \
  -d '{"repo_url":"https://github.com/user/repo","pr_number":123}'
```

**Check status:**

```bash
curl http://localhost:8000/status/abc123
```

**Fetch results:**

```bash
curl http://localhost:8000/results/abc123
```

---

## Testing

**Run test cases:**

```bash
pytest
```

**Coverage:**

```bash
pytest --cov=app
```

---

## Design Decisions

- **FastAPI** chosen for async APIs + automatic docs.
- **Celery** used for heavy/long-running tasks.
- **Redis** used for:
  - Celery broker
  - Result backend
  - Optional caching
- **Agent** uses LangChain/CrewAI/Autogen to plan tasks.
- Supports **Ollama** (local) or any cloud LLM.
- Uses structured JSON results for easy integration with CI/CD or GitHub bots.

---

## Future Improvements

- Multi-language support (Python, JS/TS, Go, Java)
- Auto-post review comments back to PR
- Web dashboard for visualizing issues
- Rate limiting & access control
- Static analyzer integrations (flake8, eslint, mypy)
- Code complexity & security scanning
- Historical analytics dashboard

---

**Happy Code Reviewing! 🚀**