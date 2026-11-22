from pathlib import Path

import pytest

from x12_mcp.explain import describe_segment, summarize_shipment_status
from x12_mcp.parser import X12ParseError, parse
from x12_mcp.validator import validate

SAMPLES = Path(__file__).parent.parent / "samples"
GOOD_214 = (SAMPLES / "shipment_status_214.edi").read_text()
BROKEN_204 = (SAMPLES / "load_tender_204_broken.edi").read_text()


def codes(text: str) -> set[str]:
    return {issue.code for issue in validate(parse(text))}


def test_detects_delimiters_from_isa():
    d = parse(GOOD_214).delimiters
    assert (d.element, d.component, d.segment) == ("*", ">", "~")


def test_handles_custom_delimiters():
    custom = GOOD_214.replace("*", "|").replace("~", "\n").replace("|>\n", "|:\n")
    ic = parse(custom)
    assert ic.delimiters.element == "|"
    assert ic.groups[0].transactions[0].set_id == "214"
    assert codes(custom) == set()


def test_builds_envelopes():
    ic = parse(GOOD_214)
    assert len(ic.groups) == 1
    txn = ic.groups[0].transactions[0]
    assert txn.set_id == "214" and txn.se is not None
    assert [s.id for s in txn.body][:3] == ["B10", "N1", "N1"]


def test_valid_file_has_no_issues():
    assert validate(parse(GOOD_214)) == []


def test_broken_file_reports_each_problem():
    assert {"SE_SEGMENT_COUNT", "SE_CONTROL_MISMATCH", "IEA_CONTROL_MISMATCH"} <= codes(BROKEN_204)


def test_missing_trailers():
    no_trailers = GOOD_214.replace("SE*14*0001~\n", "").replace("IEA*1*000000101~\n", "")
    assert {"SE_MISSING", "IEA_MISSING"} <= codes(no_trailers)


def test_missing_required_segment():
    without_b10 = GOOD_214.replace("B10*PRO123456*SHIP98765*ACMEFRT~\n", "").replace("SE*14", "SE*13")
    assert codes(without_b10) == {"REQUIRED_SEGMENT"}


def test_rejects_non_x12():
    with pytest.raises(X12ParseError):
        parse("hello world")


def test_shipment_timeline():
    [shipment] = summarize_shipment_status(parse(GOOD_214))
    assert shipment["reference"] == "PRO123456"
    assert shipment["parties"][1] == {"role": "Consignee", "name": "Lone Star Retail"}
    last = shipment["events"][-1]
    assert last["status"] == "Completed unloading at delivery location"
    assert last["location"] == "Dallas, TX"
    assert last["when"] == "2026-11-20 14:20 CT"


def test_describe_segment():
    assert "Shipment Status" in describe_segment("at7")
    assert "not in this tool" in describe_segment("ZZZ")
