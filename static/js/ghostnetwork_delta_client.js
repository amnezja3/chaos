(function (global) {
    "use strict";

    function createGhostNetworkDeltaClient(options = {}) {
        const state = {
            cycleId: "",
            stateVersion: 0,
            snapshotChecksum: "",
            baselines: {},
            transportVersion: 0,
            processed: [],
            processedSet: new Set(),
            views: {},
            adapters: {},
            recoveryHandler: typeof options.recover === "function" ? options.recover : null,
            maxProcessed: Math.max(50, Number(options.maxProcessed || 400))
        };

        function payloadOf(event) {
            return event && event.payload && typeof event.payload === "object"
                ? event.payload : {};
        }

        function eventVersion(event) {
            const payload = payloadOf(event);
            return Number(payload.state_version || event.state_version || event.version || 0);
        }

        function transportVersion(event) {
            const payload = payloadOf(event);
            return Number(
                event.transport_version
                || event.delivery_version
                || payload.transport_version
                || payload.delivery_version
                || 0
            );
        }

        function eventCycle(event) {
            const payload = payloadOf(event);
            return String(payload.cycle_id || event.cycle_id || "").trim();
        }

        function dedupeKey(event) {
            const payload = payloadOf(event);
            return String(
                event && (
                    event.dedupe_key
                    || payload.dedupe_key
                    || payload.event_id
                    || `${event.type || "event"}:${eventCycle(event)}:${eventVersion(event)}`
                ) || ""
            ).trim();
        }

        function remember(event) {
            const key = dedupeKey(event);
            if (!key) return false;
            if (state.processedSet.has(key)) return true;
            state.processedSet.add(key);
            state.processed.push(key);
            while (state.processed.length > state.maxProcessed) {
                state.processedSet.delete(state.processed.shift());
            }
            return false;
        }

        function notify(event) {
            Object.values(state.views).forEach(callback => {
                try {
                    callback(event);
                } catch (error) {
                    console.warn("[ghostnetwork] view callback failed", error);
                }
            });
        }

        function recover(reason, event) {
            const handlers = [];
            if (typeof state.recoveryHandler === "function") {
                handlers.push(state.recoveryHandler);
            }
            Object.values(state.adapters).forEach(adapter => {
                if (adapter && typeof adapter.recover === "function") {
                    handlers.push(adapter.recover);
                }
            });
            if (!handlers.length) return Promise.resolve(false);
            return Promise.all(handlers.map(handler => {
                try {
                    return Promise.resolve(handler(reason || "delta_recovery", event));
                } catch (error) {
                    console.warn("[ghostnetwork] recovery handler failed", error);
                    return false;
                }
            })).then(results => results.some(Boolean));
        }

        function recoverAdapter(adapter, reason, event) {
            if (!adapter || typeof adapter.recover !== "function") return false;
            try {
                Promise.resolve(adapter.recover(reason || "delta_recovery", event)).catch(error => {
                    console.warn("[ghostnetwork] adapter recovery failed", error);
                });
                return true;
            } catch (error) {
                console.warn("[ghostnetwork] adapter recovery failed", error);
                return false;
            }
        }

        function handle(event) {
            if (!event || typeof event !== "object") return false;
            const type = String(event.type || "");
            if (event.scope !== "ghostnetwork" && !type.startsWith("ghost.")) return false;
            if (remember(event)) return false;

            const cycleId = eventCycle(event);
            if (cycleId && state.cycleId && cycleId !== state.cycleId) {
                recover("cycle_mismatch", event);
                return false;
            }
            const deliveryVersion = transportVersion(event);
            if (deliveryVersion > 0 && state.transportVersion > 0
                    && deliveryVersion > state.transportVersion + 1) {
                recover("transport_gap", event);
                return false;
            }
            if (deliveryVersion > 0 && deliveryVersion < state.transportVersion) {
                return false;
            }

            let applied = false;
            let attempted = false;
            Object.values(state.adapters).forEach(adapter => {
                if (!adapter || typeof adapter.apply !== "function") return;
                if (typeof adapter.accepts === "function") {
                    try {
                        if (!adapter.accepts(event)) return;
                    } catch (error) {
                        console.warn("[ghostnetwork] delta adapter predicate failed", error);
                        recoverAdapter(adapter, "adapter_predicate_failed", event);
                        return;
                    }
                }
                attempted = true;
                try {
                    const adapterApplied = adapter.apply(event);
                    if (!adapterApplied) recoverAdapter(adapter, "unapplied_delta", event);
                    applied = adapterApplied || applied;
                } catch (error) {
                    console.warn("[ghostnetwork] delta adapter failed", error);
                    recoverAdapter(adapter, "adapter_failed", event);
                }
            });
            // Receiving while no view is open is valid: the transport remains
            // warm and a later view obtains its own snapshot baseline.
            if (attempted && !applied) {
                return false;
            }

            const version = eventVersion(event);
            if (cycleId) state.cycleId = cycleId;
            if (Number.isFinite(version) && version > 0) {
                state.stateVersion = Math.max(state.stateVersion, version);
            }
            if (deliveryVersion > 0) state.transportVersion = deliveryVersion;
            const payload = payloadOf(event);
            if (payload.snapshot_checksum) state.snapshotChecksum = payload.snapshot_checksum;
            notify(event);
            return true;
        }

        function register(collection, name, value) {
            const key = String(name || `view_${Date.now()}`).trim();
            if (!key || !value) return "";
            collection[key] = value;
            return key;
        }

        return {
            handle,
            recover,
            registerView(name, callback) {
                return typeof callback === "function"
                    ? register(state.views, name, callback) : "";
            },
            unregisterView(name) {
                return delete state.views[String(name || "").trim()];
            },
            registerAdapter(name, adapter) {
                return adapter && typeof adapter.apply === "function"
                    ? register(state.adapters, name, adapter) : "";
            },
            unregisterAdapter(name) {
                return delete state.adapters[String(name || "").trim()];
            },
            setRecoveryHandler(handler) {
                state.recoveryHandler = typeof handler === "function" ? handler : null;
            },
            setBaseline(baseline = {}) {
                const nextCycle = String(baseline.cycleId || baseline.cycle_id || "").trim();
                const cycleChanged = Boolean(state.cycleId && nextCycle && nextCycle !== state.cycleId);
                if (cycleChanged) {
                    this.resetDedupe();
                    state.baselines = {};
                }
                if (nextCycle) state.cycleId = nextCycle;
                const version = Number(baseline.stateVersion || baseline.state_version || 0);
                if (Number.isFinite(version) && version >= 0) {
                    state.stateVersion = cycleChanged ? version : Math.max(state.stateVersion, version);
                }
                const checksum = String(baseline.snapshotChecksum || baseline.snapshot_checksum || "");
                if (checksum) state.snapshotChecksum = checksum;
                const baselineKey = String(baseline.view || baseline.key || "default").trim() || "default";
                state.baselines[baselineKey] = {
                    cycleId: nextCycle,
                    stateVersion: Number.isFinite(version) ? version : 0,
                    snapshotChecksum: checksum,
                };
            },
            resetDedupe() {
                state.processed = [];
                state.processedSet.clear();
            },
            notify,
            state
        };
    }

    global.createGhostNetworkDeltaClient = createGhostNetworkDeltaClient;
    let owner = global;
    try {
        if (global.parent && global.parent !== global
                && global.parent.GhostNetworkDeltaClient) {
            owner = global.parent;
        }
    } catch (_error) {
        owner = global;
    }
    if (!owner.GhostNetworkDeltaClient) {
        owner.GhostNetworkDeltaClient = createGhostNetworkDeltaClient();
    }
    global.GhostNetworkDeltaClient = owner.GhostNetworkDeltaClient;
})(typeof window !== "undefined" ? window : globalThis);
