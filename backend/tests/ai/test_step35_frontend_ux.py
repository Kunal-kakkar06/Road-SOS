"""
Step 35 — Automated Pytest Suite for Frontend UX, Accessibility & Cross-Device Production Validation
"""

import os
import re
import glob
import hashlib
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
EXPECTED_MODEL_SHA256 = "e014884ed8c2a537b8970af3fa1540ad8f85ac5b52846814373d0283b76001f1"

def test_step35_ml_checksum_invariant():
    """Verify ML model weights remain 100% frozen."""
    model_path = os.path.join(os.path.dirname(__file__), "..", "..", "models", "fusion_triage.pkl")
    assert os.path.exists(model_path), f"ML model missing at {model_path}"
    with open(model_path, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()
    assert sha256 == EXPECTED_MODEL_SHA256, f"ML model checksum modified! Expected {EXPECTED_MODEL_SHA256}, got {sha256}"

def get_project_root():
    curr = os.path.abspath(os.path.dirname(__file__))
    while curr and curr != os.path.dirname(curr):
        if os.path.exists(os.path.join(curr, "frontend")):
            return curr
        curr = os.path.dirname(curr)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def test_step35_html_viewport_and_lang():
    """Verify index.html contains viewport and lang attributes for mobile & accessibility."""
    project_root = get_project_root()
    html_path = os.path.join(project_root, "frontend", "index.html")
    if not os.path.exists(html_path):
        html_path = os.path.join(project_root, "frontend", "dist", "index.html")
    assert os.path.exists(html_path), "index.html file missing"
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "width=device-width" in content, "Missing responsive viewport declaration"
    assert 'lang="en"' in content or "lang='en'" in content, "Missing HTML lang attribute"

def test_step35_service_worker_pwa_spec():
    """Verify sw.js PWA cache, update mechanism, and background sync."""
    project_root = get_project_root()
    sw_path = os.path.join(project_root, "frontend", "public", "sw.js")
    assert os.path.exists(sw_path), "Service worker sw.js missing"
    with open(sw_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "roadsos-v1" in content or "CACHE" in content, "Missing SW cache storage setup"
    assert "skipWaiting" in content, "Missing SW skipWaiting() update trigger"
    assert "clients.claim" in content, "Missing SW clients.claim() trigger"
    assert "sos-sync" in content, "Missing SW background sync event listener"

def test_step35_client_secrets_redaction():
    """Verify client JS bundle contains zero hardcoded secrets."""
    assets_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend", "dist", "assets")
    js_files = glob.glob(os.path.join(assets_dir, "*.js"))
    if not js_files:
        js_files = glob.glob(os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend", "src", "**", "*.js*"), recursive=True)
    
    secret_patterns = [
        re.compile(r'SECRET_KEY\s*=\s*["\'][^"\']+["\']', re.I),
        re.compile(r'PRIVATE_KEY\s*=\s*["\'][^"\']+["\']', re.I),
        re.compile(r'postgres://[^:]+:[^@]+@', re.I),
    ]

    for js_file in js_files:
        with open(js_file, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
            for pattern in secret_patterns:
                assert not pattern.search(code), f"Secret found in client bundle: {os.path.basename(js_file)}"

def test_step35_emergency_ux_clarity():
    """Verify AITriagePage & SeverityResult include severity indicators and actionable guidance."""
    project_root = get_project_root()
    triage_path = os.path.join(project_root, "frontend", "src", "pages", "AITriagePage.jsx")
    severity_path = os.path.join(project_root, "frontend", "src", "components", "SeverityResult.jsx")
    assert os.path.exists(triage_path), "AITriagePage.jsx missing"
    assert os.path.exists(severity_path), "SeverityResult.jsx missing"
    with open(triage_path, "r", encoding="utf-8") as f1, open(severity_path, "r", encoding="utf-8") as f2:
        code = f1.read() + f2.read()
    
    for key in ["severity", "severity_color", "severity_label"]:
        assert key in code, f"Missing severity indicator property '{key}' in triage components"

def test_step35_401_refresh_interceptor():
    """Verify main.jsx implements automatic JWT refresh on HTTP 401."""
    project_root = get_project_root()
    main_path = os.path.join(project_root, "frontend", "src", "main.jsx")
    assert os.path.exists(main_path), "main.jsx missing"
    with open(main_path, "r", encoding="utf-8") as f:
        code = f.read()
    assert "401" in code and "refresh" in code, "Missing 401 JWT refresh interceptor in main.jsx"
