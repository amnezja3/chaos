"""Ghost message format v1. Text only; escape at the HTML rendering boundary.

No profile reads, network calls, mutable global locale or translation of UGC.
JSON catalogs are also consumed directly by static/js/ghost_i18n.js.
"""
import json
import math
import logging
import re
from copy import deepcopy
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

CATALOG_ROOT = Path(__file__).resolve().parent / "static" / "locales"
TOKEN = re.compile(r"\{([a-zA-Z][a-zA-Z0-9_]*)\}")


@lru_cache(maxsize=1)
def manifest():
    return json.loads((CATALOG_ROOT / "manifest.json").read_text(encoding="utf-8"))


def normalize_locale(value, default="pl", registry=None):
    registry = registry or manifest()
    tag = value.strip().lower().replace("_", "-").split("-")[0] if isinstance(value, str) else ""
    return tag if tag in registry["locales"] else default


def resolve_locale(*, authenticated=False, account=None, device=None, browser=None):
    if authenticated:
        return normalize_locale(account)
    return normalize_locale(device, default=None) or normalize_locale(browser)


def plural_category(value, rules):
    n = abs(value)
    for rule in rules:
        matches = True
        for condition in rule["conditions"]:
            operand = {"n": n, "i": math.floor(n), "integer": int(n == math.floor(n))}[condition["operand"]]
            if "mod" in condition:
                operand %= condition["mod"]
            found = any(low <= operand <= high for low, high in condition["ranges"])
            matches = matches and (not found if condition.get("not") else found)
        if matches:
            return rule["category"]
    return "other"


def valid_number(value):
    return type(value) in (int, float) and abs(value) <= 9007199254740991 and math.isfinite(value)


def number_text(value):
    # Canonical interpolation only. Locale-aware units/dates belong to presentation.
    if value == int(value):
        return str(int(value))
    if abs(value) >= 0.000001:
        return format(Decimal(str(value)), 'f')
    mantissa, exponent = str(value).split('e')
    return f"{mantissa}e{int(exponent)}"


class Translator:
    def __init__(self, registry, catalogs, diagnostic=None):
        self.registry = deepcopy(registry)
        self.catalogs = deepcopy(catalogs)
        self.diagnostic = diagnostic or (lambda code, key, locale: logging.getLogger(__name__).warning(
            "i18n %s key=%s locale=%s", code, key, locale))
        if registry.get("format_version") != 1 or registry["default_locale"] not in catalogs:
            raise ValueError("invalid_manifest")
        for locale, bundle in catalogs.items():
            if (locale not in registry["locales"] or bundle.get("locale") != locale
                    or bundle.get("format_version") != 1
                    or bundle.get("content_version") != registry["content_version"]):
                raise ValueError("catalog_version_mismatch")

    def t(self, key, params=None, locale="pl"):
        locale = normalize_locale(locale, registry=self.registry)
        fallback = self.registry["default_locale"]
        messages = self.catalogs.get(locale, {}).get("messages", {})
        entry = messages.get(key)
        entry_locale = locale
        if entry is None:
            self.diagnostic("missing_key", key, locale)
            entry_locale = fallback
            entry = self.catalogs[fallback]["messages"].get(key)
        if entry is None:
            return self.catalogs.get(locale, self.catalogs[fallback])["messages"].get(
                "common.unavailable", self.catalogs[fallback]["messages"]["common.unavailable"])["text"]
        params = {} if params is None else params
        spec = entry["params"]
        if not isinstance(params, dict) or set(params) != set(spec):
            raise ValueError("invalid_message_params")
        for name, kind in spec.items():
            if not ((kind == "string" and isinstance(params[name], str))
                    or (kind == "number" and valid_number(params[name]))):
                raise ValueError("invalid_message_params")
        if "plural" in entry:
            category = plural_category(params[entry["plural"]], self.registry["locales"][entry_locale]["plural_rules"])
            template = entry["forms"].get(category, entry["forms"]["other"])
        else:
            template = entry["text"]
        if set(TOKEN.findall(template)) != set(spec):
            raise ValueError("invalid_message_template")
        return TOKEN.sub(lambda match: number_text(params[match[1]]) if spec[match[1]] == "number" else params[match[1]], template)

    def message(self, envelope, locale="pl"):
        if envelope.get("content_version") != self.registry["content_version"]:
            raise ValueError("message_version_mismatch")
        return self.t(envelope["key"], envelope.get("params"), locale)


