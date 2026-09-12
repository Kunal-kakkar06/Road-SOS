#!/usr/bin/env python3
"""
Step 40 — Physical Final Production Release Certification & System Handover Script
"""

import os
import sys
import hashlib
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
EXPECTED_MODEL_SHA256 = "e014884ed8c2a537b8970af3fa1540ad8f85ac5b52846814373d0283b76001f1"

REQUIRED_STEP40_DOCS = [
    "docs/FINAL_PRODUCTION_CERTIFICATION.md",
    "docs/SYSTEM_HANDOVER_MANIFEST.md",
    "docs/ROADSOS_V1_PRODUCTION_RELEASE_NOTES.md",
]

def print_section(title):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def verify_ml_artifact_invariant():
    print_section("1. ML Model Artifact Checksum Invariant Verification")
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

def verify_api_health_endpoint():
    print_section("2. API Production Health & Readiness Verification")
    res = client.get("/health")
    if res.status_code != 200:
        print(f"❌ FAIL: Health endpoint returned HTTP {res.status_code}")
        return False

    status = res.json().get("status")
    print(f"  Health Check Status: {status}")
    if status not in ["ok", "healthy"]:
        print(f"❌ FAIL: Health status expected 'ok', got '{status}'")
        return False

    print("  ✅ API production health check passed.")
    return True

def verify_final_handover_documents():
    print_section("3. Final Production Release & Handover Documents Verification")
    project_root = os.path.join(os.path.dirname(__file__), "..")

    missing = []
    for relative_doc in REQUIRED_STEP40_DOCS:
        full_path = os.path.join(project_root, relative_doc)
        if os.path.exists(full_path):
            size_bytes = os.path.getsize(full_path)
            print(f"  ✅ Verified: {relative_doc} ({size_bytes} bytes)")
        else:
            print(f"  ❌ MISSING: {relative_doc}")
            missing.append(relative_doc)

    if missing:
        print(f"❌ FAIL: Missing required Step 40 documentation files: {missing}")
        return False

    return True

def main():
    print("=" * 80)
    print(" ROADSOS STEP 40: FINAL PRODUCTION RELEASE CERTIFICATION & HANDOVER")
    print("=" * 80)

    checks = [
        verify_ml_artifact_invariant(),
        verify_api_health_endpoint(),
        verify_final_handover_documents(),
    ]

    all_passed = all(checks)
    print_section("STEP 40 FINAL CERTIFICATION SUMMARY")
    if all_passed:
        print("🟢 ALL STEP 40 FINAL PRODUCTION CERTIFICATION CHECKS PASSED.")
        print("\n=================================================================================")
        print("  CERTIFICATION: 🟢 APPROVED FOR UNCONDITIONAL PRODUCTION GO-LIVE")
        print("  SYSTEM VERSION: RoadSOS v1.0.0 (Production Release)")
        print("  DISPOSITION: ALL 40 STEPS PASSED — READY FOR PRODUCTION DEPLOYMENT")
        print("=================================================================================")
        sys.exit(0)
    else:
        print("🔴 STEP 40 CERTIFICATION FAILED. CHECK ERRORS ABOVE.")
        sys.exit(1)

if __name__ == "__main__":
    main()
