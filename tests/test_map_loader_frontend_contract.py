import unittest
from pathlib import Path


class MapLoaderFrontendContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map_template = Path("templates/map_template.html").read_text(encoding="utf-8")

    def test_map_loading_uses_glitch_overlay_contract(self):
        self.assertIn("chaos-map-glitch-overlay", self.map_template)
        self.assertIn("ensureMapGlitchOverlay", self.map_template)
        self.assertIn("pickMapGhostSystemLog", self.map_template)
        self.assertIn("GhostSystem 2108", self.map_template)
        self.assertIn("setMapLoadingIntensity", self.map_template)
        self.assertIn("seedMapGlitchBlocks", self.map_template)
        self.assertIn("chaos-map-glitch-block", self.map_template)
        self.assertIn("--glitch-color", self.map_template)
        self.assertIn("radial-gradient(circle at 50% 50%", self.map_template)
        self.assertIn("chaos-map-glitch-overlay.has-map-log::after", self.map_template)
        self.assertNotIn("chaos-map-sync-status__spinner", self.map_template)

    def test_map_loading_cleans_ready_state(self):
        self.assertIn("state.overlay.classList.remove('is-visible', 'is-slow', 'is-heavy', 'is-overloaded', 'has-map-log')", self.map_template)
        self.assertIn("state.startedAt = 0", self.map_template)
        self.assertIn("clearTimeout(state.heavyTimer)", self.map_template)
        self.assertIn("Boolean(window.mapBootState?.ready)", self.map_template)
        self.assertIn("!bootOverlay?.classList.contains('is-visible')", self.map_template)
        self.assertIn("inset: auto;", self.map_template)

    def test_map_loading_handles_slow_error_and_reduced_motion(self):
        self.assertIn("Siec przeciazona", self.map_template)
        self.assertIn("Blad ladowania", self.map_template)
        self.assertIn("is-heavy", self.map_template)
        self.assertIn("is-overloaded", self.map_template)
        self.assertIn("prefers-reduced-motion: reduce", self.map_template)

    def test_runtime_loading_effect_never_blocks_map_input(self):
        styles = self.map_template[
            self.map_template.index(".chaos-map-glitch-overlay {"):
            self.map_template.index(".chaos-map-glitch-field {")
        ]
        self.assertIn("pointer-events: none;", styles)
        self.assertNotIn("pointer-events: auto;", styles)

    def test_critical_boot_steps_retry_transient_failures(self):
        self.assertIn("waitForMapBootRetry", self.map_template)
        self.assertIn("options.critical ? 3 : 0", self.map_template)
        self.assertIn("isNarrowViewport ? 420000 : 300000", self.map_template)
        self.assertIn("Ponawiam:", self.map_template)
        self.assertIn("boot_attempt", self.map_template)

    def test_territory_tooltip_cleanup_does_not_break_map_boot(self):
        self.assertIn("function closeTerritoryTooltips()", self.map_template)
        self.assertIn("layer.isTooltipOpen()", self.map_template)
        self.assertNotIn("map.closeTooltip();", self.map_template)
        self.assertNotIn("layer.on('mouseout remove'", self.map_template)

    def test_leaflet_polyline_guard_skips_transient_invalid_renderer_bounds(self):
        self.assertIn("installLeafletPolylineBoundsGuard();", self.map_template)
        self.assertIn("function hasFiniteLeafletBounds(bounds)", self.map_template)
        self.assertIn("function installLeafletPolylineBoundsGuard()", self.map_template)
        self.assertIn("typeof proto._clipPoints !== 'function'", self.map_template)
        self.assertIn("!hasFiniteLeafletBounds(rendererBounds)", self.map_template)
        self.assertIn("!hasFiniteLeafletBounds(pixelBounds)", self.map_template)
        self.assertIn("this._parts = [];", self.map_template)

    def test_territory_polygons_bubble_contextmenu_to_empty_field_menu(self):
        style = self.map_template[
            self.map_template.index("function territoryLayerStyle"):
            self.map_template.index("function territoryTooltip")
        ]
        self.assertIn("interactive: true", style)
        self.assertIn("bubblingMouseEvents: true", style)
        self.assertNotIn("bubblingMouseEvents: false", style)
        self.assertGreaterEqual(
            self.map_template.count("interactive: true, bubblingMouseEvents: true"),
            2,
        )
        self.assertIn("map.on('contextmenu'", self.map_template)
        self.assertIn("showContextMenu(e.containerPoint.x", self.map_template)

    def test_travel_action_shows_destination_pulse_until_finished(self):
        self.assertIn("travel-destination-pulse", self.map_template)
        self.assertIn("showTravelDestinationPulse", self.map_template)
        self.assertIn("finishTravelPulse = showTravelDestinationPulse(lat, lng)", self.map_template)
        self.assertIn("typeof finishTravelPulse === 'function'", self.map_template)

    def test_motorcycle_travel_phone_preloader_contract(self):
        self.assertIn("motorcycle-phone-preloader", self.map_template)
        self.assertIn("is-travel-waiting", self.map_template)
        self.assertIn("showMotorcycleTravelPhone", self.map_template)
        self.assertIn("hideMotorcycleTravelPhone", self.map_template)
        self.assertIn("map_travel_request", self.map_template)
        self.assertIn("travel_id: travelId", self.map_template)
        self.assertIn("allowDuringMotion", self.map_template)
        self.assertIn("timeoutMs: 45000", self.map_template)
        self.assertIn("window.showMotorcycleTravelPhone", self.map_template)
        self.assertIn("waitForMotorcycleTravelPhoneFrame", self.map_template)
        self.assertIn("idleBeforeQueue", self.map_template)
        self.assertIn("movement_start", self.map_template)
        self.assertIn("chaos-phone-vibrate", self.map_template)
        self.assertIn("chaos-phone-ring", self.map_template)

    def test_motorcycle_travel_local_queue_contract(self):
        self.assertIn("shouldPlanTravelLocally", self.map_template)
        self.assertIn("planMotorcycleTravelLocally", self.map_template)
        self.assertIn("getMotorcyclePlannedPosition", self.map_template)
        self.assertIn("getTravelRangeMeters", self.map_template)
        self.assertIn("getTravelDistanceMeters", self.map_template)
        self.assertIn("pendingBackendTravelCommit", self.map_template)
        self.assertIn("flushMotorcycleTravelCommit", self.map_template)
        self.assertIn("route_commit: true", self.map_template)
        self.assertIn("route_waypoints", self.map_template)
        self.assertIn("localPlanned: true", self.map_template)
        self.assertIn("map_travel_local", self.map_template)
        self.assertIn("travelPulseCleanupById", self.map_template)
        self.assertIn("finishMotorcycleTravelPulse(point.travel_id)", self.map_template)
        self.assertIn("travelCommitSequence", self.map_template)
        self.assertIn("hasNewerLocalTravel", self.map_template)
        self.assertIn("updateMotorcycleConfirmedPositionMetadata", self.map_template)
        self.assertIn("activeLocalQueue && routeSnapshot", self.map_template)
        self.assertNotIn('"map_travel", "map_travel_local"].includes(String(source || ""))', self.map_template)
        travel_branch = self.map_template[
            self.map_template.index("async function mapAction("):
            self.map_template.index("const bikeDirectionIcons", self.map_template.index("async function mapAction("))
        ]
        self.assertIn("const localResult = planMotorcycleTravelLocally", travel_branch)
        self.assertIn("return localResult", travel_branch)
        self.assertNotIn("if (shouldPlanTravelLocally())", travel_branch)

    def test_motorcycle_icon_is_not_recreated_on_every_animation_step(self):
        start = self.map_template.index("async function animateAvatarTravel")
        end = self.map_template.index("window.motorcycleTravelState", start)
        animator = self.map_template[start:end]

        self.assertIn("window.avatarBikeDirection !== direction", animator)
        self.assertEqual(animator.count("marker.setIcon(buildBikeIcon(direction))"), 1)

    def test_hack_target_has_non_interactive_pending_marker(self):
        self.assertIn("pendingTargetMarker = L.circleMarker", self.map_template)
        self.assertIn("interactive: false", self.map_template)
        self.assertIn("pending-hack-target-marker", self.map_template)
        self.assertIn("removeMapLayerSafe(pendingTargetMarker)", self.map_template)

    def test_lightweight_target_path_runs_four_second_lore_show_after_success(self):
        self.assertIn("const secretPathLoreScenes = Object.freeze([", self.map_template)
        self.assertEqual(self.map_template.count("eyebrow: '"), 6)
        self.assertIn("function showSecretPathLore(target = {})", self.map_template)
        self.assertIn("}, 4000);", self.map_template)
        aim_start = self.map_template.index("async function aimMapTargetOnly")
        aim_end = self.map_template.index("function findClanVulnerabilityForTarget", aim_start)
        aim_branch = self.map_template[aim_start:aim_end]
        self.assertLess(aim_branch.index("if (!response.ok"), aim_branch.index("showSecretPathLore(data.target)"))
        self.assertNotIn("beginMapLoading", aim_branch)


if __name__ == "__main__":
    unittest.main()
