# Real generalized land/sea extract

Source: Natural Earth **5.1.1**, 1:10m land, pinned release file:
https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.1/geojson/ne_10m_land.geojson

Source SHA-256: `1ac90796408bc6ad6911d69448485d3c4dbf2190370080368a09976e1c9f7416`.
Downloaded and extracted 2026-10-27. Public domain:
https://www.naturalearthdata.com/about/terms-of-use/
Product description: https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-land/

Bounds: 22.1436, 60.3605, 22.1636, 60.3805 (SW Finland archipelago).
Two land polygon parts from the actual source; sea is the complement of this
**complete generalized land layer** within the rectangle. No open coastline
was closed. No snapping, simplification or topology repair was applied.
The manifest binds this extract to the source digest and dataset version.

This proves a real MultiPolygon and complete regional land/sea partition at
Natural Earth's cartographic scale. It does NOT prove detailed OSM coastline,
inland-water multipolygon ingestion or safe use for movement/PvP/POI selection.
The test approval is isolated and does not create a production source decision.
The 10 MB source stays outside Git; only the small regional extract is retained.
