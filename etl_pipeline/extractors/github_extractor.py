from pathlib import Path
from typing import Iterator, Set, List, Optional
from datetime import datetime
import tempfile
import shutil
import subprocess
import base64

try:
    from github import Github, GithubException
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False
    Github = None
    GithubException = None

from models.document import RawDocument
from extractors.base import BaseExtractor
from utils.exceptions import ExtractionError
from utils.retry import retry_api_call


class GitHubExtractor(BaseExtractor):
    """Extracts documents from GitHub repositories."""
    
    def __init__(self, config: dict):
        """
        Initialize GitHub extractor.
        
        Args:
            config: Configuration dictionary with keys:
                - token: GitHub personal access token
                - repos: List of repository names (format: "owner/repo")
                - file_extensions: List of file extensions to include
                - enabled: Whether extractor is enabled
                - method: "api" or "clone" (default: "api")
                - max_file_size_mb: Maximum file size in MB
        """
        super().__init__(config)
        
        # Extract configuration
        self.token = config.get("token") or os.getenv("GITHUB_TOKEN")
        self.repos: List[str] = config.get("repos", [])
        self.file_extensions: Set[str] = {
            ext.lower() for ext in config.get("file_extensions", [".md", ".txt"])
        }
        self.enabled = config.get("enabled", False)
        self.method = config.get("method", "api")  # "api" or "clone"
        self.max_file_size_mb = config.get("max_file_size_mb", 10)
        self.temp_dir: Optional[Path] = None
        
        # Validate configuration if enabled
        if self.enabled:
            self.validate_config()
    
    def validate_config(self) -> bool:
        """
        Validate that the extractor configuration is valid.
        
        Returns:
            bool: True if configuration is valid
        
        Raises:
            ValueError: If configuration is invalid
        """
        # Check GitHub library is available if using API
        if self.method == "api" and not GITHUB_AVAILABLE:
            raise ValueError(
                "GitHub API method requires 'PyGithub' library. "
                "Install with: pip install PyGithub"
            )
        
        # Check token is provided
        if not self.token:
            raise ValueError(
                "GitHub token is required. "
                "Set GITHUB_TOKEN environment variable or provide in config."
            )
        
        # Check repos list is not empty
        if not self.repos:
            raise ValueError(
                "Repos list cannot be empty. "
                "Please specify at least one repository (format: 'owner/repo')."
            )
        
        # Validate repo format
        for repo in self.repos:
            if "/" not in repo or repo.count("/") != 1:
                raise ValueError(
                    f"Invalid repo format: {repo}. "
                    "Expected format: 'owner/repo-name'"
                )
        
        # Check file extensions
        if not self.file_extensions:
            raise ValueError(
                "File extensions list cannot be empty."
            )
        
        # Check max_file_size_mb
        if self.max_file_size_mb <= 0:
            raise ValueError(
                f"max_file_size_mb must be positive, got {self.max_file_size_mb}"
            )
        
        return True
    
    def extract(self) -> Iterator[RawDocument]:
        """
        Extract raw documents from GitHub repositories.
        
        Yields:
            RawDocument: Extracted raw document
        
        Raises:
            ExtractionError: If extraction fails
        """
        if not self.enabled:
            return
        
        try:
            if self.method == "api":
                yield from self._extract_via_api()
            elif self.method == "clone":
                yield from self._extract_via_clone()
            else:
                raise ValueError(f"Unknown extraction method: {self.method}")
        except Exception as e:
            raise ExtractionError(
                f"Failed to extract from GitHub: {e}",
                error_code="GITHUB_EXTRACTION_FAILED"
            )
        finally:
            # Clean up temp directory if using clone method
            self._cleanup_temp_dir()
    
    def _extract_via_api(self) -> Iterator[RawDocument]:
        """
        Extract files using GitHub API.
        
        Yields:
            RawDocument: Extracted documents
        """
        github = Github(self.token)
        
        for repo_name in self.repos:
            try:
                owner, repo_name_only = repo_name.split("/", 1)
                repo = github.get_repo(repo_name)
                
                # Process all files in repository
                yield from self._process_repo_files_api(repo, repo_name)
                
            except GithubException as e:
                if e.status == 404:
                    raise ExtractionError(
                        f"Repository not found: {repo_name}",
                        source_path=repo_name,
                        error_code="REPO_NOT_FOUND"
                    )
                elif e.status == 403:
                    raise ExtractionError(
                        f"Access denied to repository: {repo_name}. "
                        "Check your token permissions.",
                        source_path=repo_name,
                        error_code="ACCESS_DENIED"
                    )
                else:
                    raise ExtractionError(
                        f"GitHub API error for {repo_name}: {e}",
                        source_path=repo_name,
                        error_code="GITHUB_API_ERROR"
                    )
            except Exception as e:
                raise ExtractionError(
                    f"Failed to process repository {repo_name}: {e}",
                    source_path=repo_name,
                    error_code="REPO_PROCESSING_ERROR"
                )
    
    @retry_api_call(max_attempts=3, wait_seconds=2.0)
    def _process_repo_files_api(self, repo, repo_name: str) -> Iterator[RawDocument]:
        """
        Process all files in a repository via API.
        
        Args:
            repo: GitHub repository object
            repo_name: Repository name (owner/repo)
        
        Yields:
            RawDocument: Extracted documents
        """
        try:
            # Get repository contents (starting from root)
            contents = repo.get_contents("")
            
            # Process files recursively
            for content in contents:
                yield from self._process_content_api(content, repo, repo_name)
                
        except GithubException as e:
            if "rate limit" in str(e).lower():
                # Handle rate limiting
                rate_limit = repo.raw_data.get("rate_limit", {})
                reset_time = rate_limit.get("reset", 0)
                raise ExtractionError(
                    f"GitHub API rate limit exceeded. "
                    f"Resets at: {datetime.fromtimestamp(reset_time)}",
                    source_path=repo_name,
                    error_code="RATE_LIMIT_EXCEEDED"
                )
            raise
    
    def _process_content_api(
        self, 
        content, 
        repo, 
        repo_name: str
    ) -> Iterator[RawDocument]:
        """
        Process a single content item (file or directory).
        
        Args:
            content: GitHub Content object
            repo: GitHub repository object
            repo_name: Repository name
        
        Yields:
            RawDocument: Extracted documents
        """
        try:
            if content.type == "file":
                # Check if file extension matches
                file_path = Path(content.path)
                if file_path.suffix.lower() not in self.file_extensions:
                    return
                
                # Check file size
                if content.size > (self.max_file_size_mb * 1024 * 1024):
                    return
                
                # Download file content
                file_content = self._download_file_content_api(content)
                
                # Create RawDocument
                metadata = {
                    "repo": repo_name,
                    "file_path": content.path,
                    "file_name": content.name,
                    "file_size": content.size,
                    "sha": content.sha,
                    "url": content.html_url,
                    "download_url": content.download_url,
                }
                
                raw_doc = RawDocument(
                    source=f"github://{repo_name}/{content.path}",
                    content=file_content,
                    content_type=self._get_content_type(file_path.suffix),
                    metadata=metadata
                )
                
                yield raw_doc
                
            elif content.type == "dir":
                # Recursively process directory
                dir_contents = repo.get_contents(content.path)
                for item in dir_contents:
                    yield from self._process_content_api(item, repo, repo_name)
                    
        except Exception as e:
            # Log error but continue processing other files
            print(f"Warning: Failed to process {content.path}: {e}")
    
    def _download_file_content_api(self, content) -> str:
        """
        Download file content from GitHub API.
        
        Args:
            content: GitHub Content object
        
        Returns:
            str: File content as string
        
        Raises:
            ExtractionError: If download fails
        """
        try:
            # If file is small, content is already in the object
            if content.encoding == "base64" and content.content:
                # Decode base64 content
                decoded = base64.b64decode(content.content)
                return decoded.decode('utf-8', errors='replace')
            
            # For larger files, use download_url
            elif content.download_url:
                import requests
                response = requests.get(
                    content.download_url,
                    headers={"Authorization": f"token {self.token}"},
                    timeout=30
                )
                response.raise_for_status()
                return response.text
            
            else:
                raise ExtractionError(
                    f"Cannot download file content: {content.path}",
                    source_path=content.path,
                    error_code="CONTENT_DOWNLOAD_FAILED"
                )
                
        except Exception as e:
            raise ExtractionError(
                f"Failed to download file content: {e}",
                source_path=content.path,
                error_code="FILE_DOWNLOAD_ERROR"
            )
    
    def _extract_via_clone(self) -> Iterator[RawDocument]:
        """
        Extract files by cloning repository locally.
        
        Yields:
            RawDocument: Extracted documents
        """
        # Create temporary directory for clones
        self.temp_dir = Path(tempfile.mkdtemp(prefix="github_extractor_"))
        
        try:
            for repo_name in self.repos:
                try:
                    # Clone repository
                    repo_path = self._clone_repository(repo_name)
                    
                    # Process files in cloned repository
                    yield from self._process_cloned_repo(repo_path, repo_name)
                    
                except Exception as e:
                    raise ExtractionError(
                        f"Failed to process repository {repo_name}: {e}",
                        source_path=repo_name,
                        error_code="REPO_CLONE_ERROR"
                    )
        finally:
            # Cleanup will happen in finally block
            pass
    
    def _clone_repository(self, repo_name: str) -> Path:
        """
        Clone repository to temporary directory.
        
        Args:
            repo_name: Repository name (owner/repo)
        
        Returns:
            Path: Path to cloned repository
        
        Raises:
            ExtractionError: If clone fails
        """
        repo_path = self.temp_dir / repo_name.replace("/", "_")
        
        # Construct clone URL
        if self.token:
            clone_url = f"https://{self.token}@github.com/{repo_name}.git"
        else:
            clone_url = f"https://github.com/{repo_name}.git"
        
        try:
            # Clone repository
            subprocess.run(
                ["git", "clone", "--depth", "1", clone_url, str(repo_path)],
                check=True,
                capture_output=True,
                timeout=300  # 5 minute timeout
            )
            
            return repo_path
            
        except subprocess.CalledProcessError as e:
            raise ExtractionError(
                f"Failed to clone repository {repo_name}: {e.stderr.decode()}",
                source_path=repo_name,
                error_code="CLONE_FAILED"
            )
        except subprocess.TimeoutExpired:
            raise ExtractionError(
                f"Clone timeout for repository {repo_name}",
                source_path=repo_name,
                error_code="CLONE_TIMEOUT"
            )
    
    def _process_cloned_repo(self, repo_path: Path, repo_name: str) -> Iterator[RawDocument]:
        """
        Process files in cloned repository.
        
        Args:
            repo_path: Path to cloned repository
            repo_name: Repository name
        
        Yields:
            RawDocument: Extracted documents
        """
        # Walk through repository files
        for file_path in repo_path.rglob("*"):
            if not file_path.is_file():
                continue
            
            # Check extension
            if file_path.suffix.lower() not in self.file_extensions:
                continue
            
            # Check file size
            try:
                file_size_mb = file_path.stat().st_size / (1024 * 1024)
                if file_size_mb > self.max_file_size_mb:
                    continue
            except OSError:
                continue
            
            # Read file
            try:
                content = file_path.read_text(encoding='utf-8', errors='replace')
                
                # Create relative path for source
                relative_path = file_path.relative_to(repo_path)
                
                metadata = {
                    "repo": repo_name,
                    "file_path": str(relative_path),
                    "file_name": file_path.name,
                    "file_size": file_path.stat().st_size,
                }
                
                raw_doc = RawDocument(
                    source=f"github://{repo_name}/{relative_path}",
                    content=content,
                    content_type=self._get_content_type(file_path.suffix),
                    metadata=metadata
                )
                
                yield raw_doc
                
            except Exception as e:
                print(f"Warning: Failed to read {file_path}: {e}")
                continue
    
    def _get_content_type(self, extension: str) -> str:
        """
        Map file extension to MIME content type.
        
        Args:
            extension: File extension (e.g., ".md", ".py")
        
        Returns:
            str: MIME content type
        """
        mapping = {
            ".md": "text/markdown",
            ".markdown": "text/markdown",
            ".txt": "text/plain",
            ".py": "text/x-python",
            ".js": "text/javascript",
            ".json": "application/json",
            ".yaml": "text/yaml",
            ".yml": "text/yaml",
            ".xml": "application/xml",
            ".html": "text/html",
            ".css": "text/css",
        }
        
        return mapping.get(extension.lower(), "application/octet-stream")
    
    def _cleanup_temp_dir(self):
        """Clean up temporary directory used for cloning."""
        if self.temp_dir and self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"Warning: Failed to cleanup temp directory: {e}")