"""Unit tests for the golden-path Python service routes."""

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


class TestRouter:
    def test_healthz_reports_ok(self):
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_hello_without_name_greets_world(self):
        response = client.get("/hello")
        assert response.status_code == 200
        assert response.json() == {"message": "hello, world"}

    def test_hello_with_name_greets_that_name(self):
        response = client.get("/hello?name=dhoclo")
        assert response.status_code == 200
        assert response.json() == {"message": "hello, dhoclo"}

    def test_unknown_path_is_404(self):
        response = client.get("/does-not-exist")
        assert response.status_code == 404

    def test_wrong_method_on_known_path_is_405(self):
        response = client.post("/hello")
        assert response.status_code == 405
