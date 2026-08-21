# GhostNetwork part assets

Final asset contract for Sprint 130.9.4:

- format: PNG with alpha transparency,
- source dimensions: 128x128 px,
- one unique image per canonical `part_code`,
- no baked background, lifecycle glow, halo, pulse or warning frame,
- keep the important silhouette inside a 108x108 px safe area,
- lifecycle and hostile variants are presentation classes, not separate files.

Classified marker contract:

- filename: `classified_part.png`,
- path: `static/images/ghostnetwork/parts/classified_part.png`,
- format and dimensions: PNG with alpha transparency, 128x128 px,
- purpose: neutral artwork for `foreign_blocked` and `foreign_active`,
- must not resemble or reveal any one of the 20 canonical parts,
- no baked lifecycle color, glow, halo or frame; BLOCKED/ACTIVE styling is CSS.

Expected files:

```text
classified_part.png
v1_ledger_nexus.png
v2_backdoor_forge.png
v3_mimicry_engine.png
v4_acquisition_drive.png
v5_probability_core.png
e1_breach_voice.png
e2_influence_relay.png
e3_truth_lens.png
e4_resonance_beacon.png
e5_spark_chamber.png
p1_mirage_projector.png
p2_glitch_reactor.png
p3_paranoia_loop.png
p4_fracture_engine.png
p5_mirror_kernel.png
s1_deep_sensor.png
s2_bastion_matrix.png
s3_restoration_engine.png
s4_accord_relay.png
s5_judgment_core.png
```
