(function () {
    "use strict";

    const SNAPSHOT_URL = "/api/ghostnetwork/snapshot";
    const PART_PANE = "ghostNetworkPartPane";
    const CONNECTION_PANE = "ghostNetworkConnectionPane";
    const PULSE_PANE = "ghostNetworkPulsePane";
    const TERRITORY_PANE = "ghostNetworkTerritoryPane";
    const MAX_VISIBLE_PARTS = 20;
    const MOBILE_PART_TAP_RADIUS_PX = 32;
    const MOBILE_MAP_QUERY = "(max-width: 900px), (hover: none) and (pointer: coarse)";
    const DELTA_TYPES = new Set([
        "ghost.part_discovered",
        "ghost.part_contained",
        "ghost.part_revealed",
        "ghost.part_activated",
        "ghost.part_deactivated",
        "ghost.part_contested",
        "ghost.part_conflict_resolved",
        "ghost.part_anchor_source_lost",
        "ghost.part_anchor_migrated",
        "ghost.part_consumed"
    ]);
    const CONNECTION_DELTA_TYPES = new Set([
        "ghost.connection_changed",
        "ghost.connection_created",
        "ghost.connection_updated",
        "ghost.connection_removed"
    ]);

    window.ghostNetworkPartLayers = window.ghostNetworkPartLayers || {};
    window.ghostNetworkConnectionLayers = window.ghostNetworkConnectionLayers || {};
    window.ghostNetworkConnectionProjections = window.ghostNetworkConnectionProjections || {};
    window.ghostNetworkTerritoryLayers = window.ghostNetworkTerritoryLayers || {};
    window.ghostNetworkPendingTerritoryParts = window.ghostNetworkPendingTerritoryParts || {};
    window.ghostNetworkPartProjections = window.ghostNetworkPartProjections || {};
    window.ghostNetworkTerritoryStates = window.ghostNetworkTerritoryStates || {};
    window.ghostNetworkStateVersion = Number(window.ghostNetworkStateVersion || 0);
    window.ghostNetworkCycleId = window.ghostNetworkCycleId || "";
    window.ghostNetworkSnapshotChecksum = window.ghostNetworkSnapshotChecksum || "";
    let ghostNetworkSnapshotRequestId = 0;
    let ghostNetworkRecoveryPromise = null;
    let ghostNetworkMobileConnectionRenderer = null;
    let ghostTerritoryRefreshDepth = 0;
    let ghostTerritoryRefreshPending = false;

    const ghostNetworkDeltaState = window.ghostNetworkDeltaState || {
        processed: [],
        processedSet: new Set(),
        callbacks: {}
    };
    if (!(ghostNetworkDeltaState.processedSet instanceof Set)) {
        ghostNetworkDeltaState.processedSet = new Set(ghostNetworkDeltaState.processed || []);
    }
    window.ghostNetworkDeltaState = ghostNetworkDeltaState;

    function getMap() {
        if (window.chaosMap) return window.chaosMap;
        if (window.map && typeof window.map.createPane === "function") return window.map;
        const key = Object.keys(window).find(name => name.startsWith("map_"));
        return key ? window[key] : null;
    }

    function ensureGhostNetworkPanes() {
        const map = getMap();
        if (!map || typeof map.createPane !== "function") return null;
        if (!map.getPane(TERRITORY_PANE)) {
            const pane = map.createPane(TERRITORY_PANE);
            pane.style.zIndex = "455";
            pane.style.pointerEvents = "none";
        }
        if (!map.getPane(CONNECTION_PANE)) {
            const pane = map.createPane(CONNECTION_PANE);
            pane.style.zIndex = "548";
            pane.style.pointerEvents = "none";
        }
        if (!map.getPane(PULSE_PANE)) {
            const pane = map.createPane(PULSE_PANE);
            pane.style.zIndex = "552";
            pane.style.pointerEvents = "none";
        }
        if (!map.getPane(PART_PANE)) {
            const pane = map.createPane(PART_PANE);
            pane.style.zIndex = "625";
            pane.style.pointerEvents = "none";
        }
        ensureMobilePartTapBridge(map);
        return map;
    }

    function isMobileGhostNetworkMap() {
        return Boolean(window.matchMedia && window.matchMedia(MOBILE_MAP_QUERY).matches);
    }

    function mobileConnectionRenderer(map) {
        if (!map || !window.L || typeof L.canvas !== "function") return null;
        if (!ghostNetworkMobileConnectionRenderer) {
            ghostNetworkMobileConnectionRenderer = L.canvas({ pane: CONNECTION_PANE, padding: 0.2, tolerance: 0 });
        }
        return ghostNetworkMobileConnectionRenderer;
    }

    function mobileTapContainerPoint(map, event) {
        if (!map || !event) return null;
        try {
            if (event.containerPoint && Number.isFinite(Number(event.containerPoint.x)) && Number.isFinite(Number(event.containerPoint.y))) {
                return event.containerPoint;
            }
            if (event.layerPoint && typeof map.layerPointToContainerPoint === "function") {
                return map.layerPointToContainerPoint(event.layerPoint) || null;
            }
            if (event.latlng && typeof map.latLngToContainerPoint === "function") {
                return map.latLngToContainerPoint(event.latlng) || null;
            }
            if (event.originalEvent && typeof map.mouseEventToContainerPoint === "function") {
                return map.mouseEventToContainerPoint(event.originalEvent) || null;
            }
        } catch (err) {
            console.warn("[ghostnetwork] mobile tap point unavailable", err);
        }
        return null;
    }

    function ensureMobilePartTapBridge(map) {
        if (!map || typeof map.on !== "function" || map._ghostNetworkMobileTapBound) return;
        map._ghostNetworkMobileTapBound = true;
        map.on("click", event => {
            const tapPoint = mobileTapContainerPoint(map, event);
            if (!tapPoint) return;
            let nearest = null;
            let nearestDistance = MOBILE_PART_TAP_RADIUS_PX;
            Object.values(window.ghostNetworkPartLayers || {}).forEach(marker => {
                if (!marker || typeof marker.getLatLng !== "function" || typeof map.latLngToContainerPoint !== "function") return;
                let point = null;
                try {
                    const markerLatLng = marker.getLatLng();
                    if (!markerLatLng) return;
                    point = map.latLngToContainerPoint(markerLatLng);
                } catch (err) {
                    console.warn("[ghostnetwork] mobile marker point unavailable", err);
                    return;
                }
                if (!point || !Number.isFinite(Number(point.x)) || !Number.isFinite(Number(point.y))) return;
                const dx = Number(point.x) - Number(tapPoint.x);
                const dy = Number(point.y) - Number(tapPoint.y);
                const distance = Math.sqrt((dx * dx) + (dy * dy));
                if (distance <= nearestDistance) {
                    nearest = marker;
                    nearestDistance = distance;
                }
            });
            if (nearest && nearest.ghostNetworkProjection) {
                openGhostPartPanel(nearest.ghostNetworkProjection, nearest);
            }
        });
    }

    function escapeHtml(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function asNumber(value) {
        const num = Number(value);
        return Number.isFinite(num) ? num : null;
    }

    function validLatLng(lat, lng) {
        const nLat = asNumber(lat);
        const nLng = asNumber(lng);
        if (nLat === null || nLng === null) return null;
        if (Math.abs(nLat) > 90 || Math.abs(nLng) > 180) return null;
        return [nLat, nLng];
    }

    function projectionKey(part) {
        if (!part || typeof part !== "object") return "";
        return String(part.public_entity_id || part.part_id || part.entity_id || part.target_id || "").trim();
    }

    function connectionKey(connection) {
        if (!connection || typeof connection !== "object") return "";
        return String(connection.public_connection_id || connection.connection_id || connection.entity_id || "").trim();
    }

    function normalizeState(part) {
        if (part && part.contested) return "contested";
        return String((part && part.module_state) || (part && part.status) || "neutral").toLowerCase();
    }

    function ghostTerritoryStrategicState(part) {
        const territoryId = String((part && part.territory_id) || "").trim();
        if (!territoryId) return "none";
        const moduleState = String((part && part.module_state) || "").toLowerCase();
        if (moduleState === "blocked") return "hostile";
        if (moduleState === "active") return "active";
        return "none";
    }

    function setGhostTerritoryLayerState(entry, state) {
        const layer = entry && entry.layer ? entry.layer : entry;
        if (!layer) return false;
        const normalized = state === "hostile" || state === "active" ? state : "none";
        if (layer._ghostNetworkStrategicState === normalized) return false;
        layer._ghostNetworkStrategicState = normalized;
        const element = typeof layer.getElement === "function" ? layer.getElement() : null;
        if (!element || !element.classList) return false;
        element.classList.remove("ghostnetwork-territory-active", "ghostnetwork-territory-hostile");
        if (normalized !== "none") element.classList.add(`ghostnetwork-territory-${normalized}`);
        return true;
    }

    function requestGhostTerritoryStatesRefresh() {
        if (ghostTerritoryRefreshDepth > 0) {
            ghostTerritoryRefreshPending = true;
            return null;
        }
        return refreshGhostTerritoryStates();
    }

    function batchGhostTerritoryStatesRefresh(callback) {
        ghostTerritoryRefreshDepth += 1;
        try {
            return callback();
        } finally {
            ghostTerritoryRefreshDepth = Math.max(0, ghostTerritoryRefreshDepth - 1);
            if (ghostTerritoryRefreshDepth === 0 && ghostTerritoryRefreshPending) {
                ghostTerritoryRefreshPending = false;
                refreshGhostTerritoryStates();
            }
        }
    }

    function refreshGhostTerritoryStates() {
        const registry = window.territoryAreaLayers || {};
        const states = {};
        Object.values(window.ghostNetworkPartProjections || {}).forEach(part => {
            const territoryId = String((part && part.territory_id) || "").trim();
            const state = ghostTerritoryStrategicState(part);
            if (!territoryId || state === "none") return;
            if (state === "hostile" || !states[territoryId]) states[territoryId] = state;
        });
        Object.keys(registry).forEach(territoryId => {
            setGhostTerritoryLayerState(registry[territoryId], states[territoryId] || "none");
        });
        window.ghostNetworkTerritoryStates = states;
        return { ...states };
    }

    function isAnchor(part) {
        return String((part && part.part_type) || (part && part.kind) || "").toLowerCase() === "ghost_anchor"
            || String((part && part.part_code) || "").toLowerCase().includes("anchor")
            || String((part && part.display_label) || "").toLowerCase().includes("anchor");
    }

    function buildGhostPartIcon(part, transition = "") {
        const state = normalizeState(part);
        const assetUrl = String((part && (part.visual_asset_url || part.marker_asset_url)) || "").trim();
        const classNames = [
            "ghostnetwork-node",
            `is-${state}`,
            isAnchor(part) ? "is-anchor" : "",
            part && part.identity_visible === false ? "is-hidden" : "",
            assetUrl ? "has-asset" : "asset-missing",
            transition ? `transition-${transition}` : ""
        ].filter(Boolean).join(" ");
        const image = assetUrl
            ? `<img class="ghostnetwork-part-art" src="${escapeHtml(assetUrl)}" alt="" draggable="false" decoding="async" onerror="this.hidden=true;this.parentElement.classList.add('asset-missing')">`
            : "";
        return L.divIcon({
            className: "ghostnetwork-part-icon",
            html: `<span class="${classNames}" aria-hidden="true"><span class="ghostnetwork-part-halo"></span>${image}<span class="ghostnetwork-part-fallback"></span></span>`,
            iconSize: [54, 54],
            iconAnchor: [27, 27],
            popupAnchor: [0, -29]
        });
    }

    function popupRow(label, value) {
        if (value == null || value === "") return "";
        return `<div class="ghostnetwork-popup-row"><span class="ghostnetwork-popup-label">${escapeHtml(label)}</span><span class="ghostnetwork-popup-value">${escapeHtml(value)}</span></div>`;
    }

    function openGhostPartPanel(part, marker) {
        if (!marker || !part) return false;
        const label = part.display_label || part.summary || "GhostNetwork";
        const rows = [
            popupRow("Stan", part.module_state || part.status),
            popupRow("Widocznosc", part.visibility_level),
            popupRow("Relacja", part.viewer_relation),
            popupRow("Terytorium", part.territory_id),
            part.identity_visible ? popupRow("Czesc", part.part_id || part.part_code) : "",
            part.ability_visible ? popupRow("Modul", part.machine_id || part.machine_code) : "",
            part.conflict_state ? popupRow("Konflikt", part.conflict_state) : ""
        ].join("");
        const summary = part.summary ? `<div class="ghostnetwork-popup-summary">${escapeHtml(part.summary)}</div>` : "";
        marker.bindPopup(
            `<div class="ghostnetwork-popup"><div class="ghostnetwork-popup-title">${escapeHtml(label)}</div>${rows}${summary}</div>`,
            { className: "ghostnetwork-leaflet-popup", closeButton: true }
        );
        marker.openPopup();
        return true;
    }

    function removeGhostPartMarker(key) {
        const map = getMap();
        const normalizedKey = String(key || "").trim();
        if (!normalizedKey) return false;
        const marker = window.ghostNetworkPartLayers[normalizedKey];
        if (marker && map) {
            try {
                map.removeLayer(marker);
            } catch (err) {
                console.warn("[ghostnetwork] remove part marker failed", err);
            }
        }
        delete window.ghostNetworkPartLayers[normalizedKey];

        const badge = window.ghostNetworkTerritoryLayers[normalizedKey];
        if (badge && map) {
            try {
                map.removeLayer(badge);
            } catch (err) {
                console.warn("[ghostnetwork] remove territory badge failed", err);
            }
        }
        delete window.ghostNetworkTerritoryLayers[normalizedKey];
        delete window.ghostNetworkPendingTerritoryParts[normalizedKey];
        delete window.ghostNetworkPartProjections[normalizedKey];
        requestGhostTerritoryStatesRefresh();
        return true;
    }

    function removeGhostConnectionLayer(key) {
        const map = getMap();
        const normalizedKey = String(key || "").trim();
        if (!normalizedKey) return false;
        const layer = window.ghostNetworkConnectionLayers[normalizedKey];
        if (layer && map) {
            try {
                map.removeLayer(layer);
            } catch (err) {
                console.warn("[ghostnetwork] remove connection failed", err);
            }
        }
        delete window.ghostNetworkConnectionLayers[normalizedKey];
        delete window.ghostNetworkConnectionProjections[normalizedKey];
        return true;
    }

    function clearGhostConnections() {
        Object.keys(window.ghostNetworkConnectionLayers || {}).forEach(removeGhostConnectionLayer);
        window.ghostNetworkConnectionLayers = {};
        window.ghostNetworkConnectionProjections = {};
    }

    function clearGhostNetworkLayer() {
        clearGhostConnections();
        Object.keys(window.ghostNetworkPartLayers || {}).forEach(removeGhostPartMarker);
        Object.keys(window.ghostNetworkTerritoryLayers || {}).forEach(removeGhostPartMarker);
        window.ghostNetworkPartLayers = {};
        window.ghostNetworkTerritoryLayers = {};
        window.ghostNetworkPendingTerritoryParts = {};
        window.ghostNetworkPartProjections = {};
        requestGhostTerritoryStatesRefresh();
    }

    function renderGhostTerritoryBadge(part) {
        const map = ensureGhostNetworkPanes();
        if (!map || !window.L || !part) return false;
        const key = projectionKey(part);
        let coords = validLatLng(part.territory_latitude || part.territory_lat, part.territory_longitude || part.territory_lng);
        if (!coords && part.territory_id) {
            const territory = window.territoryAreaLayers
                && window.territoryAreaLayers[String(part.territory_id)];
            const layer = territory && territory.layer;
            if (layer && typeof layer.getBounds === "function") {
                const bounds = layer.getBounds();
                const center = bounds && typeof bounds.getCenter === "function" ? bounds.getCenter() : null;
                coords = center ? validLatLng(center.lat, center.lng) : null;
            }
        }
        if (!key) return false;
        window.ghostNetworkPartProjections[key] = part;
        requestGhostTerritoryStatesRefresh();
        if (!coords) {
            window.ghostNetworkPendingTerritoryParts[key] = part;
            const pendingKeys = Object.keys(window.ghostNetworkPendingTerritoryParts);
            while (pendingKeys.length > MAX_VISIBLE_PARTS) {
                const expiredKey = pendingKeys.shift();
                delete window.ghostNetworkPendingTerritoryParts[expiredKey];
            }
            return false;
        }
        delete window.ghostNetworkPendingTerritoryParts[key];
        const state = normalizeState(part);
        const assetUrl = String((part.visual_asset_url || part.marker_asset_url) || "").trim();
        const html = assetUrl
            ? `<span class="ghostnetwork-territory-badge has-asset is-${escapeHtml(state)}" aria-hidden="true"><span class="ghostnetwork-part-halo"></span><img class="ghostnetwork-part-art" src="${escapeHtml(assetUrl)}" alt="" draggable="false" decoding="async"></span>`
            : `<span class="ghostnetwork-territory-badge is-${escapeHtml(state)}" aria-hidden="true"></span>`;
        const icon = L.divIcon({
            className: "ghostnetwork-territory-icon",
            html,
            iconSize: [38, 38],
            iconAnchor: [19, 19]
        });
        let marker = window.ghostNetworkTerritoryLayers[key];
        if (!marker) {
            marker = L.marker(coords, { icon, pane: TERRITORY_PANE, interactive: false });
            marker.addTo(map);
            window.ghostNetworkTerritoryLayers[key] = marker;
        } else {
            marker.setLatLng(coords);
            marker.setIcon(icon);
        }
        return true;
    }

    function refreshGhostTerritoryBadges() {
        let rendered = 0;
        Object.values(window.ghostNetworkPendingTerritoryParts || {}).forEach(part => {
            if (renderGhostTerritoryBadge(part)) rendered += 1;
        });
        requestGhostTerritoryStatesRefresh();
        return rendered;
    }

    function connectionEndpoint(connection, side) {
        const key = side === "b" ? "endpoint_b" : "endpoint_a";
        const endpoint = connection && connection[key] && typeof connection[key] === "object" ? connection[key] : {};
        const lat = endpoint.latitude ?? (side === "b" ? connection.to_latitude : connection.from_latitude);
        const lng = endpoint.longitude ?? (side === "b" ? connection.to_longitude : connection.from_longitude);
        const coords = validLatLng(lat, lng);
        if (coords) return coords;

        const publicId = endpoint.public_entity_id || (side === "b" ? connection.to_public_entity_id : connection.from_public_entity_id);
        const marker = publicId ? window.ghostNetworkPartLayers[String(publicId)] : null;
        if (marker && typeof marker.getLatLng === "function") {
            const latLng = marker.getLatLng();
            return validLatLng(latLng.lat, latLng.lng);
        }
        return null;
    }

    function hashConnectionSign(value) {
        let hash = 0;
        const text = String(value || "");
        for (let i = 0; i < text.length; i += 1) {
            hash = ((hash << 5) - hash + text.charCodeAt(i)) | 0;
        }
        return hash % 2 === 0 ? 1 : -1;
    }

    function curvePoint(a, b, connection) {
        const latMid = (a[0] + b[0]) / 2;
        const lngMid = (a[1] + b[1]) / 2;
        const dLat = b[0] - a[0];
        const dLng = b[1] - a[1];
        const distance = Math.sqrt(dLat * dLat + dLng * dLng);
        const sign = hashConnectionSign(connectionKey(connection) || connection.connection_id);
        const bend = Math.min(Math.max(distance * 0.18, 0.0009), 0.018) * sign;
        return [latMid - dLng * bend / Math.max(distance, 0.000001), lngMid + dLat * bend / Math.max(distance, 0.000001)];
    }

    function buildConnectionCurve(connection) {
        const state = String(connection && connection.state || "hidden");
        const a = connectionEndpoint(connection, "a");
        const b = connectionEndpoint(connection, "b");
        if (!a || !b) return [];
        let start = a;
        let end = b;
        let maxT = 1;
        if (state === "half_from_b") {
            start = b;
            end = a;
            maxT = 0.52;
        } else if (state === "half_from_a") {
            maxT = 0.52;
        }
        const control = curvePoint(start, end, connection);
        const points = [];
        const steps = state.startsWith("half_") ? 5 : 8;
        for (let i = 0; i <= steps; i += 1) {
            const t = maxT * (i / steps);
            const inv = 1 - t;
            points.push([
                inv * inv * start[0] + 2 * inv * t * control[0] + t * t * end[0],
                inv * inv * start[1] + 2 * inv * t * control[1] + t * t * end[1]
            ]);
        }
        return points;
    }

    function isRenderableConnectionCurve(points) {
        if (!Array.isArray(points) || points.length < 2) return false;
        if (!points.every(point => Array.isArray(point) && point.length >= 2 && validLatLng(point[0], point[1]))) return false;
        const first = points[0];
        return points.some(point => Number(point[0]) !== Number(first[0]) || Number(point[1]) !== Number(first[1]));
    }

    function connectionClass(connection, role) {
        return [
            "ghostnetwork-connection",
            `ghostnetwork-connection-${role}`,
            `is-${String(connection.state || "hidden")}`,
            connection.contested ? "is-contested" : ""
        ].filter(Boolean).join(" ");
    }

    function createGhostConnectionLayer(connection) {
        const map = ensureGhostNetworkPanes();
        if (!map || !window.L || !connection) return null;
        const points = buildConnectionCurve(connection);
        if (!isRenderableConnectionCurve(points)) return null;
        const state = String(connection.state || "hidden");
        if (!connection.can_show_on_map || !["half_from_a", "half_from_b", "active"].includes(state)) return null;

        if (isMobileGhostNetworkMap()) {
            const renderer = mobileConnectionRenderer(map);
            const contested = Boolean(connection.contested);
            return L.polyline(points, {
                pane: CONNECTION_PANE,
                renderer: renderer || undefined,
                noClip: true,
                interactive: false,
                bubblingMouseEvents: false,
                color: contested ? "#ff473d" : (state === "active" ? "#5cff8f" : "#d7ff3a"),
                weight: state === "active" ? 4 : 3,
                opacity: state === "active" ? 0.78 : 0.62,
                dashArray: state === "active" ? "10 7" : "12 10 2 10",
                lineCap: "round",
                lineJoin: "round"
            });
        }

        const layers = [
            L.polyline(points, {
                pane: CONNECTION_PANE,
                noClip: true,
                interactive: false,
                bubblingMouseEvents: false,
                className: connectionClass(connection, "base"),
                weight: state === "active" ? 9 : 7,
                opacity: 0.36
            }),
            L.polyline(points, {
                pane: CONNECTION_PANE,
                noClip: true,
                interactive: false,
                bubblingMouseEvents: false,
                className: connectionClass(connection, "core"),
                weight: state === "active" ? 4 : 3,
                opacity: state === "active" ? 0.78 : 0.62
            })
        ];
        if (state === "active") {
            layers.push(L.polyline(points, {
                pane: PULSE_PANE,
                noClip: true,
                interactive: false,
                bubblingMouseEvents: false,
                className: connectionClass(connection, "pulse"),
                weight: 3,
                opacity: 0.86
            }));
        }
        return L.layerGroup(layers);
    }

    function updateGhostConnectionLayer(connection) {
        const map = ensureGhostNetworkPanes();
        const key = connectionKey(connection);
        if (!map || !key) return false;
        removeGhostConnectionLayer(key);
        window.ghostNetworkConnectionProjections[key] = connection;
        const layer = createGhostConnectionLayer(connection);
        if (!layer) return false;
        layer.addTo(map);
        window.ghostNetworkConnectionLayers[key] = layer;
        return true;
    }

    function renderGhostConnections(connections) {
        clearGhostConnections();
        if (!Array.isArray(connections)) return 0;
        let rendered = 0;
        connections.forEach(connection => {
            const key = connectionKey(connection);
            if (key) window.ghostNetworkConnectionProjections[key] = connection;
            if (updateGhostConnectionLayer(connection)) rendered += 1;
        });
        return rendered;
    }

    function refreshGhostConnections() {
        const projections = Object.values(window.ghostNetworkConnectionProjections || {});
        if (!projections.length) return 0;
        return renderGhostConnections(projections);
    }

    function renderGhostPart(part, options = {}) {
        const map = ensureGhostNetworkPanes();
        if (!map || !window.L || !part) return false;
        const key = projectionKey(part);
        if (!key) return false;
        window.ghostNetworkPartProjections[key] = part;
        if (part.can_show_on_map === false) {
            removeGhostPartMarker(key);
            return false;
        }
        if (String(part.location_visibility || "").toLowerCase() !== "exact") {
            removeGhostPartMarker(key);
            return renderGhostTerritoryBadge(part);
        }
        delete window.ghostNetworkPendingTerritoryParts[key];
        const coords = validLatLng(part.latitude || part.lat, part.longitude || part.lng);
        if (!coords) {
            removeGhostPartMarker(key);
            return false;
        }

        const icon = buildGhostPartIcon(part, options.transition || "");
        let marker = window.ghostNetworkPartLayers[key];
        if (!marker) {
            marker = L.marker(coords, {
                icon,
                pane: PART_PANE,
                keyboard: false,
                riseOnHover: true,
                interactive: false,
                bubblingMouseEvents: true
            });
            marker.on("click", () => openGhostPartPanel(part, marker));
            marker.addTo(map);
            window.ghostNetworkPartLayers[key] = marker;
        } else {
            marker.setLatLng(coords);
            marker.setIcon(icon);
            marker.off("click");
            marker.on("click", () => openGhostPartPanel(part, marker));
        }
        marker.ghostNetworkProjection = part;
        requestGhostTerritoryStatesRefresh();
        refreshGhostConnections();
        const badge = window.ghostNetworkTerritoryLayers[key];
        if (badge) {
            try {
                map.removeLayer(badge);
            } catch (err) {
                console.warn("[ghostnetwork] remove replaced territory badge failed", err);
            }
            delete window.ghostNetworkTerritoryLayers[key];
        }
        return true;
    }

    function renderGhostParts(parts) {
        if (!Array.isArray(parts)) return 0;
        let rendered = 0;
        batchGhostTerritoryStatesRefresh(() => {
            clearGhostNetworkLayer();
            parts
                .filter(part => part && part.can_show_on_map !== false)
                .slice(0, MAX_VISIBLE_PARTS)
                .forEach(part => {
                    if (renderGhostPart(part)) rendered += 1;
                });
        });
        return rendered;
    }

    function normalizeSnapshotPayload(data) {
        const payload = data && typeof data === "object" ? data : {};
        if (!Array.isArray(payload.parts) && payload.snapshot && typeof payload.snapshot === "object") {
            return {
                ...payload,
                cycle: payload.snapshot.cycle || payload.cycle,
                parts: payload.snapshot.parts || [],
                connections: payload.snapshot.connections || [],
                state_version: payload.snapshot.state_version || payload.state_version || 0
            };
        }
        return payload;
    }

    function isCompleteGhostNetworkSnapshot(data) {
        if (!data || typeof data !== "object") return false;
        if (!Array.isArray(data.parts) || !Array.isArray(data.connections)) return false;
        const cycleId = String((data.cycle && data.cycle.cycle_id) || data.cycle_id || "").trim();
        if (!cycleId) return false;
        return data.parts.every(part => part && typeof part === "object" && projectionKey(part));
    }

    function resetGhostNetworkDeltaDedupe() {
        ghostNetworkDeltaState.processed = [];
        ghostNetworkDeltaState.processedSet.clear();
    }

    async function loadGhostNetworkSnapshot(options = {}) {
        const requestId = ++ghostNetworkSnapshotRequestId;
        try {
            let response;
            if (typeof window.fetchMapSnapshot === "function") {
                const snapshot = await window.fetchMapSnapshot("ghostnetwork", `${SNAPSHOT_URL}?view=map`, { timeoutMs: options.timeoutMs || 10000 });
                if (!snapshot || snapshot.skipped || snapshot.aborted) {
                    console.warn("[ghostnetwork] snapshot deferred", {
                        reason: snapshot && snapshot.reason || "unavailable",
                        boot: Boolean(options.boot)
                    });
                    return false;
                }
                response = snapshot.res;
            } else {
                response = await fetch(`${SNAPSHOT_URL}?view=map`, { headers: { Accept: "application/json" } });
            }
            if (!response || !response.ok) {
                console.warn("[ghostnetwork] snapshot unavailable", response && response.status);
                return false;
            }
            const data = normalizeSnapshotPayload(await response.json());
            if (data.ok === false) {
                console.warn("[ghostnetwork] snapshot rejected", data.error || data.reason || "unknown");
                return false;
            }
            if (!isCompleteGhostNetworkSnapshot(data)) {
                console.warn("[ghostnetwork] incomplete snapshot rejected");
                return false;
            }
            const version = Number(data.current_version || data.state_version || (data.cycle && data.cycle.state_version) || 0);
            if (requestId !== ghostNetworkSnapshotRequestId) return false;
            if (Number.isFinite(version) && version > 0 && version < Number(window.ghostNetworkStateVersion || 0)) {
                console.warn("[ghostnetwork] stale snapshot rejected", { version, current: window.ghostNetworkStateVersion });
                return false;
            }
            const nextCycleId = String((data.cycle && data.cycle.cycle_id) || data.cycle_id || "").trim();
            if (window.ghostNetworkCycleId && nextCycleId !== window.ghostNetworkCycleId) {
                resetGhostNetworkDeltaDedupe();
            }
            if (Number.isFinite(version)) {
                window.ghostNetworkStateVersion = Math.max(Number(window.ghostNetworkStateVersion || 0), version);
            }
            window.ghostNetworkCycleId = nextCycleId;
            window.ghostNetworkSnapshotChecksum = data.snapshot_checksum || window.ghostNetworkSnapshotChecksum || "";
            renderGhostParts(data.parts || []);
            renderGhostConnections(data.connections || []);
            notifyGhostNetworkDeltaViews({ type: "snapshot", snapshot: data });
            return true;
        } catch (err) {
            console.warn("[ghostnetwork] snapshot failed", err);
            return false;
        }
    }

    function extractDeltaProjection(event) {
        const payload = event && event.payload && typeof event.payload === "object" ? event.payload : {};
        return payload.projection || payload.part_projection || payload.part || payload.ghost_part || null;
    }

    function extractConnectionProjection(event) {
        const payload = event && event.payload && typeof event.payload === "object" ? event.payload : {};
        return payload.projection || payload.connection_projection || payload.connection || payload.ghost_connection || null;
    }

    function extractDeltaKey(event, projection) {
        const payload = event && event.payload && typeof event.payload === "object" ? event.payload : {};
        return projectionKey(projection)
            || String(event && (event.entity_id || event.public_entity_id) || "").trim()
            || String(payload.public_entity_id || payload.part_id || payload.entity_id || "").trim();
    }

    function applyGhostPartDelta(event) {
        if (!event || typeof event !== "object") return false;
        const type = String(event.type || "");
        const possibleConnection = extractConnectionProjection(event);
        const isConnectionProjection = possibleConnection && (
            possibleConnection.public_connection_id
            || possibleConnection.connection_id
            || possibleConnection.endpoint_a
            || possibleConnection.endpoint_b
        );
        if (CONNECTION_DELTA_TYPES.has(type) || (!DELTA_TYPES.has(type) && isConnectionProjection)) {
            return applyGhostConnectionDelta(event);
        }
        if (!DELTA_TYPES.has(type) && event.scope !== "ghostnetwork") return false;
        const projection = extractDeltaProjection(event);
        const key = extractDeltaKey(event, projection);
        const version = Number(
            (event.payload && (event.payload.state_version || event.payload.version))
            || (projection && projection.state_version)
            || event.version
            || 0
        );
        if (Number.isFinite(version) && version > 0 && version < Number(window.ghostNetworkStateVersion || 0)) {
            return false;
        }
        if (type === "ghost.part_consumed" || (event.payload && event.payload.removed === true)) {
            if (key) removeGhostPartMarker(key);
            refreshGhostConnections();
            if (Number.isFinite(version)) window.ghostNetworkStateVersion = Math.max(window.ghostNetworkStateVersion || 0, version);
            return true;
        }
        if (!projection) {
            return false;
        }
        const previous = window.ghostNetworkPartProjections[key] || null;
        const transition = (
            type === "ghost.part_contained" && normalizeState(previous) !== normalizeState(projection)
        ) ? "contained" : (
            type === "ghost.part_activated" && normalizeState(previous) !== normalizeState(projection)
                ? "activated" : ""
        );
        renderGhostPart(projection, { transition });
        if (Number.isFinite(version)) window.ghostNetworkStateVersion = Math.max(window.ghostNetworkStateVersion || 0, version);
        return true;
    }

    function applyGhostConnectionDelta(event) {
        if (!event || typeof event !== "object") return false;
        const type = String(event.type || "");
        const projection = extractConnectionProjection(event);
        const payload = event.payload && typeof event.payload === "object" ? event.payload : {};
        const key = connectionKey(projection) || String(event.entity_id || payload.public_connection_id || payload.connection_id || "").trim();
        const version = Number(payload.state_version || payload.version || (projection && projection.state_version) || event.version || 0);
        if (Number.isFinite(version) && version > 0 && version < Number(window.ghostNetworkStateVersion || 0)) {
            return false;
        }
        if (type === "ghost.connection_removed" || payload.removed === true) {
            if (key) removeGhostConnectionLayer(key);
            if (Number.isFinite(version)) window.ghostNetworkStateVersion = Math.max(window.ghostNetworkStateVersion || 0, version);
            return true;
        }
        if (!projection) {
            return false;
        }
        const applied = updateGhostConnectionLayer(projection);
        if (Number.isFinite(version)) window.ghostNetworkStateVersion = Math.max(window.ghostNetworkStateVersion || 0, version);
        return applied;
    }

    function applyGhostNetworkDeltaPayload(event) {
        return applyGhostPartDelta(event) || applyGhostConnectionDelta(event);
    }

    function animateGhostConnectionPulse() {
        return true;
    }

    async function recoverGhostNetworkLayer(options = {}) {
        if (ghostNetworkRecoveryPromise) return ghostNetworkRecoveryPromise;
        ghostNetworkRecoveryPromise = loadGhostNetworkSnapshot({ recovery: true, ...options })
            .finally(() => {
                ghostNetworkRecoveryPromise = null;
            });
        return ghostNetworkRecoveryPromise;
    }

    function ghostNetworkEventVersion(event) {
        const payload = event && event.payload && typeof event.payload === "object" ? event.payload : {};
        return Number(payload.state_version || event.state_version || event.version || 0);
    }

    function ghostNetworkEventCycle(event) {
        const payload = event && event.payload && typeof event.payload === "object" ? event.payload : {};
        return String(payload.cycle_id || event.cycle_id || "").trim();
    }

    function ghostNetworkDedupeKey(event) {
        const payload = event && event.payload && typeof event.payload === "object" ? event.payload : {};
        return String(event && (event.dedupe_key || payload.dedupe_key || payload.event_id || `${event.type || "event"}:${ghostNetworkEventVersion(event)}`) || "").trim();
    }

    function rememberGhostNetworkDelta(event) {
        const key = ghostNetworkDedupeKey(event);
        if (!key) return false;
        if (ghostNetworkDeltaState.processedSet.has(key)) return true;
        ghostNetworkDeltaState.processedSet.add(key);
        ghostNetworkDeltaState.processed.push(key);
        while (ghostNetworkDeltaState.processed.length > 400) {
            const removed = ghostNetworkDeltaState.processed.shift();
            ghostNetworkDeltaState.processedSet.delete(removed);
        }
        return false;
    }

    function notifyGhostNetworkDeltaViews(event) {
        Object.values(ghostNetworkDeltaState.callbacks || {}).forEach(callback => {
            try {
                if (typeof callback === "function") callback(event);
            } catch (err) {
                console.warn("[ghostnetwork] view callback failed", err);
            }
        });
    }

    function registerGhostNetworkDeltaView(name, callback) {
        const key = String(name || `view_${Date.now()}`).trim();
        if (!key || typeof callback !== "function") return "";
        ghostNetworkDeltaState.callbacks[key] = callback;
        return key;
    }

    function unregisterGhostNetworkDeltaView(name) {
        const key = String(name || "").trim();
        if (!key) return false;
        delete ghostNetworkDeltaState.callbacks[key];
        return true;
    }

    async function requestGhostNetworkRecovery(reason, event) {
        console.warn("[ghostnetwork] delta recovery requested", { reason, type: event && event.type });
        return recoverGhostNetworkLayer({ reason: reason || "delta_recovery" });
    }

    function handleGhostNetworkDelta(event) {
        if (!event || typeof event !== "object") return false;
        const type = String(event.type || "");
        if (event.scope !== "ghostnetwork" && !type.startsWith("ghost.")) return false;
        if (rememberGhostNetworkDelta(event)) return false;

        const eventCycle = ghostNetworkEventCycle(event);
        if (eventCycle && window.ghostNetworkCycleId && eventCycle !== window.ghostNetworkCycleId) {
            requestGhostNetworkRecovery("cycle_mismatch", event);
            return false;
        }

        const version = ghostNetworkEventVersion(event);
        const current = Number(window.ghostNetworkStateVersion || 0);
        if (Number.isFinite(version) && version > 0) {
            if (current > 0 && version < current) return false;
            // Domain versions are global to the cycle. Gaps are expected for
            // player projections because internal/system and other viewers'
            // events are deliberately filtered. The per-user delta bus owns
            // transport continuity and requests snapshot recovery when needed.
        }

        const applied = applyGhostNetworkDeltaPayload(event);
        if (applied) {
            if (eventCycle) window.ghostNetworkCycleId = eventCycle;
            if (Number.isFinite(version) && version > 0) {
                window.ghostNetworkStateVersion = Math.max(Number(window.ghostNetworkStateVersion || 0), version);
            }
            const payload = event.payload && typeof event.payload === "object" ? event.payload : {};
            if (payload.snapshot_checksum) window.ghostNetworkSnapshotChecksum = payload.snapshot_checksum;
            notifyGhostNetworkDeltaViews(event);
            return true;
        }
        requestGhostNetworkRecovery("unapplied_delta", event);
        return false;
    }

    window.GhostNetworkDeltaClient = {
        handle: handleGhostNetworkDelta,
        recover: requestGhostNetworkRecovery,
        registerView: registerGhostNetworkDeltaView,
        unregisterView: unregisterGhostNetworkDeltaView,
        state: ghostNetworkDeltaState
    };

    window.loadGhostNetworkSnapshot = loadGhostNetworkSnapshot;
    window.renderGhostParts = renderGhostParts;
    window.renderGhostConnections = renderGhostConnections;
    window.createGhostConnectionLayer = createGhostConnectionLayer;
    window.updateGhostConnectionLayer = updateGhostConnectionLayer;
    window.removeGhostConnectionLayer = removeGhostConnectionLayer;
    window.applyGhostConnectionDelta = applyGhostConnectionDelta;
    window.applyGhostNetworkDeltaPayload = applyGhostNetworkDeltaPayload;
    window.applyGhostNetworkDelta = handleGhostNetworkDelta;
    window.animateGhostConnectionPulse = animateGhostConnectionPulse;
    window.applyGhostPartDelta = applyGhostPartDelta;
    window.removeGhostPartMarker = removeGhostPartMarker;
    window.renderGhostTerritoryBadge = renderGhostTerritoryBadge;
    window.refreshGhostTerritoryBadges = refreshGhostTerritoryBadges;
    window.refreshGhostTerritoryStates = refreshGhostTerritoryStates;
    window.openGhostPartPanel = openGhostPartPanel;
    window.clearGhostNetworkLayer = clearGhostNetworkLayer;
    window.recoverGhostNetworkLayer = recoverGhostNetworkLayer;
    window.registerGhostNetworkDeltaView = registerGhostNetworkDeltaView;
    window.unregisterGhostNetworkDeltaView = unregisterGhostNetworkDeltaView;
})();
