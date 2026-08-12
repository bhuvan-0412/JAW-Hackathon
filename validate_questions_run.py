"""
validate_questions_run.py

Standalone sanity-checker for a submission against the real 333-question
validation set (questions.json, hidden_set_v1.4). Run this AFTER generating
answers.jsonl from your pipeline — it doesn't compute answers, it checks
whether what you produced is even well-formed and plausible before you
trust it or submit it.

Usage:
    python validate_questions_run.py --questions questions.json --answers answers.jsonl

No external deps beyond stdlib.
"""
import argparse
import json
import sys
from collections import Counter, defaultdict

# Total company value from the problem statement — ~5,530 crore rupees.
# Any single "money" answer wildly above this is almost certainly a units bug
# (e.g. accidentally returning lakh instead of rupees, or double-counting).
COMPANY_TOTAL_VALUE = 5_530 * 10_000_000  # 55,300,000,000

# Known canary qids worth eyeballing by hand regardless of what the script says.
CANARY_QIDS = {
    "HV-IC-0263": "absence pattern — 'how many of the five completed jobs lack a "
                   "client reference letter' — tests whether your pipeline proves "
                   "a negative, or silently defaults to 0",
}


def load_questions(path):
    with open(path) as f:
        data = json.load(f)
    return data


def load_answers(path):
    answers = {}
    dupes = []
    with open(path) as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[FATAL] answers.jsonl line {line_no} is not valid JSON: {e}")
                sys.exit(1)
            qid = obj.get("qid")
            if qid is None:
                print(f"[FATAL] answers.jsonl line {line_no} missing 'qid' field")
                sys.exit(1)
            if qid in answers:
                dupes.append(qid)
            answers[qid] = obj.get("answer")
    if dupes:
        print(f"[WARN] {len(dupes)} duplicate qid(s) in answers.jsonl (last write wins): {dupes[:10]}")
    return answers


