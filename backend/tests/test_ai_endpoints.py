import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ai_chat_endpoint():
    response = client.post("/api/ai/chat", json={"message": "What is the solar forecast?"})
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "model" in data
    assert len(data["response"]) > 0


def test_ai_briefing_endpoint():
    response = client.get("/api/ai/briefing")
    assert response.status_code == 200
    data = response.json()
    assert "briefing" in data
    assert "model" in data
    assert len(data["briefing"]) > 0
