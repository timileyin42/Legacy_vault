from fastapi.testclient import TestClient


def test_legacy_note_lifecycle_and_scheduling(client: TestClient, auth_headers: dict[str, str]):
    create = client.post(
        "/api/v1/legacy/notes",
        headers=auth_headers,
        json={
            "title": "Birthday Note",
            "body": "Happy birthday, my child.",
            "media_type": "written",
            "release_trigger": "event",
        },
    )
    assert create.status_code == 200
    note = create.json()["data"]
    assert note["status"] == "scheduled"
    assert note["release_trigger"] == "event"
    # Note body is encrypted at rest but returned to its owner.
    assert "Happy birthday" in create.text

    listed = client.get("/api/v1/legacy/notes", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()["data"]) == 1

    scheduled = client.get("/api/v1/legacy/notes/scheduled", headers=auth_headers)
    assert len(scheduled.json()["data"]) == 1

    updated = client.put(
        f"/api/v1/legacy/notes/{note['id']}",
        headers=auth_headers,
        json={"title": "Final Directive"},
    )
    assert updated.json()["data"]["title"] == "Final Directive"

    assert client.delete(f"/api/v1/legacy/notes/{note['id']}", headers=auth_headers).status_code == 200
    assert client.get(f"/api/v1/legacy/notes/{note['id']}", headers=auth_headers).status_code == 404


def test_legacy_memories(client: TestClient, auth_headers: dict[str, str]):
    create = client.post(
        "/api/v1/legacy/memories",
        headers=auth_headers,
        json={"caption": "Family holiday", "storage_object": "r2://bucket/photo.jpg", "content_type": "image/jpeg"},
    )
    assert create.status_code == 200
    assert "r2://bucket/photo.jpg" not in create.text

    listed = client.get("/api/v1/legacy/memories", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json()["data"][0]["caption"] == "Family holiday"
