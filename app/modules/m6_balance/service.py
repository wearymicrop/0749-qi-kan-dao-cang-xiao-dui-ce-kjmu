from collections import Counter, defaultdict

from app.modules.m6_balance.slots import tally_slots


def summarize_notes(notes, slots, quarantine):
    tagged = defaultdict(list)
    for slot in slots:
        if slot["note_id"]:
            tagged[slot["note_id"]].append(slot)
    blocked = defaultdict(list)
    for row in quarantine:
        if row.get("note_id"):
            blocked[row["note_id"]].append(row["code"])
    summary = []
    for note in notes["notes"]:
        outcomes = tagged.get(note["note_id"], [])
        counters = Counter(slot["status"] for slot in outcomes)
        if outcomes and not counters.get("disputed"):
            status = "covered"
        elif counters.get("disputed"):
            status = "disputed"
        else:
            status = "pending"
        summary.append({
            "note_id": note["note_id"], "chain": note["chain"], "title": note["title"],
            "years": note["years"], "volumes": note["volumes"], "statement": note["statement"],
            "status": status, "slots": len(outcomes),
            "covered": counters["covered"], "disputed": counters["disputed"],
            "blocking_codes": sorted(set(blocked.get(note["note_id"], []))),
        })
    return summary


def balance(orders, intake, numbers, titles, expansion, notes):
    slots = tally_slots(orders["slots"], expansion["coverage"])
    isolation = sorted(intake["isolated"] + numbers["isolated"] + titles["isolated"] + expansion["isolated"],
                       key=lambda row: row["line"])
    counts = Counter(slot["status"] for slot in slots)
    totals = {"expected": orders["expected"], **{key: counts[key] for key in ("covered", "missing", "disputed")},
              "supplements": len(expansion["supplements"]),
              "holdings": len({row["accession"] for row in expansion["coverage"]})}
    totals["difference"] = totals["expected"] - sum(counts.values())
    row_totals = {"input": intake["input"], "coverage": len(expansion["coverage"]),
                  "supplements": len(expansion["supplements"]), "duplicates": len(intake["duplicates"]),
                  "isolated": len(isolation)}
    row_totals["difference"] = row_totals["input"] - sum(value for key, value in row_totals.items() if key != "input")
    by_year = defaultdict(Counter)
    for slot in slots:
        by_year[slot["chain"], slot["year"]][slot["status"]] += 1
    return {"status": "MATCHED" if totals["difference"] == row_totals["difference"] == 0 else "MISMATCH",
            "totals": totals, "row_totals": row_totals, "slots": slots,
            "years": [{"chain": chain, "year": year, **{key: value[key] for key in ("covered", "missing", "disputed")}}
                      for (chain, year), value in by_year.items()],
            "note_summary": summarize_notes(notes, slots, isolation),
            "quarantine": isolation, "isolation_counts": dict(Counter(row["code"] for row in isolation))}
