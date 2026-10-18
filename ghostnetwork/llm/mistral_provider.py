"""Bounded REST adapter. Secrets never enter results, URLs or exception text."""
import hashlib
import json
import os
import time
from email.utils import parsedate_to_datetime

import requests

from .provider import NarrativeGenerationResult, NarrativeProviderError

ENDPOINT = "https://api.mistral.ai/v1"
MAX_BYTES = 262144


def data_review_approved():
    """Explicit operator release after reviewing the account's API data terms."""
    return os.environ.get('CHAOS_MISTRAL_DATA_REVIEW_APPROVED', '').strip() == '1'


def secret_configured():
    return bool(os.environ.get("CHAOS_MISTRAL_API_KEY", "").strip())


def generation_messages(package):
    # Mistral rejected our canonical schema in constrained-decoding mode
    # (HTTP 400/3051). JSON mode plus full instructions preserves the contract;
    # the unchanged CHAOS validator remains authoritative for acceptance.
    messages = [dict(message) for message in package["messages"]]
    if isinstance(package.get("format"), dict):
        instruction = (
            "\n\nReturn only a JSON object matching the following JSON Schema. "
            "Include every required field and no extra fields. Follow all "
            "types, enums, length limits and reference constraints. This is "
            "the output contract, not source facts to narrate:\n"
            + json.dumps(package["format"], ensure_ascii=False, separators=(",", ":"))
        )
        if messages and messages[0].get("role") == "system":
            messages[0]["content"] += instruction
        else:
            messages.insert(0, {"role": "system", "content": instruction.strip()})
    return messages


def token_reservation(package, max_tokens):
    return max_tokens + 128 + sum(
        len(str(m.get("content", "")).encode("utf-8")) for m in generation_messages(package)
    )


class MistralNarrativeProvider:
    provider = "mistral"

    def __init__(self, config, session=None):
        self.config = config
        self.session = session or requests.Session()

    @property
    def model_identity(self):
        return {"provider": self.provider, "model": self.config["model"], "model_digest": ""}

    def request(self, method, path, payload=None):
        # Free-text facts may identify players. Do not guess anonymity from a
        # public audience or field names. Block all generation until reviewed.
        if method.upper() != 'GET' and not data_review_approved():
            raise NarrativeProviderError('mistral_data_review_required', provider=self.provider)
        key = os.environ.get("CHAOS_MISTRAL_API_KEY", "").strip()
        if not key:
            raise NarrativeProviderError("mistral_secret_missing", provider=self.provider)
        response = None
        try:
            response = self.session.request(method, ENDPOINT + path, json=payload,
                headers={"Authorization": "Bearer " + key, "Accept": "application/json"},
                timeout=(3, self.config["remote_seconds"]), stream=True, allow_redirects=False)
            status = response.status_code
            if status != 200:
                error_code = f"mistral_http_{status}"
                # Only recognize a closed vocabulary; never propagate arbitrary
                # API error bodies to persistence, admin responses or logs.
                bounded = bytearray()
                for chunk in response.iter_content(4096):
                    bounded.extend(chunk)
                    if len(bounded) > 8192:
                        break
                try:
                    error_body = json.loads(bounded)
                    error_data = error_body.get('error',error_body)
                    code = error_data.get('code') if isinstance(error_data,dict) else None
                    if code in {'insufficient_quota','quota_exceeded','billing_limit_exceeded','credits_exhausted'}:
                        error_code = 'mistral_quota_exhausted'
                except (ValueError,TypeError,AttributeError):
                    pass
                retry_after = None
                raw_retry = response.headers.get("Retry-After", "")
                try:
                    retry_after = max(0, float(raw_retry))
                except (ValueError, TypeError):
                    try:
                        retry_after = max(0, parsedate_to_datetime(raw_retry).timestamp() - time.time())
                    except (ValueError, TypeError, OverflowError):
                        pass
                # Do not log the provider body: it may reflect credentials/input.
                raise NarrativeProviderError(error_code, provider=self.provider,
                    http_status=status, retryable=status in {408, 409, 429} or status >= 500,
                    retry_after=retry_after)
            chunks, size = [], 0
            for chunk in response.iter_content(8192):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise NarrativeProviderError("mistral_response_too_large", provider=self.provider, retryable=True)
                chunks.append(chunk)
            raw = b"".join(chunks)
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError()
            return data, hashlib.sha256(raw).hexdigest()
        except requests.RequestException:
            raise NarrativeProviderError("mistral_transport_error", provider=self.provider, retryable=True) from None
        except (ValueError, UnicodeError):
            raise NarrativeProviderError("mistral_invalid_response", provider=self.provider, retryable=True) from None
        finally:
            if response is not None:
                response.close()

    def list_models(self):
        data, _ = self.request("GET", "/models")
        return sorted({item["id"] for item in data.get("data", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
            and item.get("capabilities", {}).get("completion_chat") is True})[:500]

    def verify(self):
        models = self.list_models()
        ok = self.config["model"] in models
        return {"ok": ok, "provider": self.provider, "model": self.config["model"],
                "errors": [] if ok else ["mistral_model_unavailable"]}

    def generate(self, package, policy):
        started = time.monotonic()
        data, digest = self.request("POST", "/chat/completions", {
            "model": self.config["model"], "messages": generation_messages(package),
            "stream": False, "n": 1, "temperature": 0,
            "max_tokens": self.config["max_tokens"], "response_format": {"type": "json_object"},
        })
        choices = data.get("choices")
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
            raise NarrativeProviderError("mistral_missing_choice", provider=self.provider, retryable=True)
        choice = choices[0]
        reason = choice.get("finish_reason")
        if reason != "stop":
            raise NarrativeProviderError("mistral_truncated" if reason == "length" else "mistral_incomplete",
                                         provider=self.provider, retryable=True)
        content = (choice.get("message") or {}).get("content")
        if isinstance(content, list):
            if any(not isinstance(c, dict) or c.get("type") != "text" or not isinstance(c.get("text"), str) for c in content):
                raise NarrativeProviderError("mistral_nontext_content", provider=self.provider, retryable=True)
            content = "".join(c["text"] for c in content)
        if not isinstance(content, str) or not content.strip() or len(content.encode()) > 16384:
            raise NarrativeProviderError("mistral_invalid_content", provider=self.provider, retryable=True)
        model = data.get("model")
        if not isinstance(model, str) or not model:
            raise NarrativeProviderError("mistral_missing_model", provider=self.provider, retryable=True)
        usage = data.get("usage") or {}
        def tokens(key):
            value = usage.get(key)
            return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None
        return NarrativeGenerationResult(provider=self.provider, model=model[:160],
            requested_model=self.config["model"], request_id=str(data.get("id") or "")[:256],
            content=content, done=True, done_reason=reason, raw_response_hash=digest,
            total_duration_ns=int((time.monotonic() - started) * 1e9),
            prompt_eval_count=tokens("prompt_tokens"), eval_count=tokens("completion_tokens"))
