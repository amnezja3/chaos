(function bootstrapGoogleplexSearchPresentation(root, factory) {
    const api = factory();
    if (typeof module === "object" && module.exports) {
        module.exports = api;
    }
    if (root) {
        root.GoogleplexSearchPresentation = api;
    }
})(typeof globalThis !== "undefined" ? globalThis : this, function createGoogleplexSearchPresentation() {
    "use strict";

    const MIDDLE_PER_GROUP = 2;
    const SMALL_PER_GROUP = 3;
    const GROUP_SIZE = 1 + MIDDLE_PER_GROUP + SMALL_PER_GROUP;

    const categories = Object.freeze([
        { id: 'tools', label: 'Narzędzia', words: 'narzędzia narzędzie aplikacje programy tools' },
        { id: 'documents', label: 'Dokumenty', words: 'dokument dokumenty wiedza instrukcje' },
        { id: 'travel_ticket', label: 'Bilety', words: 'bilety bilet podróż podróże przejazd miasta' },
        { id: 'storage_upgrade', label: 'Dysk', words: 'dysk dyski pamięć pojemność magazyn ulepszenia' },
        { id: 'map', label: 'Mapa i skan', words: 'mapa mapy skan skanowanie zasięg zoom ulepszenia' },
        { id: 'bike_upgrade', label: 'Pojazd', words: 'pojazd motocykl rower podróż zasięg ulepszenia' },
        { id: 'other', label: 'Pozostałe', words: 'pozostałe inne produkty' }
    ]);
    const normalizeSearch = value => String(value || '').toLowerCase().normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '').replace(/ł/g, 'l').replace(/[_-]+/g, ' ');
    const list = value => Array.isArray(value) ? value : [];
    function categoryOf(item) {
        if (item.template_id === 'ptk_document') return 'documents';
        const type = item.product_type;
        if (['travel_ticket', 'storage_upgrade', 'bike_upgrade'].includes(type)) return type;
        if (['map_upgrade', 'scan_upgrade'].includes(type)) return 'map';
        return type || list(item.effects).length ? 'other' : 'tools';
    }
    const associations = [
        ['atm', 'bankomat bankomaty bankomatu logi'],
        ['camera', 'kamera kamery kamer monitoring obraz'],
        ['audio', 'odtwarzacz audio dźwięk podsłuch'],
        ['car vehicle', 'samochód samochody pojazd pojazdy pokładowy'],
        ['gps tracking track', 'śledzenie lokalizacja gps'],
        ['network hotspot wifi', 'sieć sieci hotspoty wifi'],
        ['sniffer', 'sniffer przechwytywanie'],
        ['port scan', 'skan porty portów'],
        ['exploit', 'exploit exploity'],
        ['shutdown disable', 'wyłącz wyłączenie'],
        ['credentials', 'hasła logowanie dane logowania']
    ];
    function matchesSearch(item, query, category = '') {
        if (!item || typeof item !== 'object') return false;
        if (category && categoryOf(item) !== category) return false;
        if (!query.trim() || query.trim().toLowerCase() === '/all') return true;
        const metadata = normalizeSearch([
            item.type, item.category, item.product_type, item.tool_family, ...list(item.map_actions),
            ...list(item.operation_types), ...list(item.resource_types), ...list(item.target_types)
        ].join(' '));
        const metadataWords = new Set(metadata.split(/\s+/));
        const aliases = associations.filter(([keys]) => keys.split(' ').some(key => metadataWords.has(key)))
            .map(([, words]) => words).join(' ');
        const text = normalizeSearch([
            item.name, item.description, item.app_level, item.travel_city, metadata, aliases,
            categories.find(entry => entry.id === categoryOf(item)).words,
            ...list(item.effects).map(effect => `${effect?.type || ''} ${effect?.value ?? effect?.city ?? ''}`)
        ].join(' '));
        return normalizeSearch(query).split(/\s+/).filter(Boolean).every(word => text.includes(word));
    }

    function group(items) {
        const ordered = Array.isArray(items) ? items : [];
        const groups = [];
        for (let offset = 0; offset < ordered.length; offset += GROUP_SIZE) {
            const batch = ordered.slice(offset, offset + GROUP_SIZE);
            groups.push({
                index: groups.length,
                offset,
                hero: batch[0] || null,
                middle: batch.slice(1, 1 + MIDDLE_PER_GROUP),
                small: batch.slice(1 + MIDDLE_PER_GROUP, GROUP_SIZE)
            });
        }
        return groups;
    }

    function element(documentRef, tagName, className) {
        const node = documentRef.createElement(tagName);
        node.className = className;
        return node;
    }

    function mount(rootNode, items, createCard) {
        if (!rootNode || !rootNode.ownerDocument) {
            throw new TypeError("googleplex_search_root_missing");
        }
        if (typeof createCard !== "function") {
            throw new TypeError("googleplex_search_card_factory_missing");
        }

        const ordered = Array.isArray(items) ? items : [];
        const documentRef = rootNode.ownerDocument;
        rootNode.replaceChildren();
        rootNode.classList.toggle("gp-search-results--single", ordered.length === 1);

        if (ordered.length === 1) {
            rootNode.appendChild(createCard(ordered[0], "single", 0));
            return { group_count: 0, rendered_count: 1, single: true };
        }

        const groups = group(ordered);
        groups.forEach(groupData => {
            const groupNode = element(documentRef, "section", "gp-search-group");
            groupNode.dataset.groupIndex = String(groupData.index);
            groupNode.setAttribute("aria-label", `Grupa aplikacji ${groupData.index + 1}`);

            const heroSlot = element(documentRef, "div", "gp-search-group__hero");
            heroSlot.appendChild(createCard(groupData.hero, "hero", groupData.offset));

            const side = element(documentRef, "div", "gp-search-group__side");
            const middleRow = element(documentRef, "div", "gp-search-group__middle");
            groupData.middle.forEach((item, index) => {
                middleRow.appendChild(createCard(item, "middle", groupData.offset + index + 1));
            });

            const smallRow = element(documentRef, "div", "gp-search-group__small");
            groupData.small.forEach((item, index) => {
                smallRow.appendChild(createCard(item, "small", groupData.offset + index + 3));
            });

            side.append(middleRow, smallRow);
            groupNode.append(heroSlot, side);
            rootNode.appendChild(groupNode);
        });

        return {
            group_count: groups.length,
            rendered_count: ordered.length,
            single: false
        };
    }

    return Object.freeze({
        GROUP_SIZE,
        MIDDLE_PER_GROUP,
        SMALL_PER_GROUP,
        categories,
        categoryOf,
        matchesSearch,
        group,
        mount
    });
});
