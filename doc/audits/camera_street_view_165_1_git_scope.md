# Camera Street View 165.1 — zakres Git

Base HEAD: `3556abdcb9603110271e0ea7563fbea4f590ae63`.

Weryfikacja przed usunięciem ZIP: wszystkie 99 plików ma identyczne odpowiedniki
w repo (porównanie bajtów i SHA-256, CRC archiwum). Manifest wewnętrzny również
zgodny z zewnętrznym. Brak unikalnego kodu lub dowodów testowych w ZIP.

Stan przed korektą dokumentacji workflow: M = zmodyfikowany, ?? = nowy,
unchanged = niezmieniona zależność/referencja już w HEAD, nie dodatkowa zmiana
do commitowania. Poniżej 98 zachowanych plików; pominięto usunięty builder ZIP.
Dokumenty workflow z tej listy następnie zaktualizowano zgodnie z korektą.

Zakres funkcjonalny: backend lifecycle i archiwum, integracja launch/runtime,
native Ghost UI i linki CHAOS (w tym terminal/Google Plex), panel/źródła,
konfiguracja OFF, Pillow, fixtures/testy, materiały, wzorzec i dokumentacja.
Zmiana operatora `doc/prototypes/camera_view/v164_0/preview.css` pozostaje
nietknięta i poza tym zakresem. `.playwright-mcp/` to lokalna diagnostyka,
pozostaje na dysku poza planowanym stagingiem; żadnych baz ani sekretów.
Usunięto tylko trzy artefakty dystrybucji `camera-street-view-165-1.*`
(zip/manifest.json/sha256) oraz `tools/package_camera_street_view.py`.

