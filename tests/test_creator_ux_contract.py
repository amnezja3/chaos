import pathlib
import subprocess
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class CreatorUxContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "static" / "js" / "terminal.js").read_text(encoding="utf-8")
        cls.styles = (ROOT / "static" / "css" / "style.css").read_text(encoding="utf-8")

    def test_shared_descriptor_catalog_covers_creator_contract_fields(self):
        self.assertIn("const CREATOR_OPTION_CATALOG", self.source)
        for field in ("map_actions", "operation_types", "resource_types", "target_types"):
            self.assertIn(f'{field}: CREATOR_', self.source)
        for key in ("scan_ports", "exploit", "sniff", "trace"):
            self.assertIn(f'{key}:', self.source)

    def test_creator_uses_shared_off_on_toggle_without_changing_checkbox_values(self):
        self.assertIn('class="appforge-check creator-toggle"', self.source)
        self.assertIn('type="checkbox" value="${escapeHTML(key)}"', self.source)
        self.assertIn("function syncCreatorToggle", self.source)

    def test_icon_picker_replaces_value_and_validates_one_grapheme(self):
        self.assertIn("function creatorIconGraphemes", self.source)
        self.assertIn("function validateCreatorIcon", self.source)
        self.assertIn("input.value = icon;", self.source)

    def test_options_are_grouped_semantically_without_changing_runtime_keys(self):
        self.assertIn("const CREATOR_SEMANTIC_GROUPS", self.source)
        self.assertIn('location: ["gps_logs", "location_history"', self.source)
        self.assertIn('data-creator-option-group=', self.source)
        self.assertIn('constraints: Object.freeze({ serialized_value: key })', self.source)

    def test_filters_follow_family_target_and_selected_map_action(self):
        self.assertIn("const CREATOR_ACTION_FILTERS", self.source)
        self.assertIn("function collectCreatorActionFilters", self.source)
        self.assertIn('selectedCreatorOptions(term, "map_actions")', self.source)
        self.assertIn("if (input.checked) clearedCount += 1", self.source)
        self.assertIn('data-creator-filter-status role="status" aria-live="polite"', self.source)

    def test_risk_questions_keep_existing_contract_fields(self):
        mappings = {
            "Z czym może kolidować?": "interferes_with",
            "Co musi być wyłączone na celu?": "requires_off",
            "Co narzędzie może wyłączyć?": "disables",
            "Na co wpływa po stronie gracza?": "affects",
        }
        for label, field in mappings.items():
            self.assertIn(label, self.source)
            self.assertIn(f'creatorCheckboxGroup(keys, "{field}")', self.source)

    def test_preview_separates_player_summary_from_raw_contract(self):
        self.assertIn("data-creator-player-summary", self.source)
        self.assertIn("Pokaż techniczny kontrakt JSON", self.source)
        self.assertIn("creatorOptionDescriptor(fieldName, value).label", self.source)

    def test_context_validation_routes_user_to_repair_step(self):
        self.assertIn("function validateCreatorContext", self.source)
        self.assertIn("Krok 3 · Cel", self.source)
        self.assertIn("Krok 4 · Start", self.source)
        self.assertIn("Krok 5 · Działanie", self.source)
        self.assertIn("creator:goto-step", self.source)

    def test_wizard_exposes_dynamic_accessibility_state(self):
        self.assertIn('role="tab"', self.source)
        self.assertIn("aria-controls", self.source)
        self.assertIn("aria-labelledby", self.source)
        self.assertIn("event.key === 'ArrowRight'", self.source)
        self.assertIn("aria-selected", self.source)
        self.assertIn("aria-live=\"polite\"", self.source)
        self.assertIn("aria-invalid", self.source)

    def test_filter_behavior_and_shared_creator_wiring_in_node(self):
        result = subprocess.run(
            ["node", "tests/js/test_creator_ux_contract.js"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_filter_status_is_scoped_to_family_step(self):
        family_step = self.source.index('data-creator-panel="1"')
        target_step = self.source.index('data-creator-panel="2"', family_step)
        filter_status = self.source.index('data-creator-filter-status role="status"', family_step)
        self.assertLess(filter_status, target_step)
        wizard_end = self.source.index("function insertIconAtCursor", target_step)
        self.assertEqual(
            self.source[target_step:wizard_end].count('data-creator-filter-status role="status"'),
            0,
        )

    def test_risk_step_has_bounded_responsive_layout(self):
        self.assertIn('class="creator-risk-grid"', self.source)
        self.assertIn(".creator-risk-grid .appforge-check-grid", self.styles)
        self.assertIn("term.className = 'terminal creator-window'", self.source)
        self.assertIn("term.style.display = 'block'", self.source)
        self.assertIn('class="creator-workspace"', self.source)
        self.assertIn(".creator-window > .creator-workspace", self.styles)
        self.assertIn(".creator-workspace > .appforge-form", self.styles)
        self.assertIn("inset: 32px 0 0 0;", self.styles)
        self.assertIn("height: 100%;", self.styles)

    def test_risk_toggles_do_not_recalculate_creator_filters(self):
        self.assertIn("const filterSource = event.target && event.target.closest(", self.source)
        self.assertIn("if (filterSource) applyCreatorScannerMode(term);", self.source)
        self.assertNotIn("form.addEventListener('change', () => {\n        applyCreatorScannerMode(term);", self.source)


if __name__ == "__main__":
    unittest.main()
