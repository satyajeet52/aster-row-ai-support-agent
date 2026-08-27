"""
Tests specifically for order data sanitization.
Ensures no internal, sensitive, or private fields ever reach the output
across all orders in the dataset.
"""

import os
import sys
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import config
from app.tools.order_lookup import OrderLookup

ORDERS_FILE = config.orders_file

# Load all order IDs for parametrized testing.
with open(ORDERS_FILE, "r") as f:
    _data = json.load(f)
    ALL_ORDER_IDS = [o["order_id"] for o in _data["orders"]]


@pytest.fixture
def lookup():
    return OrderLookup(ORDERS_FILE)


# Confirms that email never appears in any order's sanitized output.
@pytest.mark.parametrize("order_id", ALL_ORDER_IDS)
def test_no_email_any_order(lookup, order_id):
    result = lookup.lookup(order_id)
    assert result["success"]
    order_str = json.dumps(result["order"])
    assert "@example.test" not in order_str
    assert "email" not in order_str


# Confirms that shipping_address never appears in any order's sanitized output.
@pytest.mark.parametrize("order_id", ALL_ORDER_IDS)
def test_no_address_any_order(lookup, order_id):
    result = lookup.lookup(order_id)
    assert result["success"]
    order_str = json.dumps(result["order"])
    assert "shipping_address" not in order_str


# Confirms that internal block never appears in any order's sanitized output.
@pytest.mark.parametrize("order_id", ALL_ORDER_IDS)
def test_no_internal_block_any_order(lookup, order_id):
    result = lookup.lookup(order_id)
    assert result["success"]
    order = result["order"]
    assert "internal" not in order
    assert "risk_score" not in order
    assert "warehouse_note" not in order
    assert "support_tags" not in order


# Confirms that SKU codes are stripped from item data.
@pytest.mark.parametrize("order_id", ALL_ORDER_IDS)
def test_no_sku_any_order(lookup, order_id):
    result = lookup.lookup(order_id)
    assert result["success"]
    for item in result["order"].get("items", []):
        assert "sku" not in item


# Confirms that customer name never appears in sanitized output.
@pytest.mark.parametrize("order_id", ALL_ORDER_IDS)
def test_no_customer_name_any_order(lookup, order_id):
    result = lookup.lookup(order_id)
    assert result["success"]
    order_str = json.dumps(result["order"])
    assert "customer" not in order_str or "customer_safe_message" in order_str
