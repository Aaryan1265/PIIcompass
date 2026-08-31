"""Evaluate scanner output against the sealed ground truth.

This is the ONLY component permitted to read the answer key, and it does so only
after the pipeline has produced its results. It reports precision, recall and F1
on the PII-detection task, plus special-category recall and per-category
agreement, with the sample size printed beside every figure and the exact false
positives and false negatives listed so nothing is hidden.
"""
from __future__ import annotations

import json

from .config import GROUND_TRUTH_FILE


def _load_ground_truth() -> dict[tuple[str, str], dict]:
    data = json.loads(GROUND_TRUTH_FILE.read_text(encoding="utf-8"))
    return {(c["table"], c["column"]): c for c in data["columns"]}


def evaluate(schema: list[dict]) -> dict:
    gt = _load_ground_truth()
    scanner = {(c["table"], c["column"]): c for c in schema}

    keys = sorted(set(gt) & set(scanner))
    tp = fp = fn = tn = 0
    false_positives, false_negatives = [], []
    cat_match = cat_total = 0
    special_gt = special_hit = 0

    for key in keys:
        g, s = gt[key], scanner[key]
        gpii, spii = bool(g["is_pii"]), bool(s["is_pii"])
        if gpii and spii:
            tp += 1
            # Category agreement, excluding free_text which the scanner cannot emit.
            if g.get("category") and g["category"] != "free_text":
                cat_total += 1
                if s.get("category") == g["category"]:
                    cat_match += 1
        elif not gpii and spii:
            fp += 1
            false_positives.append({"table": key[0], "column": key[1],
                                    "scanner_category": s.get("category"),
                                    "note": g.get("note", "")})
        elif gpii and not spii:
            fn += 1
            false_negatives.append({"table": key[0], "column": key[1],
                                    "true_category": g.get("category"),
                                    "note": g.get("note", "")})
        else:
            tn += 1

        if g.get("special"):
            special_gt += 1
            if s.get("special"):
                special_hit += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    return {
        "n_columns_evaluated": len(keys),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "ground_truth_pii": tp + fn,
        "scanner_flagged": tp + fp,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "category_agreement": round(cat_match / cat_total, 3) if cat_total else None,
        "category_agreement_n": cat_total,
        "special_category_recall": round(special_hit / special_gt, 3) if special_gt else None,
        "special_category_n": special_gt,
        "false_positive_detail": sorted(false_positives, key=lambda r: (r["table"], r["column"])),
        "false_negative_detail": sorted(false_negatives, key=lambda r: (r["table"], r["column"])),
    }
