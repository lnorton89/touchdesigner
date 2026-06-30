# Research: Stack

## Recommendation

Use a small Python-first stack inside a TouchDesigner `.tox`:

- TouchDesigner Base COMP components with Python extension classes for `ModelRouter`, `Agent`, `ToolRegistry`, and utility operators.
- External Python 3.11 virtual environment for dependencies, loaded into TD via startup path injection.
- `httpx` as the low-level async HTTP client.
- `pydantic` for tool schemas, structured outputs, and validation.
- LiteLLM as an optional routing abstraction after the direct local Ollama path works.
- Ollama/OpenAI-compatible `/v1` endpoints as the primary local-model path.

## Rationale

Derivative documents TouchDesigner as shipping a custom Python build and recommends matching the shipped Python version for external package installs. The docs also describe adding custom package paths through preferences, `PYTHONPATH`, or an `onStart()` Execute DAT that prepends a site-packages path to `sys.path`.

The project brief's venv approach fits that model. The stack should avoid installing into TD's own Python and should isolate dependency loading behind a bootstrap component so the `.tox` can report missing dependencies clearly.

LiteLLM is useful once the first loop works because it provides a unified OpenAI-like interface across many providers, including custom OpenAI-compatible endpoints and Ollama-specific routes. For phase 1, direct `httpx` calls to Ollama or `/v1/chat/completions` are lower risk and easier to debug inside TD.

## Version Notes

- TouchDesigner currently documents Python 3.11 as the shipped Python family to match for external package installs.
- Use the user's installed TD build as the source of truth for exact Python micro-version.
- Pin dependency versions in a generated `requirements.txt` once the first known-good set works in TD.

## Sources

- Derivative Python docs: https://docs.derivative.ca/Python
- LiteLLM OpenAI-compatible provider docs: https://docs.litellm.ai/docs/providers/openai_compatible
- LiteLLM Ollama provider docs: https://docs.litellm.ai/docs/providers/ollama
- Ollama OpenAI compatibility docs: https://docs.ollama.com/api/openai-compatibility
