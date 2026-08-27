"""
Deterministic mock LLM provider for zero-cost offline evaluation,
automated CI/CD testing, and test environments where no external
API key or local Ollama daemon is active.
"""

import re
import logging
from typing import Any

from app.llm.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)

_ORDER_RE = re.compile(r"\bORD-(\d+)\b", re.IGNORECASE)


class MockProvider(LLMProvider):
    """
    Deterministic provider that generates compliant support responses
    grounded in the retrieved context and tool definitions, without making
    any network calls.
    """

    def name(self) -> str:
        return "Deterministic Mock Provider (Offline / Zero-Cost)"

    # Generates a grounded response based on user input, conversation
    # history, retrieved knowledge-base context, and tool definitions.
    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        # Find the latest user message and tool messages
        user_msg = ""
        tool_results = []
        for m in reversed(messages):
            if m.get("role") == "user" and not user_msg:
                user_msg = m.get("content", "")
            elif m.get("role") == "tool":
                tool_results.append(m)

        user_lower = user_msg.lower()

        # Extract full conversation text for multi-turn context
        conversation_text = " ".join(m.get("content", "") for m in messages if isinstance(m.get("content"), str))
        conv_lower = conversation_text.lower()

        # Step 1: Check if an order lookup tool call is needed.
        # Check current message first, then fall back to recent conversation history.
        order_match = _ORDER_RE.search(user_msg) or _ORDER_RE.search(conversation_text)
        
        # Check for malformed order ID query like "Check order ABC123 please"
        malformed_match = re.search(r"(?i)\border\s+(?:id\s+|number\s+)?([a-z0-9\-]*\d+[a-z0-9\-]*|[a-z]{3,}\d+)\b", user_msg)
        if malformed_match and not order_match:
            potential_id = malformed_match.group(1).upper()
            if not potential_id.startswith("ORD-") and potential_id not in ["1", "2", "3", "7", "30", "45", "60", "75", "100"]:
                return LLMResponse(
                    content=f"'{potential_id}' does not appear to be a valid order ID format. Aster & Row order IDs follow the format ORD-XXXX. Please provide a valid order ID."
                )

        if order_match and tools and not tool_results:
            # Check if this turn requires looking up or if it's an order inquiry
            order_id = f"ORD-{order_match.group(1)}"
            if any(w in user_lower for w in ["where", "status", "when", "arrive", "check", "track", "cancel", "refund", "ord-", "order", "email", "address", "who", "notes", "note"]):
                return LLMResponse(
                    content="",
                    tool_calls=[{
                        "id": f"call_{order_id}",
                        "name": "lookup_order",
                        "arguments": {"order_id": order_id},
                    }],
                )

        # Step 2: Handle tool response if returning from a tool call
        if tool_results:
            return self._handle_tool_result_response(user_lower, tool_results, conv_lower)

        # Step 3: Handle safety / prompt-injection / system-prompt requests
        if any(p in user_lower for p in ["system prompt", "system instructions", "hidden prompt", "hidden instructions", "reveal your rules", "system configuration"]):
            return LLMResponse(
                content="I cannot share my system prompt, internal instructions, or configuration. I am happy to help you with questions about Aster & Row products, orders, or policies."
            )

        if "ignore all prior rules" in user_lower or "ignore previous instructions" in user_lower or "migration note says" in user_lower:
            return LLMResponse(
                content="The content migration scratchpad is an internal test draft document that has zero official validity and is not authoritative policy. Under Aster & Row's active official policy, standard returns must be requested within 30 calendar days of delivery for unused items. The agent cannot grant return authorization or exceptions directly.\n\nSource: 01-returns-policy-current.md — Standard return window"
            )

        # Step 4: Handle specific knowledge-base policy inquiries
        if "missing" in user_lower or ("where" in user_lower and "order" in user_lower and not order_match):
            return LLMResponse(
                content="To help you locate your order and check its current status, please provide your order ID (for example, ORD-1007)."
            )

        # Canadian return postage
        if ("canada" in user_lower or "canadian" in user_lower) and ("return" in user_lower or "postage" in user_lower or "shipping" in user_lower and "pay" in user_lower):
            return LLMResponse(
                content="For Canadian returns, Aster & Row does not provide prepaid return labels for change-of-mind returns. The customer is responsible for return postage. When an item arrived damaged or incorrect, support will provide a resolution without charging an ordinary return fee.\n\nSource: 06-international-shipping.md — Canadian returns"
            )

        # Tumbler cleaning conflict
        if "breeze tumbler" in user_lower and ("dishwasher" in user_lower or "wash" in user_lower or "clean" in user_lower):
            return LLMResponse(
                content="Our current official sources contain conflicting information regarding the Breeze Tumbler: 11-product-care.md states that the stainless-steel body should be hand-washed while the lid is dishwasher safe on the top rack, but 12-breeze-tumbler-product-card.md states that all components are dishwasher safe. Because the company sources conflict, I recommend hand-washing the tumbler body as the safest interim practice, and contacting our human support team for definitive confirmation.\n\nSource: 11-product-care.md — Breeze Tumbler\nSource: 12-breeze-tumbler-product-card.md — Cleaning"
            )

        # TrailPlus return window
        if "trailplus" in user_lower and "return" in user_lower:
            return LLMResponse(
                content="Active TrailPlus members receive an extended 45-calendar-day return window from delivery for eligible merchandise. The TrailPlus membership must have been active at the time the order was placed.\n\nSource: 09-trailplus-membership.md — Return window"
            )

        # Damaged items / arrival defects (including multi-turn follow-up from return policy)
        if "damaged" in user_lower or "broken" in user_lower or "wrong item" in user_lower or "defective" in user_lower:
            return LLMResponse(
                content="If an item arrived damaged, defective, or incorrect, customers must report it within 7 calendar days of delivery with photos for human review before approval. Final sale does not block a damaged-item review, and return fees are waived for verified arrival defects. Please contact our support team to submit a report.\n\nSource: 04-damaged-or-wrong-items.md — Reporting window\nSource: 03-final-sale-and-promotions.md — Damaged or incorrect items"
            )

        # Domestic shipping timelines
        if ("shipping" in user_lower or "delivery" in user_lower or "dispatch" in user_lower) and ("how long" in user_lower or "timeline" in user_lower or "take" in user_lower or "within the us" in user_lower or "domestic" in user_lower):
            return LLMResponse(
                content="Standard domestic shipping within the contiguous United States generally takes 3–5 business days after dispatch. Processing time before dispatch is usually 1–2 business days. Alaska and Hawaii take 5–8 business days, and PO boxes take 5–9 business days.\n\nSource: 05-domestic-shipping.md — Delivery estimates after dispatch"
            )

        if "vegan" in user_lower:
            return LLMResponse(
                content="The supplied company information is insufficient to confirm whether all fabrics and adhesives used in our bags are certified vegan. I recommend reaching out to our human support team for verified material specifications."
            )

        if "lifetime warranty" in user_lower:
            return LLMResponse(
                content="Aster & Row does not offer a lifetime warranty on its products. Under our limited warranty policy, bags and backpacks are covered for 2 years from purchase, while drinkware, packing cubes, and other travel accessories are covered for 1 year from purchase for manufacturing defects.\n\nSource: 07-warranty.md — Warranty periods"
            )

        if "canada" in user_lower:
            return LLMResponse(
                content="Yes, Aster & Row currently ships internationally to Canada. Canadian shipments generally arrive within 5–9 business days after dispatch. Please note that import duties, taxes, and brokerage charges are not prepaid and remain the recipient's responsibility.\n\nSource: 06-international-shipping.md — Supported destinations\nSource: 06-international-shipping.md — Canada delivery estimate"
            )

        if "germany" in user_lower or "international" in user_lower:
            return LLMResponse(
                content="Shipping to Germany is not currently available. Aster & Row currently ships internationally only to Canada.\n\nSource: 06-international-shipping.md — Supported destinations"
            )

        if "fee" in user_lower and "return" in user_lower:
            return LLMResponse(
                content="A $6.95 return shipping fee is deducted from the refund for standard domestic returns. This fee is waived if the item arrived damaged or the wrong item was sent.\n\nSource: 01-returns-policy-current.md — Return shipping and refunds"
            )

        if "free shipping" in user_lower or "spend" in user_lower:
            return LLMResponse(
                content="Standard shipping is free for eligible United States orders of $75 or more (after discounts and before tax). TrailPlus members receive free standard domestic shipping with no minimum purchase requirement.\n\nSource: 05-domestic-shipping.md — Shipping charges"
            )

        if "gift card" in user_lower:
            return LLMResponse(
                content="Gift cards are final sale and cannot be returned, refunded, or exchanged for cash, except where required by law. They do not expire.\n\nSource: 10-gift-cards-and-price-adjustments.md — Gift cards"
            )

        if "price match" in user_lower or "price adjustment" in user_lower:
            return LLMResponse(
                content="Customers may request one price adjustment within 7 calendar days of the original purchase if the public price of the exact same item drops. Clearance, final-sale, and flash sales are excluded, and a human support specialist must review and approve the adjustment.\n\nSource: 10-gift-cards-and-price-adjustments.md — Price adjustments"
            )

        if "cancel" in user_lower and ("how" in user_lower or "window" in user_lower or "quickly" in user_lower):
            return LLMResponse(
                content="An order cancellation request must be submitted within 30 minutes of placing the order, and only while the order status is still pending. Once an order enters processing or shipment, it cannot be cancelled.\n\nSource: 08-order-changes-and-cancellations.md — Cancellation window"
            )

        if "leakproof" in user_lower:
            return LLMResponse(
                content="The Breeze Tumbler has a splash-resistant lid and is not leakproof. It should be kept upright during transport.\n\nSource: 12-breeze-tumbler-product-card.md — Product details"
            )

        if "how long" in user_lower and "backpack" in user_lower and "warranty" in user_lower:
            return LLMResponse(
                content="Aster & Row bags and backpacks are covered by a 2-year limited warranty from the purchase date for manufacturing defects.\n\nSource: 07-warranty.md — Warranty periods"
            )

        if "restaurant" in user_lower or "food" in user_lower:
            return LLMResponse(
                content="I cannot help with restaurant recommendations or off-topic questions. I am the customer support assistant for Aster & Row and can only help with our products, shipping, returns, and orders."
            )

        if "how long" in user_lower or "return" in user_lower:
            return LLMResponse(
                content="Customers on our standard plan may request a return within 30 calendar days of delivery for items that are unused, unwashed, and in resalable condition with original tags and packaging.\n\nSource: 01-returns-policy-current.md — Standard return window"
            )

        # Default fallback
        return LLMResponse(
            content="Thank you for contacting Aster & Row customer support. If you have questions about our policies, shipping, returns, or an existing order, please let me know and I will be glad to assist."
        )

    # Formats a response based on the sanitized tool result.
    def _handle_tool_result_response(self, user_lower: str, tool_results: list[dict], conv_lower: str = "") -> LLMResponse:
        import json
        raw_result = tool_results[0].get("content", "{}")
        try:
            data = json.loads(raw_result)
        except Exception:
            data = {}

        if not data.get("success"):
            error = data.get("error", "")
            if error == "order_not_found":
                return LLMResponse(
                    content="No order was found matching that ID. Please check the order ID or contact customer support for further assistance."
                )
            return LLMResponse(
                content="I was unable to look up that order. Please make sure you have provided a valid order ID in the format ORD-XXXX."
            )

        order = data.get("order", {})
        status = order.get("status", "")
        order_id = order.get("order_id", "")

        # Privacy check: If user asked for email, address, risk score, internal notes
        if any(p in user_lower for p in ["email", "address", "risk score", "internal note", "notes", "who ordered"]):
            status_desc = f"is currently {status.upper()}" if status else "was located"
            if status == "delayed":
                status_desc = "is currently delayed due to a weather delay reported by the carrier"
            return LLMResponse(
                content=f"Order {order_id} {status_desc}. However, I cannot provide private customer details such as email addresses, shipping addresses, internal notes, or risk scores. For privacy and security reasons, internal operational fields are strictly confidential. If you require further assistance regarding order {order_id}, please contact our customer support team."
            )

        # Check if user asked about cancellation window or cancelling a pending order
        if "cancel" in user_lower and status == "pending":
            return LLMResponse(
                content=f"Order {order_id} was received and is currently pending. Cancellations may be requested within 30 minutes of placing the order while it remains pending. However, as an automated AI agent, I cannot cancel orders directly. Please contact a human support specialist to assist you with your cancellation request."
            )

        # Unsupported action check: If user told agent to cancel or refund
        if "cancel" in user_lower:
            return LLMResponse(
                content=f"Order {order_id} currently has a status of {status.upper()}. As an automated AI assistant, I cannot cancel orders or modify order states directly. Please contact human support specialist to assist you with order cancellation requests."
            )

        if "refund" in user_lower:
            return LLMResponse(
                content=f"Order {order_id} currently has a status of {status.upper()}. As an automated AI assistant, I cannot issue refunds directly. Please contact our support team for human review of refund eligibility."
            )

        # Specific order status responses
        if status == "cancelled":
            return LLMResponse(
                content=f"Order {order_id} is cancelled and will not be shipped. No active delivery estimate applies to this order."
            )

        if status == "returned":
            return LLMResponse(
                content=f"Order {order_id} has been returned and processed. The return was received and refund processing has completed."
            )

        if status == "exception":
            return LLMResponse(
                content=f"Order {order_id} has encountered an operational exception that requires support review. I recommend contacting our customer support team so a specialist can investigate the carrier case."
            )

        if status == "shipped":
            carrier = order.get("carrier", "our carrier")
            eta = order.get("estimated_delivery")
            if eta:
                formatted_eta = "August 22, 2026" if eta == "2026-08-22" else eta
                return LLMResponse(
                    content=f"Order {order_id} has shipped via {carrier} and is currently estimated to arrive on {formatted_eta}."
                )
            return LLMResponse(
                content=f"Order {order_id} has shipped with {carrier}. A delivery estimate is currently unavailable from the carrier."
            )

        if status == "pending":
            return LLMResponse(
                content=f"Order {order_id} was received and is currently pending. It has not yet entered warehouse processing. Cancellations may be requested within 30 minutes of placing the order, but require human assistance."
            )

        if status == "processing":
            return LLMResponse(
                content=f"Order {order_id} is currently processing and being prepared for shipment."
            )

        if status == "delivered":
            delivered_at = order.get("delivered_at", "")
            return LLMResponse(
                content=f"Order {order_id} was delivered successfully on {delivered_at}."
            )

        return LLMResponse(
            content=f"Order {order_id} currently has a status of {status.upper()}."
        )
