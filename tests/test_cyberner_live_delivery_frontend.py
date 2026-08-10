import pathlib
import unittest


class CybernerLiveDeliveryFrontendContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = pathlib.Path("static/js/terminal.js").read_text(encoding="utf-8")

    def test_send_uses_stable_client_message_id(self):
        self.assertIn("client_message_id: pendingSend.clientMessageId", self.source)
        self.assertIn("crypto.randomUUID", self.source)
        self.assertIn("pendingSend = null", self.source)

    def test_live_message_is_deduplicated_and_rendered(self):
        self.assertIn("const messageStableId", self.source)
        self.assertIn("const appendCurrentMessage", self.source)
        self.assertIn("payload.message", self.source)
        self.assertIn("currentChatMatchesMessage", self.source)

    def test_recovery_does_not_overwrite_newer_delta(self):
        self.assertIn("latestMailDeltaVersion", self.source)
        self.assertIn("startedDeltaVersion < latestMailDeltaVersion", self.source)
        self.assertIn("mergeMessages(data.messages, currentMessages)", self.source)

    def test_refresh_has_single_flight_abort_and_recursive_timer(self):
        self.assertIn("if (state.inFlight) return state.inFlight", self.source)
        self.assertIn("if (state.inFlight && state.key === requestKey) return state.inFlight", self.source)
        self.assertIn("new AbortController()", self.source)
        self.assertIn("state.controller.abort()", self.source)
        self.assertIn("scheduleMailRefresh", self.source)
        self.assertNotIn("setInterval(refreshThreads, CYBERNER_THREAD_REFRESH_INTERVAL_MS)", self.source)


if __name__ == "__main__":
    unittest.main()
