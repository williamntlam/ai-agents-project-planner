"""Extractors package."""

from extractors.base import BaseExtractor
from extractors.filesystem_extractor import FilesystemExtractor
from extractors.github_extractor import GitHubExtractor

__all__ = [
    "BaseExtractor",
    "FilesystemExtractor",
    "GitHubExtractor",
]