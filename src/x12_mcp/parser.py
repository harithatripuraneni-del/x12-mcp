"""Parse raw X12 text into segments and envelopes.

An X12 file is a stream of *segments* (records). Each segment is a list of
*elements* (fields). The ISA header at the very start tells us which
characters the sender used as separators, so we read those first instead of
assuming the usual `*` and `~`.

Envelopes nest like this:

    ISA ... IEA          interchange (one "envelope" between two partners)
      GS ... GE          functional group (a batch of one document type)
        ST ... SE        transaction set (one business document, e.g. a 214)
"""

from __future__ import annotations

from dataclasses import dataclass, field


class X12ParseError(ValueError):
    """Raised when the text cannot be read as X12 at all."""


@dataclass
class Delimiters:
    element: str  # separates elements inside a segment, usually "*"
    component: str  # separates sub-elements, from ISA16, often ">" or ":"
    segment: str  # ends a segment, usually "~"


@dataclass
class Segment:
    id: str  # segment ID such as "ISA", "ST" or "AT7"
    elements: list[str]  # element values after the ID; elements[0] is XX01
    position: int  # 1-based position in the file, handy in error messages

    def get(self, n: int, default: str = "") -> str:
        """Return element n using X12's 1-based numbering (AT705 -> get(5))."""
        return self.elements[n - 1] if 0 < n <= len(self.elements) else default

    def to_dict(self) -> dict:
        return {"position": self.position, "id": self.id, "elements": self.elements}


@dataclass
class Transaction:
    st: Segment
    body: list[Segment] = field(default_factory=list)  # segments between ST and SE
    se: Segment | None = None

    @property
    def set_id(self) -> str:
        return self.st.get(1)  # ST01, e.g. "214"

    @property
    def control_number(self) -> str:
        return self.st.get(2)  # ST02


@dataclass
class Group:
    gs: Segment
    transactions: list[Transaction] = field(default_factory=list)
    ge: Segment | None = None


@dataclass
class Interchange:
    delimiters: Delimiters
    isa: Segment
    groups: list[Group] = field(default_factory=list)
    iea: Segment | None = None
    segments: list[Segment] = field(default_factory=list)  # every segment, in order
    stray: list[Segment] = field(default_factory=list)  # segments outside any envelope


def detect_delimiters(text: str) -> Delimiters:
    """Read the separators from the ISA header.

    ISA always has 16 elements. The character right after "ISA" is the element
    separator, ISA16 is a single character (the component separator), and the
    character right after ISA16 ends the segment.
    """
    if not text.startswith("ISA") or len(text) < 106:
        raise X12ParseError("Text must start with a complete ISA segment.")

    element_sep = text[3]
    seen = 0
    for i, ch in enumerate(text):
        if ch == element_sep:
            seen += 1
            if seen == 16:  # the next character is ISA16
                if i + 2 >= len(text):
                    break
                return Delimiters(
                    element=element_sep,
                    component=text[i + 1],
                    segment=text[i + 2],
                )
    raise X12ParseError("ISA segment is incomplete: expected 16 elements.")


def split_segments(text: str, delims: Delimiters) -> list[Segment]:
    segments: list[Segment] = []
    for raw in text.split(delims.segment):
        raw = raw.strip("\r\n\t ")  # files often add line breaks after "~"
        if not raw:
            continue
        parts = raw.split(delims.element)
        segments.append(Segment(id=parts[0], elements=parts[1:], position=len(segments) + 1))
    return segments


def parse(text: str) -> Interchange:
    """Parse one X12 interchange into nested envelopes."""
    text = text.lstrip("\ufeff \r\n\t")  # tolerate a byte-order mark or leading blank lines
    delims = detect_delimiters(text)
    segments = split_segments(text, delims)

    interchange = Interchange(delimiters=delims, isa=segments[0], segments=segments)
    group: Group | None = None
    txn: Transaction | None = None

    for seg in segments[1:]:
        if seg.id == "GS":
            group = Group(gs=seg)
            interchange.groups.append(group)
            txn = None  # a new group closes any transaction left open
        elif seg.id == "ST" and group is not None:
            txn = Transaction(st=seg)
            group.transactions.append(txn)
        elif seg.id == "SE" and txn is not None:
            txn.se = seg
            txn = None
        elif seg.id == "GE" and group is not None:
            group.ge = seg
            group = None
            txn = None  # GE closes any transaction missing its SE
        elif seg.id == "IEA":
            interchange.iea = seg
        elif txn is not None:
            txn.body.append(seg)
        else:
            interchange.stray.append(seg)

    return interchange