def check_type(qid, answer_type, value):
    """Returns a list of issue strings (empty if clean)."""
    issues = []

    if value is None:
        issues.append("answer is null")
        return issues

    if not isinstance(value, (int, float)):
        issues.append(f"answer is not numeric (got {type(value).__name__}: {value!r})")
        return issues

    if isinstance(value, bool):  # bool is a subclass of int in Python — catch explicitly
        issues.append("answer is a boolean, not a number")
        return issues

    if answer_type == "money":
        if value < 0:
            # Legitimate for mean-median-gap style questions ("negative if mean is
            # lower") — don't hard-flag, just note it for a human to sanity check.
            issues.append("NOTE: negative money value — only valid for explicit "
                           "mean/median-gap-style questions, verify this qid asks for that")
        if abs(value) > COMPANY_TOTAL_VALUE:
            issues.append(f"money value {value:,.0f} exceeds total company value "
                           f"({COMPANY_TOTAL_VALUE:,.0f}) — likely a units bug")
        if 0 < abs(value) < 1000:
            issues.append(f"money value {value} is suspiciously small for rupees — "
                           f"check you didn't return lakh/crore units instead of raw rupees")

    elif answer_type == "percent":
        if value < 0 or value > 100:
            issues.append(f"percent value {value} is outside [0, 100] — check you "
                           f"didn't return a fraction (0-1) or a raw ratio")

    elif answer_type == "days":
        if value < 0:
            issues.append(f"days value {value} is negative — date subtraction likely reversed")
        if value > 365 * 20:
            issues.append(f"days value {value} exceeds 20 years — implausible for this corpus "
                           f"(works span 2010-2025)")

    elif answer_type == "count":
        if value != int(value):
            issues.append(f"count value {value} is not a whole number")
        if value < 0:
            issues.append(f"count value {value} is negative")

    return issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default="questions.json")
    ap.add_argument("--answers", default="answers.jsonl")
    args = ap.parse_args()

    qdata = load_questions(args.questions)
    questions = qdata["questions"]
    print(f"Loaded {len(questions)} questions from {args.questions} "
          f"(set_id={qdata.get('set_id')}, frozen={qdata.get('frozen')})")

    answers = load_answers(args.answers)
    print(f"Loaded {len(answers)} answers from {args.answers}\n")

    q_by_id = {q["qid"]: q for q in questions}

    # 1. Completeness
    missing = [qid for qid in q_by_id if qid not in answers]
    extra = [qid for qid in answers if qid not in q_by_id]

    print("=" * 70)
    print("COMPLETENESS")
    print("=" * 70)
    if missing:
        print(f"[FAIL] {len(missing)} question(s) with NO answer (scores 0 each):")
        for qid in missing[:20]:
            print(f"    {qid}: {q_by_id[qid]['question'][:80]}")
        if len(missing) > 20:
            print(f"    ... and {len(missing) - 20} more")
    else:
        print("[OK] every question has an answer")

    if extra:
        print(f"[NOTE] {len(extra)} answer(s) for qids not in questions.json (harmless, ignored)")

    # 2. Type / plausibility checks
    print("\n" + "=" * 70)
    print("TYPE & PLAUSIBILITY CHECKS")
    print("=" * 70)
    issues_by_qid = {}
    clean_count = 0
    for qid, q in q_by_id.items():
        if qid not in answers:
            continue
        issues = check_type(qid, q["answer_type"], answers[qid])
        if issues:
            issues_by_qid[qid] = issues
        else:
            clean_count += 1

    print(f"{clean_count} answers passed all checks cleanly")
    if issues_by_qid:
        print(f"{len(issues_by_qid)} answer(s) flagged for review:\n")
        for qid, issues in list(issues_by_qid.items())[:30]:
            q = q_by_id[qid]
            print(f"  {qid} [{q['answer_type']}] answer={answers[qid]!r}")
            print(f"      Q: {q['question'][:100]}")
            for issue in issues:
                print(f"      -> {issue}")
        if len(issues_by_qid) > 30:
            print(f"  ... and {len(issues_by_qid) - 30} more flagged (see full output if run without truncation)")

    # 3. Distribution sanity check per answer_type
    print("\n" + "=" * 70)
    print("DISTRIBUTION BY ANSWER TYPE")
    print("=" * 70)
    by_type = defaultdict(list)
    for qid, q in q_by_id.items():
        if qid in answers and isinstance(answers[qid], (int, float)) and not isinstance(answers[qid], bool):
            by_type[q["answer_type"]].append(answers[qid])

    for atype, values in by_type.items():
        if not values:
            continue
        values_sorted = sorted(values)
        n = len(values_sorted)
        print(f"{atype:8s}: n={n:4d}  min={values_sorted[0]:,.2f}  "
              f"median={values_sorted[n//2]:,.2f}  max={values_sorted[-1]:,.2f}  "
              f"zeros={sum(1 for v in values if v == 0)}")

    zero_money = [qid for qid, q in q_by_id.items()
                  if qid in answers and q["answer_type"] == "money" and answers[qid] == 0]
    if zero_money:
        print(f"\n[NOTE] {len(zero_money)} money-type answer(s) are exactly 0 — verify these are "
              f"genuine zero-value results, not fallback/failure defaults: {zero_money[:15]}")

    # 4. Canary questions — always print regardless of pass/fail
    print("\n" + "=" * 70)
    print("CANARY QUESTIONS (eyeball these by hand)")
    print("=" * 70)
    for qid, why in CANARY_QIDS.items():
        if qid in q_by_id:
            q = q_by_id[qid]
            ans = answers.get(qid, "<MISSING>")
            print(f"  {qid}: {why}")
            print(f"      Q: {q['question']}")
            print(f"      Your answer: {ans}\n")

    # 5. Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    total = len(q_by_id)
    print(f"  Total questions:      {total}")
    print(f"  Answered:             {total - len(missing)}")
    print(f"  Missing:              {len(missing)}")
    print(f"  Flagged for review:   {len(issues_by_qid)}")
    print(f"  Clean:                {clean_count}")

    if missing or issues_by_qid:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
