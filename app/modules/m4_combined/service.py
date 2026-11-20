from app.errors import LedgerError
from app.modules.m4_combined.claims import claim_cross_year, claim_issues


def expand_claims(titles, orders, notes):
    years = {(row["chain"], row["year"]): row for row in orders["years"]}
    coverage, supplements, isolated = [], [], []
    for row in titles["matched"]:
        note_id = row.get("note_id")
        try:
            if note_id is None:
                issues = claim_issues(row["numbers"], years.get((row["chain"], row["year"])))
                if issues:
                    coverage.append({**row, "issues": issues, "cross_year": False, "note_id": None})
                else:
                    supplements.append(row)
                continue
            note = notes["index"].get(note_id)
            if note is None:
                raise LedgerError("NOTE_NOT_FOUND", "引用的出版说明不存在，跨年度合期不予采信")
            if note["chain"] != row["chain"] or row["year"] != note["years"][0]:
                raise LedgerError("NOTE_MISMATCH", "来刊订阅链或登记年度与出版说明不符")
            spans = claim_cross_year(row["numbers"], note,
                                     [years[(row["chain"], year)] for year in note["years"]])
            coverage.append({**row, "issues": spans[0]["issues"], "cross_year": True, "note_id": note_id,
                             "note": note, "spans": spans})
        except LedgerError as error:
            isolated.append({**row, **error.payload()})
    return {"coverage": coverage, "supplements": supplements, "isolated": isolated,
            "notes": notes["notes"]}
