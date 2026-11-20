from collections import defaultdict


def slot_claims(receipt):
    """同一件实物在说明覆盖的每个年度各挂一次依据，但验收号始终是同一个。"""
    if receipt.get("cross_year"):
        return [(span["chain"], span["year"], issue) for span in receipt["spans"] for issue in span["issues"]]
    return [(receipt["chain"], receipt["year"], issue) for issue in receipt["issues"]]


def tally_slots(slots, coverage):
    lookup = defaultdict(list)
    for receipt in coverage:
        for key in slot_claims(receipt):
            lookup[key].append(receipt)
    outcomes = []
    for slot in slots:
        rows = lookup[slot["chain"], slot["year"], slot["issue"]]
        if not rows:
            status, code = "missing", "NO_CLAIM"
        elif any(row.get("code") == "ACCESSION_CONFLICT" for row in rows):
            status, code = "disputed", "ACCESSION_CONFLICT"
        elif len(rows) > 1:
            status, code = "disputed", "CLAIM_OVERLAP"
        else:
            status, code = "covered", None
        outcomes.append({**slot, "status": status, "code": code,
                         "cross_year": any(row.get("cross_year") for row in rows),
                         "note_id": next((row.get("note_id") for row in rows if row.get("note_id")), None),
                         "evidence": [{key: row[key] for key in ("line", "accession", "raw", "official_title")}
                                      for row in rows]})
    return outcomes
