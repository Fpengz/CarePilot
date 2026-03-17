"""Tests for companion web surfaces."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = ROOT / "apps" / "web"


def test_companion_demo_pages_and_client_exist() -> None:
    assert (WEB_ROOT / "lib" / "api" / "companion-client.ts").exists()
    assert (WEB_ROOT / "app" / "companion" / "page.tsx").exists()
    assert (WEB_ROOT / "app" / "clinician-digest" / "page.tsx").exists()
    assert (WEB_ROOT / "app" / "impact" / "page.tsx").exists()


def test_route_meta_advertises_companion_surfaces() -> None:
    route_meta = (WEB_ROOT / "components" / "app" / "route-meta.ts").read_text(encoding="utf-8")
    assert 'href: "/companion"' in route_meta
    assert 'href: "/clinician-digest"' in route_meta
    assert 'href: "/impact"' in route_meta


def test_companion_page_has_workspace_title() -> None:
    companion_page = (WEB_ROOT / "app" / "companion" / "page.tsx").read_text(encoding="utf-8")
    assert "Companion Workspace" in companion_page


def test_clinician_and_impact_pages_no_longer_lead_with_raw_json() -> None:
    clinician_page = (WEB_ROOT / "app" / "clinician-digest" / "page.tsx").read_text(
        encoding="utf-8"
    )
    impact_page = (WEB_ROOT / "app" / "impact" / "page.tsx").read_text(encoding="utf-8")
    assert "JsonViewer" not in clinician_page
    assert "JsonViewer" not in impact_page
