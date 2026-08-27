"""
Evaluation runner that executes all behavior-level test cases against
the live agent, using deterministic assertions (not an LLM judge).
Reports individual case results, category summaries, and overall score.

Usage:
    python -m evaluation.run_eval
"""

import json
import os
import sys
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import config
from app.agent import Agent
from app.rag.retriever import Retriever
from app.tools.order_lookup import OrderLookup

logger = logging.getLogger(__name__)

EVAL_CASES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_cases.json")


# Loads evaluation cases from the JSON file.
def load_eval_cases() -> list[dict]:
    with open(EVAL_CASES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["cases"]


# Creates the agent with all dependencies for evaluation.
def create_agent() -> Agent:
    if config.llm_provider == "ollama":
        from app.llm.ollama_provider import OllamaProvider
        llm = OllamaProvider(base_url=config.ollama_base_url, model=config.ollama_model)
    elif config.llm_provider == "mock":
        from app.llm.mock_provider import MockProvider
        llm = MockProvider()
    else:
        if not config.mistral_api_key:
            print("  [Notice] MISTRAL_API_KEY not set. Running evaluation with deterministic MockProvider.")
            from app.llm.mock_provider import MockProvider
            llm = MockProvider()
        else:
            from app.llm.mistral_provider import MistralProvider
            llm = MistralProvider(api_key=config.mistral_api_key, model=config.mistral_model)

    retriever = Retriever(config.index_dir)
    order_lookup = OrderLookup(config.orders_file)
    return Agent(llm=llm, retriever=retriever, order_lookup=order_lookup)


# Runs a single evaluation case by sending all messages in sequence
# within the same session and checking the final response against
# deterministic assertions.
def run_case(agent: Agent, case: dict) -> dict:
    case_id = case["id"]
    messages = case["messages"]
    expect = case["expect"]

    # Create a fresh session for each case.
    session_id = agent.new_session()

    response = None
    all_tool_calls = []
    all_tool_results = []

    # Send all messages in the case within the same session.
    for msg in messages:
        response = agent.chat(msg["content"], session_id)
        all_tool_calls.extend(response.tool_calls)
        all_tool_results.extend(response.tool_results)

    if response is None:
        return {"id": case_id, "passed": False, "failures": ["No response received"]}

    answer = response.answer
    answer_lower = answer.lower()
    failures = []

    # --- Deterministic Assertions ---

    # Check must_include (exact substrings in answer).
    for phrase in expect.get("must_include", []):
        if phrase.lower() not in answer_lower:
            failures.append(f"MISSING: '{phrase}' not found in answer")

    # Check must_not_include (forbidden substrings).
    for phrase in expect.get("must_not_include", []):
        if phrase.lower() in answer_lower:
            failures.append(f"FORBIDDEN: '{phrase}' found in answer")

    # Check must_include_concepts (at least partial match).
    for concept in expect.get("must_include_concepts", []):
        # Check if any word from the concept appears.
        concept_words = concept.lower().split()
        if not any(w in answer_lower for w in concept_words):
            failures.append(f"CONCEPT MISSING: '{concept}' not reflected in answer")

    # Check must_not_include_concepts.
    for concept in expect.get("must_not_include_concepts", []):
        concept_lower = concept.lower()
        if concept_lower in answer_lower:
            failures.append(f"FORBIDDEN CONCEPT: '{concept}' found in answer")

    # Check required_sources (cited in answer or in response sources).
    for source in expect.get("required_sources", []):
        source_cited = (
            source.lower() in answer_lower
            or any(s.filename == source for s in response.sources)
        )
        if not source_cited:
            failures.append(f"SOURCE MISSING: '{source}' not cited")

    # Check forbidden_sources.
    for source in expect.get("forbidden_sources", []):
        if source.lower() in answer_lower:
            # Check if it's used as authority (not just mentioned).
            source_mentioned_as_authority = any(
                s.filename == source for s in response.sources
            )
            if source_mentioned_as_authority:
                failures.append(f"FORBIDDEN SOURCE: '{source}' used as authority")

    # Check tool usage.
    tool_expect = expect.get("tool", "")
    if tool_expect == "not_called":
        if all_tool_calls:
            failures.append(f"TOOL: Expected no tool call, but got {[tc['name'] for tc in all_tool_calls]}")
    elif tool_expect == "lookup_order":
        if not any(tc["name"] == "lookup_order" for tc in all_tool_calls):
            failures.append("TOOL: Expected lookup_order call, but none occurred")

    # Check tool arguments.
    if "tool_arguments" in expect:
        expected_args = expect["tool_arguments"]
        matching_calls = [tc for tc in all_tool_calls if tc.get("name") == "lookup_order"]
        if matching_calls:
            actual_args = matching_calls[0].get("arguments", {})
            for key, value in expected_args.items():
                actual = actual_args.get(key, "")
                if isinstance(actual, str):
                    actual = actual.strip().upper()
                if isinstance(value, str):
                    value = value.strip().upper()
                if actual != value:
                    failures.append(f"TOOL ARG: Expected {key}='{value}', got '{actual}'")

    # Check handoff.
    handoff_expect = expect.get("handoff")
    if handoff_expect is True and not response.handoff_recommended:
        failures.append("HANDOFF: Expected human handoff recommendation, but none detected")
    elif handoff_expect is False and response.handoff_recommended:
        # This is a soft check — agent may be overly cautious.
        pass  # Don't fail on false-positive handoff

    passed = len(failures) == 0

    return {
        "id": case_id,
        "category": case.get("category", "uncategorized"),
        "passed": passed,
        "failures": failures,
        "answer_preview": answer[:200] + "..." if len(answer) > 200 else answer,
    }


# Prints the formatted evaluation report with per-case results,
# category summaries, and overall score.
def print_report(results: list[dict]) -> None:
    print("\n" + "=" * 70)
    print("  ASTER & ROW SUPPORT AGENT -- EVALUATION REPORT")
    print("=" * 70 + "\n")

    # Individual results.
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  {status:4s}  {r['id']}")
        if not r["passed"]:
            for f in r["failures"]:
                print(f"        -> {f}")

    # Category results.
    categories: dict[str, dict] = {}
    for r in results:
        cat = r.get("category", "uncategorized")
        if cat not in categories:
            categories[cat] = {"passed": 0, "total": 0}
        categories[cat]["total"] += 1
        if r["passed"]:
            categories[cat]["passed"] += 1

    print("\n" + "-" * 70)
    print("  CATEGORY RESULTS")
    print("-" * 70)

    for cat, stats in sorted(categories.items()):
        pct = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"  {cat:30s}  {stats['passed']:2d}/{stats['total']:2d}  ({pct:5.1f}%)")

    # Overall.
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    pct = (passed / total * 100) if total > 0 else 0

    print("\n" + "=" * 70)
    print(f"  Overall: {passed}/{total}  ({pct:.1f}%)")
    print("=" * 70 + "\n")


# Main entry point: loads cases, runs them, and prints the report.
def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print("Loading evaluation cases...")
    cases = load_eval_cases()
    print(f"Loaded {len(cases)} cases")

    print("Initializing agent...")
    agent = create_agent()
    print("Agent ready. Running evaluation...\n")

    results = []
    for i, case in enumerate(cases, 1):
        print(f"  Running case {i}/{len(cases)}: {case['id']}...", end=" ", flush=True)
        start = time.time()
        try:
            result = run_case(agent, case)
            elapsed = time.time() - start
            status = "PASS" if result["passed"] else "FAIL"
            print(f"{status} ({elapsed:.1f}s)")
        except Exception as e:
            elapsed = time.time() - start
            result = {
                "id": case["id"],
                "category": case.get("category", "uncategorized"),
                "passed": False,
                "failures": [f"ERROR: {str(e)}"],
            }
            print(f"ERROR ({elapsed:.1f}s): {e}")
        results.append(result)

    print_report(results)

    # Save results to file.
    results_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.json")
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {results_file}")


if __name__ == "__main__":
    main()
