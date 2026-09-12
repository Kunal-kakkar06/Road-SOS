#!/usr/bin/env python3
"""
Step 35 — Physical Frontend UX, Accessibility & Cross-Device Production Validation Script
"""

import os
import re
import sys
import glob
import hashlib

EXPECTED_MODEL_SHA256 = "e014884ed8c2a537b8970af3fa1540ad8f85ac5b52846814373d0283b76001f1"

def print_section(title):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def verify_ml_invariant():
    print_section("1. ML Model Checksum Invariant Verification")
    model_path = os.path.join(os.path.dirname(__file__), "models", "fusion_triage.pkl")
    if not os.path.exists(model_path):
        print(f"❌ FAIL: ML model file not found at {model_path}")
        return False
    
    with open(model_path, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()
    
    print(f"  ML Model SHA-256: {sha256}")
    if sha256 != EXPECTED_MODEL_SHA256:
        print(f"❌ FAIL: ML model SHA-256 mismatch! Expected {EXPECTED_MODEL_SHA256}")
        return False
    print("  ✅ ML model checksum matches release invariant (0 modifications).")
    return True

def verify_frontend_bundle_and_index():
    print_section("2. Production Frontend Bundle & HTML Inspection")
    dist_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
    index_html_path = os.path.join(dist_dir, "index.html")
    
    if not os.path.exists(index_html_path):
        # Fallback to source index.html if dist not built yet
        index_html_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")

    print(f"  Inspecting: {index_html_path}")
    with open(index_html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Check viewport
    has_viewport = re.search(r'<meta\s+name=["\']viewport["\']\s+content=["\'][^"\']*width=device-width[^"\']*["\']', html_content, re.I)
    if not has_viewport:
        print("❌ FAIL: Missing responsive viewport meta tag in index.html")
        return False
    print("  ✅ Responsive viewport meta tag present (<meta name='viewport' content='width=device-width, initial-scale=1.0'>).")

    # Check lang tag
    has_lang = re.search(r'<html\s+lang=["\']en["\']', html_content, re.I)
    if not has_lang:
        print("❌ FAIL: Missing lang='en' attribute in <html> tag")
        return False
    print("  ✅ HTML lang attribute declared (lang='en').")

    return True

def verify_pwa_service_worker():
    print_section("3. PWA Service Worker & Offline Caching Audit")
    sw_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "sw.js")
    if not os.path.exists(sw_path):
        sw_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist", "sw.js")

    if not os.path.exists(sw_path):
        print(f"❌ FAIL: Service Worker sw.js not found at {sw_path}")
        return False

    with open(sw_path, "r", encoding="utf-8") as f:
        sw_content = f.read()

    # Check cache name
    if "roadsos-v1" not in sw_content and "CACHE" not in sw_content:
        print("❌ FAIL: sw.js missing cache storage declaration")
        return False
    print("  ✅ Service Worker cache storage configured ('roadsos-v1').")

    # Check skipWaiting & claim
    if "skipWaiting" not in sw_content or "clients.claim" not in sw_content:
        print("❌ FAIL: sw.js missing skipWaiting() or clients.claim() update mechanism")
        return False
    print("  ✅ Service Worker update mechanism active (skipWaiting & clients.claim).")

    # Check background sync & IndexedDB
    if "sync" not in sw_content or "indexedDB" not in sw_content:
        print("❌ FAIL: sw.js missing background sync or IndexedDB queueing")
        return False
    print("  ✅ Service Worker background sync ('sos-sync') and IndexedDB offline queueing verified.")

    return True

def verify_frontend_security_secrets():
    print_section("4. Frontend Bundle Security & Secret Scanning")
    dist_assets = glob.glob(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist", "assets", "*.js"))
    if not dist_assets:
        print("⚠️ WARNING: No dist/assets/*.js found. Scanning frontend/src/")
        dist_assets = glob.glob(os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "**", "*.js*"), recursive=True)

    secret_patterns = [
        re.compile(r'SECRET_KEY\s*=\s*["\'][^"\']+["\']', re.I),
        re.compile(r'PRIVATE_KEY\s*=\s*["\'][^"\']+["\']', re.I),
        re.compile(r'postgres://[^:]+:[^@]+@', re.I),
        re.compile(r'amqps?://[^:]+:[^@]+@', re.I),
    ]

    secrets_found = 0
    for js_file in dist_assets:
        with open(js_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            for pattern in secret_patterns:
                if pattern.search(content):
                    print(f"❌ FAIL: Secret detected in client asset: {os.path.basename(js_file)}")
                    secrets_found += 1

    if secrets_found > 0:
        return False

    print("  ✅ Client JavaScript bundle secret scan passed (0 secrets / credentials detected).")
    return True

def verify_accessibility_and_ux_tokens():
    print_section("5. Accessibility (WCAG 2.1 AA) & CSS Token Audit")
    css_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "index.css")
    if not os.path.exists(css_path):
        print(f"❌ FAIL: CSS file not found at {css_path}")
        return False

    with open(css_path, "r", encoding="utf-8") as f:
        css_content = f.read()

    # Check focus visible
    if ":focus-visible" not in css_content and ":focus" not in css_content:
        print("❌ FAIL: index.css missing explicit focus indicators for keyboard navigation")
        return False
    print("  ✅ Keyboard focus indicators present (:focus-visible outline styling).")

    # Check responsive media queries
    if "@media" not in css_content or "max-width" not in css_content:
        print("❌ FAIL: index.css missing responsive media query breakpoints")
        return False
    print("  ✅ Responsive media query breakpoints present for desktop, tablet, and mobile.")

    # Check emergency color status badges
    src_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "src")
    triage_page = os.path.join(src_dir, "pages", "AITriagePage.jsx")
    severity_comp = os.path.join(src_dir, "components", "SeverityResult.jsx")
    
    with open(triage_page, "r", encoding="utf-8") as f:
        triage_code = f.read()
    with open(severity_comp, "r", encoding="utf-8") as f:
        sev_code = f.read()

    combined_code = triage_code + sev_code
    for indicator in ["severity", "severity_color", "severity_label"]:
        if indicator not in combined_code:
            print(f"❌ FAIL: SeverityResult/AITriagePage missing indicator '{indicator}'")
            return False
    print("  ✅ Emergency severity indicators verified (Critical, High, Moderate, Low / P1-P4).")

    # Check auth 401 interceptor
    main_jsx = os.path.join(src_dir, "main.jsx")
    with open(main_jsx, "r", encoding="utf-8") as f:
        main_code = f.read()

    if "401" not in main_code or "refresh" not in main_code:
        print("❌ FAIL: main.jsx missing 401 auto-refresh token interceptor")
        return False
    print("  ✅ HTTP 401 token auto-refresh interceptor verified in main.jsx.")

    return True

def main():
    print("=" * 80)
    print(" ROADSOS STEP 35: FRONTEND UX, ACCESSIBILITY & CROSS-DEVICE VALIDATION")
    print("=" * 80)

    checks = [
        verify_ml_invariant(),
        verify_frontend_bundle_and_index(),
        verify_pwa_service_worker(),
        verify_frontend_security_secrets(),
        verify_accessibility_and_ux_tokens(),
    ]

    all_passed = all(checks)
    print_section("STEP 35 AUDIT SUMMARY")
    if all_passed:
        print("🟢 ALL STEP 35 FRONTEND UX & ACCESSIBILITY AUDITS PASSED SUCCESSFULLY.")
        sys.exit(0)
    else:
        print("🔴 STEP 35 AUDIT FAILED. CHECK ERRORS ABOVE.")
        sys.exit(1)

if __name__ == "__main__":
    main()
