"""Extractors package."""

from etl_pipeline.extractors.base import BaseExtractor
from etl_pipeline.extractors.filesystem_extractor import FilesystemExtractor

__all__ = [
    "BaseExtractor",
    "FilesystemExtractor",
]