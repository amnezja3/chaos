import unittest
from pathlib import Path


class MapIncrementalRuntimeContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path("templates/map_template.html").read_text(encoding="utf-8")

    def section(self, start, end):
        return self.source[self.source.index(start):self.source.index(end)]

    def test_operations_reconcile_by_stable_id_without_clear_all(self):
        renderer = self.section(
            "window.renderActiveOperationMarkers = function",
            "window.notifyOperationLifecycle = function",
        )
        self.assertIn("operationClientId(operation)", renderer)
        self.assertIn("window.activeOperationMarkers.get(operationId)", renderer)
        self.assertIn("window.activeOperationMarkers.delete(operationId)", renderer)
        self.assertNotIn("window.clearActiveOperationLayers()", renderer)

    def test_operation_panel_mutates_clocks_and_only_changed_cards(self):
        renderer = self.section(
            "window.operationDomSignature = function",
            "window.clearActiveOperationLayers = function",
        )
        self.assertIn("data-operation-render-signature", renderer)
        self.assertIn("currentCard.dataset.operationRenderSignature", renderer)
        self.assertIn("currentCard.replaceWith(card)", renderer)
        self.assertIn("window.updateActiveOperationCountdowns", renderer)
        self.assertIn("activeTab === 'history'", renderer)

    def test_npc_icon_and_countdown_have_separate_update_paths(self):
        updater = self.section(
            "window.responseNpcIconSignature = function",
            "window.applyDetectionFeedbackToNpc = function",
        )
        self.assertIn("marker._responseNpcIconSignature !== signature", updater)
        self.assertIn("marker.setIcon", updater)
        self.assertIn("marker.setLatLng", updater)
        self.assertIn("marker._responseNpcCountdownSecond === second", updater)

        tick = self.section(
            "window.tickResponseNpcActors = function",
            "window.ensureResponseNpcAnimation = function",
        )
        self.assertIn("document.visibilityState === 'hidden'", tick)
        self.assertIn("paddedBounds.contains", tick)
        self.assertIn("window.runLocalDetectionProbe(now)", tick)
        self.assertNotIn("marker.setIcon", tick)

    def test_resize_and_ability_badge_avoid_periodic_rebuilds(self):
        invalidation = self.section(
            "function mapContainerPixelSize",
            "function clearZoomReturn",
        )
        self.assertIn("sizeKey === window.chaosMapLastInvalidatedSize", invalidation)
        self.assertIn("new ResizeObserver", invalidation)

        badge = self.section(
            "function renderGhostAbilityControl",
            "function scheduleGhostAbilityClock",
        )
        self.assertIn("control.dataset.renderKey === renderKey", badge)
        self.assertIn("existingTimer.textContent", badge)


if __name__ == "__main__":
    unittest.main()
