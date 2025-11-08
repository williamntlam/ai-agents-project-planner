"""Review feedback schema for ReviewerAgent.

WHY THIS SCHEMA EXISTS:
=======================
The ReviewFeedback schema enables STRUCTURED QUALITY ASSURANCE in the agent workflow:

1. **Automated Quality Control**: The ReviewerAgent uses this schema to provide
   machine-readable feedback that the workflow can act upon. The `needs_revision` flag
   directly controls workflow routing (conditional edges in LangGraph).

2. **Structured Feedback**: Instead of free-form text, this schema enforces a consistent
   format that can be:
   - Parsed programmatically
   - Used to update DocumentState
   - Displayed in UI dashboards
   - Stored in databases for analytics

3. **Prioritization**: The severity levels (CRITICAL, HIGH, MEDIUM, LOW, INFO) allow
   agents to prioritize fixes. Critical issues must be addressed before proceeding.

4. **Actionable Feedback**: Each ReviewIssue includes both a problem description AND
   a suggestion, making it easier for revision agents to fix issues.

5. **Validation Integration**: The `passes_validation` field separates structural
   validation (JSON Schema) from quality review (LLM-based), providing two layers of QA.

6. **Revision Control**: The `needs_revision` flag is the primary mechanism for
   triggering the revision loop in the workflow. Without this structured feedback,
   the workflow couldn't make automated decisions about when to revise.

7. **Transparency**: By storing both issues AND strengths, the feedback provides
   balanced, constructive criticism that helps improve the document while acknowledging
   what's working well.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from enum import Enum


class ReviewSeverity(str, Enum):
    """Review issue severity levels.
    
    Severity determines:
    - Priority for fixes (CRITICAL must be fixed first)
    - Whether revision is required (CRITICAL/HIGH usually trigger revision)
    - Display in UI (color coding, sorting)
    
    Hierarchy:
    - CRITICAL: Breaks functionality, violates core requirements
    - HIGH: Significant quality issues, may cause problems
    - MEDIUM: Moderate issues, should be addressed
    - LOW: Minor issues, nice to have fixes
    - INFO: Suggestions, not necessarily problems
    """
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class ReviewIssue(BaseModel):
    """Individual review issue/feedback item.
    
    Represents a single problem or suggestion identified during review.
    Multiple ReviewIssues are collected into a ReviewFeedback object.
    
    Example:
        ReviewIssue(
            category="security",
            severity=ReviewSeverity.CRITICAL,
            description="API endpoints lack authentication",
            suggestion="Add OAuth2 authentication to all endpoints",
            location="Section 3.2: API Endpoints"
        )
    """
    
    category: str = Field(
        ...,
        description="Issue category (e.g., 'architecture', 'security', 'performance', 'documentation')",
        min_length=1
    )
    """Groups related issues together.
    
    Common categories:
    - architecture: Design patterns, component structure
    - security: Authentication, authorization, data protection
    - performance: Scalability, latency, throughput
    - data_modeling: Database design, schema issues
    - api_design: REST/GraphQL endpoint design
    - documentation: Clarity, completeness, formatting
    - standards_compliance: Adherence to internal standards
    """
    
    severity: ReviewSeverity = Field(
        ...,
        description="Issue severity level"
    )
    """How critical this issue is.
    
    Used by workflow to decide:
    - CRITICAL/HIGH → Must fix, triggers revision
    - MEDIUM → Should fix, may trigger revision if multiple
    - LOW/INFO → Optional fixes, don't block progression
    """
    
    description: str = Field(
        ...,
        description="Detailed description of the issue",
        min_length=10
    )
    """Clear explanation of what's wrong.
    
    Should be specific enough that an agent can understand and fix it.
    Example: "The microservices architecture lacks a service mesh, which
    is required for inter-service communication in our standards."
    """
    
    suggestion: Optional[str] = Field(
        None,
        description="Suggested fix or improvement"
    )
    """Actionable recommendation for fixing the issue.
    
    Makes it easier for revision agents to address the problem.
    Example: "Add Istio service mesh configuration with mTLS enabled
    for all inter-service communication."
    """
    
    location: Optional[str] = Field(
        None,
        description="Where in document (section, line number, etc.)"
    )
    """Helps locate the issue in the document.
    
    Format can vary:
    - "Section 2.3: Architecture Overview"
    - "Line 45-52"
    - "API Endpoints > POST /orders"
    
    Makes it easier for humans or agents to find and fix issues.
    """
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Normalize category to lowercase for consistency."""
        return v.lower().strip()


