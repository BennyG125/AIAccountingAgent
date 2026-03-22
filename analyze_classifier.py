#!/usr/bin/env python3
"""Comprehensive classifier analysis against all competition requests.

Loads all JSON files from competition/requests/, runs the current classifier,
and checks for coverage gaps, misclassifications, and pipeline readiness.
"""

import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from execution_plans._classifier import classify_task, detect_language, LANG_PATTERNS, UNIVERSAL_PATTERNS
from execution_plans._registry import PLANS
from deterministic_executor import EXTRACTION_SCHEMAS, DETERMINISTIC_WHITELIST

# ── 1. Load all requests ─────────────────────────────────────────────────

REQUESTS_DIR = Path(__file__).parent / "competition" / "requests"

requests = []
for f in sorted(REQUESTS_DIR.glob("*.json")):
    try:
        data = json.loads(f.read_text())
        data["_filename"] = f.name
        requests.append(data)
    except Exception as e:
        print(f"WARNING: Failed to load {f.name}: {e}")

print(f"{'=' * 80}")
print(f"CLASSIFIER ANALYSIS REPORT")
print(f"{'=' * 80}")
print(f"\nLoaded {len(requests)} requests from {REQUESTS_DIR}")

# ── 2. Infrastructure check ─────────────────────────────────────────────

print(f"\n{'─' * 80}")
print("INFRASTRUCTURE CHECK")
print(f"{'─' * 80}")

all_plan_types = set(PLANS.keys())
all_schema_types = set(EXTRACTION_SCHEMAS.keys())
all_whitelist_types = DETERMINISTIC_WHITELIST

print(f"\n  Registered PLANS:        {len(all_plan_types):3d} types")
print(f"  EXTRACTION_SCHEMAS:      {len(all_schema_types):3d} types")
print(f"  DETERMINISTIC_WHITELIST: {len(all_whitelist_types):3d} types")

missing_plan = all_whitelist_types - all_plan_types
missing_schema = all_whitelist_types - all_schema_types
missing_whitelist = all_plan_types - all_whitelist_types

if missing_plan:
    print(f"\n  !! In WHITELIST but no PLAN:   {sorted(missing_plan)}")
if missing_schema:
    print(f"\n  !! In WHITELIST but no SCHEMA: {sorted(missing_schema)}")
if missing_whitelist:
    print(f"\n  !! Has PLAN but not WHITELISTED: {sorted(missing_whitelist)}")
if not missing_plan and not missing_schema and not missing_whitelist:
    print(f"\n  All three sets are perfectly aligned.")

# ── 3. Classify every request ────────────────────────────────────────────

# Map heuristic language codes to language names used by classify_task
LANG_CODE_TO_NAME = {
    "no": "Norwegian",
    "nn": "Nynorsk",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "pt": "Portuguese",
    "en": "English",
}

results = []
for req in requests:
    prompt = req.get("prompt", "")
    tagged_type = req.get("task_type")
    tagged_tier = req.get("tier")
    filename = req["_filename"]

    # Detect language
    lang_code = detect_language(prompt)
    lang_name = LANG_CODE_TO_NAME.get(lang_code, "Unknown")

    # ── Classify with detected language (what would happen for non-English)
    classified_with_lang = classify_task(prompt, language=lang_name)

    # ── Classify as English (what production does after Gemini translation)
    # For English prompts, this IS the production path.
    # For non-English, the classifier runs on the TRANSLATED text in production,
    # but here we simulate by classifying the ORIGINAL prompt with English patterns.
    classified_as_english = classify_task(prompt, language="English")

    # ── Classify with NO language (universal patterns only)
    classified_universal = classify_task(prompt, language=None)

    # ── Check pipeline readiness
    effective_type = classified_with_lang  # what the classifier returns
    has_plan = effective_type in all_plan_types if effective_type else False
    has_schema = effective_type in all_schema_types if effective_type else False
    in_whitelist = effective_type in all_whitelist_types if effective_type else False

    # ── Detect disagreements
    tag_disagrees = (
        tagged_type is not None
        and effective_type is not None
        and tagged_type != effective_type
    )

    # ── Would English-only classification differ?
    english_differs = (
        classified_with_lang != classified_as_english
        and lang_code != "en"
    )

    results.append({
        "filename": filename,
        "task_id": req.get("task_id", "?"),
        "prompt_snippet": prompt[:120].replace("\n", " "),
        "lang_code": lang_code,
        "lang_name": lang_name,
        "tagged_type": tagged_type,
        "tagged_tier": tagged_tier,
        "classified_with_lang": classified_with_lang,
        "classified_as_english": classified_as_english,
        "classified_universal": classified_universal,
        "has_plan": has_plan,
        "has_schema": has_schema,
        "in_whitelist": in_whitelist,
        "tag_disagrees": tag_disagrees,
        "english_differs": english_differs,
    })

