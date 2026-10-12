"""Provider-neutral generation boundary; narrative validation stays in the worker."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol, runtime_checkable


class NarrativeProviderError(RuntimeError):
    def __init__(self, code, message="", *, provider="", retryable=False,
                 http_status=0, retry_after=None):
        super().__init__(str(message or code))
        self.code = str(code or "provider_error")
        self.provider = str(provider)
        self.retryable = bool(retryable)
        self.http_status = int(http_status or 0)
        self.retry_after = retry_after


@dataclass(frozen=True)
class NarrativeGenerationResult:
    provider: str
    model: str
    content: str
    done: bool
    done_reason: str
    raw_response_hash: str
    requested_model: str = ""
    request_id: str = ""
    total_duration_ns: int = 0
    prompt_eval_count: int | None = None
    eval_count: int | None = None
    # Compatibility fields for existing persistence. External adapters leave
    # these empty, rather than claiming a local runtime/digest they did not use.
    model_digest: str = ""
    runtime_version: str = ""
    load_duration_ns: int = 0

    def as_dict(self):
        return asdict(self)


@runtime_checkable
class NarrativeProvider(Protocol):
    provider: str

    @property
    def model_identity(self) -> dict: ...

    def verify(self) -> dict: ...

    def generate(self, task_package, policy) -> NarrativeGenerationResult: ...


def create_narrative_provider(provider="ollama", *, config=None, session=None, db_path=None):
    """Explicit factory; an unknown provider must never silently route elsewhere."""
    if db_path is not None:
        from .router import NarrativeRouter
        return NarrativeRouter(db_path)
    if provider == "mistral":
        from .mistral_provider import MistralNarrativeProvider
        return MistralNarrativeProvider(config, session=session)
    if provider == "ollama":
        from .ollama_provider import OllamaNarrativeProvider
        return OllamaNarrativeProvider(config=config, session=session)
    raise NarrativeProviderError("provider_not_supported", provider=provider)
