import json
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import delete, event, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from test_assignments import PASSWORD, Team, login
from test_assignments import team as team
from test_insights import populated as populated

from app.config import Settings, get_settings
from app.main import app
from app.models import (
    Activity,
    AIConfiguration,
    AISummaryCache,
    AISummaryLatest,
    AuditLog,
    Client,
    Department,
    DepartmentMember,
    Organization,
    OrganizationMode,
    User,
)
from app.models.activity_type import activity_type_identifier
from app.routers.summaries import get_summary_provider
from app.schemas.summaries import ProviderSummaryBatch, ProviderSummarySection
from app.services.bootstrap import bootstrap_organization
from app.services.summary_provider import (
    SYSTEM_PROMPT,
    HttpSummaryProvider,
    ProviderSummaryResult,
    ProviderTokenUsage,
    SummaryFailure,
    configuration_from_settings,
    provider_enabled,
)


class FakeProvider:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def summarize(self, records: str) -> ProviderSummaryResult:
        data = json.loads(records)
        self.calls.append(data)
        return ProviderSummaryResult(
            batch=ProviderSummaryBatch(
                g=[
                    ProviderSummarySection(
                        k=group["k"],
                        s="Resumen de prueba",
                        p=["Revisar seguimiento"],
                        i=[record[0] for record in group["r"]],
                    )
                    for group in data["g"]
                ]
            ),
            usage=ProviderTokenUsage(input_tokens=100, output_tokens=200),
        )


@pytest.fixture
def simulated():
    fake = FakeProvider()
    settings = Settings(
        _env_file=None, ai_provider="ollama", ai_model="test-model", ai_ollama_local_confirmed=True
    )
    app.dependency_overrides[get_summary_provider] = lambda: fake
    app.dependency_overrides[get_settings] = lambda: settings
    yield fake, settings
    app.dependency_overrides.pop(get_summary_provider, None)
    app.dependency_overrides.pop(get_settings, None)


def body(**changes: object) -> dict:
    return {
        "scope": "ORGANIZATION",
        "since": "2026-09-01T00:00:00Z",
        "until": "2026-09-10T00:00:00Z",
        **changes,
    }


@pytest.mark.parametrize(
    "role,scope,expected,status",
    [
        ("owner", "CLIENT", 2, 200),
        ("admin", "CLIENT", 1, 200),
        ("employee", "CLIENT", 0, 403),
        ("owner", "ORGANIZATION", 2, 200),
        ("admin", "ORGANIZATION", 0, 403),
        ("admin", "DEPARTMENT", 1, 200),
    ],
)
async def test_summary_scope_and_department_isolation(
    populated: Team,
    api_client: AsyncClient,
    simulated,
    db_session: AsyncSession,
    role: str,
    scope: str,
    expected: int,
    status: int,
) -> None:
    fake, _ = simulated
    headers = await login(api_client, populated.users[role])
    payload = body(
        scope=scope,
        **(
            {"client_id": str(populated.client.id)}
            if scope == "CLIENT"
            else {"department_id": str(populated.department.id)}
            if scope == "DEPARTMENT"
            else {}
        ),
    )
    response = await api_client.post("/api/v1/ai/summaries", json=payload, headers=headers)
    assert response.status_code == status, response.text
    assert len(fake.calls) == (1 if status == 200 else 0)
    if status == 200:
        result = response.json()
        assert len(result["sections"]) == expected
        call = fake.calls[0]
        assert set(call) == {"g"} and len(call["g"]) == expected
        assert [group["k"] for group in call["g"]] == [f"g{index}" for index in range(expected)]
        assert all(set(group) == {"k", "r"} for group in call["g"])
        assert all(
            len(record) == 8 and record[0].startswith("r")
            for group in call["g"]
            for record in group["r"]
        )
        for group, section in zip(call["g"], result["sections"], strict=True):
            for record, source in zip(group["r"], section["sources"], strict=True):
                assert source["client_name"] == record[1]
                assert source["activity_type_name"] == record[2]
                assert source["title"] == record[3]
                assert source["status"] == record[4]
                assert source["description"] == record[6]
            ids = [item["id"] for item in section["sources"]]
            departments = set(
                await db_session.scalars(select(Activity.department_id).where(Activity.id.in_(ids)))
            )
            assert len(departments) == 1
            if role == "admin":
                assert departments == {populated.department.id}
        events = list(
            await db_session.scalars(select(AuditLog).where(AuditLog.action.like("AI_%")))
        )
        assert {item.action for item in events} == {"AI_SUMMARY_REQUESTED", "AI_SUMMARY_COMPLETED"}
        metadata = next(item.event_data for item in events if item.action == "AI_SUMMARY_REQUESTED")
        assert len(metadata["context_sha256"]) == 64
        assert "Activity A" not in json.dumps(metadata)
        assert "Resumen de prueba" not in json.dumps(metadata)