# ── 4. Summary statistics ───────────────────────────────────────────────

print(f"\n{'─' * 80}")
print("CLASSIFICATION SUMMARY")
print(f"{'─' * 80}")

lang_counts = Counter(r["lang_code"] for r in results)
print(f"\n  Language distribution:")
for lang, count in lang_counts.most_common():
    name = LANG_CODE_TO_NAME.get(lang, lang)
    print(f"    {name:15s} ({lang}): {count:3d}")

type_counts = Counter(r["classified_with_lang"] for r in results)
print(f"\n  Classification distribution (with detected language):")
for t, count in type_counts.most_common():
    label = t or "(None — falls through to Claude)"
    in_wl = " [WHITELISTED]" if t in all_whitelist_types else " [NOT WHITELISTED]" if t else ""
    print(f"    {label:40s}: {count:3d}{in_wl}")

# ── 5. Tier breakdown ───────────────────────────────────────────────────

print(f"\n{'─' * 80}")
print("TIER BREAKDOWN")
print(f"{'─' * 80}")

tier_counts = Counter(r["tagged_tier"] for r in results)
for tier in sorted((t for t in tier_counts if t is not None), key=lambda x: str(x)):
    tier_results = [r for r in results if r["tagged_tier"] == tier]
    none_count = sum(1 for r in tier_results if r["classified_with_lang"] is None)
    not_wl = sum(1 for r in tier_results if r["classified_with_lang"] and not r["in_whitelist"])
    no_schema = sum(1 for r in tier_results if r["classified_with_lang"] and not r["has_schema"])
    ok = sum(1 for r in tier_results if r["classified_with_lang"] and r["in_whitelist"] and r["has_schema"] and r["has_plan"])
    print(f"\n  Tier {tier}: {len(tier_results)} requests")
    print(f"    Fully pipeline-ready:  {ok:3d}")
    print(f"    Classifier returns None: {none_count:3d}")
    print(f"    Not in whitelist:      {not_wl:3d}")
    print(f"    No extraction schema:  {no_schema:3d}")

untagged = [r for r in results if r["tagged_tier"] is None]
if untagged:
    none_count = sum(1 for r in untagged if r["classified_with_lang"] is None)
    ok = sum(1 for r in untagged if r["classified_with_lang"] and r["in_whitelist"])
    print(f"\n  Untagged (no tier): {len(untagged)} requests")
    print(f"    Fully pipeline-ready:    {ok:3d}")
    print(f"    Classifier returns None: {none_count:3d}")

# ── 6. PROBLEM REPORTS ──────────────────────────────────────────────────

print(f"\n{'=' * 80}")
print("PROBLEM REPORTS")
print(f"{'=' * 80}")

# ── 6a. Classifier returns None
none_results = [r for r in results if r["classified_with_lang"] is None]
print(f"\n{'─' * 80}")
print(f"6a. CLASSIFIER RETURNS None ({len(none_results)} requests) — falls through to Claude")
print(f"{'─' * 80}")
if none_results:
    for r in none_results:
        print(f"\n  [{r['filename']}] task_id={r['task_id']}")
        print(f"    Lang: {r['lang_name']} ({r['lang_code']})")
        print(f"    Tagged: {r['tagged_type']}  Tier: {r['tagged_tier']}")
        print(f"    Prompt: {r['prompt_snippet']}...")
        print(f"    Universal: {r['classified_universal']}")
        print(f"    As English: {r['classified_as_english']}")
else:
    print("  (none — all requests are classified)")

# ── 6b. Classified but not in DETERMINISTIC_WHITELIST
not_wl = [r for r in results if r["classified_with_lang"] and not r["in_whitelist"]]
print(f"\n{'─' * 80}")
print(f"6b. CLASSIFIED BUT NOT IN WHITELIST ({len(not_wl)} requests)")
print(f"{'─' * 80}")
if not_wl:
    types_not_wl = Counter(r["classified_with_lang"] for r in not_wl)
    for t, count in types_not_wl.most_common():
        print(f"\n  Type '{t}': {count} requests")
        for r in not_wl:
            if r["classified_with_lang"] == t:
                print(f"    [{r['filename']}] {r['prompt_snippet'][:80]}...")
else:
    print("  (none — all classified types are whitelisted)")

