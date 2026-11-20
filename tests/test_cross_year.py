import pytest

from app.errors import LedgerError
from app.modules.m3_numbering.parser import parse_numbering
from app.pipeline import calculate


@pytest.fixture
def cross_stages(crossyear):
    return calculate(crossyear)


def test_one_physical_item_traces_to_slots_in_both_years_but_counts_once(cross_stages):
    # 裁决：两个年度保留同一实物依据，馆藏按验收号只计一件
    slots = cross_stages["balance"]["slots"]
    traced = {(s["year"], s["issue"]): s for s in slots if s["note_id"] == "PN-CST-2025-04"}
    assert sorted(traced) == [(2025, 4), (2026, 1)]
    for slot in traced.values():
        assert slot["cross_year"] is True and slot["status"] == "covered"
        assert [e["accession"] for e in slot["evidence"]] == ["00033"]
    holdings = {row["accession"] for row in cross_stages["combined"]["coverage"]}
    assert "00033" in holdings and len(holdings) == cross_stages["balance"]["totals"]["holdings"] == 10


def test_cross_year_note_summary_shows_statement_years_and_status(cross_stages):
    summary = {row["note_id"]: row for row in cross_stages["balance"]["note_summary"]}
    cst = summary["PN-CST-2025-04"]
    assert cst["years"] == [2025, 2026] and cst["volumes"] == [17, 18]
    assert cst["status"] == "covered" and cst["slots"] == 2 and "出版方函" in cst["statement"]
    geo = summary["PN-GEO-2025-09"]
    assert geo["status"] == "disputed" and geo["covered"] == 1 and geo["disputed"] == 1
    assert geo["blocking_codes"] == []


def test_overlap_on_cross_year_boundary_disputes_only_shared_slot(cross_stages):
    # 争议只落在 2026 年第 10 期，2025 年第 9 期仍由同一实物单独覆盖
    slots = cross_stages["balance"]["slots"]
    disputed = [s for s in slots if s["note_id"] == "PN-GEO-2025-09"]
    assert [(s["year"], s["issue"], s["status"], s["code"]) for s in disputed] == [
        (2025, 9, "covered", None), (2026, 10, "disputed", "CLAIM_OVERLAP")]
    shared = next(s for s in disputed if s["status"] == "disputed")
    assert [e["accession"] for e in shared["evidence"]] == ["00042", "00045"]


def test_cross_year_replay_is_counted_once(cross_stages):
    # 同一验收号重试（含说明引用）不重复计入藏
    duplicates = cross_stages["receipts"]["duplicates"]
    assert [(d["line"], d["original_line"], d["accession"], d["note_id"]) for d in duplicates] == [
        (11, 7, "00042", "PN-GEO-2025-09")]
    totals = cross_stages["balance"]["totals"]
    assert totals["expected"] == 14 and totals["covered"] == 12 and totals["missing"] == 1
    assert totals["disputed"] == 1 and totals["difference"] == 0


def test_year_breakdown_keeps_both_years_without_double_counting(cross_stages):
    rows = [r for r in cross_stages["balance"]["years"] if r["chain"] == "CST"]
    assert [(r["year"], r["covered"], r["missing"], r["disputed"]) for r in rows] == [
        (2025, 4, 0, 0), (2026, 3, 1, 0)]


def test_continuous_cross_year_uses_global_boundary_numbers(cross_stages):
    claim = next(row for row in cross_stages["combined"]["coverage"] if row["accession"] == "00042")
    assert claim["cross_year"] is True
    assert claim["spans"] == [
        {"chain": "GEO", "year": 2025, "volume": 3, "issues": [9]},
        {"chain": "GEO", "year": 2026, "volume": 4, "issues": [10]},
    ]


def test_descending_range_without_note_is_still_rejected():
    # TRAP-07 保持有效：逆序范围只有引用出版说明时才放行
    with pytest.raises(LedgerError) as error:
        parse_numbering("17", "4-1")
    assert error.value.code == "ISSUE_ORDER"
    admitted = parse_numbering("17", "4-1", note_id="PN-CST-2025-04")
    assert (admitted["first"], admitted["last"]) == (4, 1)


def test_unknown_note_quarantines_whole_claim(crossyear):
    crossyear["receipts"].append({
        "accession": "00099", "title": "海岸观测通报", "year": 2025,
        "volume": "17", "issue": "4-1", "kind": "regular", "note_id": "PN-MISSING"})
    result = calculate(crossyear)["balance"]
    assert any(q["accession"] == "00099" and q["code"] == "NOTE_NOT_FOUND" for q in result["quarantine"])
    assert all("00099" not in [e["accession"] for e in s["evidence"]] for s in result["slots"])


def test_wrong_boundary_is_never_partially_applied(crossyear):
    # 卷界不符时整条隔离，两个年度都不产生部分覆盖
    crossyear["receipts"][2]["issue"] = "3-1"
    result = calculate(crossyear)["balance"]
    assert any(q["line"] == 3 and q["code"] == "NOTE_MISMATCH" for q in result["quarantine"])
    assert all(s["note_id"] != "PN-CST-2025-04" for s in result["slots"])


def test_supplement_cannot_quote_note(crossyear):
    crossyear["receipts"].append({
        "accession": "00098", "title": "方志资料辑刊", "year": 2025,
        "volume": "3", "issue": "增刊９", "kind": "supplement", "note_id": "PN-GEO-2025-09"})
    result = calculate(crossyear)["balance"]
    assert any(q["accession"] == "00098" and q["code"] == "NOTE_MISMATCH" for q in result["quarantine"])


def test_note_year_outside_order_segment_blocks_dataset(crossyear):
    crossyear["publication_notes"][0]["span"] = [2025, 2027]
    with pytest.raises(LedgerError) as error:
        calculate(crossyear)
    assert error.value.code == "NOTE_OUT_OF_ORDER"


def test_duplicate_note_id_blocks_dataset(crossyear):
    crossyear["publication_notes"].append({**crossyear["publication_notes"][0]})
    with pytest.raises(LedgerError) as error:
        calculate(crossyear)
    assert error.value.code == "NOTE_ID_DUPLICATE"


def test_note_title_from_other_chain_blocks_dataset(crossyear):
    crossyear["publication_notes"][0]["title"] = "方志资料辑刊"
    with pytest.raises(LedgerError) as error:
        calculate(crossyear)
    assert error.value.code == "NOTE_TITLE_MISMATCH"


def test_invalid_note_shape_blocks_dataset(crossyear):
    crossyear["publication_notes"].append({"note_id": "PN-BAD", "chain": "CST"})
    with pytest.raises(LedgerError) as error:
        calculate(crossyear)
    assert error.value.code == "INVALID_NOTE"


def test_dataset_without_notes_remains_backward_compatible(clean):
    result = calculate(clean)["balance"]
    assert result["note_summary"] == []
    assert all(s["cross_year"] is False and s["note_id"] is None for s in result["slots"])
