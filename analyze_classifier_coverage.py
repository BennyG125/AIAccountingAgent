#!/usr/bin/env python3
"""Comprehensive analysis of 311 competition requests against the classifier and execution plans.

Reads ALL 311 JSON request files, runs the classifier logic, and produces
a full coverage report.
"""

import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Add project root to path so we can import the classifier
sys.path.insert(0, str(Path(__file__).parent))

from execution_plans._classifier import detect_language, classify_task, LANG_PATTERNS, UNIVERSAL_PATTERNS

# --------------------------------------------------------------------------
# Deterministic whitelist (copied from deterministic_executor.py)
# --------------------------------------------------------------------------
DETERMINISTIC_WHITELIST = {
    "create_product", "create_invoice", "create_customer", "create_supplier",
    "create_departments", "create_employee", "credit_note", "register_payment",
    "create_order", "employee_onboarding", "register_supplier_invoice",
    "travel_expense", "project_lifecycle", "overdue_invoice_reminder",
    "bank_reconciliation", "cost_analysis_projects", "forex_payment",
    "register_hours", "fixed_price_project", "monthly_closing",
    "year_end_close", "year_end_corrections", "run_salary",
    "custom_dimension", "create_project", "reverse_payment",
}

# Plans that have actual execution plan files
PLANS_WITH_FILES = {
    "create_customer", "create_employee", "create_supplier", "create_product",
    "create_departments", "create_invoice", "credit_note", "register_payment",
    "register_supplier_invoice", "register_hours", "run_salary",
    "custom_dimension", "fixed_price_project", "forex_payment",
    "overdue_invoice_reminder", "employee_onboarding", "travel_expense",
    "cost_analysis_projects", "bank_reconciliation", "year_end_corrections",
    "monthly_closing", "year_end_close", "project_lifecycle",
    "create_project", "reverse_payment", "create_order",
}

# Language code to name mapping (used by detect_language_gemini)
LANG_CODE_TO_NAME = {
    "no": "Norwegian", "nn": "Nynorsk", "de": "German",
    "fr": "French", "es": "Spanish", "pt": "Portuguese", "en": "English",
}

# Inverse: name to code
LANG_NAME_TO_CODE = {
    "norwegian": "no", "norsk": "no", "bokmål": "no", "bokmal": "no",
    "nynorsk": "nn", "german": "de", "deutsch": "de",
    "french": "fr", "français": "fr", "francais": "fr",
    "spanish": "es", "español": "es", "espanol": "es",
    "portuguese": "pt", "português": "pt", "portugues": "pt",
    "english": "en",
}


def load_all_requests(requests_dir: str) -> list[dict]:
    """Load all JSON request files."""
    requests = []
    for filename in sorted(os.listdir(requests_dir)):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(requests_dir, filename)
        with open(filepath) as f:
            data = json.load(f)
        data["_filename"] = filename
        requests.append(data)
    return requests


def extract_prompt(req: dict) -> str:
    """Extract prompt text from request, trying multiple field names."""
    return (
        req.get("prompt")
        or req.get("task_prompt")
        or req.get("task")
        or req.get("description")
        or ""
    )


