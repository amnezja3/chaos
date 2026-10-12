"""Compatibility adapter over the proven local client, with unchanged wire IO."""
from ..ollama_client import ChaosOllamaClient
from .provider import NarrativeGenerationResult


class OllamaNarrativeProvider:
    provider = "ollama"

    def __init__(self, config=None, session=None):
        self.client = ChaosOllamaClient(config=config, session=session)

    @property
    def config(self):
        return self.client.config

    @property
    def model_identity(self):
        return {"provider": self.provider, "model": self.config.model,
                "model_digest": self.config.model_digest}

    def verify(self):
        return {**self.client.verify(), "provider": self.provider}

    def generate(self, task_package, policy):
        result = self.client.generate(task_package, policy)
        return NarrativeGenerationResult(provider=self.provider,
            requested_model=self.config.model, **result.as_dict())
