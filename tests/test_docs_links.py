from pathlib import Path


def test_docs_do_not_include_absolute_local_paths() -> None:
    docs_root = Path("docs")
    offenders: list[str] = []
    for path in docs_root.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        if "/Users/zhoufuwang/Projects/" in text:
            offenders.append(str(path))
    assert not offenders, f"docs contain absolute local paths: {offenders}"
