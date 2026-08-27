"""
Order lookup tool that loads orders.json and provides a sanitized
lookup function. Only customer-safe fields are ever returned.
Internal fields (email, address, risk score, warehouse notes) are
stripped at the data layer so they never reach the LLM.
"""

import json
import os
import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Regex for valid order ID format: ORD- followed by digits.
_ORDER_ID_RE = re.compile(r"^ORD-\d+$")

# Fields that are safe to return to the customer per the data dictionary.
_CUSTOMER_SAFE_FIELDS = {
    "order_id",
    "membership_tier",
    "items",
    "placed_at",
    "status",
    "status_updated_at",
    "shipped_at",
    "delivered_at",
    "carrier",
    "tracking_number",
    "estimated_delivery",
    "customer_safe_message",
}

# Item-level fields that are safe to expose.
_SAFE_ITEM_FIELDS = {"name", "quantity", "final_sale"}


class OrderLookup:
    """
    Loads order data from orders.json and provides a sanitized lookup
    that never exposes internal or sensitive customer fields.
    """

    def __init__(self, orders_file: str):
        self._orders: dict[str, dict[str, Any]] = {}
        self._snapshot_at: str = ""
        self._load(orders_file)

    # Loads orders.json and indexes orders by uppercase order_id.
    def _load(self, orders_file: str) -> None:
        if not os.path.exists(orders_file):
            logger.error("Orders file not found: %s", orders_file)
            return

        with open(orders_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._snapshot_at = data.get("snapshot_at", "")
        for order in data.get("orders", []):
            oid = order.get("order_id", "").upper()
            self._orders[oid] = order

        logger.info("Loaded %d orders (snapshot_at=%s)", len(self._orders), self._snapshot_at)

    @property
    def snapshot_at(self) -> str:
        return self._snapshot_at

    # Looks up an order by ID, normalizing input (strip whitespace,
    # uppercase), validating format, and returning only customer-safe
    # fields. Returns a result dict with status and optional order data.
    def lookup(self, order_id: str) -> dict[str, Any]:
        if not order_id or not isinstance(order_id, str):
            return {
                "success": False,
                "error": "missing_order_id",
                "message": "Please provide an order ID (e.g., ORD-1007).",
            }

        # Normalize: strip whitespace and convert to uppercase.
        normalized = order_id.strip().upper()

        # Validate format.
        if not _ORDER_ID_RE.match(normalized):
            return {
                "success": False,
                "error": "malformed_order_id",
                "message": f"'{order_id.strip()}' does not appear to be a valid order ID. "
                           "Order IDs follow the format ORD-XXXX.",
            }

        # Look up the order.
        order = self._orders.get(normalized)
        if order is None:
            return {
                "success": False,
                "error": "order_not_found",
                "message": f"No order found with ID '{normalized}'. "
                           "Please verify the order ID or contact support.",
            }

        # Sanitize and return only customer-safe fields.
        return {
            "success": True,
            "order": self._sanitize(order),
        }

    # Strips internal/sensitive fields and handles status-specific
    # logic (e.g., suppressing stale delivery info for cancelled orders).
    def _sanitize(self, order: dict[str, Any]) -> dict[str, Any]:
        status = order.get("status", "")

        safe: dict[str, Any] = {}
        for key in _CUSTOMER_SAFE_FIELDS:
            if key == "items":
                # Sanitize items to only safe item fields.
                raw_items = order.get("items", [])
                safe["items"] = [
                    {k: v for k, v in item.items() if k in _SAFE_ITEM_FIELDS}
                    for item in raw_items
                ]
            elif key in order:
                safe[key] = order[key]

        # For cancelled or returned orders, suppress stale delivery fields
        # to prevent the agent from claiming the order is still arriving.
        if status in ("cancelled", "returned"):
            safe.pop("estimated_delivery", None)
            safe.pop("carrier", None)
            safe.pop("tracking_number", None)
            safe.pop("shipped_at", None)
            if status == "cancelled":
                safe.pop("delivered_at", None)

        # For exception status, add a flag indicating human review is needed.
        if status == "exception":
            safe["requires_human_review"] = True

        return safe


# Tool definition in the format expected by LLM function-calling APIs
# (OpenAI/Mistral compatible schema).
ORDER_LOOKUP_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "lookup_order",
        "description": (
            "Look up the current status and details of a customer order by order ID. "
            "Only call this tool when the user asks about a specific order and provides "
            "an order ID. Do NOT call this tool without an order ID."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID to look up, e.g. ORD-1007",
                }
            },
            "required": ["order_id"],
        },
    },
}
