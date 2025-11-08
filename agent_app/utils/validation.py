"""Document validation utilities."""

import jsonschema
from typing import Dict, Any, Tuple, List
import yaml
import re


def extract_yaml_frontmatter(markdown_content: str) -> Dict[str, Any]:
    """
    Extract YAML frontmatter from markdown document.
    
    Args:
        markdown_content: Markdown document with YAML frontmatter
        
    Returns:
        Dictionary of frontmatter values
    """
    pattern = r'^---\s*\n(.*?)\n---\s*\n'
    match = re.match(pattern, markdown_content, re.DOTALL)
    if match:
        try:
            return yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            return {}
    return {}


def validate_document_schema(document: str, schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate document against JSON Schema.
    
    Args:
        document: Markdown document with YAML frontmatter
        schema: JSON Schema definition
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    try:
        frontmatter = extract_yaml_frontmatter(document)
        jsonschema.validate(instance=frontmatter, schema=schema)
        return True, []
    except jsonschema.ValidationError as e:
        return False, [str(e)]
    except Exception as e:
        return False, [f"Validation error: {str(e)}"]

