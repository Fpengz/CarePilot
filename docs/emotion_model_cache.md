# Emotion Model Cache

This app uses Hugging Face models for emotion inference (text, speech, and ASR).
You can pre-download these models to a local cache to reduce startup latency and
avoid repeated network calls.

## Quick start

1. Set a cache directory (optional):

```bash
export EMOTION_MODEL_CACHE_DIR=/path/to/hf-cache
```

2. Pre-download the configured emotion models:

```bash
uv run python scripts/cache_emotion_models.py
```

The script will download the text, speech, and ASR models (plus fusion model if
configured) into the cache directory.

## Notes

- `EMOTION_MODEL_CACHE_DIR` sets both `HF_HOME` and `TRANSFORMERS_CACHE`.
- You can also pass `--cache-dir` to the script to override the setting.
- Transformers accepts local paths, so the model IDs can be replaced with local
  directories if you need fully offline operation.
