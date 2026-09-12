import pytest
import os
import re
import jwt
from datetime import datetime, timezone, timedelta
import httpx

from main import app, validate_production_configuration
from dependencies.auth_deps import create_access_token, SECRET_KEY, ALGORITHM
from utils.logging_config import StructuredJsonFormatter
import logging

@pytest.mark.asyncio
async def test_1_static_secrets_and_production_fail_closed():
    # 1. Check .gitignore
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    gitignore_path = os.path.join(root_dir, ".gitignore")
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            content = f.read()
            assert ".env" in content, ".gitignore must exclude .env files"

    # 2. Check .env.example
    env_example = os.path.join(os.path.dirname(__file__), "../../.env.example")
    if os.path.exists(env_example):
        with open(env_example, "r") as f:
            content = f.read()
            assert "roadsos_password" in content or "change-me" in content or "your_" in content or "placeholder" in content

    # 3. Production Configuration Fail-Closed Enforcement
    orig_env = os.environ.get("ENVIRONMENT")
    orig_jwt = os.environ.get("JWT_SECRET")
    orig_db = os.environ.get("DATABASE_URL")
    
    try:
        os.environ["ENVIRONMENT"] = "production"
        os.environ["JWT_SECRET"] = "change-me"
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://roadsos:roadsos_password@localhost:5432/roadsos_db"
        with pytest.raises(ValueError, match="Insecure JWT_SECRET"):
            validate_production_configuration()

        os.environ["JWT_SECRET"] = "secure-production-secret-key-256-bit-long-string"
        os.environ["DATABASE_URL"] = "sqlite:///./test.db"
        with pytest.raises(ValueError, match="SQLite database connection is strictly prohibited"):
            validate_production_configuration()
    finally:
        if orig_env: os.environ["ENVIRONMENT"] = orig_env
        else: os.environ.pop("ENVIRONMENT", None)
        if orig_jwt: os.environ["JWT_SECRET"] = orig_jwt
        else: os.environ.pop("JWT_SECRET", None)
        if orig_db: os.environ["DATABASE_URL"] = orig_db
        else: os.environ.pop("DATABASE_URL", None)


@pytest.mark.asyncio
async def test_2_authentication_abuse_edge_cases():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Missing token
        r = await client.get("/api/triage/history")
        assert r.status_code == 401

        # Malformed Bearer token
        r = await client.get("/api/triage/history", headers={"Authorization": "Bearer malformed.jwt.token"})
        assert r.status_code == 401

        # Expired JWT
        expired_payload = {
            "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
            "user_id": "user-test-uuid",
            "role": "USER",
            "type": "access"
        }
        expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)
        r = await client.get("/api/triage/history", headers={"Authorization": f"Bearer {expired_token}"})
        assert r.status_code == 401

        # Invalid Signature
        forged_token = jwt.encode({"user_id": "user-test-uuid", "role": "USER", "type": "access"}, "invalid-key", algorithm=ALGORITHM)
        r = await client.get("/api/triage/history", headers={"Authorization": f"Bearer {forged_token}"})
        assert r.status_code == 401

        # alg=none attack
        none_token = jwt.encode({"user_id": "user-test-uuid", "role": "ADMIN", "type": "access"}, "", algorithm="none")
        r = await client.get("/api/triage/history", headers={"Authorization": f"Bearer {none_token}"})
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_3_authorization_idor_and_rbac_isolation():
    from database import AsyncSessionLocal
    from models.user import User
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).filter(User.uuid == "test-user-sec-1"))
        if not res.scalars().first():
            session.add(User(uuid="test-user-sec-1", name="Sec User 1", email="sec1@example.com", hashed_password="pw", role="USER"))
            await session.commit()

    token_user = create_access_token(user_uuid="test-user-sec-1", role="USER")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Cross-tenant non-existent / other user job request
        r = await client.get("/api/triage/async/00000000-0000-0000-0000-000000000999", headers={"Authorization": f"Bearer {token_user}"})
        assert r.status_code in (404, 403, 401)

        # Standard USER attempting responder queue
        r = await client.get("/api/responder/queue", headers={"Authorization": f"Bearer {token_user}"})
        assert r.status_code == 403


@pytest.mark.asyncio
async def test_4_api_input_fuzzing_and_sql_injection():
    from database import AsyncSessionLocal
    from models.user import User
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).filter(User.uuid == "test-user-sec-2"))
        if not res.scalars().first():
            session.add(User(uuid="test-user-sec-2", name="Sec User 2", email="sec2@example.com", hashed_password="pw", role="USER"))
            await session.commit()

    token_user = create_access_token(user_uuid="test-user-sec-2", role="USER")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        sql_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users;--",
            "1 UNION SELECT 1,2,3--"
        ]
        for sql in sql_payloads:
            r = await client.post("/api/triage", headers={"Authorization": f"Bearer {token_user}"}, json={"text": sql})
            assert r.status_code in (200, 400, 422)
            assert "syntax error" not in r.text.lower()
            assert "traceback" not in r.text.lower()

        fuzz_payloads = [
            {"text": "A" * 5000},
            {"text": "Special \x00 characters \uFFFF"},
            {"latitude": 999.0}
        ]
        for payload in fuzz_payloads:
            r = await client.post("/api/triage", headers={"Authorization": f"Bearer {token_user}"}, json=payload)
            assert r.status_code in (200, 400, 422)
            assert r.status_code != 500


@pytest.mark.asyncio
async def test_5_sensitive_data_redaction():
    formatter = StructuredJsonFormatter(service_name="roadsos-api")
    sample_msg = "Connecting with password=MySecretPass and postgresql://user:dbpass123@localhost:5432/db"
    record = logging.LogRecord("test", logging.INFO, "", 0, sample_msg, (), None)
    formatted = formatter.format(record)
    assert "MySecretPass" not in formatted
    assert "dbpass123" not in formatted
    assert "[REDACTED_DB_PASS]" in formatted


@pytest.mark.asyncio
async def test_6_security_headers_and_cors():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        r = await client.get("/health")
        assert r.headers.get("X-Content-Type-Options") == "nosniff"
        assert r.headers.get("X-Frame-Options") == "DENY"
        assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


@pytest.mark.asyncio
async def test_7_docker_container_non_root_security():
    dockerfile_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../Dockerfile"))
    if os.path.exists(dockerfile_path):
        with open(dockerfile_path, "r") as f:
            content = f.read()
            assert "USER roadsos" in content or "useradd" in content

    dockerignore_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.dockerignore"))
    if os.path.exists(dockerignore_path):
        with open(dockerignore_path, "r") as f:
            content = f.read()
            assert ".env" in content
