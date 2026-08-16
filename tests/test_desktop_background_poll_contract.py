import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DesktopBackgroundPollContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "static" / "js" / "terminal.js").read_text(encoding="utf-8")

    def test_background_fetch_has_abort_timeout(self):
        self.assertIn("function fetchDesktopBackground", self.source)
        self.assertIn("controller.abort()", self.source)
        self.assertIn("fetchDesktopBackground(`/api/state/changes?", self.source)

    def test_system_message_poll_cannot_overlap(self):
        self.assertIn("let systemMessagesPollInFlight = false", self.source)
        self.assertIn("if (!desktopSessionActive || systemMessagesPollInFlight) return", self.source)
        self.assertIn("fetchDesktopBackground('/system-messages')", self.source)

    def test_launch_queue_poll_is_bounded(self):
        self.assertIn("fetchDesktopBackground('/launch-queue'", self.source)
        self.assertIn("LAUNCH_QUEUE_FETCH_TIMEOUT_MS", self.source)


if __name__ == "__main__":
    unittest.main()
