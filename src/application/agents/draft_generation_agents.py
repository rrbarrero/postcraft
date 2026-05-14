"""Phase 2 agents for local draft generation."""

from src.domain.ports.llm import ILlmPort

MAX_PROMPT_CONTEXT_CHARS = 7_000
MAX_PREVIOUS_ARTIFACT_CHARS = 1_200


class ArchitectureNarratorAgent:
    """Generate candidate post angles from repository analysis."""

    def __init__(self, llm_port: ILlmPort) -> None:
        self.llm_port = llm_port

    def generate(
        self,
        project_facts: str,
        technical_analysis: str,
        requested_angle: str | None = None,
        language: str = "English",
    ) -> str:
        """Generate possible portfolio post angles."""
        prompt = f"""/no_think
You are planning a portfolio technical post. Answer in {language}.
Use only the provided evidence. Do not invent business impact or production maturity.

Requested angle, if any: {requested_angle or "none"}

Project facts:
{self._truncate(project_facts)}

Technical analysis:
{self._truncate(technical_analysis)}

Required format:
## Candidate Angles
### Angle 1: <specific angle>
- Thesis:
- Evidence:
- Portfolio value:
- Risks:

Generate 3 angles, then:
## Recommended Angle
- Name:
- Why this angle is strongest:
- Claims to avoid:
"""
        return self.llm_port.generate(self._truncate(prompt, MAX_PROMPT_CONTEXT_CHARS))

    def _truncate(
        self, value: str, max_chars: int = MAX_PREVIOUS_ARTIFACT_CHARS
    ) -> str:
        if len(value) <= max_chars:
            return value
        return f"{value[:max_chars]}\n[truncated]"


class PortfolioPositioningAgent:
    """Identify professional signals from technical evidence."""

    def __init__(self, llm_port: ILlmPort) -> None:
        self.llm_port = llm_port

    def generate(
        self,
        technical_analysis: str,
        post_angles: str,
        audience: str,
        language: str = "English",
    ) -> str:
        """Generate portfolio positioning guidance."""
        prompt = f"""/no_think
You are positioning a technical project for a portfolio post. Answer in {language}.
Audience: {audience}

Technical analysis:
{self._truncate(technical_analysis)}

Post angles:
{self._truncate(post_angles)}

Required format:
## Strong Signals
- Evidence-backed professional signal.

## Moderate Signals
- Useful but weaker signal.

## Claims To Avoid
- Claims that are not supported.

## Phrases That Fit
- Grounded wording for the post.

## Phrases To Avoid
- Overstated or CV-like wording.
"""
        return self.llm_port.generate(self._truncate(prompt, MAX_PROMPT_CONTEXT_CHARS))

    def _truncate(
        self, value: str, max_chars: int = MAX_PREVIOUS_ARTIFACT_CHARS
    ) -> str:
        if len(value) <= max_chars:
            return value
        return f"{value[:max_chars]}\n[truncated]"


class OutlineAgent:
    """Generate a post outline before drafting."""

    def __init__(self, llm_port: ILlmPort) -> None:
        self.llm_port = llm_port

    def generate(
        self,
        post_angles: str,
        portfolio_positioning: str,
        target_length: str,
        language: str = "English",
    ) -> str:
        """Generate a structured post outline."""
        prompt = f"""/no_think
Create a technical post outline in {language}. Target length: {target_length}.
The outline must tell a story: problem -> design -> decisions -> trade-offs -> learning.

Post angles:
{self._truncate(post_angles)}

Portfolio positioning:
{self._truncate(portfolio_positioning)}

Required format:
# Working Title

## Outline
1. Problem context
2. Project goal
3. General design
4. Technical decisions
5. Trade-offs
6. Testing, maintainability, or automation
7. What I learned
8. Next steps
9. Conclusion

For each section include:
- Purpose:
- Evidence to use:
"""
        return self.llm_port.generate(self._truncate(prompt, MAX_PROMPT_CONTEXT_CHARS))

    def _truncate(
        self, value: str, max_chars: int = MAX_PREVIOUS_ARTIFACT_CHARS
    ) -> str:
        if len(value) <= max_chars:
            return value
        return f"{value[:max_chars]}\n[truncated]"


class TechnicalWriterAgent:
    """Generate the first Markdown draft."""

    def __init__(self, llm_port: ILlmPort) -> None:
        self.llm_port = llm_port

    def generate(
        self,
        outline: str,
        technical_analysis: str,
        portfolio_positioning: str,
        language: str = "English",
    ) -> str:
        """Generate a first draft."""
        prompt = f"""/no_think
Write a portfolio technical post draft in {language}.
Use only supported claims. Mark uncertain claims as [pending verification].
Do not say production-ready. Do not overstate architecture.

Outline:
{self._truncate(outline)}

Technical analysis:
{self._truncate(technical_analysis)}

Portfolio positioning:
{self._truncate(portfolio_positioning)}

Return only the Markdown draft.
"""
        return self.llm_port.generate(self._truncate(prompt, MAX_PROMPT_CONTEXT_CHARS))

    def _truncate(
        self, value: str, max_chars: int = MAX_PREVIOUS_ARTIFACT_CHARS
    ) -> str:
        if len(value) <= max_chars:
            return value
        return f"{value[:max_chars]}\n[truncated]"


class TechnicalReviewerAgent:
    """Review draft claims against technical evidence."""

    def __init__(self, llm_port: ILlmPort) -> None:
        self.llm_port = llm_port

    def generate(
        self,
        draft: str,
        project_facts: str,
        technical_analysis: str,
        language: str = "English",
    ) -> str:
        """Generate a technical review."""
        prompt = f"""/no_think
Review the draft against the evidence. Answer in {language}.
Be strict. Flag generic or unsupported claims.

Draft:
{self._truncate(draft, 2_000)}

Project facts:
{self._truncate(project_facts)}

Technical analysis:
{self._truncate(technical_analysis)}

Required format:
## Supported Claims

## Weak Or Unsupported Claims

## Exaggerations

## Required Corrections

## Optional Improvements

## Verdict
Use PASS only if there are no critical unsupported claims. Otherwise use BLOCK.
"""
        return self.llm_port.generate(self._truncate(prompt, MAX_PROMPT_CONTEXT_CHARS))

    def _truncate(
        self, value: str, max_chars: int = MAX_PREVIOUS_ARTIFACT_CHARS
    ) -> str:
        if len(value) <= max_chars:
            return value
        return f"{value[:max_chars]}\n[truncated]"


class FinalEditorAgent:
    """Produce the final local draft from review feedback."""

    def __init__(self, llm_port: ILlmPort) -> None:
        self.llm_port = llm_port

    def generate(
        self,
        draft: str,
        technical_review: str,
        language: str = "English",
    ) -> str:
        """Generate the final Markdown post."""
        prompt = f"""/no_think
Edit the draft into a final local portfolio post in {language}.
Apply required corrections. Remove or soften unsupported claims.
Return only Markdown.

Draft:
{self._truncate(draft, 2_200)}

Technical review:
{self._truncate(technical_review)}
"""
        return self.llm_port.generate(self._truncate(prompt, MAX_PROMPT_CONTEXT_CHARS))

    def _truncate(
        self, value: str, max_chars: int = MAX_PREVIOUS_ARTIFACT_CHARS
    ) -> str:
        if len(value) <= max_chars:
            return value
        return f"{value[:max_chars]}\n[truncated]"
