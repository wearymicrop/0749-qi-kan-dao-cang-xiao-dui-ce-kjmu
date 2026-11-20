from app.modules.m1_orders.service import build_orders
from app.modules.m2_receipts.service import read_receipts
from app.modules.m3_numbering.service import normalize_receipts
from app.modules.m4_combined.service import expand_claims
from app.modules.m5_titles.service import build_titles, resolve_titles
from app.modules.m6_balance.service import balance
from app.modules.m8_notes.service import build_notes


def calculate(data, through="balance"):
    results = {}
    if through == "orders":
        return {"orders": build_orders(data["rules"])}
    intake = results["receipts"] = read_receipts(data["receipts"])
    if through == "receipts":
        return results
    numbering = results["numbering"] = normalize_receipts(intake)
    if through == "numbering":
        return results
    orders = results["orders"] = build_orders(data["rules"])
    title_book = build_titles(data["titles"], orders)
    titles = results["titles"] = resolve_titles(numbering, title_book)
    if through == "titles":
        return results
    notes = results["notes"] = build_notes(data.get("publication_notes", []), orders, title_book)
    if through == "notes":
        return results
    combined = results["combined"] = expand_claims(titles, orders, notes)
    if through != "combined":
        results["balance"] = balance(orders, intake, numbering, titles, combined, notes)
    return results
