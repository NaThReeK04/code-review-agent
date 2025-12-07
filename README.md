# Code-Review-Agent

An autonomous code review system that uses AI to analyze GitHub pull requests. It implements a goal-oriented agent that can:

- Fetch PR metadata and diffs from GitHub  
- Plan and execute a multi-step review process  
- Run asynchronously using Celery workers  
- Expose a clean FastAPI HTTP API for developers  
- Return structured, machine-readable feedback for each file and issue  

**Tech stack:** FastAPI, Celery, Redis, MySQL, LangChain/Agent framework, Ollama (llama3.2) or LLM API, Docker, pytest

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

### Redis/MySQL Storage
- Redis: Stores task queues and caching entries  
- MySQL: Persistently stores final processed review results  

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

High-level flow:

1. Client sends POST /analyze-pr  
2. FastAPI enqueues Celery task  
3. Worker fetches PR diff, runs AI analysis, stores results in MySQL  
4. Client polls status + results  

---

## API Overview

### POST /analyze-pr

```json
{
  "repo_url": "https://github.com/user/repo",
  "pr_number": 123,
  "github_token": "optional_token"
}
```

Response:

```json
{
  "task_id": "abc123",
  "status": "pending"
}
```

---

### GET /status/{task_id}

```json
{
  "task_id": "abc123",
  "status": "processing"
}
```

---

### GET /results/{task_id}

```json
{
  "task_id": "abc123",
  "status": "completed",
  "results": {}
}
```

---

## Example Project Structure

```
code-review-agent/
├── app/
│   ├── __init__.py
│   ├── agent.py
│   ├── celery_worker.py
│   ├── database.py
│   ├── github_client.py
│   ├── logging_config.py
│   ├── main.py
│   ├── models.py
│   └── schemas.py
├── .env
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── README.md
└── requirements.txt
```

---

## Persistent Storage in MySQL

All processed results are stored in MySQL.

### Example schema:

```sql
CREATE TABLE reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(255) UNIQUE NOT NULL,
    repo_url TEXT NOT NULL,
    pr_number INT NOT NULL,
    status VARCHAR(50) NOT NULL,
    result_json JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

---

## Viewing Stored Data

### Terminal (Docker)

```bash
docker exec -it code-review-agent-db-1 mysql -u user -p
USE codereviewdb;
SELECT * FROM reviews \G;
```

### MySQL Workbench

```
Host: 127.0.0.1
Port: 3307
User: user
Password: password
Database: codereviewdb
```

---

## Setup & Installation

### Clone repo

```bash
git clone https://github.com/<your-username>/code-review-agent
cd code-review-agent
```

### Pull model

```bash
ollama pull llama3.2
```

### Create environment file

```bash
cp .env.example .env
```

---

## Running With Docker

```bash
docker-compose up --build
```

Docs:

```
http://localhost:8000/docs
```

Stop:

```bash
docker-compose down
```

---

## Testing

```bash
pytest
```

Coverage:

```bash
pytest --cov=app
```

---

## Future Improvements

- Multi-language analyzers  
- PR auto-commenting  
- Web dashboard  
- Static analysis + security scanning  
