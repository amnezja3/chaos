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
        group,
        mount
    });
});
