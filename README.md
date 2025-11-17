Autonomous AI Code Review Agent (v1.1)
An autonomous AI-powered code review system that automatically analyzes GitHub pull requests (PRs) using a local large language model. It provides structured, asynchronous feedback on code quality, style, and performance—and integrates seamlessly with GitHub webhooks for fully automated reviews.

🚀 Overview
Autonomous AI Code Review Agent uses FastAPI, Celery, Redis, and LangChain (with Ollama-based local LLMs such as llama3) to review pull requests end-to-end. It is designed for developers who want fast, private, and automated AI code analysis directly within their development workflow.

⚙️ Core Features
FastAPI Endpoints: A structured API to submit PRs, check task status, and retrieve AI review results.
Asynchronous Processing: Celery and Redis manage AI review tasks in the background.
AI-Powered Review: LangChain agents analyze code diffs using local LLMs for bugs, style, and best practices.
GitHub Webhook Integration: Automatically triggers code reviews on pull request events.
Result Caching: Avoids redundant analysis using commit SHA-based caching.
Structured Logging: Emits JSON logs via structlog for production observability.
Rate Limiting: slowapi prevents endpoint abuse.
Dockerized Deployment: Fully containerized for a one-command setup.
🧠 Technical Stack
Component	Technology
Backend	Python 3.10
API Framework	FastAPI
Async Queue	Celery
Broker/Cache	Redis
AI Agent	LangChain
LLM	Ollama (e.g., llama3, mistral)
Containerization	Docker & Docker Compose
Logging	Structlog
Rate Limiting	SlowAPI
🧩 Project Setup & Running
1. Prerequisites
Docker and Docker Compose installed
Ollama installed and running locally
2. Install Ollama Model
ollama pull llama3

text

3. Configure Environment
Clone the repository and copy the environment example file:

cp .env.example .env

text

Add your GitHub Personal Access Token to .env:

GITHUB_TOKEN=ghp_...

text

4. Build and Run Containers
From the project root:

docker-compose up --build

text

This starts:

api → FastAPI server at http://localhost:8000
worker → Celery worker processing review jobs
redis → Redis for message brokering and caching
API Docs: http://localhost:8000/docs

🧪 Test Instructions & API Usage
✅ Test 1: Manual Analysis
Step 1. Submit a PR for Analysis
Endpoint: POST /analyze-pr

Example (Mac/Linux):

curl -X POST "http://localhost:8000/analyze-pr"
-H "Content-Type: application/json"
-d '{
"repo_url": "https://github.com/pallets/flask",
"pr_number": 5336
}'

text

Response:

{
"task_id": "3fee0bc3-6e37-48d6-ad07-a8040746bac3",
"status": "PENDING"
}

text

Step 2. Check Job Status
Endpoint: GET /status/<task_id>

curl "http://localhost:8000/status/3fee0bc3-6e37-48d6-ad07-a8040746bac3"

text

Success Response:

{
"task_id": "3fee0bc3-6e37-48d6-ad07-a8040746bac3",
"status": "SUCCESS"
}

text

Step 3. Get Review Results
Endpoint: GET /results/<task_id>

curl "http://localhost:8000/results/3fee0bc3-6e37-48d6-ad07-a8040746bac3"

text

Example Output:

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
"description": "Function name is too long, reducing readability.",
"suggestion": "Consider renaming to _check_deferred_bound_method."
}
]
}
],
"summary": {
"total_files_reviewed": 1,
"total_issues_found": 1,
"critical_issues": 0,
"overview": "Refactor looks sound overall; minor style suggestion noted."
}
},
"error": null
}

text

🤖 Test 2: Automated Webhook Analysis
Use ngrok to expose your local FastAPI server.

Step 1. Start ngrok
ngrok config add-authtoken YOUR_TOKEN_HERE
ngrok http 8000

text