def test_prompt_identifies_service_team_and_client_roles() -> None:
    assert "activities are work done for clients" in SYSTEM_PROMPT
    assert "not the actor" in SYSTEM_PROMPT
    assert "client did it" in SYSTEM_PROMPT


async def test_future_period_includes_scheduled_work_without_marking_it_complete(
    populated: Team, api_client: AsyncClient, simulated
) -> None:
    headers = await login(api_client, populated.users["owner"])
    response = await api_client.post(
        "/api/v1/ai/summaries",
        headers=headers,
        json=body(since="2026-09-08T00:00:00Z", until="2026-09-10T23:59:00Z"),
    )
    assert response.status_code == 200, response.text
    records = [record for group in simulated[0].calls[0]["g"] for record in group["r"]]
    assert len(records) == 3
    assert all(record[4] == "PENDING" for record in records)
    sources = [source for section in response.json()["sections"] for source in section["sources"]]
    assert all(source["occurred_at"] is None for source in sources)
    assert {source["scheduled_for"] for source in sources} == {
        "2026-09-08",
        "2026-09-09",
        "2026-09-10",
    }


async def test_latest_summaries_are_persisted_per_department_and_client_scope(
    populated: Team, api_client: AsyncClient, simulated, db_session: AsyncSession
) -> None:
    owner_headers = await login(api_client, populated.users["owner"])
    generated = await api_client.post("/api/v1/ai/summaries", json=body(), headers=owner_headers)
    assert generated.status_code == 200, generated.text
    global_latest = await api_client.get("/api/v1/ai/summaries/latest?scope=ORGANIZATION")
    assert global_latest.status_code == 200, global_latest.text
    entries = global_latest.json()
    assert len(entries) == 2
    assert {entry["section"]["department_id"] for entry in entries} == {
        section["department_id"] for section in generated.json()["sections"]
    }
    assert all(
        datetime.fromisoformat(entry["since"]) == datetime.fromisoformat(body()["since"])
        for entry in entries
    )
    assert all(
        datetime.fromisoformat(entry["until"]) == datetime.fromisoformat(body()["until"])
        for entry in entries
    )
    assert all(entry["generated_at"] for entry in entries)
    department_url = (
        f"/api/v1/ai/summaries/latest?scope=DEPARTMENT&department_id={populated.department.id}"
    )
    assert len((await api_client.get(department_url)).json()) == 1
    client_url = f"/api/v1/ai/summaries/latest?scope=CLIENT&client_id={populated.client.id}"
    assert (await api_client.get(client_url)).json() == []

    repeated = await api_client.post(
        "/api/v1/ai/summaries",
        json=body(until="2026-09-11T23:59:00Z"),
        headers=owner_headers,
    )
    assert repeated.status_code == 200 and repeated.json()["cached"] is True
    updated = (await api_client.get(department_url)).json()[0]
    assert datetime.fromisoformat(updated["until"]) == datetime.fromisoformat(
        "2026-09-11T23:59:00Z"
    )

    client_generated = await api_client.post(
        "/api/v1/ai/summaries",
        json=body(scope="CLIENT", client_id=str(populated.client.id)),
        headers=owner_headers,
    )
    assert client_generated.status_code == 200
    assert len((await api_client.get(client_url)).json()) == 2
    assert len((await api_client.get("/api/v1/ai/summaries/latest?scope=ORGANIZATION")).json()) == 2
    assert len(list(await db_session.scalars(select(AISummaryLatest)))) == 4

    await login(api_client, populated.users["admin"])
    assert (
        await api_client.get("/api/v1/ai/summaries/latest?scope=ORGANIZATION")
    ).status_code == 403
    assert len((await api_client.get(department_url)).json()) == 1
    assert len((await api_client.get(client_url)).json()) == 1
    await db_session.execute(
        delete(DepartmentMember).where(DepartmentMember.user_id == populated.users["admin"].id)
    )
    await db_session.commit()
    assert (await api_client.get(client_url)).json() == []


