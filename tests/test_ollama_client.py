import json
import unittest

import requests

from ghostnetwork.ollama_client import (
    ChaosOllamaClient,
    OllamaClientConfig,
    OllamaClientError,
)
from ghostnetwork.ollama_policy import (
    assign_ollama_task_policy,
    build_ollama_task_package,
    resolve_ollama_task_policy,
)


class FakeResponse:
    def __init__(self, payload, status=200, content_length=None):
        self.raw = json.dumps(payload).encode("utf-8")
        self.status_code = status
        self.headers = {}
        if content_length is not None:
            self.headers["Content-Length"] = str(content_length)
        self.closed = False

    def iter_content(self, chunk_size=8192):
        for offset in range(0, len(self.raw), chunk_size):
            yield self.raw[offset:offset + chunk_size]

    def close(self):
        self.closed = True


class FakeSession:
    def __init__(self, responses=None, error=None):
        self.responses = list(responses or [])
        self.error = error
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if self.error:
            raise self.error
        return self.responses.pop(0)


class OllamaClientTest(unittest.TestCase):
    def package(self):
        task = assign_ollama_task_policy({
            "source_scope": "blacknet_world",
            "task_variant": "world_digest",
            "target_medium": "blacknet",
            "audience_scope": "public",
            "truth_class_policy": "canonical_facts_only",
            "facts": [{"fact_id": "fact-1", "fact_type": "test"}],
            "allowed_actions": [],
        })
        policy = resolve_ollama_task_policy("blacknet_world", "world_digest", "blacknet")
        return build_ollama_task_package(task, policy), policy

    def test_generate_uses_local_chat_without_tools_and_with_fixed_options(self):
        response = FakeResponse({
            "model": "llama3.1:8b",
            "message": {"role": "assistant", "content": json.dumps({
                "title": "T", "body": "B", "tone": "info",
                "fact_refs": ["fact-1"], "cta_ref": None,
            })},
            "done": True,
            "done_reason": "stop",
        })
        session = FakeSession([response])
        client = ChaosOllamaClient(session=session)
        package, policy = self.package()
        result = client.generate(package, policy)

        self.assertEqual(result.model, "llama3.1:8b")
        method, url, kwargs = session.calls[0]
        self.assertEqual((method, url), ("POST", "http://127.0.0.1:11434/api/chat"))
        self.assertFalse(kwargs["json"]["stream"])
        self.assertFalse(kwargs["json"]["think"])
        self.assertNotIn("tools", kwargs["json"])
        self.assertEqual(kwargs["json"]["options"]["num_ctx"], 4096)
        self.assertEqual(kwargs["json"]["options"]["num_predict"], 192)

    def test_non_loopback_config_and_oversized_response_fail_closed(self):
        config = OllamaClientConfig(base_url="http://example.test:11434")
        client = ChaosOllamaClient(config=config, session=FakeSession([]))
        package, policy = self.package()
        with self.assertRaisesRegex(OllamaClientError, "ollama_base_url_not_loopback"):
            client.generate(package, policy)

        oversized = FakeResponse({}, content_length=70000)
        client = ChaosOllamaClient(session=FakeSession([oversized]))
        with self.assertRaisesRegex(OllamaClientError, "ollama_response_too_large"):
            client.generate(package, policy)

    def test_timeout_is_retryable_and_response_model_is_pinned(self):
        package, policy = self.package()
        timeout_client = ChaosOllamaClient(session=FakeSession(error=requests.Timeout("slow")))
        with self.assertRaises(OllamaClientError) as raised:
            timeout_client.generate(package, policy)
        self.assertTrue(raised.exception.retryable)

        response = FakeResponse({
            "model": "other:model",
            "message": {"content": "{}"},
            "done": True,
        })
        pinned_client = ChaosOllamaClient(session=FakeSession([response]))
        with self.assertRaisesRegex(OllamaClientError, "ollama_response_model_mismatch"):
            pinned_client.generate(package, policy)

    def test_verify_pins_runtime_digest_quantization_and_completion_capability(self):
        digest = OllamaClientConfig().model_digest
        session = FakeSession([
            FakeResponse({"version": "0.15.4"}),
            FakeResponse({"models": [{"model": "llama3.1:8b", "digest": digest}]}),
            FakeResponse({
                "capabilities": ["completion"],
                "details": {"quantization_level": "Q4_K_M"},
            }),
        ])
        result = ChaosOllamaClient(session=session).verify()
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["quantization"], "Q4_K_M")

        bad_session = FakeSession([
            FakeResponse({"version": "0.15.4"}),
            FakeResponse({"models": [{"model": "llama3.1:8b", "digest": "bad"}]}),
            FakeResponse({"capabilities": [], "details": {"quantization_level": "Q8_0"}}),
        ])
        bad = ChaosOllamaClient(session=bad_session).verify()
        self.assertFalse(bad["ok"])
        self.assertEqual(set(bad["errors"]), {
            "ollama_completion_capability_missing",
            "ollama_model_digest_mismatch",
            "ollama_quantization_mismatch",
        })


if __name__ == "__main__":
    unittest.main()
