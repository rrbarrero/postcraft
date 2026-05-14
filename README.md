# PostCraft

PostCraft is a local editorial pipeline for turning software repositories into
credible technical portfolio posts.

![alt text](image.png)

The project solves a common gap in engineering portfolios: real projects often
contain useful design decisions, trade-offs, tests, automation, and learning, but
that evidence usually stays buried in the repository. PostCraft is meant to
read a local codebase, understand what it actually contains, and transform that
evidence into a technical article that explains the problem, the design, the
engineering judgement, and the professional value of the work.

The system is designed around evidence before narrative. It first scans the
repository, identifies the stack, entrypoints, documentation, tests,
configuration, automation, and relevant source files, and selects a small set of
files that can support a grounded analysis. From there, a multi-agent workflow
builds a factual inventory, interprets the architecture and main flows, proposes
portfolio-oriented angles, extracts professional signals, drafts the post,
reviews technical claims, improves the tone, prepares metadata, and finally
creates a blog draft.

The goal is not to generate generic marketing copy or inflate a project beyond
what the code supports. The goal is to produce articles that show engineering
judgement: why a project exists, what constraints shaped it, which technical
decisions mattered, what trade-offs were accepted, how maintainability and
testing were approached, what was learned, and what could reasonably come next.

PostCraft should keep the process auditable. Each run should produce a local
workspace with the files and intermediate artifacts used to create the post:
inventory, selected evidence, project facts, technical analysis, candidate
angles, portfolio positioning, outline, draft, technical review, final article,
metadata, warnings, and publication result. This makes it possible to review how
the post was generated and to correct unsupported claims before anything reaches
the blog.

Publishing is part of the complete workflow, but it must remain controlled. The
system should create drafts through the blog MCP and mark them as drafts by
default. Final publication stays a manual editorial decision, with the generated
post traceable back to repository evidence and review artifacts.
