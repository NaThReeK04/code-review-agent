import os
import structlog
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.models import AnalysisResult, AnalysisSummary

# Use structured logger
logger = structlog.get_logger(__name__)

# [MODIFIED] Added explicit JSON example to force the model to conform
SYSTEM_PROMPT_TEMPLATE = """
You are an expert Autonomous Code Review Agent. Your goal is to analyze a given Git diff and provide a structured, actionable review.

**Your Task:**
1.  Analyze the provided `diff` text.
2.  Focus *only* on the changes (lines starting with `+` or `-`).
3.  Identify issues related to:
    - Potential Bugs (e.g., null pointers, off-by-one errors)
    - Performance (e.g., N+1 queries, inefficient loops)
    - Best Practices (e.g., magic numbers, code duplication)
    - Security (e.g., SQL injection, hardcoded secrets)
    - Code Style (e.g., complex logic, poor naming)

**CRITICAL: JSON Output Format**
You MUST provide your review in the following JSON format. 
IMPORTANT: The "summary" field must be a nested OBJECT, not a string.

**Example of Valid Output:**
{{
    "files": [
        {{
            "file_path": "src/main.py",
            "issues": [
                {{
                    "type": "style",
                    "line": 10,
                    "description": "Line too long",
                    "suggestion": "Break line"
                }}
            ]
        }}
    ],
    "summary": {{
        "total_files_reviewed": 1,
        "total_issues_found": 1,
        "critical_issues": 0,
        "overview": "Brief overview of changes."
    }}
}}

**Your JSON Schema:**
{json_schema}
"""

class CodeReviewAgent:
    
    def __init__(self):
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3")
        
        logger.info(f"Initializing agent", ollama_url=self.ollama_base_url, model=self.ollama_model)

        try:
            self.llm = ChatOllama(
                base_url=self.ollama_base_url,
                model=self.ollama_model,
                temperature=0,
                keep_alive="5m" 
            )
            self.llm.invoke("Hi")
            logger.info("Ollama connection successful.")
        except Exception as e:
            logger.error(f"Failed to connect to Ollama", url=self.ollama_base_url, error=str(e))
            logger.error("Please ensure Ollama is running and accessible.")
            raise

        self.parser = JsonOutputParser(pydantic_object=AnalysisResult)
        
        self.prompt = ChatPromptTemplate(
            messages=[
                SystemMessagePromptTemplate.from_template(
                    SYSTEM_PROMPT_TEMPLATE,
                    partial_variables={"json_schema": self.parser.get_format_instructions()}
                ),
                HumanMessagePromptTemplate.from_template(
                    "Here is the diff to review:\n\n```diff\n{diff_text}\n```"
                )
            ]
        )
        
        self.chain = self.prompt | self.llm | self.parser

    def review_code_diff(self, diff_text: str) -> AnalysisResult:
        if not diff_text.strip():
            logger.warn("Diff text is empty. Returning empty analysis.")
            return AnalysisResult(
                files=[],
                summary=AnalysisSummary(
                    total_files_reviewed=0,
                    total_issues_found=0,
                    critical_issues=0,
                    overview="The provided diff was empty. No changes to review."
                )
            )
            
        logger.info("Starting code review with LLM...")
        try:
            raw_result = self.chain.invoke({"diff_text": diff_text})
            analysis = AnalysisResult.model_validate(raw_result)
            logger.info("Code review analysis complete.")
            return analysis
            
        except Exception as e:
            logger.error("Error during LLM chain invocation or parsing", error=str(e), exc_info=True)
            raise ValueError(f"Failed to get valid analysis from LLM: {e}")