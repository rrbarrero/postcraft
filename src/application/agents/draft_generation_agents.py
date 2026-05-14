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
    """Generate and repair Markdown drafts."""

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
Write a standalone portfolio technical post in {language}.

Use the outline as a private writing plan, not as content to paste.
Return an article that a reader could publish as a draft blog post.

Hard rules:
- Return only the Markdown article.
- Start with one H1 title.
- Use prose sections with paragraphs, not an outline dump.
- Do not include sections named "Outline", "Technical Analysis",
  "Portfolio Positioning", "Supported Claims", "Weak Or Unsupported Claims",
  "Claims To Avoid", or "Required Corrections".
- Do not copy bullet lists from the outline unless they become natural prose.
- Use only supported claims.
- Mark uncertain claims as [pending verification].
- Do not say production-ready, scalable, full-featured, must-have, or seamless.
- Do not overstate architecture.

Outline:
{self._truncate(outline)}

Technical analysis:
{self._truncate(technical_analysis)}

Portfolio positioning:
{self._truncate(portfolio_positioning)}

Return only the Markdown draft article.
"""
        return self.llm_port.generate(self._truncate(prompt, MAX_PROMPT_CONTEXT_CHARS))

    def repair(
        self,
        draft: str,
        issues: list[str],
        outline: str,
        technical_analysis: str,
        portfolio_positioning: str,
        language: str = "English",
    ) -> str:
        """Rewrite a malformed draft into a standalone article."""
        issue_list = "\n".join(f"- {issue}" for issue in issues)
        prompt = f"""/no_think
Rewrite the malformed draft into a standalone portfolio technical post in {language}.

The current draft failed these deterministic artifact checks:
{issue_list}

Hard rules:
- Return only the Markdown article.
- Start with one H1 title.
- Write prose paragraphs under article sections.
- Do not include "## Outline", "Technical Analysis", "Portfolio Positioning",
  "Claims To Avoid", "Supported Claims", "Weak Or Unsupported Claims", or
  "Required Corrections".
- Do not include the outline itself.
- Do not include review language or meta-commentary about the pipeline.
- Do not use generic marketing words such as scalable, production-ready,
  full-featured, must-have, seamless, or seamlessly.
- Preserve only claims grounded in the evidence.

Malformed draft:
{self._truncate(draft, 2_200)}

Original outline to use only as a plan:
{self._truncate(outline)}

Technical analysis:
{self._truncate(technical_analysis)}

Portfolio positioning:
{self._truncate(portfolio_positioning)}

Return only the Markdown article.
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
Reference specific file paths for supported or unsupported technical claims
whenever the evidence contains file paths.

Draft:
{self._truncate(draft, 2_000)}

Project facts:
{self._truncate(project_facts)}

Technical analysis:
{self._truncate(technical_analysis)}

Required format:
## Supported Claims
- Claim, with file-path evidence when available.

## Weak Or Unsupported Claims
- Claim, with missing or weak file-path evidence when relevant.

## Exaggerations
- Exaggerated claim and why the evidence does not support it.

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
