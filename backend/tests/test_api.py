import pytest
from django.test import Client, override_settings


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_health_endpoint():
    client = Client()
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
