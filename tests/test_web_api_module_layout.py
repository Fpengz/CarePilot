from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "apps" / "web"
LEGACY_API_MODULE = WEB_ROOT / "lib" / "api.ts"
CANONICAL_CORE_MODULE = WEB_ROOT / "lib" / "api" / "core.ts"


def test_frontend_uses_domain_clients_and_core_module_only() -> None:
    assert not LEGACY_API_MODULE.exists()
    assert CANONICAL_CORE_MODULE.exists()


def test_frontend_has_no_legacy_api_imports() -> None:
    offenders: list[str] = []
    for path in WEB_ROOT.rglob("*.ts"):
        contents = path.read_text(encoding="utf-8")
        if 'from "@/lib/api"' in contents or "from '@/lib/api'" in contents:
            offenders.append(str(path.relative_to(ROOT)))
    for path in WEB_ROOT.rglob("*.tsx"):
        contents = path.read_text(encoding="utf-8")
        if 'from "@/lib/api"' in contents or "from '@/lib/api'" in contents:
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
