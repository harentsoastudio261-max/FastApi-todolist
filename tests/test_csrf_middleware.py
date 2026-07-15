"""Regression tests for the HTTP-wide CSRF boundary."""
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.csrf import CsrfMiddleware


class CsrfMiddlewareTests(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()

        # The test app proves the middleware guards writes without involving database services.
        app.add_middleware(CsrfMiddleware, cookie_name="csrf_token", header_name="X-CSRF-Token")

        @app.get("/read")
        def read() -> dict[str, bool]:
            return {"ok": True}

        @app.api_route("/write", methods=["POST", "PUT", "PATCH", "DELETE"])
        def write() -> dict[str, bool]:
            return {"ok": True}

        self.client = TestClient(app)

    def test_read_method_does_not_require_a_token(self) -> None:
        self.assertEqual(self.client.get("/read").status_code, 200)

    def test_write_method_rejects_a_missing_token(self) -> None:
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            with self.subTest(method=method):
                response = self.client.request(method, "/write")
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()["error"]["code"], "csrf_validation_failed")

    def test_write_method_rejects_a_mismatched_token(self) -> None:
        self.client.cookies.set("csrf_token", "cookie-token")
        response = self.client.post("/write", headers={"X-CSRF-Token": "header-token"})
        self.assertEqual(response.status_code, 403)

    def test_write_method_accepts_matching_cookie_and_header(self) -> None:
        self.client.cookies.set("csrf_token", "matching-token")
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            with self.subTest(method=method):
                response = self.client.request(method, "/write", headers={"X-CSRF-Token": "matching-token"})
                self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
