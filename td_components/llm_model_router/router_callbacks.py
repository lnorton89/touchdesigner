"""TouchDesigner callback helpers for the Model Router component."""

from __future__ import annotations

from typing import Any


def _router_from_owner(owner: Any) -> Any:
    ext = getattr(owner, "ext", None)
    router = getattr(ext, "ModelRouter", None) if ext is not None else None
    if router is None and hasattr(owner, "ModelRouter"):
        router = owner.ModelRouter
    if router is None:
        raise RuntimeError("ModelRouter extension was not found on the owner component")
    return router


def onTriggerPulse(par: Any) -> int:
    router = _router_from_owner(par.owner)
    return router.request(trigger_source="pulse")


def onResetPulse(par: Any) -> Any:
    router = _router_from_owner(par.owner)
    return router.reset()


def onRetryPulse(par: Any) -> int:
    router = _router_from_owner(par.owner)
    return router.retry()


def onPromptTableChange(dat: Any, cells: Any = None, prev: Any = None) -> int:
    router = _router_from_owner(dat.owner)
    prompt = getattr(dat, "text", None)
    if prompt is None:
        prompt = str(dat)
    return router.request(prompt=str(prompt), trigger_source="dat_table_change")
