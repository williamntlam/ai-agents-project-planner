"""Reviewer Agent - Quality assurance and validation."""

from typing import Dict, Any, List, Tuple, Optional
import json
import os
from pathlib import Path
from agent_app.agents.base import BaseAgent
from agent_app.schemas.document_state import DocumentState
from agent_app.schemas.agent_output import AgentOutput
from agent_app.schemas.review_feedback import ReviewFeedback, ReviewIssue, ReviewSeverity
from agent_app.utils.validation import validate_document_schema, extract_yaml_frontmatter
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


class ReviewerAgent(BaseAgent):
    """Agent responsible for quality assurance and validation.
    
    This agent reviews the generated HLD and LLD, validates against JSON Schema,
    and provides structured feedback. It sets the needs_revision flag which
    controls workflow routing.
    """
    
    def __init__(self, config: Dict[str, Any], tools: Dict[str, Any] = None):
        super().__init__(config, tools)
        self.schema = self._load_validation_schema()
        self.rubric = self._load_rubric()
        self.min_score_threshold = self.get_config_value('min_score_threshold', 0.7)
        self.llm = self._initialize_llm()
    
    def _load_validation_schema(self) -> Dict[str, Any]:
        """
        Load JSON Schema for document validation.
        
        Returns:
            JSON Schema dictionary, or empty dict if not found
        """
        schema_path = self.get_config_value('validation_schema_path')
        if not schema_path:
            self.logger.warning("No validation_schema_path in config, using empty schema")
            return {}
        
        # Resolve path relative to project root or config directory
        if not os.path.isabs(schema_path):
            # Try relative to agent_app directory
            base_path = Path(__file__).parent.parent
            schema_path = base_path / schema_path
        
        schema_path = Path(schema_path)
        
        if not schema_path.exists():
            self.logger.warning(
                f"Validation schema file not found: {schema_path}",
                schema_path=str(schema_path)
            )
            return {}
        
        try:
            with open(schema_path, 'r') as f:
                schema = json.load(f)
            self.logger.info("Loaded validation schema", schema_path=str(schema_path))
            return schema
        except Exception as e:
            self.logger.error(
                "Failed to load validation schema",
                schema_path=str(schema_path),
                error=str(e)
            )
            return {}
    
    def _load_rubric(self) -> Dict[str, Any]:
        """
        Load review rubric from config or file.
        
        Returns:
            Rubric dictionary
        """
        # Try to get rubric from config directly
        rubric = self.get_config_value('rubric', {})
        
        # If not in config, try loading from file
        if not rubric:
            rubric_path = self.get_config_value('rubric_path')
            if rubric_path:
                if not os.path.isabs(rubric_path):
                    base_path = Path(__file__).parent.parent
                    rubric_path = base_path / rubric_path
                
                rubric_path = Path(rubric_path)
                if rubric_path.exists():
                    try:
                        import yaml
                        with open(rubric_path, 'r') as f:
                            rubric = yaml.safe_load(f) or {}
                        self.logger.info("Loaded rubric from file", rubric_path=str(rubric_path))
                    except Exception as e:
                        self.logger.warning(
                            "Failed to load rubric file",
                            rubric_path=str(rubric_path),
                            error=str(e)
                        )
        
        # Default rubric if none provided
        if not rubric:
            rubric = {
                "completeness": {
                    "weight": 0.3,
                    "criteria": [
                        "All required sections present",
                        "Sufficient detail in each section",
                        "Clear explanations"
                    ]
                },
                "quality": {
                    "weight": 0.3,
                    "criteria": [
                        "Follows architectural best practices",
                        "Appropriate technology choices",
                        "Well-structured design"
                    ]
                },
                "standards_compliance": {
                    "weight": 0.2,
                    "criteria": [
                        "Adheres to coding standards",
                        "Follows security best practices",
                        "Meets performance requirements"
                    ]
                },
                "clarity": {
                    "weight": 0.2,
                    "criteria": [
                        "Clear and readable",
                        "Well-documented",
                        "Easy to understand"
                    ]
                }
            }
            self.logger.info("Using default rubric")
        
        return rubric
    
    def _initialize_llm(self):
        """
        Initialize LLM client for quality review.
        
        Returns:
            ChatOpenAI instance configured from config
        """
        model = self.get_config_value('model', 'gpt-4o-mini')
        temperature = self.get_config_value('temperature', 0.3)  # Lower for consistent reviews
        max_tokens = self.get_config_value('max_tokens', 2000)
        
        # Get API key from config or environment
        api_key = self.get_config_value('api_key')
        
        self.logger.debug(
            "Initializing LLM for review",
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key
        )
    
    def _combine_documents(self, state: DocumentState) -> str:
        """
        Combine HLD and LLD into a single document for review.
        
        Args:
            state: Document state with hld_draft and lld_draft
            
        Returns:
            Combined document string
        """
        parts = []
        
        if state.hld_draft:
            parts.append("# High-Level Design\n\n")
            parts.append(state.hld_draft)
            parts.append("\n\n")
        
        if state.lld_draft:
            parts.append("# Low-Level Design\n\n")
            parts.append(state.lld_draft)
        
        return "\n".join(parts)
    
    def perform_action(self, state: DocumentState) -> AgentOutput:
        """
        Review document and generate structured feedback.
        
        Steps:
        1. Validate against JSON Schema
        2. Review content quality using rubric
        3. Generate structured feedback
        4. Set needs_revision flag
        
        Args:
            state: Document state with hld_draft and lld_draft
            
        Returns:
            AgentOutput with ReviewFeedback JSON
        """
        # Combine HLD and LLD for review
        combined_doc = self._combine_documents(state)
        
        # 1. Schema validation
        self.logger.info("Validating document against schema", agent=self.name)
        is_valid = True
        validation_errors = []
        
        if self.schema:
            is_valid, validation_errors = validate_document_schema(
                combined_doc,
                self.schema
            )
            self.logger.info(
                "Schema validation completed",
                passes=is_valid,
                error_count=len(validation_errors)
            )
        else:
            self.logger.warning("No validation schema loaded, skipping schema validation")
        
        # 2. Quality review using LLM + rubric
        self.logger.info("Reviewing document quality", agent=self.name)
        quality_feedback = self._review_quality(combined_doc)
        
        # 3. Build structured review feedback
        issues = self._build_issues(validation_errors, quality_feedback)
        
        # Calculate overall score
        overall_score = quality_feedback.get('score', 0.5)
        if not is_valid:
            # Penalize score if validation fails
            overall_score = min(overall_score, 0.5)
        
        # Determine if revision is needed
        needs_revision = (
            not is_valid or
            overall_score < self.min_score_threshold or
            any(issue.severity in (ReviewSeverity.CRITICAL, ReviewSeverity.HIGH) for issue in issues)
        )
        
        review_feedback = ReviewFeedback(
            overall_score=overall_score,
            passes_validation=is_valid,
            issues=issues,
            strengths=quality_feedback.get('strengths', []),
            needs_revision=needs_revision
        )
        
        self.logger.info(
            "Review completed",
            agent=self.name,
            overall_score=overall_score,
            passes_validation=is_valid,
            issues_count=len(issues),
            needs_revision=needs_revision
        )
        
        return AgentOutput(
            content=review_feedback.model_dump_json(),
            reasoning=f"Validated schema (pass: {is_valid}), reviewed quality (score: {overall_score:.2f}), found {len(issues)} issues",
            confidence=0.9 if is_valid and overall_score >= 0.8 else 0.7,
            metadata={
                "needs_revision": review_feedback.needs_revision,
                "validation_passed": is_valid,
                "overall_score": overall_score,
                "issues_count": len(issues),
                "critical_issues": review_feedback.has_critical_issues()
            }
        )
    
    def _review_quality(self, document: str) -> Dict[str, Any]:
        """
        Review document quality using LLM and rubric.
        
        Args:
            document: Combined document to review
            
        Returns:
            Dictionary with score, strengths, issues
        """
        try:
            prompt = f"""Review this System Design Document against the following rubric:

Rubric:
{json.dumps(self.rubric, indent=2)}

Document:
{document[:8000]}  # Limit document length to avoid token limits

Provide a comprehensive review in JSON format with the following structure:
{{
    "score": <float between 0.0 and 1.0>,
    "strengths": ["strength1", "strength2", ...],
    "issues": [
        {{
            "category": "<category>",
            "severity": "<CRITICAL|HIGH|MEDIUM|LOW|INFO>",
            "description": "<detailed description>",
            "suggestion": "<suggested fix>",
            "location": "<section or location>"
        }},
        ...
    ]
}}

Evaluate based on:
1. Completeness: Are all required sections present and detailed?
2. Quality: Does it follow best practices and architectural patterns?
3. Standards Compliance: Does it adhere to coding/security/performance standards?
4. Clarity: Is it clear, readable, and well-documented?

Be thorough but fair. Identify both strengths and areas for improvement.
Return ONLY valid JSON, no additional text.
"""
            
            messages = [
                SystemMessage(content="""You are an expert technical reviewer specializing in system design documents. 
You provide thorough, constructive feedback that helps improve document quality while acknowledging strengths.
You are objective, specific, and actionable in your reviews."""),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            response_text = response.content.strip()
            
            # Try to extract JSON from response (handle markdown code blocks)
            if response_text.startswith("```"):
                # Extract JSON from code block
                lines = response_text.split("\n")
                json_lines = []
                in_code_block = False
                for line in lines:
                    if line.strip().startswith("```"):
                        in_code_block = not in_code_block
                        continue
                    if in_code_block:
                        json_lines.append(line)
                response_text = "\n".join(json_lines)
            
            # Parse JSON response
            quality_feedback = json.loads(response_text)
            
            # Validate and normalize
            score = float(quality_feedback.get('score', 0.5))
            score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
            
            return {
                'score': score,
                'strengths': quality_feedback.get('strengths', []),
                'issues': quality_feedback.get('issues', [])
            }
            
        except json.JSONDecodeError as e:
            self.logger.error(
                "Failed to parse LLM review response as JSON",
                error=str(e),
                response_preview=response.content[:200] if 'response' in locals() else "No response"
            )
            # Return default feedback on parse error
            return {
                'score': 0.5,
                'strengths': [],
                'issues': [{
                    'category': 'review',
                    'severity': 'MEDIUM',
                    'description': 'Failed to parse review response',
                    'suggestion': 'Review process encountered an error'
                }]
            }
        except Exception as e:
            self.logger.error(
                "Quality review failed",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            return {
                'score': 0.5,
                'strengths': [],
                'issues': []
            }
    
    def _build_issues(self, validation_errors: List[str], quality_feedback: Dict[str, Any]) -> List[ReviewIssue]:
        """
        Build list of ReviewIssue objects from validation errors and quality feedback.
        
        Args:
            validation_errors: List of validation error messages
            quality_feedback: Quality review feedback dictionary
            
        Returns:
            List of ReviewIssue objects
        """
        issues = []
        
        # Add validation errors as CRITICAL issues
        for error in validation_errors:
            issues.append(ReviewIssue(
                category="validation",
                severity=ReviewSeverity.CRITICAL,
                description=f"Schema validation error: {error}",
                suggestion="Fix the document structure to match the required schema",
                location="Document structure"
            ))
        
        # Add quality issues from LLM review
        for issue_dict in quality_feedback.get('issues', []):
            try:
                severity_str = issue_dict.get('severity', 'MEDIUM').upper()
                # Map string to ReviewSeverity enum
                try:
                    severity = ReviewSeverity(severity_str)
                except ValueError:
                    # Default to MEDIUM if invalid severity
                    severity = ReviewSeverity.MEDIUM
                
                issues.append(ReviewIssue(
                    category=issue_dict.get('category', 'quality'),
                    severity=severity,
                    description=issue_dict.get('description', ''),
                    suggestion=issue_dict.get('suggestion'),
                    location=issue_dict.get('location')
                ))
            except Exception as e:
                self.logger.warning(
                    "Failed to create ReviewIssue from quality feedback",
                    issue_dict=issue_dict,
                    error=str(e)
                )
                # Create a generic issue if parsing fails
                issues.append(ReviewIssue(
                    category="quality",
                    severity=ReviewSeverity.MEDIUM,
                    description=str(issue_dict.get('description', 'Quality issue identified')),
                    suggestion=issue_dict.get('suggestion', 'Review and improve this aspect')
                ))
        
        return issues
    
    def validate_state(self, state: DocumentState) -> Tuple[bool, List[str]]:
        """
        Validate state for ReviewerAgent.
        
        Requires:
        - project_brief (always required)
        - hld_draft (required)
        - lld_draft (required)
        """
        is_valid, errors = super().validate_state(state)
        
        # ReviewerAgent requires both drafts
        if not state.hld_draft or len(state.hld_draft.strip()) < 100:
            errors.append("hld_draft is required and must be at least 100 characters")
            is_valid = False
        
        if not state.lld_draft or len(state.lld_draft.strip()) < 100:
            errors.append("lld_draft is required and must be at least 100 characters")
            is_valid = False
        
        return is_valid, errors

