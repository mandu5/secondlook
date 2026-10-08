"""Read-only model inventory. Availability is not a quality estimate."""

from __future__ import annotations

import json
import math
import ssl
from urllib.request import Request, urlopen

import certifi

from .core import CapsuleError

CATALOG_URL = "https://openrouter.ai/api/v1/models"
MAX_CATALOG_BYTES = 8 * 1024 * 1024


def _prices(prices: object, *, tier: bool = False) -> None:
    if not isinstance(prices, dict):
        raise CapsuleError("Invalid catalog pricing")
    for key, value in prices.items():
        if key == "overrides" and not tier:
            if not isinstance(value, list) or len(value) > 100:
                raise CapsuleError("Invalid catalog pricing tiers")
            for override in value:
                _prices(override, tier=True)
            continue
        if key == "min_prompt_tokens" and tier:
            if type(value) is not int or value < 0:
                raise CapsuleError("Invalid price tier threshold")
            continue
        if tier and key.startswith("utc_"):
            # The public API also carries time-based discount conditions.
            # Preserve these as opaque observation metadata; we never use
            # catalog prices/conditions to compute a campaign's spending.
            continue
        try:
            price = float(value)
        except (ValueError, TypeError) as error:
            raise CapsuleError("Invalid catalog price") from error
        # Routing entries may use -1 for dynamically priced models.
        if isinstance(value, bool) or not math.isfinite(price) or price < -1:
            raise CapsuleError("Invalid catalog price")


def fetch_catalog() -> dict:
    request = Request(CATALOG_URL, headers={"User-Agent": "secondlook/0.3", "Accept": "application/json"})
    context = ssl.create_default_context()
    # Retain system/SSL_CERT_FILE trust and supplement Python installs that
    # ship without a configured CA bundle. Never disable TLS verification.
    context.load_verify_locations(cafile=certifi.where())
    with urlopen(request, timeout=30, context=context) as response:
        raw = response.read(MAX_CATALOG_BYTES + 1)
    if len(raw) > MAX_CATALOG_BYTES:
        raise CapsuleError("Model catalog exceeds 8 MiB")
    return json.loads(raw)


def normalize_catalog(payload: object) -> dict[str, dict]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise CapsuleError("Catalog needs a data array")
    if not 1 <= len(payload["data"]) <= 20000:
        raise CapsuleError("Catalog must contain 1 through 20000 models; empty responses are not removals")
    try:
        encoded = json.dumps(payload, allow_nan=False).encode("utf-8")
    except (ValueError, UnicodeError, TypeError) as error:
        raise CapsuleError("Catalog must be finite UTF-8 JSON") from error
    if len(encoded) > MAX_CATALOG_BYTES:
        raise CapsuleError("Model catalog exceeds 8 MiB")
    models = {}
    for model in payload["data"]:
        if not isinstance(model, dict):
            raise CapsuleError("Catalog model must be an object")
        key = model.get("id")
        if not isinstance(key, str) or not key.strip() or len(key) > 240 or key in models:
            raise CapsuleError("Catalog model IDs must be nonempty and unique")
        for field in ("created", "context_length"):
            if field in model and model[field] is not None and (type(model[field]) is not int or model[field] < 0):
                raise CapsuleError(f"Invalid catalog {field}")
        _prices(model.get("pricing", {}))
        models[key] = {field: model[field] for field in (
            "id", "canonical_slug", "name", "created", "context_length", "architecture",
            "supported_parameters", "pricing") if field in model}
    return models
