<!-- GSD:project-start source:PROJECT.md -->

## Project

**Native LLM Operators for TouchDesigner**

This project builds a custom TouchDesigner operator family that lets TD networks call local or cloud LLMs natively from inside the node graph. The toolkit should feel like a first-class TD component set: drop in a `.tox`, configure a model endpoint, send messages from DATs/CHOPs, and receive structured DAT/CHOP/TOP-friendly output that downstream operators can react to in real time.

The project occupies the same broad problem space as dotsimulate's Language Operators, but it is designed from scratch with its own architecture, names, dependency strategy, and implementation choices.

**Core Value:** TouchDesigner projects can talk to LLMs asynchronously through reusable native-looking operators without freezing the network or requiring an external app/server wrapper.

### Constraints

- **Runtime**: TouchDesigner embedded Python is limited and version-pinned - do not depend on pip installing into TD itself.
- **Performance**: Network calls must not block the main TD thread - frame stalls are project-breaking.
- **Packaging**: Deliverable must be a reusable `.tox` component - the operator family should travel between TD projects.
- **Platform**: Target Windows first - most target users are Windows/NVIDIA TD users.
- **Portability**: Avoid hard-coded Windows-only paths where reasonable - macOS support remains a stretch goal.
- **Security**: API keys should be stored locally and not embedded into saved `.toe` project files.
- **Local-first**: Ollama or another local OpenAI-compatible endpoint must work without cloud dependency.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->

## Technology Stack

## Recommendation

- TouchDesigner Base COMP components with Python extension classes for `ModelRouter`, `Agent`, `ToolRegistry`, and utility operators.
- External Python 3.11 virtual environment for dependencies, loaded into TD via startup path injection.
- `httpx` as the low-level async HTTP client.
- `pydantic` for tool schemas, structured outputs, and validation.
- LiteLLM as an optional routing abstraction after the direct local Ollama path works.
- Ollama/OpenAI-compatible `/v1` endpoints as the primary local-model path.

## Rationale

## Version Notes

- TouchDesigner currently documents Python 3.11 as the shipped Python family to match for external package installs.
- Use the user's installed TD build as the source of truth for exact Python micro-version.
- Pin dependency versions in a generated `requirements.txt` once the first known-good set works in TD.

## Sources

- Derivative Python docs: https://docs.derivative.ca/Python
- LiteLLM OpenAI-compatible provider docs: https://docs.litellm.ai/docs/providers/openai_compatible
- LiteLLM Ollama provider docs: https://docs.litellm.ai/docs/providers/ollama
- Ollama OpenAI compatibility docs: https://docs.ollama.com/api/openai-compatibility

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
