"""Tests for companion web surfaces."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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


def test_companion_page_uses_interaction_selector_and_product_cards() -> None:
    companion_page = (WEB_ROOT / "app" / "companion" / "page.tsx").read_text(encoding="utf-8")
    assert 'interaction_type: "check_in"' not in companion_page
    assert "Select" in companion_page or "interaction type" in companion_page.lower()
    assert "Supporting Evidence" in companion_page
    assert "Why This Matters" in companion_page
    assert "Impact to Watch" in companion_page
    assert "JsonViewer" not in companion_page


def test_clinician_and_impact_pages_no_longer_lead_with_raw_json() -> None:
    clinician_page = (WEB_ROOT / "app" / "clinician-digest" / "page.tsx").read_text(encoding="utf-8")
    impact_page = (WEB_ROOT / "app" / "impact" / "page.tsx").read_text(encoding="utf-8")
    assert "JsonViewer" not in clinician_page
    assert "JsonViewer" not in impact_page