# ── 6c. Classified but no EXTRACTION_SCHEMA
no_schema = [r for r in results if r["classified_with_lang"] and not r["has_schema"]]
print(f"\n{'─' * 80}")
print(f"6c. CLASSIFIED BUT NO EXTRACTION SCHEMA ({len(no_schema)} requests)")
print(f"{'─' * 80}")
if no_schema:
    for r in no_schema:
        print(f"  [{r['filename']}] type={r['classified_with_lang']} — {r['prompt_snippet'][:80]}...")
else:
    print("  (none — all classified types have schemas)")

# ── 6d. Tagged type disagrees with classification
disagree = [r for r in results if r["tag_disagrees"]]
print(f"\n{'─' * 80}")
print(f"6d. TAGGED TYPE DISAGREES WITH CLASSIFICATION ({len(disagree)} requests)")
print(f"{'─' * 80}")
if disagree:
    for r in disagree:
        print(f"\n  [{r['filename']}] task_id={r['task_id']}")
        print(f"    Tagged:     {r['tagged_type']}")
        print(f"    Classified: {r['classified_with_lang']}")
        print(f"    Lang: {r['lang_name']} ({r['lang_code']})")
        print(f"    Tier: {r['tagged_tier']}")
        print(f"    Prompt: {r['prompt_snippet']}...")
else:
    print("  (none — all tagged types agree with classification)")

# ── 6e. Language-specific vs English classification differs
english_diff = [r for r in results if r["english_differs"]]
print(f"\n{'─' * 80}")
print(f"6e. NON-ENGLISH: NATIVE vs ENGLISH CLASSIFICATION DIFFERS ({len(english_diff)} requests)")
print(f"    (Simulates what happens if Gemini translation changes the classification)")
print(f"{'─' * 80}")
if english_diff:
    for r in english_diff:
        print(f"\n  [{r['filename']}] task_id={r['task_id']}")
        print(f"    Lang: {r['lang_name']} ({r['lang_code']})")
        print(f"    With native lang: {r['classified_with_lang']}")
        print(f"    As English only:  {r['classified_as_english']}")
        print(f"    Universal:        {r['classified_universal']}")
        print(f"    Tagged:           {r['tagged_type']}")
        print(f"    Prompt: {r['prompt_snippet']}...")
else:
    print("  (none — native and English classifications always agree)")

# ── 7. Production simulation ────────────────────────────────────────────

print(f"\n{'=' * 80}")
print("PRODUCTION SIMULATION")
print(f"{'=' * 80}")
print("""
In production, the flow is:
  1. detect_language(prompt) → lang_code
  2. If lang_code != 'en': Gemini translates to English
  3. classify_task(english_prompt, language="English")
  4. Check whitelist → if not whitelisted, fall to Claude
  5. Check EXTRACTION_SCHEMA → if missing, fall to Claude
  6. Extract params → execute plan

Since we can't run Gemini translation here, we simulate by:
  - For English prompts: classify directly (this IS production path)
  - For non-English: classify the ORIGINAL (untranslated) prompt with English patterns
    to check if English patterns would match the foreign text (they often won't —
    that's why Gemini translates first)
""")

# Production path: English prompts classified directly
en_requests = [r for r in results if r["lang_code"] == "en"]
en_classified = sum(1 for r in en_requests if r["classified_as_english"] is not None)
en_whitelisted = sum(1 for r in en_requests if r["classified_as_english"] in all_whitelist_types)
print(f"  English prompts: {len(en_requests)} total, {en_classified} classified, {en_whitelisted} whitelisted")

# Non-English: original with English patterns (worst case — no translation)
non_en = [r for r in results if r["lang_code"] != "en"]
non_en_with_native = sum(1 for r in non_en if r["classified_with_lang"] is not None)
non_en_with_eng = sum(1 for r in non_en if r["classified_as_english"] is not None)
non_en_with_univ = sum(1 for r in non_en if r["classified_universal"] is not None)
print(f"  Non-English prompts: {len(non_en)} total")
print(f"    Classified with native lang patterns: {non_en_with_native}")
print(f"    Classified with English-only patterns: {non_en_with_eng} (worst case: no translation)")
print(f"    Classified with universal patterns:    {non_en_with_univ}")

# How many non-English would FAIL if Gemini translation breaks?
non_en_only_native = [
    r for r in non_en
    if r["classified_with_lang"] is not None and r["classified_as_english"] is None
]
print(f"\n  Non-English that DEPEND on Gemini translation: {len(non_en_only_native)}")
print(f"    (these classify with native patterns but NOT with English-only patterns)")
if non_en_only_native:
    lang_breakdown = Counter(r["lang_name"] for r in non_en_only_native)
    for lang, count in lang_breakdown.most_common():
        print(f"      {lang}: {count}")

