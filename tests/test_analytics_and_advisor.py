from fastapi.testclient import TestClient


def _seed(client: TestClient, headers: dict[str, str]):
    client.post(
        "/api/v1/vault/assets",
        headers=headers,
        json={"category": "investment", "name": "Equity", "value_estimate": 6000, "currency": "USD"},
    )
    client.post(
        "/api/v1/vault/assets",
        headers=headers,
        json={"category": "crypto_wallet", "name": "BTC", "value_estimate": 4000, "currency": "USD"},
    )
    client.post(
        "/api/v1/beneficiaries",
        headers=headers,
        json={"full_name": "Heir", "email": "heir@example.com", "relationship": "child", "allocation_percent": 100},
    )
    client.post(
        "/api/v1/vault/documents",
        headers=headers,
        json={"title": "Will", "document_type": "will", "storage_object": "r2://b/w.pdf", "checksum": "abc123456789def0"},
    )


def test_analytics_endpoints(client: TestClient, auth_headers: dict[str, str]):
    _seed(client, auth_headers)

    distribution = client.get("/api/v1/analytics/asset-distribution", headers=auth_headers)
    assert distribution.status_code == 200
    dist = distribution.json()["data"]
    assert dist["total_value"] == 10000.0
    percents = {e["category"]: e["percent"] for e in dist["entries"]}
    assert percents["investment"] == 60
    assert percents["crypto_wallet"] == 40

    coverage = client.get("/api/v1/analytics/beneficiary-coverage", headers=auth_headers)
    assert coverage.json()["data"]["coverage_percent"] == 100

    readiness = client.get("/api/v1/analytics/readiness", headers=auth_headers)
    assert readiness.status_code == 200
    assert 0 <= readiness.json()["data"]["overall_score"] <= 100

    security = client.get("/api/v1/analytics/security-metrics", headers=auth_headers)
    assert security.json()["data"]["active_sessions"] >= 1


def test_advisor_recommendations_risk_and_chat(client: TestClient, auth_headers: dict[str, str]):
    # With an empty estate the advisor should recommend adding a beneficiary first.
    recs = client.get("/api/v1/ai-advisor/recommendations", headers=auth_headers)
    assert recs.status_code == 200
    titles = [item["title"] for item in recs.json()["data"]["items"]]
    assert any("beneficiary" in title.lower() for title in titles)

    _seed(client, auth_headers)
    risk = client.get("/api/v1/ai-advisor/risk-analysis", headers=auth_headers)
    assert risk.status_code == 200
    labels = {insight["label"] for insight in risk.json()["data"]["insights"]}
    assert "Asset volatility" in labels

    chat = client.post(
        "/api/v1/ai-advisor/chat",
        headers=auth_headers,
        json={"message": "How ready is my estate?"},
    )
    assert chat.status_code == 200
    assert "ready" in chat.json()["data"]["reply"].lower()
