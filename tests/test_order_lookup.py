"""
Deterministic tests for the order lookup tool.
Validates sanitization, normalization, error handling, and status-specific
logic without requiring an LLM.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import config
from app.tools.order_lookup import OrderLookup

ORDERS_FILE = config.orders_file


@pytest.fixture
def lookup():
    return OrderLookup(ORDERS_FILE)


# --- Valid Lookup ---

# Confirms a standard valid order lookup returns success and expected fields.
def test_valid_order_lookup(lookup):
    result = lookup.lookup("ORD-1007")
    assert result["success"] is True
    order = result["order"]
    assert order["order_id"] == "ORD-1007"
    assert order["status"] == "shipped"
    assert "carrier" in order


# Confirms that lowercase order IDs are normalized and found.
def test_lowercase_order_id(lookup):
    result = lookup.lookup("ord-1007")
    assert result["success"] is True
    assert result["order"]["order_id"] == "ORD-1007"


# Confirms that surrounding whitespace is stripped before lookup.
def test_whitespace_order_id(lookup):
    result = lookup.lookup("  ORD-1007  ")
    assert result["success"] is True
    assert result["order"]["order_id"] == "ORD-1007"


# Confirms mixed case with whitespace is handled.
def test_mixed_case_whitespace(lookup):
    result = lookup.lookup("  ord-1003  ")
    assert result["success"] is True
    assert result["order"]["order_id"] == "ORD-1003"


# --- Error Handling ---

# Confirms unknown order IDs return a clear not-found error.
def test_unknown_order(lookup):
    result = lookup.lookup("ORD-9999")
    assert result["success"] is False
    assert result["error"] == "order_not_found"


# Confirms malformed order IDs are rejected with a format error.
def test_malformed_order_id(lookup):
    result = lookup.lookup("INVALID")
    assert result["success"] is False
    assert result["error"] == "malformed_order_id"


# Confirms empty string is treated as missing order ID.
def test_empty_order_id(lookup):
    result = lookup.lookup("")
    assert result["success"] is False
    assert result["error"] == "missing_order_id"


# Confirms None input is treated as missing order ID.
def test_none_order_id(lookup):
    result = lookup.lookup(None)
    assert result["success"] is False
    assert result["error"] == "missing_order_id"


# --- Privacy / Sanitization ---

# Confirms that customer email is NEVER present in sanitized output.
def test_no_email_in_output(lookup):
    result = lookup.lookup("ORD-1007")
    order_str = str(result)
    assert "ava.morgan@example.test" not in order_str
    assert "email" not in result["order"]


# Confirms that shipping address is NEVER present in sanitized output.
def test_no_address_in_output(lookup):
    result = lookup.lookup("ORD-1007")
    order_str = str(result)
    assert "220 King Street" not in order_str
    assert "shipping_address" not in result["order"]


# Confirms that internal notes and risk scores are NEVER present.
def test_no_internal_fields(lookup):
    result = lookup.lookup("ORD-1007")
    order = result["order"]
    assert "internal" not in order
    assert "risk_score" not in order
    assert "warehouse_note" not in order
    assert "support_tags" not in order

    # Also verify string representation doesn't leak
    order_str = str(order)
    assert "82" not in order_str or "risk" not in order_str.lower()
    assert "fraud review" not in order_str.lower()


# Confirms that customer name is not in sanitized output.
def test_no_customer_name_in_output(lookup):
    result = lookup.lookup("ORD-1007")
    order_str = str(result["order"])
    assert "Ava Morgan" not in order_str


# --- Status-Specific Logic ---

# Confirms cancelled orders do NOT expose stale delivery information.
def test_cancelled_order_no_stale_eta(lookup):
    result = lookup.lookup("ORD-1004")
    assert result["success"] is True
    order = result["order"]
    assert order["status"] == "cancelled"
    # Stale delivery fields must be removed.
    assert "estimated_delivery" not in order
    assert "carrier" not in order
    assert "tracking_number" not in order


# Confirms returned orders do NOT expose stale shipping fields.
def test_returned_order_no_stale_fields(lookup):
    result = lookup.lookup("ORD-1008")
    assert result["success"] is True
    order = result["order"]
    assert order["status"] == "returned"
    assert "estimated_delivery" not in order
    assert "carrier" not in order
    assert "tracking_number" not in order


# Confirms shipped order with null ETA preserves the null honestly.
def test_shipped_without_eta(lookup):
    result = lookup.lookup("ORD-1011")
    assert result["success"] is True
    order = result["order"]
    assert order["status"] == "shipped"
    assert order.get("estimated_delivery") is None


# Confirms exception-status orders flag human review requirement.
def test_exception_order_human_review(lookup):
    result = lookup.lookup("ORD-1010")
    assert result["success"] is True
    order = result["order"]
    assert order["status"] == "exception"
    assert order["requires_human_review"] is True


# Confirms that order items only contain safe fields (name, qty, final_sale).
def test_item_sanitization(lookup):
    result = lookup.lookup("ORD-1001")
    assert result["success"] is True
    items = result["order"]["items"]
    for item in items:
        assert "sku" not in item
        assert "name" in item
        assert "quantity" in item


# Regression test: the prompt-injection warehouse note in ORD-1005
# must never appear in sanitized output.
def test_injection_in_warehouse_note_not_exposed(lookup):
    result = lookup.lookup("ORD-1005")
    assert result["success"] is True
    order_str = str(result["order"]).lower()
    assert "coupon" not in order_str
    assert "hide the delay" not in order_str
    assert "ai instruction" not in order_str