class ReviewFeedback(BaseModel):
    """Structured review feedback from ReviewerAgent.
    
    This is the complete review result, containing:
    - Overall quality assessment (score)
    - Validation status (pass/fail)
    - List of specific issues
    - List of strengths
    - Revision decision
    
    This object is serialized to JSON and stored in DocumentState.review_feedback,
    then used by conditional edges to decide workflow routing.
    
    Example:
        ReviewFeedback(
            overall_score=0.75,
            passes_validation=True,
            issues=[...],
            strengths=["Well-structured architecture", "Clear API design"],
            needs_revision=True  # Has issues but not critical
        )
    """
    
    overall_score: float = Field(
        ...,
        description="Overall quality score (0.0 to 1.0)",
        ge=0.0,
        le=1.0
    )
    """Synthetic quality metric combining all review factors.
    
    Calculation typically considers:
    - Number and severity of issues
    - Validation pass/fail
    - Completeness of document
    - Adherence to standards
    
    Used for:
    - Threshold-based decisions (e.g., score < 0.7 → revision)
    - Progress tracking
    - Quality metrics/analytics
    """
    
    passes_validation: bool = Field(
        ...,
        description="Whether document passes JSON Schema validation"
    )
    """Structural validation result.
    
    Separate from quality review - this is a hard pass/fail based on:
    - Required fields present in YAML frontmatter
    - Correct data types
    - Valid enum values
    - Required sections present
    
    If False, document MUST be revised (structural issues).
    If True, document structure is valid (but may have quality issues).
    """
    
    issues: List[ReviewIssue] = Field(
        default_factory=list,
        description="List of identified issues"
    )
    """All problems found during review.
    
    Empty list means no issues found (perfect document).
    Issues are typically sorted by severity (CRITICAL first).
    
    Used by:
    - Revision agents to know what to fix
    - Workflow to determine if revision needed
    - UI to display problems to users
    """
    
    strengths: List[str] = Field(
        default_factory=list,
        description="List of document strengths/positive aspects"
    )
    """What the document does well.
    
    Important for:
    - Balanced feedback (not just criticism)
    - Preserving good parts during revision
    - Building confidence in the system
    - Learning what works well
    
    Example: ["Clear component boundaries", "Well-documented API contracts"]
    """
    
    needs_revision: bool = Field(
        ...,
        description="Whether revision is required based on this review"
    )
    """PRIMARY WORKFLOW CONTROL FLAG.
    
    This is the key decision point for LangGraph conditional edges:
    - True → Route to revision loop (back to draft_hld)
    - False → Proceed to formatting stage
    
    Typically set to True if:
    - passes_validation == False (structural issues)
    - overall_score < threshold (quality too low)
    - Has CRITICAL or HIGH severity issues
    - Multiple MEDIUM issues
    
    Set to False if:
    - passes_validation == True AND
    - overall_score >= threshold AND
    - Only LOW/INFO issues (or no issues)
    """
    
    @field_validator('overall_score')
    @classmethod
    def validate_score(cls, v: float) -> float:
        """Ensure score is in valid range."""
        if not (0.0 <= v <= 1.0):
            raise ValueError("Overall score must be between 0.0 and 1.0")
        return v
    
    def has_critical_issues(self) -> bool:
        """Check if there are any CRITICAL severity issues."""
        return any(issue.severity == ReviewSeverity.CRITICAL for issue in self.issues)
    
    def has_high_severity_issues(self) -> bool:
        """Check if there are CRITICAL or HIGH severity issues."""
        return any(
            issue.severity in (ReviewSeverity.CRITICAL, ReviewSeverity.HIGH)
            for issue in self.issues
        )
    
    def get_issues_by_severity(self, severity: ReviewSeverity) -> List[ReviewIssue]:
        """Get all issues of a specific severity level."""
        return [issue for issue in self.issues if issue.severity == severity]
    
    def get_issues_by_category(self, category: str) -> List[ReviewIssue]:
        """Get all issues in a specific category."""
        return [issue for issue in self.issues if issue.category.lower() == category.lower()]
    
    def should_trigger_revision(self, score_threshold: float = 0.7) -> bool:
        """Determine if this feedback should trigger revision.
        
        Revision is triggered if:
        - Validation fails (structural issues)
        - Score below threshold (quality too low)
        - Has critical/high severity issues
        
        This is a helper method - the needs_revision field is the source of truth.
        """
        if not self.passes_validation:
            return True
        if self.overall_score < score_threshold:
            return True
        if self.has_high_severity_issues():
            return True
        return False
    
    class Config:
        """Pydantic configuration."""
        # Enable JSON serialization for storage in DocumentState
        json_encoders = {
            # Custom encoders if needed
        }

