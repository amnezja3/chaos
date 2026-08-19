# GhostNetwork SFX assets

This directory is the asset contract for Sprint 130.9.2. Gameplay remains
functional when these files are absent; `GameSfx` treats a missing or rejected
asset as a presentation-only failure.

Required MP3 files:

1. `01_part_discovered.mp3` — a short, unstable discovery signature.
2. `02_part_contained.mp3` — a controlled lock/containment confirmation.
3. `03_part_activated.mp3` — a stronger energy activation confirmation.
4. `04_part_hostile.mp3` — an urgent strategic under-fire warning.
5. `05_part_lost.mp3` — a short power-down or lost-stability cue.
6. `06_module_progress.mp3` — a restrained machine-progress checkpoint.
7. `07_module_complete.mp3` — a clear machine/module completion cue.
8. `08_signal.mp3` — the strongest final GhostSignal transmission cue.

All files use the existing manifest v1 contract and must be valid MP3. Keep
their useful audible duration within the matching `max_duration_ms` declared in
`../manifest.v1.json`.
