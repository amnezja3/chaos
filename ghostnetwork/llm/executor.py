"""Killable, sequential provider calls; no abandoned HTTP threads in the worker."""
import multiprocessing
import time

from .provider import NarrativeProviderError


def _child(pipe, provider, config, operation, package, policy):
    try:
        if provider == "ollama":
            from .ollama_provider import OllamaNarrativeProvider
            adapter = OllamaNarrativeProvider()
        else:
            from .mistral_provider import MistralNarrativeProvider
            adapter = MistralNarrativeProvider(config)
        result = adapter.generate(package, policy) if operation == "generate" else getattr(adapter, operation)()
        pipe.send((True, result))
    except NarrativeProviderError as exc:
        pipe.send((False, {"code": exc.code, "provider": provider,
            "retryable": exc.retryable, "http_status": exc.http_status, "retry_after": exc.retry_after}))
    except Exception:
        pipe.send((False, {"code": "provider_invalid_response", "provider": provider, "retryable": True}))
    finally:
        pipe.close()


def execute(provider, config, operation, package=None, policy=None, *, seconds, guard=lambda: True):
    end = time.monotonic() + seconds
    if seconds <= 0 or not guard():
        raise NarrativeProviderError("generation_cancelled", provider=provider, retryable=True)
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=_child, args=(child, provider, config, operation, package, policy), daemon=True)
    try:
        process.start()
        child.close()
        while True:
            remaining = end - time.monotonic()
            if remaining <= 0:
                raise NarrativeProviderError("provider_deadline", provider=provider, retryable=True)
            if not guard():
                raise NarrativeProviderError("generation_cancelled", provider=provider, retryable=True)
            if parent.poll(min(.2, remaining)):
                try:
                    ok, result = parent.recv()
                except EOFError:
                    raise NarrativeProviderError("provider_process_failed", provider=provider, retryable=True) from None
                if time.monotonic() >= end:
                    raise NarrativeProviderError("provider_deadline", provider=provider, retryable=True)
                if not guard():
                    raise NarrativeProviderError("generation_cancelled", provider=provider, retryable=True)
                if ok:
                    return result
                raise NarrativeProviderError(**result)
    finally:
        parent.close()
        child.close()
        if process.pid is not None:
            if process.is_alive():
                process.terminate()
            process.join(1)
            if process.is_alive():
                process.kill()
                process.join(1)
            process.close()