async def test_generation_reports_usage_without_preflight_or_confirmation(
    populated: Team, api_client: AsyncClient, simulated
) -> None:
    fake, _ = simulated
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        ai_provider="openai",
        ai_model="gpt-5.6-luna",
        ai_openai_api_key="test-key",
    )
    headers = await login(api_client, populated.users["owner"])
    response = await api_client.post(
        "/api/v1/ai/summaries",
        json=body(),
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["usage"] == {
        "input_tokens": 100,
        "output_tokens": 200,
        "estimated_cost_usd": 0.00026,
    }
    assert len(fake.calls) == 1
    repeated = await api_client.post("/api/v1/ai/summaries", json=body(), headers=headers)
    assert repeated.status_code == 200
    assert repeated.json()["cached"] is True
    assert repeated.json()["usage"] is None
    assert len(fake.calls) == 1


async def test_unknown_targets_csrf_and_forged_scope(
    populated: Team, api_client: AsyncClient, simulated, db_session: AsyncSession
) -> None:
    fake, _ = simulated
    assert (await api_client.get("/api/v1/ai/options")).status_code == 401
    headers = await login(api_client, populated.users["admin"])
    assert (await api_client.post("/api/v1/ai/summaries", json=body())).status_code == 403
    other_id = await db_session.scalar(
        select(DepartmentMember.department_id).where(
            DepartmentMember.user_id == populated.users["hidden"].id
        )
    )
    assert (
        await api_client.post(
            "/api/v1/ai/summaries",
            headers=headers,
            json=body(scope="DEPARTMENT", department_id=str(other_id)),
        )
    ).status_code == 403
    other = Organization(name="Other", mode=OrganizationMode.BUSINESS)
    db_session.add(other)
    await db_session.flush()
    foreign_client = Client(organization_id=other.id, name="Foreign client")
    foreign_department = Department(
        organization_id=other.id, name="Foreign department", normalized_name="foreign department"
    )
    db_session.add_all([foreign_client, foreign_department])
    await db_session.commit()
    for payload in [
        body(scope="CLIENT", client_id=str(foreign_client.id)),
        body(scope="DEPARTMENT", department_id=str(foreign_department.id)),
        body(scope="CLIENT", client_id=str(uuid4())),
        body(scope="DEPARTMENT", department_id=str(uuid4())),
    ]:
        assert (
            await api_client.post("/api/v1/ai/summaries", json=payload, headers=headers)
        ).status_code == 404
    for payload in [
        body(client_id=str(populated.client.id)),
        body(provider="openai"),
        body(since="2026-09-01"),
        body(since="2027-01-01T00:00:00Z"),
        body(since="2024-01-01T00:00:00Z"),
    ]:
        assert (
            await api_client.post("/api/v1/ai/summaries", json=payload, headers=headers)
        ).status_code == 422
    assert fake.calls == []


async def test_disabled_and_empty_external_summary(
    populated: Team, api_client: AsyncClient, simulated
) -> None:
    fake, settings = simulated
    headers = await login(api_client, populated.users["owner"])
    settings.ai_provider = "disabled"
    assert (await api_client.get("/api/v1/ai/options")).json()["enabled"] is False
    assert (
        await api_client.post("/api/v1/ai/summaries", json=body(), headers=headers)
    ).status_code == 503
    settings.ai_provider = "openai"
    from pydantic import SecretStr

    settings.ai_openai_api_key = SecretStr("test-key")
    empty = await api_client.post(
        "/api/v1/ai/summaries",
        headers=headers,
        json=body(since="2020-01-01T00:00:00Z", until="2020-02-01T00:00:00Z"),
    )
    assert empty.status_code == 200 and empty.json()["sections"] == []
    assert empty.json()["request_id"] is None and fake.calls == []


async def test_only_owner_can_store_encrypted_organization_ai_configuration(
    populated: Team,
    api_client: AsyncClient,
    db_session: AsyncSession,
    simulated,
) -> None:
    admin_headers = await login(api_client, populated.users["admin"])
    assert (await api_client.get("/api/v1/ai/configuration")).status_code == 403
    assert (
        await api_client.put(
            "/api/v1/ai/configuration",
            headers=admin_headers,
            json={"provider": "disabled", "model": ""},
        )
    ).status_code == 403

    owner_headers = await login(api_client, populated.users["owner"])
    inherited = await api_client.get("/api/v1/ai/configuration")
    assert inherited.status_code == 200
    assert inherited.json() == {
        "provider": "ollama",
        "model": "test-model",
        "has_api_key": False,
        "source": "environment",
    }
    missing_key = await api_client.put(
        "/api/v1/ai/configuration",
        headers=owner_headers,
        json={"provider": "anthropic", "model": "claude-model"},
    )
    assert missing_key.status_code == 422
    saved = await api_client.put(
        "/api/v1/ai/configuration",
        headers=owner_headers,
        json={"provider": "anthropic", "model": "claude-model", "api_key": "secret-key"},
    )
    assert saved.status_code == 200
    assert saved.json() == {
        "provider": "anthropic",
        "model": "claude-model",
        "has_api_key": True,
        "source": "organization",
    }
    stored = await db_session.get(AIConfiguration, populated.client.organization_id)
    assert stored and stored.encrypted_api_key
    assert "secret-key" not in stored.encrypted_api_key
    assert "secret-key" not in saved.text

    updated = await api_client.put(
        "/api/v1/ai/configuration",
        headers=owner_headers,
        json={"provider": "anthropic", "model": "new-claude-model"},
    )
    assert updated.status_code == 200 and updated.json()["has_api_key"] is True
    event_data = await db_session.scalars(
        select(AuditLog.event_data).where(AuditLog.action == "UPDATED_AI_CONFIGURATION")
    )
    events = list(event_data)
    assert events[-1] == {"provider": "anthropic", "model": "new-claude-model"}
    assert "secret-key" not in json.dumps(events)


async def test_individual_summary_has_no_department(
    db_session: AsyncSession, api_client: AsyncClient, simulated
) -> None:
    _, owner = await bootstrap_organization(
        db_session,
        mode=OrganizationMode.INDIVIDUAL,
        organization_name="Personal",
        owner_name="Owner",
        owner_email="owner@example.com",
        owner_password=PASSWORD,
    )
    client = Client(organization_id=owner.organization_id, name="Personal client")
    db_session.add(client)
    await db_session.flush()
    db_session.add(
        Activity(
            organization_id=owner.organization_id,
            client_id=client.id,
            user_id=owner.id,
            assigned_to_user_id=owner.id,
            department_id=None,
            activity_type_id=activity_type_identifier(owner.organization_id, "nota"),
            description="Personal note",
            scheduled_for=datetime(2026, 9, 7, tzinfo=UTC).date(),
            status="COMPLETED",
            occurred_at=datetime(2026, 9, 7, tzinfo=UTC),
            completed_at=datetime(2026, 9, 7, tzinfo=UTC),
        )
    )
    await db_session.commit()
    headers = await login(api_client, owner)
    assert (await api_client.get("/api/v1/ai/options")).json()["departments"] == []
    response = await api_client.post("/api/v1/ai/summaries", json=body(), headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["sections"][0]["department_id"] is None
    assert simulated[0].calls[0]["g"][0]["k"] == "g0"
    assert "department" not in simulated[0].calls[0]
    latest = await api_client.get("/api/v1/ai/summaries/latest?scope=ORGANIZATION")
    assert latest.status_code == 200
    assert len(latest.json()) == 1
    assert latest.json()[0]["section"]["department_id"] is None


async def test_rate_limit_is_shared_by_organization(
    populated: Team, api_client: AsyncClient, simulated
) -> None:
    headers = await login(api_client, populated.users["owner"])
    assert (
        await api_client.post("/api/v1/ai/summaries", json=body(), headers=headers)
    ).status_code == 200
    headers = await login(api_client, populated.users["admin"])
    response = await api_client.post(
        "/api/v1/ai/summaries",
        headers=headers,
        json=body(scope="CLIENT", client_id=str(populated.client.id)),
    )
    assert response.status_code == 429
    assert len(simulated[0].calls) == 1


@pytest.mark.parametrize("failure", ["provider", "citation", "timeout", "membership", "session"])
async def test_failures_and_permission_changes_discard_output(
    populated: Team,
    api_client: AsyncClient,
    db_session: AsyncSession,
    simulated,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    fake, _ = simulated
    original = fake.summarize

    async def generate(records: str) -> ProviderSummaryResult:
        result = await original(records)
        if failure == "provider":
            raise SummaryFailure("AI_PROVIDER_UNAVAILABLE")
        if failure == "citation":
            result.batch.g[0].i = ["r49"]
        if failure == "timeout":
            raise TimeoutError()
        if failure == "membership":
            await db_session.execute(
                delete(DepartmentMember).where(
                    DepartmentMember.user_id == populated.users["admin"].id
                )
            )
            await db_session.commit()
        if failure == "session":
            await db_session.execute(
                update(User).where(User.id == populated.users["admin"].id).values(status="DISABLED")
            )
            await db_session.commit()
        return result

    monkeypatch.setattr(fake, "summarize", generate)
    headers = await login(api_client, populated.users["admin"])
    response = await api_client.post(
        "/api/v1/ai/summaries",
        headers=headers,
        json=body(scope="CLIENT", client_id=str(populated.client.id)),
    )
    assert (
        response.status_code
        == {"provider": 503, "citation": 502, "timeout": 504, "membership": 403, "session": 401}[
            failure
        ]
    ), response.text
    assert "Resumen de prueba" not in response.text
    assert await db_session.scalar(
        select(AuditLog.id).where(AuditLog.action == "AI_SUMMARY_FAILED")
    )


async def test_audit_failure_prevents_provider_request(
    populated: Team, api_client: AsyncClient, simulated
) -> None:
    headers = await login(api_client, populated.users["owner"])

    def fail(mapper, connection, target) -> None:
        if target.action == "AI_SUMMARY_REQUESTED":
            raise RuntimeError("Audit unavailable")

    event.listen(AuditLog, "before_insert", fail)
    try:
        with pytest.raises(RuntimeError, match="Audit unavailable"):
            await api_client.post("/api/v1/ai/summaries", json=body(), headers=headers)
    finally:
        event.remove(AuditLog, "before_insert", fail)
    assert simulated[0].calls == []


async def test_identical_summary_uses_short_lived_cache(
    populated: Team,
    api_client: AsyncClient,
    db_session: AsyncSession,
    simulated,
) -> None:
    fake, _ = simulated
    headers = await login(api_client, populated.users["owner"])
    first = await api_client.post("/api/v1/ai/summaries", json=body(), headers=headers)
    second = await api_client.post("/api/v1/ai/summaries", json=body(), headers=headers)
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["sections"] == second.json()["sections"]
    assert first.json()["request_id"] != second.json()["request_id"]
    assert first.json()["cached"] is False and second.json()["cached"] is True
    assert len(fake.calls) == 1
    assert await db_session.scalar(select(AISummaryCache.id))
    completed = list(
        await db_session.scalars(select(AuditLog).where(AuditLog.action == "AI_SUMMARY_COMPLETED"))
    )
    assert [item.event_data["cache_hit"] for item in completed] == [False, True]


@pytest.mark.parametrize(
    "url",
    [
        "http://attacker.test:11434",
        "http://localhost:invalid",
        "http://ollama:11434/redirect",
        "http://user@localhost:11434",
        "https://ollama:11434",
    ],
)
def test_ollama_endpoint_is_installation_controlled(url: str) -> None:
    settings = Settings(
        _env_file=None,
        ai_provider="ollama",
        ai_model="test",
        ai_ollama_local_confirmed=True,
        ai_ollama_url=url,
    )
    assert not provider_enabled(configuration_from_settings(settings), settings)


@pytest.mark.parametrize("provider", ["ollama", "openai", "anthropic", "gemini"])
async def test_provider_http_contract_without_network(
    monkeypatch: pytest.MonkeyPatch, provider: str
) -> None:
    settings = Settings(
        _env_file=None,
        ai_provider=provider,
        ai_model="test",
        ai_ollama_local_confirmed=True,
        ai_openai_api_key="test-key",
        ai_anthropic_api_key="test-key",
        ai_gemini_api_key="test-key",
    )
    output = {"g": [{"k": "g0", "s": "Valid", "p": [], "i": ["r0"]}]}
    seen = []

    def handle(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        seen.append(payload)
        if provider == "openai":
            assert str(request.url) == "https://api.openai.com/v1/responses"
            assert payload["store"] is False and "tools" not in payload
            assert payload["max_output_tokens"] == 620
            assert payload["text"]["format"]["strict"] is True
            return httpx.Response(
                200,
                json={
                    "status": "completed",
                    "usage": {"input_tokens": 123, "output_tokens": 45},
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "output_text", "text": json.dumps(output)}],
                        }
                    ],
                },
            )
        if provider == "anthropic":
            assert str(request.url) == "https://api.anthropic.com/v1/messages"
            assert request.headers["x-api-key"] == "test-key"
            assert request.headers["anthropic-version"] == "2023-06-01"
            assert payload["max_tokens"] == 620
            assert payload["output_config"]["format"]["type"] == "json_schema"
            return httpx.Response(
                200,
                json={
                    "stop_reason": "end_turn",
                    "content": [{"type": "text", "text": json.dumps(output)}],
                },
            )
        if provider == "gemini":
            assert str(request.url).endswith("/models/test:generateContent")
            assert request.headers["x-goog-api-key"] == "test-key"
            assert payload["generationConfig"]["maxOutputTokens"] == 620
            assert payload["generationConfig"]["responseMimeType"] == "application/json"
            return httpx.Response(
                200,
                json={
                    "candidates": [
                        {
                            "finishReason": "STOP",
                            "content": {"parts": [{"text": json.dumps(output)}]},
                        }
                    ],
                },
            )
        assert payload["stream"] is False and payload["format"]["additionalProperties"] is False
        assert payload["think"] is False and payload["keep_alive"] == "15m"
        assert payload["options"]["num_predict"] == 620
        return httpx.Response(200, json={"done": True, "message": {"content": json.dumps(output)}})

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs),
    )
    result = await HttpSummaryProvider(settings).summarize(
        '{"g":[{"k":"g0","r":[["r0","Client","Note","2026-09-01T10:00Z","Done",null]]}]}'
    )
    assert result.batch.g[0].i == ["r0"] and len(seen) == 1
    if provider == "openai":
        assert result.usage == ProviderTokenUsage(input_tokens=123, output_tokens=45)


