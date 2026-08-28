"""
NetPulse HTTP Networking Engine.

Provides an HTTPClient wrapping requests.Session with connection pooling, timeout handling,
latency measurement, and an embedded multi-threaded HTTPServer for local offline testing.
"""

from http.server import HTTPServer as BaseHTTPServer, BaseHTTPRequestHandler
import json
from socketserver import ThreadingMixIn
import threading
import time
from typing import Any, Dict, Optional
import urllib.parse

import requests
from requests.adapters import HTTPAdapter
from requests.structures import CaseInsensitiveDict
from urllib3.util.retry import Retry

from app.core.exceptions import (
    ConnectionError as NetPulseConnectionError,
    TimeoutError as NetPulseTimeoutError,
    PacketValidationError,
    ServerLifecycleError,
)
from app.core.logging import get_logger

logger = get_logger("http")


class HTTPResponse:
    """Standardized HTTP response container with timing and payload helpers."""

    def __init__(self, raw_response: requests.Response, duration_ms: float):
        self.raw = raw_response
        self.status_code = raw_response.status_code
        self.headers = CaseInsensitiveDict(raw_response.headers)
        self.content = raw_response.content
        self.text = raw_response.text
        self.duration_ms = duration_ms
        self.url = raw_response.url

    def json(self) -> Any:
        """Parse response body as JSON."""
        try:
            return self.raw.json()
        except Exception as e:
            raise PacketValidationError(f"Response is not valid JSON: {e}", actual=self.text) from e

    def __repr__(self) -> str:
        return f"<HTTPResponse [{self.status_code}] {self.duration_ms:.2f}ms>"


