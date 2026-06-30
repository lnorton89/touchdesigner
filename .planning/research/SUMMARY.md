# Research Summary

## Stack

TouchDesigner Base COMP `.tox` components with Python extension classes, an external Python 3.11-compatible virtual environment, `httpx` for async HTTP, `pydantic` for schema validation, and optional LiteLLM after the first direct Ollama/OpenAI-compatible path works.

## Table Stakes

- Reusable `.tox` operator family.
- Model Router with provider/base URL/model/API-key configuration.
- Agent with prompt/message inputs, history, response DAT output, and CHOP trigger/status output.
- Nonblocking request execution with TD-safe result delivery.
- Tool declaration/discovery convention.
- One working TD-native tool-call round trip.
- Local Ollama/OpenAI-compatible endpoint support.
- Dependency bootstrap/status flow for external venv loading.

## Watch Out For

- Never block TD's main thread with network calls.
- Keep worker threads away from TD object access.
- Load external dependencies carefully to avoid conflicting with TD's shipped packages.
- Treat invalid local-model tool calls as visible recoverable errors.
- Keep secrets outside saved `.toe`/`.tox` artifacts.

## Roadmap Implications

Phase 1 should prove the async Router against local Ollama before building a broad provider abstraction. Phase 2 should add Agent history and output conventions. Phase 3 should add tool discovery and one real TD tool. Phase 4 should package and harden the `.tox` plus dependency installer. Later phases can add structured output, RAG, and voice.
