import requests
import re
import structlog
from typing import Optional, Tuple

logger = structlog.get_logger(__name__)

class GitHubClient:
    """
    A simple client to interact with the GitHub API.
    """
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: Optional[str] = None):
        self.base_headers = {
            "X-GitHub-Api-Version": "2022-11-28"
        }
        if token:
            self.base_headers["Authorization"] = f"token {token}"

    def _parse_repo_url(self, repo_url: str) -> Optional[Tuple[str, str]]:
        """Extracts 'owner/repo' from a GitHub URL."""
        match = re.search(r"github\.com/([\w-]+)/([\w-]+)", repo_url)
        if match:
            return match.group(1), match.group(2)
        return None

    def _make_request(self, url: str, headers: dict) -> requests.Response:
        """Helper to make a generic, error-handled request."""
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Raises HTTPError for bad responses
            return response
        
        except requests.exceptions.HTTPError as http_err:
            if response.status_code == 404:
                logger.warn("Resource not found", url=url, status_code=404)
                raise ValueError(f"Resource not found: {url}")
            elif response.status_code == 401:
                logger.error("Authentication failed. Check your GITHUB_TOKEN.", url=url)
                raise ValueError("Authentication failed. Check your GITHUB_TOKEN.")
            else:
                logger.error("HTTP error occurred", url=url, status=response.status_code, text=response.text)
                raise Exception(f"HTTP error occurred: {http_err} - {response.text}")
        except requests.exceptions.RequestException as req_err:
            logger.error("An error occurred during request", url=url, error=str(req_err))
            raise Exception(f"An error occurred: {req_err}")

    def get_pr_diff(self, repo_url: str, pr_number: int) -> str:
        """
        Fetches the diff for a given pull request.
        """
        parsed_url = self._parse_repo_url(repo_url)
        if not parsed_url:
            raise ValueError("Invalid GitHub repository URL")
        
        owner, repo = parsed_url
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
        
        headers = self.base_headers.copy()
        headers["Accept"] = "application/vnd.github.v3.diff"
        
        response = self._make_request(url, headers=headers)
        return response.text
        
    def get_pr_head_sha(self, repo_url: str, pr_number: int) -> str:
        """
        Fetches the SHA of the HEAD commit for a given PR.
        This is used as a cache key.
        """
        parsed_url = self._parse_repo_url(repo_url)
        if not parsed_url:
            raise ValueError("Invalid GitHub repository URL")
            
        owner, repo = parsed_url
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
        
        headers = self.base_headers.copy()
        headers["Accept"] = "application/vnd.github.v3+json"
        
        response = self._make_request(url, headers=headers)
        try:
            sha = response.json()["head"]["sha"]
            return sha
        except KeyError as e:
            logger.error("Failed to parse 'head.sha' from PR response", url=url, key_error=str(e))
            raise ValueError("Could not get PR head SHA. Response format may have changed.")


# --- Helper Functions for Celery ---

def fetch_pr_diff(repo_url: str, pr_number: int, token: Optional[str] = None) -> str:
    """Helper: Fetches the diff for a pull request."""
    logger.info("Fetching PR diff", repo_url=repo_url, pr_number=pr_number)
    client = GitHubClient(token=token)
    diff_text = client.get_pr_diff(repo_url, pr_number)
    
    if not diff_text:
        logger.warn("No diff content returned from GitHub.", repo_url=repo_url, pr_number=pr_number)
        raise ValueError("No diff content returned from GitHub.")
        
    return diff_text

def fetch_pr_head_sha(repo_url: str, pr_number: int, token: Optional[str] = None) -> str:
    """Helper: Fetches the head SHA for a pull request."""
    logger.info("Fetching PR head SHA", repo_url=repo_url, pr_number=pr_number)
    client = GitHubClient(token=token)
    sha = client.get_pr_head_sha(repo_url, pr_number)
    return sha