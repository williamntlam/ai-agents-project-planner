from pathlib import Path
from typing import Iterator, Set, List, Optional
from datetime import datetime
import os

try:
    import boto3
    from botocore.exceptions import ClientError, BotoCoreError
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False
    boto3 = None
    ClientError = None
    BotoCoreError = None

from models.document import RawDocument
from extractors.base import BaseExtractor
from utils.exceptions import ExtractionError
from utils.retry import retry_connection


class S3Extractor(BaseExtractor):
    """Extracts documents from AWS S3 buckets."""
    
    def __init__(self, config: dict):
        """
        Initialize S3 extractor.
        
        Args:
            config: Configuration dictionary with keys:
                - bucket: S3 bucket name
                - prefix: S3 key prefix to filter objects (default: "")
                - access_key_id: AWS access key ID (from env if not provided)
                - secret_access_key: AWS secret access key (from env if not provided)
                - region: AWS region (from env if not provided)
                - extensions: List of file extensions to include
                - max_file_size_mb: Maximum file size in MB
                - enabled: Whether extractor is enabled
        """
        super().__init__(config)
        
        # Extract configuration
        self.bucket = config.get("bucket") or os.getenv("S3_BUCKET")
        self.prefix = config.get("prefix", "")
        self.access_key_id = config.get("access_key_id") or os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_access_key = config.get("secret_access_key") or os.getenv("AWS_SECRET_ACCESS_KEY")
        self.region = config.get("region") or os.getenv("AWS_REGION", "us-east-1")
        self.extensions: Set[str] = {
            ext.lower() for ext in config.get("extensions", [".md", ".pdf", ".txt", ".docx"])
        }
        self.max_file_size_mb = config.get("max_file_size_mb", 50)
        self.enabled = config.get("enabled", False)
        
        # S3 client (initialized lazily)
        self.s3_client = None
        
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
        # Check boto3 library is available
        if not S3_AVAILABLE:
            raise ValueError(
                "S3 extractor requires 'boto3' library. "
                "Install with: pip install boto3"
            )
        
        # Check bucket is provided
        if not self.bucket:
            raise ValueError(
                "S3 bucket is required. "
                "Set S3_BUCKET environment variable or provide in config."
            )
        
        # Check credentials are provided
        if not self.access_key_id or not self.secret_access_key:
            raise ValueError(
                "AWS credentials are required. "
                "Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables "
                "or provide in config."
            )
        
        # Check extensions
        if not self.extensions:
            raise ValueError(
                "File extensions list cannot be empty."
            )
        
        # Check max_file_size_mb
        if self.max_file_size_mb <= 0:
            raise ValueError(
                f"max_file_size_mb must be positive, got {self.max_file_size_mb}"
            )
        
        return True
    
    def _get_s3_client(self):
        """Get or create S3 client with retry on connection."""
        if self.s3_client is None:
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.access_key_id,
                    aws_secret_access_key=self.secret_access_key,
                    region_name=self.region
                )
                # Test connection
                self.s3_client.head_bucket(Bucket=self.bucket)
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                if error_code == '404':
                    raise ExtractionError(
                        f"S3 bucket not found: {self.bucket}",
                        source_path=f"s3://{self.bucket}",
                        error_code="BUCKET_NOT_FOUND"
                    )
                elif error_code == '403':
                    raise ExtractionError(
                        f"Access denied to S3 bucket: {self.bucket}. "
                        "Check your AWS credentials and permissions.",
                        source_path=f"s3://{self.bucket}",
                        error_code="ACCESS_DENIED"
                    )
                else:
                    raise ExtractionError(
                        f"Failed to connect to S3 bucket: {e}",
                        source_path=f"s3://{self.bucket}",
                        error_code="S3_CONNECTION_ERROR"
                    )
            except Exception as e:
                raise ExtractionError(
                    f"Failed to initialize S3 client: {e}",
                    source_path=f"s3://{self.bucket}",
                    error_code="S3_INIT_ERROR"
                )
        
        return self.s3_client
    
    def extract(self) -> Iterator[RawDocument]:
        """
        Extract raw documents from S3 bucket.
        
        Yields:
            RawDocument: Extracted raw document
        
        Raises:
            ExtractionError: If extraction fails
        """
        if not self.enabled:
            return
        
        try:
            yield from self._extract_from_s3()
        except Exception as e:
            if isinstance(e, ExtractionError):
                raise
            raise ExtractionError(
                f"Failed to extract from S3: {e}",
                source_path=f"s3://{self.bucket}/{self.prefix}",
                error_code="S3_EXTRACTION_FAILED"
            )
    
    @retry_connection(max_attempts=5, wait_seconds=2.0)
    def _extract_from_s3(self) -> Iterator[RawDocument]:
        """
        Extract documents from S3 bucket.
        
        Yields:
            RawDocument: Extracted documents
        """
        s3_client = self._get_s3_client()
        
        # List objects with pagination
        paginator = s3_client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(
            Bucket=self.bucket,
            Prefix=self.prefix
        )
        
        for page in page_iterator:
            # Handle empty bucket
            if 'Contents' not in page:
                continue
            
            # Process each object
            for obj in page['Contents']:
                try:
                    # Skip directories (objects ending with /)
                    if obj['Key'].endswith('/'):
                        continue
                    
                    # Check file extension
                    file_path = Path(obj['Key'])
                    if file_path.suffix.lower() not in self.extensions:
                        continue
                    
                    # Check file size
                    file_size_mb = obj['Size'] / (1024 * 1024)
                    if file_size_mb > self.max_file_size_mb:
                        continue
                    
                    # Download and process file
                    yield from self._process_s3_object(s3_client, obj)
                    
                except ExtractionError:
                    # Re-raise extraction errors
                    raise
                except Exception as e:
                    # Log and skip other errors
                    print(f"Warning: Skipping S3 object {obj['Key']}: {e}")
                    continue
    
    def _process_s3_object(self, s3_client, obj: dict) -> Iterator[RawDocument]:
        """
        Process a single S3 object.
        
        Args:
            s3_client: Boto3 S3 client
            obj: S3 object metadata from list_objects_v2
        
        Yields:
            RawDocument: Extracted document
        """
        try:
            # Download file content
            response = s3_client.get_object(Bucket=self.bucket, Key=obj['Key'])
            content = response['Body'].read()
            
            # Try to decode as text
            try:
                # Try UTF-8 first
                content_str = content.decode('utf-8')
            except UnicodeDecodeError:
                # Try other encodings
                for encoding in ['utf-8-sig', 'latin-1', 'cp1252']:
                    try:
                        content_str = content.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    # If all encodings fail, use replacement
                    content_str = content.decode('utf-8', errors='replace')
            
            # Get metadata
            file_path = Path(obj['Key'])
            metadata = {
                "s3_bucket": self.bucket,
                "s3_key": obj['Key'],
                "file_name": file_path.name,
                "file_path": str(file_path),
                "file_size": obj['Size'],
                "file_size_mb": round(obj['Size'] / (1024 * 1024), 2),
                "last_modified": obj['LastModified'].isoformat() if 'LastModified' in obj else None,
                "etag": obj.get('ETag', '').strip('"'),
                "storage_class": obj.get('StorageClass', 'STANDARD'),
            }
            
            # Determine content type
            content_type = self._get_content_type(file_path.suffix)
            
            # Create RawDocument
            raw_doc = RawDocument(
                source=f"s3://{self.bucket}/{obj['Key']}",
                content=content_str,
                content_type=content_type,
                metadata=metadata
            )
            
            yield raw_doc
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'NoSuchKey':
                raise ExtractionError(
                    f"S3 object not found: {obj['Key']}",
                    source_path=f"s3://{self.bucket}/{obj['Key']}",
                    error_code="OBJECT_NOT_FOUND"
                )
            elif error_code == 'AccessDenied':
                raise ExtractionError(
                    f"Access denied to S3 object: {obj['Key']}",
                    source_path=f"s3://{self.bucket}/{obj['Key']}",
                    error_code="OBJECT_ACCESS_DENIED"
                )
            else:
                raise ExtractionError(
                    f"Failed to download S3 object {obj['Key']}: {e}",
                    source_path=f"s3://{self.bucket}/{obj['Key']}",
                    error_code="OBJECT_DOWNLOAD_ERROR"
                )
        except Exception as e:
            raise ExtractionError(
                f"Failed to process S3 object {obj['Key']}: {e}",
                source_path=f"s3://{self.bucket}/{obj['Key']}",
                error_code="OBJECT_PROCESSING_ERROR"
            )
    
    def _get_content_type(self, extension: str) -> str:
        """
        Map file extension to MIME content type.
        
        Args:
            extension: File extension (e.g., ".md", ".pdf")
        
        Returns:
            str: MIME content type
        """
        mapping = {
            ".md": "text/markdown",
            ".markdown": "text/markdown",
            ".txt": "text/plain",
            ".text": "text/plain",
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
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
