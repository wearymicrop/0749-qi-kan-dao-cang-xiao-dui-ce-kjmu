from pydantic import ValidationError

from app.errors import LedgerError
from app.modules.m5_titles.service import title_key
from app.modules.m8_notes.models import PublicationNote


def build_notes(rows, orders, titles):
    if rows is None:
        rows = []
    notes = []
    seen_ids = set()
    order_years = {(row["chain"], row["year"]): row for row in orders["years"]}
    periods = titles["index"]
    for line, row in enumerate(rows, 1):
        try:
            note = PublicationNote.model_validate(row)
        except ValidationError as error:
            fields = [str(item["loc"][0]) for item in error.errors() if item["loc"]]
            raise LedgerError("INVALID_NOTE", f"出版说明第 {line} 条无效：{','.join(fields) or '结构'}") from error
        if note.note_id in seen_ids:
            raise LedgerError("NOTE_ID_DUPLICATE", f"出版说明编号 {note.note_id} 重复")
        seen_ids.add(note.note_id)
        if len(note.span) != 2 or len(set(note.span)) != 2:
            raise LedgerError("NOTE_SPAN", f"出版说明 {note.note_id} 须给出两个不同年度")
        start, end = sorted(note.span)
        years = list(range(start, end + 1))
        expected = [order_years.get((note.chain, year)) for year in years]
        if any(item is None for item in expected):
            raise LedgerError("NOTE_OUT_OF_ORDER", f"出版说明 {note.note_id} 的年度超出订阅链订购段")
        match = next((period for period in periods.get(title_key(note.title), [])
                      if period.chain == note.chain), None)
        if match is None:
            raise LedgerError("NOTE_TITLE_MISMATCH", f"出版说明 {note.note_id} 的刊名不属于该订阅链")
        notes.append({"note_id": note.note_id, "chain": note.chain, "title": note.title,
                      "years": years, "statement": note.statement,
                      "volumes": [item["volume"] for item in expected]})
    return {"notes": notes, "index": {note["note_id"]: note for note in notes}}