# ── 8. Cross-language pattern robustness ─────────────────────────────────

print(f"\n{'─' * 80}")
print("CROSS-LANGUAGE PATTERN ROBUSTNESS")
print(f"{'─' * 80}")

# Check: do universal patterns catch everything that lang-specific patterns catch?
universal_miss = [
    r for r in results
    if r["classified_with_lang"] is not None and r["classified_universal"] is None
]
print(f"\n  Classified by lang-specific BUT NOT universal patterns: {len(universal_miss)}")
if universal_miss:
    for r in universal_miss[:10]:
        print(f"    [{r['filename']}] lang={r['lang_code']} type={r['classified_with_lang']}")
        print(f"      Prompt: {r['prompt_snippet'][:80]}...")
    if len(universal_miss) > 10:
        print(f"    ... and {len(universal_miss) - 10} more")

# Check: do universal patterns give DIFFERENT results than lang-specific?
universal_diff = [
    r for r in results
    if (r["classified_with_lang"] is not None
        and r["classified_universal"] is not None
        and r["classified_with_lang"] != r["classified_universal"])
]
print(f"\n  Lang-specific and universal give DIFFERENT types: {len(universal_diff)}")
if universal_diff:
    for r in universal_diff:
        print(f"    [{r['filename']}] lang={r['lang_code']}")
        print(f"      Lang-specific: {r['classified_with_lang']}")
        print(f"      Universal:     {r['classified_universal']}")
        print(f"      Tagged:        {r['tagged_type']}")
        print(f"      Prompt: {r['prompt_snippet'][:80]}...")

# ── 9. Full coverage matrix ─────────────────────────────────────────────

print(f"\n{'=' * 80}")
print("COVERAGE MATRIX: task_type × language")
print(f"{'=' * 80}")

# Build matrix
matrix = defaultdict(Counter)
for r in results:
    t = r["classified_with_lang"] or "(None)"
    matrix[t][r["lang_code"]] += 1

all_langs = sorted(set(r["lang_code"] for r in results))
header = f"  {'Task Type':40s} " + " ".join(f"{l:>4s}" for l in all_langs) + " Total"
print(f"\n{header}")
print(f"  {'─' * len(header)}")

for t in sorted(matrix.keys()):
    row = f"  {t:40s} "
    total = 0
    for lang in all_langs:
        count = matrix[t].get(lang, 0)
        total += count
        row += f"{count:4d} "
    row += f"{total:5d}"
    print(row)

# ── 10. Requests without tags ───────────────────────────────────────────

untagged_reqs = [r for r in results if r["tagged_type"] is None]
print(f"\n{'─' * 80}")
print(f"REQUESTS WITHOUT task_type TAG ({len(untagged_reqs)} requests)")
print(f"{'─' * 80}")
if untagged_reqs:
    for r in untagged_reqs[:20]:
        print(f"  [{r['filename']}] classified={r['classified_with_lang']} lang={r['lang_code']}")
        print(f"    Prompt: {r['prompt_snippet'][:100]}...")
    if len(untagged_reqs) > 20:
        print(f"  ... and {len(untagged_reqs) - 20} more")

# ── 11. Final scorecard ─────────────────────────────────────────────────

print(f"\n{'=' * 80}")
print("FINAL SCORECARD")
print(f"{'=' * 80}")

total = len(results)
classified = sum(1 for r in results if r["classified_with_lang"] is not None)
pipeline_ready = sum(1 for r in results if r["in_whitelist"])
tag_agrees = sum(1 for r in results if r["tagged_type"] and not r["tag_disagrees"])
tag_total = sum(1 for r in results if r["tagged_type"])

print(f"\n  Total requests:              {total:3d}")
print(f"  Classified (not None):       {classified:3d}  ({100 * classified / total:.1f}%)")
print(f"  Pipeline-ready (whitelisted): {pipeline_ready:3d}  ({100 * pipeline_ready / total:.1f}%)")
print(f"  Falls through to Claude:     {total - pipeline_ready:3d}  ({100 * (total - pipeline_ready) / total:.1f}%)")
print(f"  Tag agrees with classifier:  {tag_agrees:3d} / {tag_total} tagged  ({100 * tag_agrees / tag_total:.1f}% agreement)" if tag_total else "")
print(f"  Disagree count:              {len(disagree):3d}")
print(f"  English-diff count:          {len(english_diff):3d}")
print()
