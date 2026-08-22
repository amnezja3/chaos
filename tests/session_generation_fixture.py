"""Test-only helpers for authenticated endpoint session generations."""

import tempfile
import uuid
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import run
from session_generation_store import SessionGenerationStore


class IsolatedFixtureSessionGenerationStore(SessionGenerationStore):
    """Keep precommit checks authoritative when fixtures use split databases."""

    def build_precommit_guard(self, lineage_secret, generation_secret, actor_username):
        expected_actor = str(actor_username or "").strip()

        def precommit_guard(*, conn, username, current_revision):
            del conn, username, current_revision
            self.assert_current(lineage_secret, generation_secret, expected_actor)

        return precommit_guard

    def build_transaction_precommit_guard(
        self,
        lineage_secret,
        generation_secret,
        actor_username,
    ):
        expected_actor = str(actor_username or "").strip()

        def precommit_guard(*, conn):
            del conn
            self.assert_current(lineage_secret, generation_secret, expected_actor)

        return precommit_guard


class SessionGenerationFixture:
    """Install an isolated durable store and seed matching cookie/header state."""

    def __init__(self, prefix="chaos_endpoint_session_"):
        self._tmp = tempfile.TemporaryDirectory(prefix=prefix)
        self._original_store = None
        self.store = IsolatedFixtureSessionGenerationStore(
            str(Path(self._tmp.name) / "session-generation.sqlite3")
        )

    def start(self):
        if self._original_store is None:
            self._original_store = run.session_generation_store
            run.session_generation_store = self.store
        return self

    def stop(self):
        if self._original_store is not None:
            run.session_generation_store = self._original_store
            self._original_store = None
        self._tmp.cleanup()

    def authenticate(self, client, username, *, generation=None):
        fixture_id = uuid.uuid4().hex
        generation = generation or f"fixture-generation-{fixture_id}"
        lineage = f"fixture-lineage-{fixture_id}"
        self.store.activate(
            lineage,
            generation,
            username,
            reason="authenticated_endpoint_fixture",
        )
        with client.session_transaction() as flask_session:
            flask_session["user"] = username
            flask_session[run.SESSION_LINEAGE_KEY] = lineage
            flask_session[run.SESSION_GENERATION_KEY] = generation
        environ_header = "HTTP_" + run.SESSION_GENERATION_HEADER.upper().replace("-", "_")
        client.environ_base[environ_header] = generation
        return {run.SESSION_GENERATION_HEADER: generation}

    @staticmethod
    def document_url(path, generation_headers):
        """Add the hashed bootstrap token required by authenticated documents."""
        generation = generation_headers[run.SESSION_GENERATION_HEADER]
        parts = urlsplit(path)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query["_session_generation"] = run._session_generation_query_token(generation)
        return urlunsplit((
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query),
            parts.fragment,
        ))