class HTTPClient:
    """
    Client for executing and validating HTTP requests with session reuse and latency metrics.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 5.0,
        headers: Optional[Dict[str, str]] = None,
        retries: int = 0
    ):
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.timeout = timeout
        self.session = requests.Session()

        if headers:
            self.session.headers.update(headers)

        if retries > 0:
            retry_strategy = Retry(
                total=retries,
                backoff_factor=0.2,
                status_forcelist=[500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)

    def _resolve_url(self, endpoint: str) -> str:
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        if not self.base_url:
            return endpoint
        return f"{self.base_url}/{endpoint.lstrip('/')}"

    def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        json_data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> HTTPResponse:
        """Execute an HTTP request and measure round-trip duration."""
        url = self._resolve_url(endpoint)
        effective_timeout = timeout if timeout is not None else self.timeout

        start = time.perf_counter()
        try:
            raw = self.session.request(
                method=method.upper(),
                url=url,
                params=params,
                data=data,
                json=json_data,
                headers=headers,
                timeout=effective_timeout
            )
            duration_ms = (time.perf_counter() - start) * 1000.0
            response = HTTPResponse(raw, duration_ms)
            logger.debug(
                f"HTTP {method.upper()} {url} -> {response.status_code} ({duration_ms:.2f}ms)",
                extra={"protocol": "HTTP", "duration_ms": duration_ms, "status": str(response.status_code)}
            )
            return response
        except requests.exceptions.Timeout as e:
            duration_ms = (time.perf_counter() - start) * 1000.0
            raise NetPulseTimeoutError(
                f"HTTP request to {url} timed out after {effective_timeout}s",
                timeout_seconds=effective_timeout
            ) from e
        except requests.exceptions.ConnectionError as e:
            duration_ms = (time.perf_counter() - start) * 1000.0
            raise NetPulseConnectionError(f"HTTP connection failed for {url}: {e}") from e
        except requests.exceptions.RequestException as e:
            duration_ms = (time.perf_counter() - start) * 1000.0
            raise NetPulseConnectionError(f"HTTP request error for {url}: {e}") from e

    def get(self, endpoint: str, **kwargs: Any) -> HTTPResponse:
        return self.request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs: Any) -> HTTPResponse:
        return self.request("POST", endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs: Any) -> HTTPResponse:
        return self.request("PUT", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs: Any) -> HTTPResponse:
        return self.request("DELETE", endpoint, **kwargs)

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "HTTPClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


class ThreadingHTTPServer(ThreadingMixIn, BaseHTTPServer):
    """Multi-threaded HTTP Server for testing."""
    daemon_threads = True


class LocalHTTPRequestHandler(BaseHTTPRequestHandler):
    """
    Standard test request handler implementing common testing endpoints.
    """

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress standard logging to keep test output clean
        pass

    def _send_json(self, status_code: int, payload: Any, extra_headers: Optional[Dict[str, str]] = None) -> None:
        try:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Server", "NetPulse-Mock-HTTP")
            if extra_headers:
                for k, v in extra_headers.items():
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass

    def _send_text(self, status_code: int, text: str, extra_headers: Optional[Dict[str, str]] = None) -> None:
        try:
            body = text.encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Server", "NetPulse-Mock-HTTP")
            if extra_headers:
                for k, v in extra_headers.items():
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path in ("/", "/health"):
            self._send_json(200, {"status": "ok", "message": "NetPulse HTTP Test Server"})
        elif path == "/get":
            self._send_json(200, {
                "method": "GET",
                "args": query,
                "headers": dict(self.headers),
                "url": self.path
            })
        elif path == "/json":
            self._send_json(200, {
                "id": 1001,
                "name": "netpulse-probe",
                "active": True,
                "protocols": ["tcp", "udp", "http"]
            })
        elif path == "/headers":
            self._send_json(200, dict(self.headers))
        elif path.startswith("/delay/"):
            try:
                delay_sec = float(path.split("/delay/")[1])
                time.sleep(delay_sec)
                self._send_json(200, {"delayed": delay_sec})
            except Exception as e:
                self._send_json(400, {"error": f"Invalid delay: {e}"})
        elif path.startswith("/status/"):
            try:
                code = int(path.split("/status/")[1])
                self._send_json(code, {"code": code, "status": "custom status response"})
            except Exception as e:
                self._send_json(400, {"error": f"Invalid status code: {e}"})
        else:
            self._send_json(404, {"error": "Not Found", "path": path})

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b""

        body_json = None
        if "application/json" in self.headers.get("Content-Type", ""):
            try:
                body_json = json.loads(raw_body.decode("utf-8"))
            except Exception:
                body_json = None

        if path in ("/post", "/upload"):
            self._send_json(200, {
                "method": "POST",
                "path": path,
                "headers": dict(self.headers),
                "json": body_json,
                "data": raw_body.decode("utf-8", errors="replace"),
                "size": len(raw_body)
            })
        elif path.startswith("/status/"):
            try:
                code = int(path.split("/status/")[1])
                self._send_json(code, {"code": code, "received_bytes": len(raw_body)})
            except Exception as e:
                self._send_json(400, {"error": f"Invalid status code: {e}"})
        else:
            self._send_json(404, {"error": "Not Found", "path": path})


class HTTPServer:
    """
    Lightweight, thread-safe embedded HTTP test server for local automated test suites.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.host = host
        self.requested_port = port
        self.port = port
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._is_running = threading.Event()

    @property
    def is_running(self) -> bool:
        return self._is_running.is_set()

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def start(self) -> "HTTPServer":
        if self.is_running:
            return self

        try:
            self._server = ThreadingHTTPServer((self.host, self.requested_port), LocalHTTPRequestHandler)
            self.port = self._server.server_address[1]
            self._is_running.set()

            self._thread = threading.Thread(
                target=self._server.serve_forever,
                daemon=True,
                name=f"HTTPServer-{self.port}"
            )
            self._thread.start()
            logger.info(f"HTTPServer started on {self.url}")
            return self
        except Exception as e:
            self.stop()
            raise ServerLifecycleError(f"Failed to start HTTPServer on {self.host}:{self.requested_port}: {e}") from e

    def stop(self) -> None:
        self._is_running.clear()
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info(f"HTTPServer on port {self.port} stopped cleanly")

    def __enter__(self) -> "HTTPServer":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False
