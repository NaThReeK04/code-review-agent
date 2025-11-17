# Autonomous AI Code Review Agent (v1.1)

This project is an autonomous code review system that uses AI to analyze GitHub pull requests. It processes PRs asynchronously, provides structured feedback via an API, and can be integrated directly with GitHub webhooks for fully automated reviews.

The system is built with FastAPI, Celery, Redis, Docker, and uses a LangChain agent with a local Ollama model (`llama3`) for AI analysis.

## Core Features

-   **FastAPI Endpoints:** A structured API to submit, check status, and retrieve results.
-   **Asynchronous Processing:** Uses Celery and Redis to handle time-consuming AI analysis in the background without blocking the API.
-   **AI-Powered Review:** A LangChain agent prompts a local LLM (via Ollama) to analyze code diffs for bugs, style, performance, and best practices.
-   **GitHub Webhook Integration:** A `/webhook/github` endpoint automatically triggers reviews on `pull_request` events.
-   **Result Caching:** Caches results in Redis based on the PR's commit SHA to avoid re-analyzing unchanged code instantly.
-   **Structured Logging:** All logs are emitted as JSON (using `structlog`) for easy parsing in a production environment.
-   **Rate Limiting:** Protects the API from abuse using `slowapi`.
-   **Dockerized:** Fully containerized with `docker-compose` for one-command setup.

---

## Technical Stack

-   **Backend:** Python 3.10
-   **API:** FastAPI
-   **Async Task Queue:** Celery
-   **Message Broker / Result / Cache:** Redis
-   **AI Agent:** LangChain
-   **LLM:** Ollama (e.g., `llama3`, `mistral`)
-   **Containerization:** Docker & Docker Compose
-   **Logging:** Structlog
-   **Rate Limiting:** SlowAPI

---

## Project Setup & Running

These instructions explain how to run the project on your local machine.

### 1. Prerequisites

