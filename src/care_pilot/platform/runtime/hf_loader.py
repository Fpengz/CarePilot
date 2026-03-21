"""
Unified HuggingFace model loading with local-first caching.
"""

from __future__ import annotations

import os
from typing import Any, Protocol, cast

from transformers import pipeline

from care_pilot.platform.observability import get_logger

logger = get_logger(__name__)


class LoadFunc(Protocol):
    def __call__(self, repo_id: str, *args: Any, **kwargs: Any) -> Any: ...


def get_hf_loader(
    repo_id: str,
    *,
    load_func: LoadFunc | None = None,
    task: str | None = None,
    cache_dir: str | None = None,
    **kwargs: Any,
) -> Any:
    """
    Attempt to load a HuggingFace model/pipeline locally first.
    If local loading fails, download from HF and cache it.
    """
    if cache_dir:
        # Ensure HF uses the specified cache directory
        os.environ.setdefault("HF_HOME", cache_dir)
        os.environ.setdefault("TRANSFORMERS_CACHE", cache_dir)

    # 1. Try local-only first
    try:
        if load_func:
            return load_func(repo_id, local_files_only=True, cache_dir=cache_dir, **kwargs)
        if task:
            return cast(Any, pipeline)(
                task=task,
                model=repo_id,
                local_files_only=True,
                model_kwargs={"cache_dir": cache_dir} if cache_dir else {},
                **kwargs,
            )
    except Exception:
        logger.info("hf_local_load_miss repo_id=%s task=%s", repo_id, task)

    # 2. Fallback to download
    logger.info("hf_remote_load_start repo_id=%s task=%s", repo_id, task)
    if load_func:
        return load_func(repo_id, local_files_only=False, cache_dir=cache_dir, **kwargs)
    if task:
        return cast(Any, pipeline)(
            task=task,
            model=repo_id,
            local_files_only=False,
            model_kwargs={"cache_dir": cache_dir} if cache_dir else {},
            **kwargs,
        )

    raise ValueError("Either load_func or task must be provided")
