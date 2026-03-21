"""Extract recipes from prompts.py into individual .md files.

Reads the f-string content, splits by recipe headings,
converts f-string escaping ({{ → {, }} → }) and writes
each recipe to recipes/<NN>_<name>.md.

The {today} placeholder is kept as-is — _load_recipes() handles it at runtime.
"""
import re
from pathlib import Path

# Recipe number → filename mapping
RECIPE_FILES = {
    1: "01_create_customer",
    2: "02_create_employee",
    3: "03_create_supplier",
    4: "04_create_departments",
    5: "05_create_product",
    6: "06_create_invoice",
    7: "07_register_payment",
    8: "08_create_project",
    9: "09_fixed_price_project",
    10: "10_run_salary",
    11: "11_register_supplier_invoice",
    12: "12_create_order",
    13: "13_custom_dimension_voucher",
    14: "14_reverse_payment_voucher",
    15: "15_credit_note",
    16: "16_register_hours",
    17: "17_travel_expense",
    18: "18_bank_reconciliation",
    19: "19_asset_registration",
    20: "20_year_end_corrections",
}

def unescape_fstring(text: str) -> str:
    """Convert f-string escaping to plain text.

    {{ → {  and  }} → }
    But preserve {today} as a literal placeholder.
    """
    # First, temporarily protect {today}
    text = text.replace("{today}", "___TODAY___")
    # Unescape doubled braces
    text = text.replace("{{", "{")
    text = text.replace("}}", "}")
    # Restore {today} placeholder
    text = text.replace("___TODAY___", "{today}")
    return text


def extract():
    project_root = Path(__file__).parent.parent
    prompts_file = project_root / "prompts.py"
    recipes_dir = project_root / "recipes"
    recipes_dir.mkdir(exist_ok=True)

    content = prompts_file.read_text()

    # Find the recipes section: starts at "## Recipes for Known Task Types"
    # and ends at "## Handling Unknown Tasks"
    recipes_start = content.index("## Recipes for Known Task Types")
    recipes_end = content.index("## Handling Unknown Tasks")
    recipes_section = content[recipes_start:recipes_end]

    # Split by ### headings (recipe numbers)
    # Pattern: ### N. Title or ### NN. Title
    parts = re.split(r'(?=^### \d+\.)', recipes_section, flags=re.MULTILINE)

    # First part is the section header — skip it
    # Also skip the "### Tier 3 Recipes (anticipated — opens Saturday)" line
    recipe_parts = []
    for part in parts[1:]:
        part = part.strip()
        if part and re.match(r'^### \d+\.', part):
            recipe_parts.append(part)

    print(f"Found {len(recipe_parts)} recipes")

    for part in recipe_parts:
        # Extract recipe number from "### N. Title"
        match = re.match(r'^### (\d+)\.\s+(.+?)$', part, re.MULTILINE)
        if not match:
            print(f"WARNING: Could not parse recipe heading: {part[:80]}")
            continue

        num = int(match.group(1))
        title = match.group(2).strip()

        if num not in RECIPE_FILES:
            print(f"WARNING: Unknown recipe number {num}: {title}")
            continue

        filename = RECIPE_FILES[num]
        # Convert ### heading to # heading for standalone file
        md_content = part.replace(f"### {num}.", f"#", 1)
        md_content = unescape_fstring(md_content)

        filepath = recipes_dir / f"{filename}.md"
        filepath.write_text(md_content.strip() + "\n")
        print(f"  Wrote {filepath.name} ({len(md_content)} chars)")

    # Handle the "Tier 3 Recipes" separator line — skip it, recipes 18-20 are extracted above


if __name__ == "__main__":
    extract()