| Repository path | Git status |
| --- | --- |
| `assets/camera_visual/pilot_164_0/paris/README.md` | ?? |
| `assets/camera_visual/pilot_164_0/paris/generation.json` | ?? |
| `assets/camera_visual/pilot_164_0/paris/paris-01-dusk.png` | ?? |
| `assets/camera_visual/pilot_164_0/paris/paris-02-night.png` | ?? |
| `assets/camera_visual/pilot_164_0/paris/paris-03-dawn.png` | ?? |
| `camera_visual.py` | ?? |
| `camera_visual_archive.py` | ?? |
| `camera_visual_source.py` | ?? |
| `database.py` | M |
| `doc/architecture/chaos_links_v1.md` | ?? |
| `doc/architecture/profile_hot_path_contract_130_11_plus.md` | unchanged |
| `doc/audits/camera_street_view_package_165_1.md` | ?? |
| `doc/audits/camera_visual_gameplay_164_0.md` | ?? |
| `doc/audits/camera_visual_prototype_164_0.md` | M |
| `doc/history/project_journal.md` | M |
| `doc/plans/camera_street_view_operator_contract_2026_10_31.md` | ?? |
| `doc/plans/camera_visual_pilot_164_0_board.md` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/README.md` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/artifacts/cvn-164-effects-comparison.png` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/artifacts/cvn-164-effects-dropout.png` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/assets/camera_visual/pilot_164_0/paris/README.md` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/assets/camera_visual/pilot_164_0/paris/generation.json` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/assets/camera_visual/pilot_164_0/paris/paris-01-dusk.png` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/assets/camera_visual/pilot_164_0/paris/paris-02-night.png` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/assets/camera_visual/pilot_164_0/paris/paris-03-dawn.png` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/doc/audits/camera_visual_gameplay_164_0.md` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/doc/plans/camera_visual_pilot_164_0_board.md` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/manifest.json` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/static/css/camera_visual.css` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/static/css/chaos_links.css` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/static/images/camera_visual/camera-network-v1.png` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/static/images/camera_visual/effects/README.md` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/static/images/camera_visual/effects/chroma-tear.svg` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/static/images/camera_visual/effects/compression-blocks.svg` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/static/images/camera_visual/effects/fine-grain.svg` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/static/images/camera_visual/effects/manifest.json` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/static/images/camera_visual/effects/scan-lines.svg` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/static/images/camera_visual/effects/signal-dropout.svg` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/static/images/camera_visual/effects/tracking-band.svg` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/static/images/camera_visual/generation.json` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/static/images/system/chaos-actions.svg` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/static/js/camera_visual.js` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/static/js/chaos_links.js` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/tests/browser/camera_visual_effects_164_0.js` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/tests/browser/camera_visual_gameplay_164_0.js` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/tests/browser/camera_visual_reconnect_164_0.js` | ?? |
| `doc/prototypes/camera_view/accepted_164_0_2026_10_31/tests/browser/camera_visual_resize_164_0.js` | ?? |
| `doc/runbooks/camera_street_view_package_165_1.md` | ?? |
| `doc/runbooks/handoff_project_2026_10_31.md` | M |
| `doc/sprints/sprint_164_camera_visual_archive.md` | M |
| `doc/sprints/sprint_165_camera_visual_network_rollout.md` | M |
| `doc/sprints/sprint_166_camera_street_view_live.md` | ?? |
| `ecosystem.camera.config.js` | ?? |
| `ecosystem.web.config.js` | M |
| `requirements.txt` | M |
| `run.py` | M |
| `static/css/camera_visual.css` | ?? |
| `static/css/chaos_links.css` | ?? |
| `static/images/camera_visual/camera-network-v1.png` | ?? |
| `static/images/camera_visual/effects/README.md` | ?? |
| `static/images/camera_visual/effects/chroma-tear.svg` | ?? |
| `static/images/camera_visual/effects/compression-blocks.svg` | ?? |
| `static/images/camera_visual/effects/fine-grain.svg` | ?? |
| `static/images/camera_visual/effects/manifest.json` | ?? |
| `static/images/camera_visual/effects/scan-lines.svg` | ?? |
| `static/images/camera_visual/effects/signal-dropout.svg` | ?? |
| `static/images/camera_visual/effects/tracking-band.svg` | ?? |
| `static/images/camera_visual/generation.json` | ?? |
| `static/images/system/chaos-actions.svg` | ?? |
| `static/js/camera_visual.js` | ?? |
| `static/js/chaos_links.js` | ?? |
| `static/js/googleplex_news.js` | M |
| `static/js/terminal.js` | M |
| `templates/admin_base.html` | M |
| `templates/admin_camera.html` | ?? |
| `templates/camera_sources.html` | ?? |
| `templates/linux.html` | M |
| `tests/browser/camera_street_view_close.js` | ?? |
| `tests/browser/camera_street_view_material.js` | ?? |
| `tests/browser/camera_visual_effects_164_0.js` | ?? |
| `tests/browser/camera_visual_gameplay_164_0.js` | ?? |
| `tests/browser/camera_visual_map_focus_164_0.js` | ?? |
| `tests/browser/camera_visual_reconnect_164_0.js` | ?? |
| `tests/browser/camera_visual_resize_164_0.js` | ?? |
| `tests/browser/chaos_links_164_0.js` | ?? |
| `tests/browser/chaos_text_links.js` | ?? |
| `tests/js/test_camera_operation_delta.js` | unchanged |
| `tests/js/test_camera_target_transport.js` | unchanged |
| `tests/js/test_camera_window_dedupe.js` | unchanged |
| `tests/seed_camera_street_view_local.py` | ?? |
| `tests/test_camera_archive.py` | ?? |
| `tests/test_camera_exposure.py` | unchanged |
| `tests/test_camera_incident_audit.py` | unchanged |
| `tests/test_camera_shutdown_contract.py` | unchanged |
| `tests/test_camera_visual_gameplay.py` | ?? |
| `tools/camera_archive.py` | ?? |
| `tools/camera_visual_local.py` | ?? |
| `tools/freeze_camera_presentation.js` | ?? |

## Additional preserved evidence and workflow document

- `doc/audits/camera_street_view_165_1_git_scope.md` (new)
- `artifacts/camera-street-view-material.png` (new, test evidence)
- `artifacts/cvn-164-0-b-desktop.png` (new, test evidence)
- `artifacts/cvn-164-0-b-download.png` (new, test evidence)
- `artifacts/cvn-164-0-b-failure.png` (new, test evidence)
- `artifacts/cvn-164-0-b-mobile.png` (new, test evidence)
- `artifacts/cvn-164-0-b-no-signal.png` (new, test evidence)
- `artifacts/cvn-164-0-b-session-close.png` (new, test evidence)
- `artifacts/cvn-164-0-desktop.png` (new, test evidence)
- `artifacts/cvn-164-0-external-en.png` (new, test evidence)
- `artifacts/cvn-164-0-mobile-en.png` (new, test evidence)
- `artifacts/cvn-164-0-mobile-pl.png` (new, test evidence)
- `artifacts/cvn-164-0-no-signal.png` (new, test evidence)
- `artifacts/cvn-164-camera-hud-desktop.png` (new, test evidence)
- `artifacts/cvn-164-camera-hud-mobile.png` (new, test evidence)
- `artifacts/cvn-164-camera-map-focus.png` (new, test evidence)
- `artifacts/cvn-164-camera-motion-desktop.png` (new, test evidence)
- `artifacts/cvn-164-camera-motion-mobile.png` (new, test evidence)
- `artifacts/cvn-164-camera-motion-panel.png` (new, test evidence)
- `artifacts/cvn-164-effects-blocks.png` (new, test evidence)
- `artifacts/cvn-164-effects-chroma.png` (new, test evidence)
- `artifacts/cvn-164-effects-comparison.png` (new, test evidence)
- `artifacts/cvn-164-effects-dropout.png` (new, test evidence)
- `artifacts/cvn-164-effects-grain.png` (new, test evidence)
- `artifacts/cvn-164-effects-scan.png` (new, test evidence)
- `artifacts/cvn-164-effects-tracking.png` (new, test evidence)
- `artifacts/cvn-164-gameplay-download.png` (new, test evidence)
- `artifacts/cvn-164-gameplay-failure-restored.png` (new, test evidence)
- `artifacts/cvn-164-gameplay-failure.png` (new, test evidence)
- `artifacts/cvn-164-gameplay-mobile-en.png` (new, test evidence)
- `artifacts/cvn-164-gameplay-mobile.png` (new, test evidence)
- `artifacts/cvn-164-gameplay-no-signal.png` (new, test evidence)
- `artifacts/cvn-164-gameplay-session-close.png` (new, test evidence)
- `artifacts/cvn-164-gameplay-viewer.png` (new, test evidence)
- `artifacts/cvn-164-mapifi-footer.png` (new, test evidence)
- `artifacts/cvn-164-mapifi-mobile.png` (new, test evidence)
- `artifacts/cvn-164-mapifi-window.png` (new, test evidence)
- `artifacts/cvn-164-resize-links.png` (new, test evidence)
