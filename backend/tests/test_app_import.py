"""Application import and route smoke tests."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_check() -> None:
    """The FastAPI app should initialize and expose health status."""
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_generate_and_verify_gracefully_flags_without_model_key() -> None:
    """The generate-and-verify endpoint should fail closed when no model key is configured."""
    client = TestClient(app)
    response = client.post(
        "/v1/recommendations/generate-and-verify",
        json={
            "patient_context": {"age": 67, "symptoms": ["chest pain"]},
            "clinical_question": "What should be the next step?",
            "metadata": {"case_id": "test-case"},
        },
    )

    assert response.status_code == 200
    assert response.json()["decision"] == "FLAG"


def test_validation_error_does_not_echo_request_body() -> None:
    """Validation errors should avoid echoing submitted clinical content."""
    client = TestClient(app)
    response = client.post(
        "/v1/recommendations/verify",
        json={
            "patient_context": {"age": 200},
            "clinical_question": "secret clinical detail",
            "recommendation": "secret recommendation",
        },
    )

    assert response.status_code == 422
    response_text = response.text
    assert "secret clinical detail" not in response_text
    assert "secret recommendation" not in response_text
