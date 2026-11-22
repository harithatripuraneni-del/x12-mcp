"""Turn X12 into plain English that a person (or Claude) can reason about."""

from __future__ import annotations

from datetime import datetime

from .dictionary import PARTY_ROLES, SEGMENTS, SHIPMENT_STATUS, TRANSACTION_SETS
from .parser import Interchange, Segment


def describe_segment(segment_id: str) -> str:
    seg = segment_id.strip().upper()
    return SEGMENTS.get(seg, f"'{seg}' is not in this tool's segment reference.")


def _format_when(date: str, time: str, zone: str) -> str:
    """'20261120', '1420', 'CT' -> '2026-11-20 14:20 CT' (best effort)."""
    try:
        stamp = datetime.strptime(date + (time or "0000")[:4], "%Y%m%d%H%M")
        text = stamp.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        text = f"{date} {time}".strip()
    return f"{text} {zone}".strip()


def summarize_shipment_status(ic: Interchange) -> list[dict]:
    """Summarize every 214 in the file: references, parties and status timeline."""
    shipments: list[dict] = []
    for group in ic.groups:
        for txn in group.transactions:
            if txn.set_id != "214":
                continue
            summary: dict = {"control_number": txn.control_number, "parties": [], "events": []}
            location = ""
            pending: dict | None = None

            def flush() -> None:
                if pending is not None:
                    pending["location"] = location
                    summary["events"].append(pending)

            for seg in txn.body:
                if seg.id == "B10":
                    summary["reference"] = seg.get(1)  # often the carrier PRO number
                    summary["shipment_id"] = seg.get(2)
                    summary["carrier_scac"] = seg.get(3)
                elif seg.id == "N1":
                    role = PARTY_ROLES.get(seg.get(1), seg.get(1))
                    summary["parties"].append({"role": role, "name": seg.get(2)})
                elif seg.id == "AT7":
                    flush()
                    location = ""
                    code = seg.get(1)
                    pending = {
                        "status_code": code,
                        "status": SHIPMENT_STATUS.get(code, f"Status code {code}"),
                        "when": _format_when(seg.get(5), seg.get(6), seg.get(7)),
                    }
                elif seg.id == "MS1":
                    location = ", ".join(part for part in (seg.get(1), seg.get(2)) if part)
            flush()
            shipments.append(summary)
    return shipments


def outline(ic: Interchange) -> dict:
    """A compact, JSON-friendly view of the file's structure."""

    def seg_list(segments: list[Segment]) -> list[dict]:
        return [s.to_dict() for s in segments]

    return {
        "delimiters": vars(ic.delimiters),
        "sender": ic.isa.get(6).strip(),
        "receiver": ic.isa.get(8).strip(),
        "interchange_control_number": ic.isa.get(13),
        "groups": [
            {
                "functional_id": g.gs.get(1),
                "control_number": g.gs.get(6),
                "transactions": [
                    {
                        "set_id": t.set_id,
                        "name": TRANSACTION_SETS.get(t.set_id, "Unknown transaction set"),
                        "control_number": t.control_number,
                        "segments": seg_list([t.st, *t.body, *([t.se] if t.se else [])]),
                    }
                    for t in g.transactions
                ],
            }
            for g in ic.groups
        ],
        "segments_outside_envelopes": seg_list(ic.stray),
    }
