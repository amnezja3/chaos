"""Canonical presentation contract for GhostNetwork part artwork."""

ASSET_ROOT = "static/images/ghostnetwork/parts"
PUBLIC_ASSET_ROOT = f"/{ASSET_ROOT}"
SUPERPOWER_ASSET_ROOT = "static/images/ghostnetwork/superpower"
PUBLIC_SUPERPOWER_ASSET_ROOT = f"/{SUPERPOWER_ASSET_ROOT}"
RECOMMENDED_DIMENSIONS = "128x128"
PRESENTATION_ASSET_MAX_PX = 560
PRESENTATION_ASSET_PADDING_PX = 52
PRESENTATION_ASSET_MOTION = "shake"
CLASSIFIED_MARKER_ASSET_FILENAME = "classified_part.png"
CLASSIFIED_MARKER_ASSET_URL = f"{PUBLIC_ASSET_ROOT}/{CLASSIFIED_MARKER_ASSET_FILENAME}"


def part_visual_asset_contract(part_definition):
    definition = part_definition if isinstance(part_definition, dict) else {}
    part_code = str(definition.get("part_code") or "").strip()
    icon_key = str(definition.get("icon_key") or "").strip()
    if not part_code or not icon_key:
        return {}
    filename = f"{part_code.lower()}_{icon_key}.png"
    return {
        "visual_asset_key": f"ghostnetwork.part.{icon_key}",
        "visual_asset_filename": filename,
        "visual_asset_path": f"{ASSET_ROOT}/{filename}",
        "visual_asset_url": f"{PUBLIC_ASSET_ROOT}/{filename}",
        "presentation_asset_max_px": PRESENTATION_ASSET_MAX_PX,
        "presentation_asset_padding_px": PRESENTATION_ASSET_PADDING_PX,
        "presentation_asset_motion": PRESENTATION_ASSET_MOTION,
    }


def part_superpower_asset_contract(part_definition):
    """Presentation-only artwork for the active superpower scene and timer."""
    contract = part_visual_asset_contract(part_definition)
    filename = str(contract.get("visual_asset_filename") or "").strip()
    if not filename:
        return {}
    return {
        **contract,
        "visual_asset_key": contract["visual_asset_key"].replace(
            "ghostnetwork.part.", "ghostnetwork.superpower.", 1,
        ),
        "visual_asset_path": f"{SUPERPOWER_ASSET_ROOT}/{filename}",
        "visual_asset_url": f"{PUBLIC_SUPERPOWER_ASSET_ROOT}/{filename}",
    }