@lru_cache(maxsize=1)
def translator():
    registry = manifest()
    bundles = {}
    for locale in registry["locales"]:
        merged = {"locale": locale, "format_version": 1,
                  "content_version": registry["content_version"], "messages": {}}
        for domain in registry["domains"]:
            bundle = json.loads((CATALOG_ROOT / locale / f"{domain}.json").read_text(encoding="utf-8"))
            if (bundle.get("locale") != locale or bundle.get("format_version") != 1
                    or bundle.get("content_version") != registry["content_version"]):
                raise ValueError("catalog_version_mismatch")
            if merged["messages"].keys() & bundle["messages"].keys():
                raise ValueError("duplicate_message_key")
            merged["messages"].update(bundle["messages"])
        bundles[locale] = merged
    return Translator(registry, bundles)


def format_number(value, locale="pl", *, minimum_fraction_digits=0, maximum_fraction_digits=3, grouping=True):
    """Presentation only. Canonical amounts are never rounded for storage."""
    from decimal import Decimal, ROUND_HALF_UP
    if not valid_number(value) or not 0 <= minimum_fraction_digits <= maximum_fraction_digits <= 20:
        raise ValueError("invalid_number_format")
    formats = manifest()["locales"][normalize_locale(locale)]["formats"]
    number = Decimal(str(value)).quantize(Decimal(1).scaleb(-maximum_fraction_digits), rounding=ROUND_HALF_UP)
    whole, _, fraction = format(abs(number), "f").partition(".")
    fraction = fraction.rstrip("0").ljust(minimum_fraction_digits, "0")
    if grouping and len(whole) >= formats.get("minimum_grouping_digits", 1) + 3:
        whole = formats["group"].join(
            [whole[:len(whole) % 3]] * bool(len(whole) % 3) + [whole[i:i+3] for i in range(len(whole) % 3, len(whole), 3)])
    return ("-" if number.is_signed() and number else "") + whole + (formats["decimal"] + fraction if fraction else "")


def format_unit(value, unit, locale="pl", **options):
    label = manifest()["locales"][normalize_locale(locale)]["formats"]["units"].get(unit)
    if label is None:
        raise ValueError("unsupported_unit")
    return format_number(value, locale, **options) + " " + label


def format_date(value, locale="pl", *, time_zone="UTC", include_time=False):
    """An explicit time zone belongs to the player/request, never to the locale."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    date = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    if not isinstance(date, datetime) or date.tzinfo is None:
        raise ValueError("date_requires_timezone")
    date = date.astimezone(ZoneInfo(time_zone))
    template = manifest()["locales"][normalize_locale(locale)]["formats"]["date"]
    parts = {"d": str(date.day).zfill(2), "m": str(date.month).zfill(2), "y": str(date.year)}
    result = "".join(parts.get(part, part) for part in template)
    return result + (date.strftime(" %H:%M") if include_time else "")


def approved_locales(purpose="interface"):
    """Shared approval registry; radio ANY is a filter, never an output language."""
    if purpose not in ("interface", "radio", "narration"):
        raise ValueError("invalid_locale_purpose")
    return tuple(tag for tag, entry in manifest()["locales"].items()
                 if purpose in entry.get("approved_for", []))


def radio_locale_filters():
    return (*approved_locales("radio"), manifest()["radio_any_filter"])
