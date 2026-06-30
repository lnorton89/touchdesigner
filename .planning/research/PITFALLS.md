# Research: Pitfalls

## Main-Thread Blocking

TouchDesigner networks are realtime systems. A synchronous HTTP request in `onCook` or another hot execution path can stall frames. Treat nonblocking request execution as the first milestone, not an optimization.

## Worker Access to TD Objects

Derivative's Python docs warn that Python threads do not have access to TouchDesigner objects. Keep TD object reads/writes on the TD side, and keep worker threads limited to network calls and pure Python data shaping.

## Dependency Conflicts

Derivative warns that changing `sys.path` can load different versions of dependencies than TD expects, especially packages TD or palette components rely on. Keep the dependency set small, prepend only the toolkit venv path when needed, and surface version conflicts.

## Local Tool Calling Variance

Ollama supports tool calling, but not every local model reliably emits valid tool-call structures. Agent parsing must fail gracefully with a visible error DAT/CHOP state rather than crashing or silently ignoring the issue.

## Secrets in Saved Projects

API keys should not be stored directly in saved `.toe`/`.tox` files. Use local env vars, a local settings file outside the project, OS credential storage later, or explicit "not saved" custom parameter handling.

## Scope Creep

RAG, voice, streaming TOP visualizers, and broad provider support are tempting but should wait until the async local Agent plus one TD-native tool round trip works.

## Sources

- Derivative Python docs: https://docs.derivative.ca/Python
- Ollama tool-calling docs: https://docs.ollama.com/capabilities/tool-calling
- Derivative Virtual File System docs: https://docs.derivative.ca/Virtual_File_System