-   [Docker](https://www.docker.com/get-started) and [Docker Compose](https://docs.docker.com/compose/install/)
-   [Ollama](https://ollama.com/download) installed and running on your host machine.

### 2. Install Ollama Model

Before starting, pull the AI model. Open your terminal and run:

```bash
ollama pull llama3
3. Configure Environment
Clone this repository.

Copy the example environment file:

Bash

cp .env.example .env
Open the .env file and add your GitHub Personal Access Token. This is required for the webhook and caching features.

GITHUB_TOKEN=ghp_...
4. Build and Run Containers
From the project root, run:

Bash

docker-compose up --build
This will build the Docker images and start all three services:

api: The FastAPI server on http://localhost:8000

worker: The Celery worker processing jobs.

redis: The Redis database.

The API documentation is now available at http://localhost:8000/docs.

Test Instructions & API Usage
You can test the API with any terminal.

Test 1: Manual Analysis
Step 1. Submit a PR for Analysis
Task: Submits a job to the queue.

Endpoint: POST /analyze-pr

PowerShell Command (for Windows):

PowerShell

curl -Method POST -Uri "http://localhost:8000/analyze-pr" `
-Headers @{"Content-Type"="application/json"} `
-Body '{
    "repo_url": "[https://github.com/pallets/flask](https://github.com/pallets/flask)",
    "pr_number": 5336
}'
cURL Command (for Mac/Linux):

Bash

curl -X POST "http://localhost:8000/analyze-pr" \
-H "Content-Type: application/json" \
-d '{
      "repo_url": "[https://github.com/pallets/flask](https://github.com/pallets/flask)",
      "pr_number": 5336
    }'
Response:

JSON

{
  "task_id": "3fee0bc3-6e37-48d6-ad07-a8040746bac3",
  "status": "PENDING"
}
Step 2. Check Job Status
Task: Check the status of the job. (Wait 30-60 seconds for the AI).

Endpoint: GET /status/<task_id>

PowerShell:

PowerShell

# Replace with your task_id
curl -Uri "http://localhost:8000/status/3fee0bc3-6e37-48d6-ad07-a8040746bac3"
cURL:

Bash

# Replace with your task_id
curl "http://localhost:8000/status/3fee0bc3-6e37-48d6-ad07-a8040746bac3"
Response (when done):

JSON

{
  "task_id": "3fee0bc3-6e37-48d6-ad07-a8040746bac3",
  "status": "SUCCESS"
}
Step 3. Get the Results
Task: Get the final JSON review.

Endpoint: GET /results/<task_id>

PowerShell:

PowerShell

# Replace with your task_id
curl -Uri "http://localhost:8000/results/3fee0bc3-6e37-48d6-ad07-a8040746bac3"
cURL:

Bash

# Replace with your task_id
curl "http://localhost:8000/results/3fee0bc3-6e37-48d6-ad07-a8040746bac3"
Response (Example JSON Output):

JSON

{
  "task_id": "3fee0bc3-6e37-48d6-ad07-a8040746bac3",
  "status": "COMPLETED",
  "results": {
    "files": [
      {
        "file_path": "src/flask/app.py",
        "issues": [
          {
            "type": "best_practice",
            "line": 490,
            "description": "The function `_check_for_deferred_endpoint_bound_method` has a very long name, which can slightly reduce readability.",
            "suggestion": "Consider a shorter name like `_check_deferred_bound_method` if it doesn't sacrifice clarity within the module."
          }
        ]
      }
    ],
    "summary": {
      "total_files_reviewed": 1,
      "total_issues_found": 1,
      "critical_issues": 0,
      "overview": "The pull request refactors internal endpoint handling logic. One minor best_practice issue regarding a long function name was identified. The overall change appears solid."
    }
  },
  "error": null
}
Test 2: Automated Webhook Analysis
This tests the full, automated workflow.

Expose Localhost: Your server at localhost:8000 must be visible to GitHub. We use ngrok for this.

Install ngrok.

Add your free authtoken (one-time setup):

Bash

ngrok config add-authtoken YOUR_TOKEN_HERE
Run ngrok to get a public URL:

Bash

ngrok http 8000
Copy the https://....ngrok-free.app URL. This is your Live API URL.

Configure GitHub Webhook:

Go to a test repository you own on GitHub.

Go to Settings > Webhooks > Add webhook.

Payload URL: Paste your ngrok URL + /webhook/github (e.g., https://1a2b-3c4d-5e6f.ngrok-free.app/webhook/github)

Content type: application/json

Which events? Select "Let me select individual events." and check "Pull requests".

Click "Add webhook".

Test It:

Go to your test repository and open a new Pull Request (or push a new commit to an existing one).

Observe:

The ngrok terminal will show a POST /webhook/github 202 Accepted.

Your docker-compose logs will show the worker-1 service start the new task.

The review has been triggered automatically. You can use the task_id from the logs to check the results, just like in Test 1.

Design Decisions
FastAPI: Chosen for its high performance, async capabilities, and automatic documentation (/docs), which is ideal for an API-first service.

Celery & Redis: Selected for a robust, distributed task queue. This decouples the time-consuming AI analysis from the API request, preventing timeouts and allowing the system to be scaled (e.g., by adding more workers).

Ollama: Used to run powerful LLMs locally. This avoids API costs (OpenAI, Anthropic) and keeps data private.

LangChain: Acts as the "brain" or agent framework. It simplifies prompt management, output parsing (ensuring valid JSON), and interaction with the LLM.

Result Caching: Implemented to improve performance and reduce redundant compute. Caching by commit SHA is a reliable way to ensure we only re-run analysis when the code actually changes.

Structured Logging: structlog was chosen to make all logs machine-readable (JSON). In a production system, this is non-negotiable for feeding into log aggregation tools (e.g., Splunk, Datadog).

Future Improvements
Database: Use PostgreSQL instead of Redis for the result backend. This allows for persistent, relational storage of all review history.

GitHub App: Convert the service into a formal GitHub App instead of using a simple webhook. This would allow for a more secure authentication flow and the ability to post review comments directly onto the PR in GitHub.

Multi-LLM Support: Refactor the agent to easily swap LLMs (e.g., llama3, gpt-4o, claude-3-sonnet) based on configuration, allowing users to choose their preferred model.

In-Depth Analysis: Use a multi-agent framework (like LangGraph or CrewAI) to create a team of specialized agents (e.g., SecurityAgent, PerformanceAgent, StyleAgent) that collaborate on the review for more detailed feedback.

Add Tests: Implement pytest unit tests for the API and agent logic, mocking external services.
