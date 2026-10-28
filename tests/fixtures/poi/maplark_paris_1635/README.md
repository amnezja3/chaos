# Paris compact bbox regression

Derived from the operator's MapLark capture (2026-10-28), operation
region:paris-poi-1635-compact-v3. Original body SHA-256:
2d62d5317470f7db5897499884bf5e491a679afab3b495427a6bfe593e215441.

826 complete objects: 706 Point, 2 LineString, 116 Polygon, 2 MultiPolygon.
All source IDs and geometries retained. Properties deliberately reduced to
shop/amenity/office/healthcare/atm/man_made classification tags. Names, contact
details and other descriptive properties removed. This is a derived fixture,
not the byte-identical original capture. No credentials or player data.

Source: MapLark OSM Features API. Map data © OpenStreetMap contributors,
https://www.openstreetmap.org/copyright (ODbL).

CHAOS geometry-v2 selects 479 and 465 objects at the two acceptance positions.
These are geometry-layer counts before the existing gameplay limit of 60.
This fixture tests the explicitly accepted local metric, not provider radius
parity or current production freshness. Geometry-v1 rejected both positions
because of its five-metre ambiguity band.