Copy your live ngrok URL (e.g., https://1a2b-3c4d-5e6f.ngrok-free.app).

Step 2. Configure GitHub Webhook
Go to Settings → Webhooks → Add webhook
Payload URL:
https://your-ngrok-url/webhook/github
Content type: application/json
Events: Select “Pull requests”
After adding the webhook, opening or updating a PR will automatically trigger analysis.

Check logs:

ngrok terminal: Should show POST /webhook/github 202 Accepted
Docker logs: Celery worker starts analyzing automatically
🧱 Design Decisions
FastAPI: High performance, async support, and built-in OpenAPI documentation.
Celery + Redis: Robust distributed task queue to decouple slow LLM processing.
Ollama: Runs LLMs locally, ensuring privacy and eliminating API costs.
LangChain: Provides prompt orchestration, parsing, and structured JSON output.
Result Caching: Commit SHA–based caching avoids redundant AI work.
Structured Logging: Ensures logs are JSON-formatted and easily integrated into tools like Datadog or Splunk.
🔮 Future Improvements
Database: Migrate from Redis to PostgreSQL for durable result storage.
GitHub App Integration: Replace basic webhook with a secure GitHub App for posting inline PR comments.
Multi-LLM Support: Enable dynamic model choices (Llama3, GPT-4o, Claude).
Multi-Agent Analysis: Introduce agents specialized for Security, Performance, and Style.
Automated Testing: Add pytest suite with mocks for external services.
📜 License
MIT License © 2025 – Autonomous AI Code Review Agent
Developed for autonomous, efficient, and private AI-driven code analysis.
Would you like this version to include a table of contents section with navigation links (common for large GitHub READMEs)?

can u give me a downloaable readme file

A downloadable README.md file can be generated directly from your project’s description. Below is the content packaged in a file format you can copy into your environment or request as a file download.

Since this platform cannot send files directly, you can do one of the following:

Copy the content below into a file named README.md in your project root.

Or save it using command-line redirection:

bash
curl -o README.md https://pastebin.com/raw/your_paste_id_here
Here’s the ready-to-save Markdown file content:

text

Autonomous AI Code Review Agent (v1.1)
An autonomous AI code review system that automatically analyzes GitHub pull requests using a local large language model (LLM). It provides structured, asynchronous feedback on code quality, performance, and best practices, with optional GitHub webhook automation.

Overview
Autonomous AI Code Review Agent uses FastAPI, Celery, Redis, and LangChain (with Ollama-based local LLMs like llama3) to review pull requests end-to-end. Designed for developers who want fast, private, and automated AI review directly in their workflows.

Core Features
FastAPI endpoints to submit PRs, check task status, and retrieve AI-generated code reviews.
Asynchronous processing with Celery and Redis for smooth, non-blocking AI analysis.
Local AI analysis using LangChain agents with Ollama LLMs.
Automatic GitHub webhook integration for pull request events.
Commit SHA-based caching to skip redundant reviews.
Structured JSON logs via structlog for production observability.
Rate limiting to prevent abuse.
Fully containerized Docker setup.
Technical Stack
Component	Technology
Backend	Python 3.10
API Framework	FastAPI
Async Task Queue	Celery
Broker/Cache	Redis
AI Agent	LangChain
LLM	Ollama (llama3, mistral)
Containerization	Docker & Docker Compose
Logging	Structlog
Rate Limiting	SlowAPI
Setup Instructions
1. Prerequisites
Docker and Docker Compose
Ollama installed and running locally
2. Pull the AI Model
ollama pull llama3

text

3. Configure Environment
Clone the repository and copy .env.example:

cp .env.example .env

text

Add your GitHub token:

GITHUB_TOKEN=ghp_...

text

4. Build and Run
docker-compose up --build

text

This starts:

api – FastAPI server at http://localhost:8000
worker – Celery task processor
redis – Redis cache and broker
Docs: http://localhost:8000/docs

Testing & API Usage
Manual Analysis
Submit PR for analysis
curl -X POST "http://localhost:8000/analyze-pr"
-H "Content-Type: application/json"
-d '{
"repo_url": "https://github.com/pallets/flask",
"pr_number": 5336
}'

text

Check job status
curl "http://localhost:8000/status/<task_id>"

text

Get results
curl "http://localhost:8000/results/<task_id>"

text

Example response:

{
"task_id": "example-task-id",
"status": "COMPLETED",
"results": {
"files": [...],
"summary": {
"total_files_reviewed": 1,
"total_issues_found": 1,
"critical_issues": 0
}
}
}

text

Automated Webhook Analysis
To test automatic PR analysis, use ngrok to expose your local instance.

Setup steps
Install and authenticate ngrok:
ngrok config add-authtoken YOUR_TOKEN_HERE
ngrok http 8000
text

In your GitHub repository:
Go to Settings → Webhooks → Add webhook
Payload URL: https://your-ngrok-url/webhook/github
Content type: application/json
Select: “Pull requests”
Click Add webhook
After creating or updating a PR:

ngrok should display POST /webhook/github 202 Accepted
Celery workers begin AI review automatically
Design Choices
FastAPI for high performance and async handling.
Celery + Redis for a distributed, reliable task queue.
Ollama to run local LLMs, keeping data private.
LangChain for agent orchestration and structured JSON outputs.
Structlog for clean, machine-readable logs.
Commit-based caching to optimize performance.
Future Improvements
PostgreSQL backend for persistent, relational storage.
GitHub App integration for inline PR comments.
Multi-LLM support (GPT-4o, Claude, Llama3).
Multi-agent collaboration using LangGraph or CrewAI.
Unit testing with pytest and service mocks.
License
MIT License © 2025 – Autonomous AI Code Review Agent
