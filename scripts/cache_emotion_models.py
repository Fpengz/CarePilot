"""Pre-download emotion model artifacts into the local HF cache."""

from __future__ import annotations

import argparse
import os

from huggingface_hub import snapshot_download

from dietary_guardian.config.app import get_settings


def _configure_cache_dir(cache_dir: str | None) -> str | None:
    if not cache_dir:
        return None
    os.environ.setdefault("HF_HOME", cache_dir)
    os.environ.setdefault("TRANSFORMERS_CACHE", cache_dir)
    return cache_dir


def _download(repo_id: str, cache_dir: str | None) -> None:
    if cache_dir:
        os.environ.setdefault("HF_HOME", cache_dir)
        os.environ.setdefault("TRANSFORMERS_CACHE", cache_dir)
    snapshot_download(repo_id=repo_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Cache HF emotion models locally.")
    parser.add_argument(
        "--cache-dir",
        dest="cache_dir",
        default=None,
        help="Override the HF cache directory (sets HF_HOME/TRANSFORMERS_CACHE).",
    )
    args = parser.parse_args()

    settings = get_settings()
    cache_dir = _configure_cache_dir(args.cache_dir or getattr(settings.emotion, "model_cache_dir", None))

    model_ids = [
        settings.emotion.text_model_id,
        settings.emotion.speech_model_id,
        settings.emotion.asr_model_id,
    ]
    if settings.emotion.fusion_model_id:
        model_ids.append(settings.emotion.fusion_model_id)

    for model_id in model_ids:
        _download(model_id, cache_dir)


if __name__ == "__main__":
    main()
