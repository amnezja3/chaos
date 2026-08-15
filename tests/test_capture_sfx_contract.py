import unittest
from pathlib import Path


class CaptureSfxContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backend = Path("run.py").read_text(encoding="utf-8")
        cls.terminal = Path("static/js/terminal.js").read_text(encoding="utf-8")

    def test_backend_publishes_stable_capture_version(self):
        self.assertIn('captured_target["capture_version"] = hashlib.sha1(', self.backend)
        self.assertIn('payload["captured"] = True', self.backend)
        self.assertIn('change_type="map.target_captured"', self.backend)

    def test_response_and_delta_share_one_capture_player(self):
        self.assertGreaterEqual(
            self.terminal.count("playAuthoritativeCaptureSfx(data.captured_target)"), 2
        )
        self.assertIn('String(event.type || "") === "map.target_captured"', self.terminal)
        self.assertIn("playAuthoritativeCaptureSfx(payload.target || payload.captured_target || {})", self.terminal)
        self.assertIn('event_id: `target-captured:${targetId}:${captureVersion}`', self.terminal)

    def test_variants_are_based_only_on_canonical_payload(self):
        self.assertIn('role === "pillar"', self.terminal)
        self.assertIn('"capture.conflict_pillar"', self.terminal)
        self.assertIn('"capture.target"', self.terminal)
        helper = self.terminal.split("function playAuthoritativeCaptureSfx", 1)[1].split(
            "function playAuthoritativeConflictResolvedSfx", 1
        )[0]
        self.assertNotIn('role === "inner"', helper)

    def test_conflict_resolution_comes_from_canonical_delta(self):
        self.assertIn('String(event.type || "") === "territory.conflict_changed"', self.terminal)
        self.assertIn('String(payload.status || "").toLowerCase() !== "resolved"', self.terminal)
        self.assertIn('"capture.conflict_resolved"', self.terminal)
        self.assertIn('event_id: `conflict-resolved:${conflictId}:${version}`', self.terminal)

    def test_recovery_is_explicitly_silent(self):
        self.assertIn("if (options.recovery === true) return false", self.terminal)
        self.assertIn("if (payload.recovery_required === true) return false", self.terminal)


if __name__ == "__main__":
    unittest.main()
