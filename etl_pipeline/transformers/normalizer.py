# md/pdf → RawDocument normalizer

from typing import Dict
from datetime import datetime
from pathlib import Path

from transformers.base import BaseNormalizer
from models.document import RawDocument, Document
from utils.exceptions import TransformationError
import re
import textwrap


class Normalizer(BaseNormalizer):
    def __init__(self, config: Dict):
        super().__init__(config)
        self.preserve_formatting = config.get("preserve_formatting", False)
        self.extract_metadata_flag = config.get("extract_metadata", True)

    def validate_config(self) -> bool:
        return True

    def normalize(self, raw_document: RawDocument) -> Document:
        try:
            content = raw_document.content
            content_type = raw_document.content_type.lower().strip()

            # Only markdown/plain
            if content_type in ("text/markdown", "markdown"):
                text = self._normalize_markdown(content)
            else:
                # treat everything else as plain text
                text = self._normalize_plain(content)

            if not self.preserve_formatting:
                text = self._clean_whitespace(text)

            enriched_metadata = dict(raw_document.metadata or {})
            if self.extract_metadata_flag:
                enriched_metadata.update(self._infer_metadata_from_source(raw_document.source))
                enriched_metadata.update(self._try_extract_title_from_markdown(text))

            return Document(
                id=raw_document.id,
                source=raw_document.source,
                content=text,
                content_type=self._normalize_content_type_label(content_type),
                metadata=enriched_metadata,
                extracted_at=raw_document.extracted_at,
                normalized_at=datetime.utcnow(),
            )
        except Exception as e:
            raise TransformationError(
                f"Normalization failed: {e}",
                document_id=str(raw_document.id),
                transformation_stage="normalize",
            )

    def _normalize_plain(self, content: str) -> str:
        return content if self.preserve_formatting else content.strip()

    def _normalize_markdown(self, content: str) -> str:
        if not self.preserve_formatting:
            content = content.strip()
        return self._strip_yaml_front_matter(content)

    def _strip_yaml_front_matter(self, text: str) -> str:
        pattern = r"^---\s*\n.*?\n---\s*\n"
        return re.sub(pattern, "", text, flags=re.DOTALL) if not self.preserve_formatting else text

    def _clean_whitespace(self, text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = textwrap.dedent(text)
        return text.strip()

    def _infer_metadata_from_source(self, source: str) -> Dict:
        try:
            p = Path(source)
            return {
                "file_name": p.name,
                "file_stem": p.stem,
                "file_extension": p.suffix.lower(),
                "parent_dir": p.parent.name if p.parent else "",
            }
        except Exception:
            return {}

    def _try_extract_title_from_markdown(self, text: str) -> Dict:
        m = re.search(r"^\s*#\s+(?P<title>.+)$", text, flags=re.MULTILINE)
        return {"title": m.group("title").strip()} if m else {}

    def _normalize_content_type_label(self, content_type: str) -> str:
        if "markdown" in content_type:
            return "markdown"
        if "plain" in content_type:
            return "plain"
        return "plain"