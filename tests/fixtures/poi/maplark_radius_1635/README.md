# MapLark independent bbox/radius pair — 163.5

Captured by the operator on the VPS, 2026-10-28. Source: MapLark OSM
Features API, https://api.maplark.com/v3/osm_features. Underlying map data:
© OpenStreetMap contributors, https://www.openstreetmap.org/copyright (ODbL).

Bodies and allowlisted response headers are unchanged. Reports contain only
query parameters, status, capture time and provider revision; no credentials,
request headers, account records or server paths are included.

Parent: bbox 20.36,51.53,20.37,51.54, 23 objects.
Radius: latitude 51.53357, longitude 20.365, radius 300 m, 18 objects.
Both use the full CHAOS POI filter, limit 1000 and clipGeometry=false.
The regression test pins original body SHA-256 hashes.

Full-geometry distance selects all 18 observed radius objects and reproduces
the existing gameplay export (IDs, tags and marker positions). Bounds-center
distance selects 17, missing osm:way:1028355440. This distinguishes selection
geometry from the marker location; changing markers is unnecessary.

This is one empirical pair, using an approximate local distance metric. It
does not establish general provider completeness, source version consistency,
boundary precision, relation handling, or authorize regional gameplay reads.
