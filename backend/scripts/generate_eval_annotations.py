import json
import random
from pathlib import Path

# Category distributions
# 20 F1/F2
# 20 F3
# 20 F4
# 15 F5
# 25 Clean

dataset = []
id_counter = 1


def add_entry(text, expected_annotations, category, glossary=None, length_type="medium"):
    global id_counter
    dataset.append(
        {
            "id": id_counter,
            "text": text,
            "category": category,
            "length_type": length_type,
            "active_glossary": glossary or [],
            "expected_annotations": expected_annotations,
        }
    )
    id_counter += 1


# F1/F2 (Deterministic - Glossary & DNT) - 20 items
glos_f1_f2 = [
    {"entry_id": 1, "target_text": "Cabinet body", "is_dnt": False, "is_case_sensitive": False},
    {"entry_id": 2, "target_text": "Greenline", "is_dnt": True, "is_case_sensitive": True},
    {"entry_id": 3, "target_text": "Rotpunkt Küchen", "is_dnt": True, "is_case_sensitive": False},
    {"entry_id": 4, "target_text": "Front", "is_dnt": False, "is_case_sensitive": False},
]

for i in range(20):
    if i % 3 == 0:
        add_entry(
            "The Cabinet body is white.",
            [{"type": "glossary", "text": "Cabinet body"}],
            "F1_F2",
            glos_f1_f2,
            "short",
        )
    elif i % 3 == 1:
        add_entry(
            "The new Greenline series features a durable Cabinet body.",
            [{"type": "dnt", "text": "Greenline"}, {"type": "glossary", "text": "Cabinet body"}],
            "F1_F2",
            glos_f1_f2,
            "medium",
        )
    else:
        add_entry(
            "When assembling the Rotpunkt Küchen components, ensure the Greenline spec is met for the Front.",
            [
                {"type": "dnt", "text": "Rotpunkt Küchen"},
                {"type": "dnt", "text": "Greenline"},
                {"type": "glossary", "text": "Front"},
            ],
            "F1_F2",
            glos_f1_f2,
            "big",
        )

# F3 (Trade Terms) - 20 items
for i in range(20):
    if i % 3 == 0:
        add_entry(
            "ABS edge banding applied.",
            [{"type": "kitchen_trade_term", "text": "ABS edge banding"}],
            "F3",
            [],
            "short",
        )
    elif i % 3 == 1:
        add_entry(
            "The melamine resin coated panels are standard.",
            [{"type": "kitchen_trade_term", "text": "melamine resin coated"}],
            "F3",
            [],
            "medium",
        )
    else:
        add_entry(
            "For optimal durability, the MDF carrier board is fully sealed using thick ABS edge banding.",
            [
                {"type": "kitchen_trade_term", "text": "MDF carrier board"},
                {"type": "kitchen_trade_term", "text": "ABS edge banding"},
            ],
            "F3",
            [],
            "big",
        )

# F4 (Ambiguous Terms) - 20 items
for i in range(20):
    if i % 3 == 0:
        add_entry(
            "Attach the filler panel.",
            [{"type": "ambiguous_term", "text": "filler panel"}],
            "F4",
            [],
            "short",
        )
    elif i % 3 == 1:
        add_entry(
            "The fascia must be aligned with the filler panel carefully.",
            [
                {"type": "ambiguous_term", "text": "fascia"},
                {"type": "ambiguous_term", "text": "filler panel"},
            ],
            "F4",
            [],
            "medium",
        )
    else:
        add_entry(
            "If dealing with a blind corner, use the filler panel to bridge the gap before attaching the fascia.",
            [
                {"type": "ambiguous_term", "text": "blind corner"},
                {"type": "ambiguous_term", "text": "filler panel"},
                {"type": "ambiguous_term", "text": "fascia"},
            ],
            "F4",
            [],
            "big",
        )

# F5 (Faulty / OCR Errors) - 15 items
for i in range(15):
    if i % 3 == 0:
        add_entry(
            "Use 4mm screvvs.", [{"type": "faulty_term", "text": "screvvs"}], "F5", [], "short"
        )
    elif i % 3 == 1:
        add_entry(
            "The C4binet b0dy is made of solid w00d.",
            [
                {"type": "faulty_term", "text": "C4binet"},
                {"type": "faulty_term", "text": "b0dy"},
                {"type": "faulty_term", "text": "w00d"},
            ],
            "F5",
            [],
            "medium",
        )
    else:
        add_entry(
            "Warning: failure to tighten the screvvs on the C4binet may lead to failure of the th!ck units.",
            [
                {"type": "faulty_term", "text": "screvvs"},
                {"type": "faulty_term", "text": "C4binet"},
                {"type": "faulty_term", "text": "th!ck"},
            ],
            "F5",
            [],
            "big",
        )

# Clean (Negative Controls) - 25 items
for i in range(25):
    if i % 3 == 0:
        add_entry("Please read carefully.", [], "Clean", [], "short")
    elif i % 3 == 1:
        add_entry(
            "The product is designed for indoor use only and should be kept dry at all times.",
            [],
            "Clean",
            [],
            "medium",
        )
    else:
        add_entry(
            "In the event of a warranty claim, please contact the customer service department with your original receipt.",
            [],
            "Clean",
            [],
            "big",
        )

random.seed(42)
random.shuffle(dataset)

out_dir = Path("backend/scripts/data")
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "rotpunkt_eval_annotations.json"
out_path.write_text(json.dumps(dataset, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"Generated {len(dataset)} evaluation segments to {out_path}")
