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

    def test_world_players_are_not_classified_as_system_messages(self):
        self.assertIn('const systemSourceKeys = new Set([', self.source)
        self.assertIn('systemSourceKeys.has(sourceKey)', self.source)
        system_block = self.source.split("const systemSourceKeys = new Set([", 1)[1].split("]);", 1)[0]
        self.assertNotIn('"world"', system_block)
        self.assertNotIn('"clan"', system_block)

    def test_sidebar_uses_one_shared_scroll_container(self):
        self.assertIn('class="mail-sidebar-scroll"', self.source)
        self.assertGreaterEqual(self.source.count('class="mail-sidebar-section"'), 2)
        sidebar = self.source.split('<div class="mail-sidebar">', 1)[1].split('<div class="mail-main mail-chat">', 1)[0]
        self.assertLess(sidebar.index('mail-contact-search'), sidebar.index('mail-sidebar-scroll'))
        self.assertIn('<div class="mail-section-title">Znajomi</div>', sidebar)


if __name__ == "__main__":
    unittest.main()