def analyze_all(requests: list[dict]):
    """Run full analysis."""

    # =====================================================================
    # Phase 1: Run classifier on every request
    # =====================================================================
    results = []
    for req in requests:
        prompt = extract_prompt(req)

        # Run our heuristic language detection
        lang_code = detect_language(prompt)
        lang_name = LANG_CODE_TO_NAME.get(lang_code, "Unknown")

        # Run classifier (simulating the pipeline: detect lang -> classify)
        classified_type = classify_task(prompt, language=lang_name)

        # Tagged info from the JSON
        tagged_type = req.get("task_type")
        tagged_tier = req.get("tier")

        # Check coverage
        has_whitelist = classified_type in DETERMINISTIC_WHITELIST if classified_type else False
        has_plan = classified_type in PLANS_WITH_FILES if classified_type else False

        # Normalize tier
        raw_tier = tagged_tier
        if isinstance(raw_tier, str):
            raw_tier = int(raw_tier.replace("T", "").strip()) if raw_tier.replace("T", "").strip().isdigit() else None
        elif isinstance(raw_tier, (int, float)):
            raw_tier = int(raw_tier)

        results.append({
            "filename": req["_filename"],
            "task_id": req.get("task_id", ""),
            "prompt": prompt,
            "prompt_preview": prompt[:120],
            "detected_lang": lang_code,
            "detected_lang_name": lang_name,
            "classified_type": classified_type,
            "tagged_type": tagged_type,
            "tagged_tier": raw_tier,
            "has_whitelist": has_whitelist,
            "has_plan": has_plan,
            "files_count": len(req.get("files", [])),
        })

    # =====================================================================
    # Section A: Language Distribution
    # =====================================================================
    print("=" * 80)
    print("A. LANGUAGE DISTRIBUTION")
    print("=" * 80)

    lang_counter = Counter(r["detected_lang"] for r in results)
    for lang, count in lang_counter.most_common():
        name = LANG_CODE_TO_NAME.get(lang, lang)
        pct = count / len(results) * 100
        print(f"  {name:15s} ({lang:2s}): {count:4d} requests ({pct:.1f}%)")

    print(f"\n  Total: {len(results)} requests")

    # Language detection edge cases
    print("\n  --- Potential Language Misdetection Cases ---")
    misdetect_candidates = []
    for r in results:
        prompt_lower = r["prompt"].lower()
        # Check if a Norwegian prompt might be misdetected (common words overlap)
        # Check for false positives on "de" language (German) due to "de" appearing in
        # Portuguese/Spanish/French text
        if r["detected_lang"] == "de" and not any(c in prompt_lower for c in "äöüß"):
            misdetect_candidates.append(r)
        # Check for "no" detected but prompt seems English
        elif r["detected_lang"] == "no" and not any(c in prompt_lower for c in "øåæ"):
            misdetect_candidates.append(r)
        # Check for "en" detected but prompt has accented chars
        elif r["detected_lang"] == "en" and any(c in prompt_lower for c in "éèêëàâùûüïôœçñ¿¡ãõäöüß"):
            misdetect_candidates.append(r)

    if misdetect_candidates:
        for r in misdetect_candidates[:15]:
            print(f"    [{r['detected_lang']}] {r['filename']}: {r['prompt_preview']}")
    else:
        print("    None found")

    # =====================================================================
    # Section B: Task Type Distribution
    # =====================================================================
    print("\n" + "=" * 80)
    print("B. TASK TYPE DISTRIBUTION (Classifier Output)")
    print("=" * 80)

    classified_counter = Counter(r["classified_type"] for r in results)
    for task_type, count in classified_counter.most_common():
        label = task_type or "(None / unclassified)"
        pct = count / len(results) * 100
        in_whitelist = "WL" if task_type and task_type in DETERMINISTIC_WHITELIST else "  "
        has_plan_flag = "PL" if task_type and task_type in PLANS_WITH_FILES else "  "
        print(f"  [{in_whitelist}][{has_plan_flag}] {label:35s}: {count:4d} ({pct:.1f}%)")

    # Tagged task types from the JSON for comparison
    print("\n  --- Tagged Task Type Distribution (from JSON metadata) ---")
    tagged_counter = Counter(r["tagged_type"] for r in results)
    for task_type, count in tagged_counter.most_common():
        label = task_type or "(None / untagged)"
        pct = count / len(results) * 100
        print(f"  {label:35s}: {count:4d} ({pct:.1f}%)")

    # =====================================================================
    # Section C: Classifier Coverage
    # =====================================================================
    print("\n" + "=" * 80)
    print("C. CLASSIFIER COVERAGE")
    print("=" * 80)

    classified = [r for r in results if r["classified_type"] is not None]
    unclassified = [r for r in results if r["classified_type"] is None]

    print(f"  Classified:   {len(classified):4d} / {len(results)} ({len(classified)/len(results)*100:.1f}%)")
    print(f"  Unclassified: {len(unclassified):4d} / {len(results)} ({len(unclassified)/len(results)*100:.1f}%)")

    # =====================================================================
    # Section D: Plan Coverage
    # =====================================================================
    print("\n" + "=" * 80)
    print("D. PLAN COVERAGE (of classified requests)")
    print("=" * 80)

    with_whitelist = [r for r in classified if r["has_whitelist"]]
    without_whitelist = [r for r in classified if not r["has_whitelist"]]
    with_plan = [r for r in classified if r["has_plan"]]
    without_plan = [r for r in classified if not r["has_plan"]]

    print(f"  In whitelist:     {len(with_whitelist):4d} / {len(classified)} ({len(with_whitelist)/len(classified)*100:.1f}%)")
    print(f"  NOT in whitelist: {len(without_whitelist):4d} / {len(classified)} ({len(without_whitelist)/len(classified)*100:.1f}%)")
    print(f"  Has plan file:    {len(with_plan):4d} / {len(classified)} ({len(with_plan)/len(classified)*100:.1f}%)")

    # Which classified types have NO plan?
    classified_types_no_plan = set()
    for r in classified:
        if not r["has_plan"]:
            classified_types_no_plan.add(r["classified_type"])

    if classified_types_no_plan:
        print(f"\n  Classified types with NO execution plan:")
        for t in sorted(classified_types_no_plan):
            count = sum(1 for r in classified if r["classified_type"] == t and not r["has_plan"])
            print(f"    {t}: {count} requests")

    # Which classified types are NOT in whitelist?
    classified_types_no_wl = set()
    for r in classified:
        if not r["has_whitelist"]:
            classified_types_no_wl.add(r["classified_type"])

    if classified_types_no_wl:
        print(f"\n  Classified types NOT in deterministic whitelist:")
        for t in sorted(classified_types_no_wl):
            count = sum(1 for r in classified if r["classified_type"] == t and not r["has_whitelist"])
            print(f"    {t}: {count} requests → falls through to Claude")

    # Full pipeline: classified + whitelisted + has plan = deterministic execution
    deterministic = [r for r in results if r["classified_type"] and r["has_whitelist"] and r["has_plan"]]
    claude_fallback = [r for r in results if not (r["classified_type"] and r["has_whitelist"] and r["has_plan"])]

    print(f"\n  PIPELINE SUMMARY:")
    print(f"    Deterministic execution: {len(deterministic):4d} / {len(results)} ({len(deterministic)/len(results)*100:.1f}%)")
    print(f"    Claude fallback:         {len(claude_fallback):4d} / {len(results)} ({len(claude_fallback)/len(results)*100:.1f}%)")

    print(f"\n  By tier:")
    all_tiers = sorted(set(r["tagged_tier"] for r in results if r["tagged_tier"] is not None))
    for tier in all_tiers:
        tier_reqs = [r for r in results if r["tagged_tier"] == tier]
        tier_det = [r for r in tier_reqs if r["classified_type"] and r["has_whitelist"] and r["has_plan"]]
        print(f"    Tier {tier}: {len(tier_det)}/{len(tier_reqs)} deterministic ({len(tier_det)/len(tier_reqs)*100:.1f}%)")

    # =====================================================================
    # Section E: Misclassification Risks
    # =====================================================================
    print("\n" + "=" * 80)
    print("E. MISCLASSIFICATION RISKS")
    print("=" * 80)

    misclass_cases = []
    for r in results:
        classified = r["classified_type"]
        tagged = r["tagged_type"]

        if classified and tagged and classified != tagged:
            misclass_cases.append(r)

    print(f"  Classifier disagrees with tagged type: {len(misclass_cases)} cases")

    if misclass_cases:
        # Group by (classified, tagged) pair
        pair_counter = Counter((r["classified_type"], r["tagged_type"]) for r in misclass_cases)
        print(f"\n  Misclassification patterns (classifier → tagged):")
        for (classified, tagged), count in pair_counter.most_common():
            print(f"    {classified:35s} → {tagged:35s}: {count}x")

        print(f"\n  Detailed misclassification examples (first 30):")
        for r in misclass_cases[:30]:
            print(f"    [{r['filename']}]")
            print(f"      Classifier: {r['classified_type']}")
            print(f"      Tagged:     {r['tagged_type']}")
            print(f"      Prompt:     {r['prompt_preview']}")
            print()

    # =====================================================================
    # Section E2: Specific risky patterns
    # =====================================================================
    print("  --- Specific Pattern Collision Risks ---")

    # Check: "project" keyword matching create_project when it should be project_lifecycle
    project_issues = [r for r in results
                      if r["classified_type"] == "create_project"
                      and r["tagged_type"] and "lifecycle" in r["tagged_type"]]
    print(f"\n  create_project classified but tagged as project_lifecycle: {len(project_issues)}")
    for r in project_issues[:5]:
        print(f"    {r['filename']}: {r['prompt_preview']}")

    # Check: "invoice" matching create_invoice when it should be register_supplier_invoice
    invoice_issues = [r for r in results
                      if r["classified_type"] == "create_invoice"
                      and r["tagged_type"] and "supplier" in r["tagged_type"]]
    print(f"\n  create_invoice classified but tagged as register_supplier_invoice: {len(invoice_issues)}")
    for r in invoice_issues[:5]:
        print(f"    {r['filename']}: {r['prompt_preview']}")

    # Check: "payment" matching register_payment when it should be something else
    payment_issues = [r for r in results
                      if r["classified_type"] == "register_payment"
                      and r["tagged_type"] and r["tagged_type"] != "register_payment"]
    print(f"\n  register_payment classified but tagged as something else: {len(payment_issues)}")
    for r in payment_issues[:10]:
        print(f"    Tagged: {r['tagged_type']:30s} | {r['prompt_preview']}")

    # Check: "customer" matching create_customer when really about register_payment or overdue_invoice
    customer_issues = [r for r in results
                       if r["classified_type"] == "create_customer"
                       and r["tagged_type"] and r["tagged_type"] != "create_customer"]
    print(f"\n  create_customer classified but tagged differently: {len(customer_issues)}")
    for r in customer_issues[:10]:
        print(f"    Tagged: {r['tagged_type']:30s} | {r['prompt_preview']}")

    # Check: "order" matching create_order when it might be about order flow (invoice)
    order_issues = [r for r in results
                    if r["classified_type"] == "create_order"
                    and r["tagged_type"] and r["tagged_type"] != "create_order"]
    print(f"\n  create_order classified but tagged differently: {len(order_issues)}")
    for r in order_issues[:10]:
        print(f"    Tagged: {r['tagged_type']:30s} | {r['prompt_preview']}")

    # Check: "dimension" matching custom_dimension when prompt is really about something else
    dim_issues = [r for r in results
                  if r["classified_type"] == "custom_dimension"
                  and r["tagged_type"] and r["tagged_type"] != "custom_dimension"]
    print(f"\n  custom_dimension classified but tagged differently: {len(dim_issues)}")
    for r in dim_issues[:10]:
        print(f"    Tagged: {r['tagged_type']:30s} | {r['prompt_preview']}")

    # Check: supplier matching create_supplier when tagged differently
    supplier_issues = [r for r in results
                       if r["classified_type"] == "create_supplier"
                       and r["tagged_type"] and r["tagged_type"] != "create_supplier"]
    print(f"\n  create_supplier classified but tagged differently: {len(supplier_issues)}")
    for r in supplier_issues[:10]:
        print(f"    Tagged: {r['tagged_type']:30s} | {r['prompt_preview']}")

    # Check: employee matching create_employee when tagged differently
    employee_issues = [r for r in results
                       if r["classified_type"] == "create_employee"
                       and r["tagged_type"] and r["tagged_type"] != "create_employee"]
    print(f"\n  create_employee classified but tagged differently: {len(employee_issues)}")
    for r in employee_issues[:10]:
        print(f"    Tagged: {r['tagged_type']:30s} | {r['prompt_preview']}")

    # =====================================================================
    # Section F: Unclassified Request Analysis
    # =====================================================================
    print("\n" + "=" * 80)
    print("F. UNCLASSIFIED REQUEST ANALYSIS")
    print("=" * 80)

    unclassified = [r for r in results if r["classified_type"] is None]

    if unclassified:
        print(f"\n  {len(unclassified)} requests would fall through to Claude:")

        # Group by tagged type
        unclass_by_tag = Counter(r["tagged_type"] for r in unclassified)
        print(f"\n  By tagged task type:")
        for tag, count in unclass_by_tag.most_common():
            label = tag or "(untagged)"
            print(f"    {label:35s}: {count}")

        print(f"\n  All unclassified prompts:")
        for r in unclassified:
            print(f"    [{r['filename']}] [{r['tagged_type'] or 'untagged'}] [{r['detected_lang']}]")
            print(f"      {r['prompt_preview']}")
            print()
    else:
        print("  ALL requests are classified! No fallthrough.")

    # =====================================================================
    # Section G: Architecture Reflection
    # =====================================================================
    print("\n" + "=" * 80)
    print("G. ARCHITECTURE REFLECTION")
    print("=" * 80)

    # Accuracy of classifier vs tagged type
    total_tagged = sum(1 for r in results if r["tagged_type"])
    correct = sum(1 for r in results if r["classified_type"] == r["tagged_type"] and r["tagged_type"])
    wrong = sum(1 for r in results if r["classified_type"] != r["tagged_type"] and r["tagged_type"] and r["classified_type"])
    missed = sum(1 for r in results if r["classified_type"] is None and r["tagged_type"])

    print(f"\n  Classifier Accuracy (vs tagged ground truth):")
    print(f"    Total tagged:     {total_tagged}")
    print(f"    Correct match:    {correct} ({correct/total_tagged*100:.1f}%)" if total_tagged else "")
    print(f"    Wrong match:      {wrong} ({wrong/total_tagged*100:.1f}%)" if total_tagged else "")
    print(f"    Missed (None):    {missed} ({missed/total_tagged*100:.1f}%)" if total_tagged else "")

    # What percentage goes deterministic vs Claude?
    det_count = len([r for r in results if r["classified_type"] and r["has_whitelist"] and r["has_plan"]])
    claude_count = len(results) - det_count

    print(f"\n  Pipeline Routing:")
    print(f"    Deterministic:    {det_count} ({det_count/len(results)*100:.1f}%)")
    print(f"    Claude fallback:  {claude_count} ({claude_count/len(results)*100:.1f}%)")

    # Misclassified requests that would get WRONG deterministic plan
    wrong_det = [r for r in results
                 if r["classified_type"] and r["classified_type"] != r["tagged_type"]
                 and r["tagged_type"] and r["has_whitelist"] and r["has_plan"]]

    print(f"\n  CRITICAL: Requests that get WRONG deterministic plan: {len(wrong_det)}")
    if wrong_det:
        print(f"  These requests will be executed with the WRONG plan, causing scoring failures:")
        for r in wrong_det:
            print(f"    [{r['filename']}] Classified={r['classified_type']} but should be {r['tagged_type']}")
            print(f"      {r['prompt_preview']}")
            print()

    # Correctly classified that could benefit from deterministic but aren't whitelisted
    classified_no_wl = [r for r in results
                        if r["classified_type"]
                        and r["classified_type"] == r["tagged_type"]
                        and not r["has_whitelist"]]
    if classified_no_wl:
        print(f"\n  Correctly classified but NOT whitelisted (could add): {len(classified_no_wl)}")
        types = Counter(r["classified_type"] for r in classified_no_wl)
        for t, c in types.most_common():
            print(f"    {t}: {c}")

    # =====================================================================
    # Summary Table
    # =====================================================================
    print("\n" + "=" * 80)
    print("SUMMARY: TASK TYPE × TIER MATRIX")
    print("=" * 80)

    # Build matrix: task_type → {tier → count}
    matrix = defaultdict(lambda: defaultdict(int))
    for r in results:
        tt = r["classified_type"] or "(unclassified)"
        tier = r["tagged_tier"] or "?"
        matrix[tt][tier] += 1

    tiers = sorted(set(r["tagged_tier"] for r in results if r["tagged_tier"] is not None))
    tier_headers = [f"T{t}" for t in tiers] + ["T?"]

    print(f"  {'Task Type':35s} | {'Total':>5s} | " + " | ".join(f"{h:>4s}" for h in tier_headers) + " | WL | PL | Match%")
    print("  " + "-" * 100)

    for tt in sorted(matrix.keys()):
        total = sum(matrix[tt].values())
        counts = [matrix[tt].get(t, 0) for t in tiers] + [matrix[tt].get("?", 0) + matrix[tt].get(None, 0)]

        # Compute match rate
        tt_reqs = [r for r in results if (r["classified_type"] or "(unclassified)") == tt]
        matched = sum(1 for r in tt_reqs if r["classified_type"] == r["tagged_type"])
        match_pct = f"{matched/len(tt_reqs)*100:.0f}%" if tt_reqs else "N/A"

        wl = "Y" if tt in DETERMINISTIC_WHITELIST else "N"
        pl = "Y" if tt in PLANS_WITH_FILES else "N"

        count_str = " | ".join(f"{c:>4d}" for c in counts)
        print(f"  {tt:35s} | {total:>5d} | {count_str} | {wl:>2s} | {pl:>2s} | {match_pct:>6s}")


def main():
    requests_dir = os.path.join(os.path.dirname(__file__), "competition", "requests")

    if not os.path.isdir(requests_dir):
        print(f"ERROR: Requests directory not found: {requests_dir}")
        sys.exit(1)

    requests = load_all_requests(requests_dir)
    print(f"Loaded {len(requests)} competition requests\n")

    analyze_all(requests)


if __name__ == "__main__":
    main()
