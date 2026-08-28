from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from urllib.parse import urlparse

import requests

from .ollama_policy import (
    MAX_HTTP_RESPONSE_BYTES,
    MAX_MODEL_CONTENT_BYTES,
    MODEL_DIGEST,
    MODEL_NAME,
)


EXPECTED_BASE_URL = "http://127.0.0.1:11434"
EXPECTED_RUNTIME_VERSION = "0.15.4"


class OllamaClientError(RuntimeError):
    def __init__(self, code, message="", *, retryable=False, http_status=0):
        super().__init__(str(message or code))
        self.code = str(code or "ollama_error")
        self.retryable = bool(retryable)
        self.http_status = int(http_status or 0)


@dataclass(frozen=True)
class OllamaClientConfig:
    base_url: str = EXPECTED_BASE_URL
    model: str = MODEL_NAME
    model_digest: str = MODEL_DIGEST
    runtime_version: str = EXPECTED_RUNTIME_VERSION
    quantization: str = "Q4_K_M"
    num_ctx: int = 4096
    num_predict: int = 192
    temperature: float = 0.0
    keep_alive: str = "5m"
    connect_timeout_sec: float = 2.0
    read_timeout_sec: float = 120.0
    max_http_response_bytes: int = MAX_HTTP_RESPONSE_BYTES

    @classmethod
    def from_env(cls):
        return cls(
            base_url=os.environ.get("CHAOS_OLLAMA_BASE_URL", EXPECTED_BASE_URL),
            model=os.environ.get("CHAOS_OLLAMA_MODEL", MODEL_NAME),
            model_digest=os.environ.get("CHAOS_OLLAMA_MODEL_DIGEST", MODEL_DIGEST),
            runtime_version=os.environ.get(
                "CHAOS_OLLAMA_RUNTIME_VERSION", EXPECTED_RUNTIME_VERSION
            ),
            quantization=os.environ.get("CHAOS_OLLAMA_QUANTIZATION", "Q4_K_M"),
            num_ctx=int(os.environ.get("CHAOS_OLLAMA_NUM_CTX", "4096")),
            num_predict=int(os.environ.get("CHAOS_OLLAMA_NUM_PREDICT", "192")),
            temperature=float(os.environ.get("CHAOS_OLLAMA_TEMPERATURE", "0")),
            keep_alive=os.environ.get("CHAOS_OLLAMA_KEEP_ALIVE", "5m"),
            connect_timeout_sec=float(os.environ.get(
                "CHAOS_OLLAMA_CONNECT_TIMEOUT_SEC", "2"
            )),
            read_timeout_sec=float(os.environ.get(
                "CHAOS_OLLAMA_READ_TIMEOUT_SEC", "120"
            )),
            max_http_response_bytes=int(os.environ.get(
                "CHAOS_OLLAMA_MAX_HTTP_RESPONSE_BYTES",
                str(MAX_HTTP_RESPONSE_BYTES),
            )),
        )

    def validate(self):
        errors = []
        parsed = urlparse(str(self.base_url or ""))
        if (
            self.base_url.rstrip("/") != EXPECTED_BASE_URL
            or parsed.scheme != "http"
            or parsed.hostname != "127.0.0.1"
            or parsed.port != 11434
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            errors.append("ollama_base_url_not_loopback")
        if self.model != MODEL_NAME:
            errors.append("ollama_model_not_allowed")
        if self.model_digest != MODEL_DIGEST:
            errors.append("ollama_model_digest_not_allowed")
        if self.runtime_version != EXPECTED_RUNTIME_VERSION:
            errors.append("ollama_runtime_version_not_allowed")
        if self.quantization != "Q4_K_M":
            errors.append("ollama_quantization_not_allowed")
        if not 512 <= int(self.num_ctx) <= 4096:
            errors.append("ollama_num_ctx_out_of_policy")
        if not 128 <= int(self.num_predict) <= 192:
            errors.append("ollama_num_predict_out_of_policy")
        if float(self.temperature) != 0.0:
            errors.append("ollama_temperature_must_be_zero")
        if not 1024 <= int(self.max_http_response_bytes) <= MAX_HTTP_RESPONSE_BYTES:
            errors.append("ollama_response_limit_out_of_policy")
        return errors


@dataclass(frozen=True)
class OllamaGenerationResult:
    model: str
    model_digest: str
    runtime_version: str
    content: str
    done: bool
    done_reason: str
    total_duration_ns: int
    load_duration_ns: int
    prompt_eval_count: int
    eval_count: int
    raw_response_hash: str

    def as_dict(self):
        return {
            "model": self.model,
            "model_digest": self.model_digest,
            "runtime_version": self.runtime_version,
            "content": self.content,
            "done": self.done,
            "done_reason": self.done_reason,
            "total_duration_ns": self.total_duration_ns,
            "load_duration_ns": self.load_duration_ns,
            "prompt_eval_count": self.prompt_eval_count,
            "eval_count": self.eval_count,
            "raw_response_hash": self.raw_response_hash,
        }


class ChaosOllamaClient:
    def __init__(self, config=None, session=None):
        self.config = config or OllamaClientConfig.from_env()
        self.session = session or requests.Session()

    def _ensure_config(self):
        errors = self.config.validate()
        if errors:
            raise OllamaClientError(errors[0], ",".join(errors), retryable=False)

    def _url(self, path):
        return self.config.base_url.rstrip("/") + path

    def _bounded_json_response(self, response):
        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                if int(content_length) > self.config.max_http_response_bytes:
                    raise OllamaClientError(
                        "ollama_response_too_large", retryable=True,
                        http_status=response.status_code,
                    )
            except ValueError:
                pass
        chunks = []
        size = 0
        for chunk in response.iter_content(chunk_size=8192):
            if not chunk:
                continue
            size += len(chunk)
            if size > self.config.max_http_response_bytes:
                raise OllamaClientError(
                    "ollama_response_too_large", retryable=True,
                    http_status=response.status_code,
                )
            chunks.append(chunk)
        raw = b"".join(chunks)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise OllamaClientError(
                "ollama_invalid_http_json", str(exc)[:160], retryable=True,
                http_status=response.status_code,
            ) from exc
        return payload, raw

    @staticmethod
    def _http_retryable(status):
        return int(status or 0) in {404, 408, 409, 425, 429, 500, 502, 503, 504}

    def _request_json(self, method, path, payload=None, *, timeout=None):
        self._ensure_config()
        try:
            response = self.session.request(
                method,
                self._url(path),
                json=payload,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=timeout or (
                    self.config.connect_timeout_sec,
                    self.config.read_timeout_sec,
                ),
                stream=True,
            )
        except requests.Timeout as exc:
            raise OllamaClientError("ollama_timeout", str(exc)[:160], retryable=True) from exc
        except requests.RequestException as exc:
            raise OllamaClientError(
                "ollama_unreachable", str(exc)[:160], retryable=True
            ) from exc
        try:
            body, raw = self._bounded_json_response(response)
        finally:
            response.close()
        if not 200 <= int(response.status_code) < 300:
            message = body.get("error") if isinstance(body, dict) else ""
            raise OllamaClientError(
                f"ollama_http_{response.status_code}",
                str(message or "Ollama request failed")[:160],
                retryable=self._http_retryable(response.status_code),
                http_status=response.status_code,
            )
        if not isinstance(body, dict):
            raise OllamaClientError("ollama_response_not_object", retryable=True)
        return body, raw

    def verify(self):
        version, _raw = self._request_json("GET", "/api/version")
        runtime_version = str(version.get("version") or "").strip()
        tags, _raw = self._request_json("GET", "/api/tags")
        model = next((
            item for item in (tags.get("models") or [])
            if isinstance(item, dict)
            and str(item.get("model") or item.get("name") or "").strip() == self.config.model
        ), None)
        show, _raw = self._request_json(
            "POST", "/api/show", {"model": self.config.model, "verbose": False}
        )
        capabilities = set(show.get("capabilities") or [])
        details = show.get("details") if isinstance(show.get("details"), dict) else {}
        quantization = str(details.get("quantization_level") or "").strip()
        errors = []
        if runtime_version != self.config.runtime_version:
            errors.append("ollama_runtime_version_mismatch")
        if not model:
            errors.append("ollama_model_missing")
        elif str(model.get("digest") or "").strip() != self.config.model_digest:
            errors.append("ollama_model_digest_mismatch")
        if "completion" not in capabilities:
            errors.append("ollama_completion_capability_missing")
        if quantization != self.config.quantization:
            errors.append("ollama_quantization_mismatch")
        return {
            "ok": not errors,
            "errors": errors,
            "base_url": self.config.base_url,
            "runtime_version": runtime_version,
            "model": self.config.model,
            "model_digest": str((model or {}).get("digest") or ""),
            "capabilities": sorted(capabilities),
            "quantization": quantization,
        }

    def generate(self, task_package, policy):
        self._ensure_config()
        if policy.model_name != self.config.model or policy.model_digest != self.config.model_digest:
            raise OllamaClientError("ollama_task_model_policy_mismatch", retryable=False)
        payload = {
            "model": self.config.model,
            "stream": False,
            "think": False,
            "keep_alive": self.config.keep_alive,
            "messages": task_package["messages"],
            "format": task_package["format"],
            "options": {
                "temperature": self.config.temperature,
                "num_ctx": self.config.num_ctx,
                "num_predict": self.config.num_predict,
            },
        }
        body, raw = self._request_json("POST", "/api/chat", payload)
        message = body.get("message") if isinstance(body.get("message"), dict) else {}
        content = message.get("content")
        if body.get("done") is not True:
            raise OllamaClientError("ollama_generation_incomplete", retryable=True)
        if not isinstance(content, str) or not content.strip():
            raise OllamaClientError("ollama_empty_content", retryable=True)
        if len(content.encode("utf-8")) > MAX_MODEL_CONTENT_BYTES:
            raise OllamaClientError("ollama_content_too_large", retryable=True)
        response_model = str(body.get("model") or "").strip()
        if response_model != self.config.model:
            raise OllamaClientError("ollama_response_model_mismatch", retryable=False)
        return OllamaGenerationResult(
            model=response_model,
            model_digest=self.config.model_digest,
            runtime_version=self.config.runtime_version,
            content=content,
            done=True,
            done_reason=str(body.get("done_reason") or "")[:48],
            total_duration_ns=int(body.get("total_duration") or 0),
            load_duration_ns=int(body.get("load_duration") or 0),
            prompt_eval_count=int(body.get("prompt_eval_count") or 0),
            eval_count=int(body.get("eval_count") or 0),
            raw_response_hash=hashlib.sha256(raw).hexdigest(),
        )
