"""Envelope and structure checks: the problems that break EDI in production.

Every check returns plain Issue objects. Nothing here guesses or uses AI:
the rules are deterministic, so they can safely gate a release.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .dictionary import FUNCTIONAL_IDS, REQUIRED_SEGMENTS, TRANSACTION_SETS
from .parser import Interchange, Segment, Transaction


@dataclass
class Issue:
    severity: str  # "error" breaks processing; "warning" deserves a look
    code: str  # short stable identifier, useful for filtering
    message: str
    position: int | None = None  # segment position in the file, if known

    def to_dict(self) -> dict:
        return asdict(self)


def _same_number(a: str, b: str) -> bool:
    """Control numbers can be zero-padded differently: '000000101' == '101'."""
    a, b = a.strip(), b.strip()
    if a.isdigit() and b.isdigit():
        return int(a) == int(b)
    return a == b


def _check_interchange(ic: Interchange) -> list[Issue]:
    issues: list[Issue] = []
    isa = ic.isa
    if len(isa.elements) != 16:
        issues.append(Issue("error", "ISA_ELEMENTS", f"ISA must have 16 elements, found {len(isa.elements)}.", isa.position))

    if ic.iea is None:
        issues.append(Issue("error", "IEA_MISSING", "Interchange has no IEA trailer."))
        return issues

    if not _same_number(ic.iea.get(2), isa.get(13)):
        issues.append(Issue(
            "error", "IEA_CONTROL_MISMATCH",
            f"IEA02 '{ic.iea.get(2)}' does not match ISA13 '{isa.get(13)}'.", ic.iea.position,
        ))
    if not _same_number(ic.iea.get(1), str(len(ic.groups))):
        issues.append(Issue(
            "error", "IEA_GROUP_COUNT",
            f"IEA01 says {ic.iea.get(1)} group(s) but the file has {len(ic.groups)}.", ic.iea.position,
        ))
    return issues


def _check_transaction(txn: Transaction, functional_id: str) -> list[Issue]:
    issues: list[Issue] = []
    st = txn.st
    set_id = txn.set_id

    if set_id not in TRANSACTION_SETS:
        issues.append(Issue("warning", "UNKNOWN_SET", f"Transaction set '{set_id}' is not in this tool's reference list.", st.position))

    expected_fid = FUNCTIONAL_IDS.get(set_id)
    if expected_fid and functional_id != expected_fid:
        issues.append(Issue(
            "warning", "GS_FUNCTIONAL_ID",
            f"A {set_id} is usually sent in a GS with functional ID '{expected_fid}', not '{functional_id}'.", st.position,
        ))

    if txn.se is None:
        issues.append(Issue("error", "SE_MISSING", f"Transaction {set_id} (ST02 {txn.control_number}) has no SE trailer.", st.position))
    else:
        actual = len(txn.body) + 2  # SE01 counts ST and SE themselves
        if not _same_number(txn.se.get(1), str(actual)):
            issues.append(Issue(
                "error", "SE_SEGMENT_COUNT",
                f"SE01 says {txn.se.get(1)} segments but the transaction has {actual}.", txn.se.position,
            ))
        if txn.se.get(2) != txn.control_number:
            issues.append(Issue(
                "error", "SE_CONTROL_MISMATCH",
                f"SE02 '{txn.se.get(2)}' does not match ST02 '{txn.control_number}'.", txn.se.position,
            ))

    present = {seg.id for seg in txn.body}
    for required in REQUIRED_SEGMENTS.get(set_id, []):
        if required not in present:
            issues.append(Issue("error", "REQUIRED_SEGMENT", f"A {set_id} needs a {required} segment.", st.position))
    return issues


def validate(ic: Interchange) -> list[Issue]:
    """Run every check and return the issues found, in file order."""
    issues = _check_interchange(ic)

    for seg in ic.stray:
        issues.append(Issue("error", "OUTSIDE_ENVELOPE", f"Segment {seg.id} sits outside any ST/SE or GS/GE envelope.", seg.position))

    for group in ic.groups:
        gs: Segment = group.gs
        if group.ge is None:
            issues.append(Issue("error", "GE_MISSING", f"Group with GS06 '{gs.get(6)}' has no GE trailer.", gs.position))
        else:
            if not _same_number(group.ge.get(2), gs.get(6)):
                issues.append(Issue(
                    "error", "GE_CONTROL_MISMATCH",
                    f"GE02 '{group.ge.get(2)}' does not match GS06 '{gs.get(6)}'.", group.ge.position,
                ))
            if not _same_number(group.ge.get(1), str(len(group.transactions))):
                issues.append(Issue(
                    "error", "GE_TRANSACTION_COUNT",
                    f"GE01 says {group.ge.get(1)} transaction(s) but the group has {len(group.transactions)}.", group.ge.position,
                ))
        for txn in group.transactions:
            issues.extend(_check_transaction(txn, gs.get(1)))

    return sorted(issues, key=lambda i: (i.position is None, i.position or 0))