@pytest.mark.parametrize("limit", ["activities", "bytes", "departments"])
async def test_oversized_context_is_rejected_before_sending(
    populated: Team, api_client: AsyncClient, db_session: AsyncSession, simulated, limit: str
) -> None:
    for index in range(51 if limit == "activities" else 9):
        department_id = populated.department.id
        if limit == "departments":
            department = Department(
                organization_id=populated.client.organization_id,
                name=f"D{index}",
                normalized_name=f"d{index}",
            )
            db_session.add(department)
            await db_session.flush()
            department_id = department.id
        db_session.add(
            Activity(
                organization_id=populated.client.organization_id,
                client_id=populated.client.id,
                user_id=populated.users["owner"].id,
                assigned_to_user_id=populated.users["owner"].id,
                department_id=department_id,
                activity_type_id=activity_type_identifier(populated.client.organization_id, "nota"),
                description="x" * 4000 if limit == "bytes" else "Note",
                scheduled_for=datetime(2026, 9, 7, tzinfo=UTC).date(),
                status="COMPLETED",
                occurred_at=datetime(2026, 9, 7, tzinfo=UTC),
                completed_at=datetime(2026, 9, 7, tzinfo=UTC),
            )
        )
    await db_session.commit()
    headers = await login(api_client, populated.users["owner"])
    response = await api_client.post("/api/v1/ai/summaries", json=body(), headers=headers)
    assert response.status_code == 413, response.text
    assert simulated[0].calls == []
    assert not await db_session.scalar(select(AuditLog.id).where(AuditLog.action.like("AI_%")))


@pytest.mark.parametrize("failure", ["redirect", "json", "oversized", "incomplete", "schema"])
async def test_provider_discards_invalid_responses(
    monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    settings = Settings(
        _env_file=None, ai_provider="ollama", ai_model="test", ai_ollama_local_confirmed=True
    )
    calls = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if failure == "redirect":
            return httpx.Response(302, headers={"Location": "https://attacker.test"})
        if failure == "json":
            return httpx.Response(200, content="secret-provider-error")
        if failure == "oversized":
            return httpx.Response(200, content="x" * 65537)
        return httpx.Response(
            200,
            json={
                "done": failure != "incomplete",
                "message": {"content": '{"summary": "missing fields"}'},
            },
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs),
    )
    with pytest.raises(SummaryFailure) as caught:
        await HttpSummaryProvider(settings).summarize("{}")
    assert caught.value.code == (
        "AI_PROVIDER_UNAVAILABLE" if failure == "redirect" else "AI_INVALID_OUTPUT"
    )
    assert len(calls) == 1
