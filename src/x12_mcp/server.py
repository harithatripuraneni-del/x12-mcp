"""The MCP server: exposes the parser, validator and explainers as Claude tools.

Design choices worth knowing:
- Every tool is read-only and works on text passed in by the client. The server
  never opens files, calls the network or changes anything, so it is safe to
  connect to Claude without granting access to real systems.
- Validation is deterministic. Claude can explain the results, but the pass or
  fail verdict comes from plain code, not from the model.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from . import explain
from .parser import X12ParseError, parse
from .validator import validate

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)

mcp = MCPServer(
    name="x12-mcp",
    instructions=(
        "Tools for reading X12 EDI. Use validate_edi before trusting a file, "
        "parse_edi to see its structure, and summarize_shipment_status for 214s."
    ),
)


def _parse_or_error(edi_text: str):
    try:
        return parse(edi_text), None
    except X12ParseError as exc:
        return None, {"error": str(exc)}


@mcp.tool(annotations=READ_ONLY)
def validate_edi(edi_text: str) -> dict:
    """Check an X12 file's envelopes and structure.

    Verifies ISA/IEA, GS/GE and ST/SE control numbers and counts, segments
    outside envelopes, and required segments for 204, 210, 214, 990 and 997.
    """
    ic, err = _parse_or_error(edi_text)
    if err:
        return {"valid": False, "errors": [err["error"]], "warnings": []}
    issues = validate(ic)
    errors = [i.to_dict() for i in issues if i.severity == "error"]
    warnings = [i.to_dict() for i in issues if i.severity == "warning"]
    return {"valid": not errors, "errors": errors, "warnings": warnings}


@mcp.tool(annotations=READ_ONLY)
def parse_edi(edi_text: str) -> dict:
    """Break an X12 file into its envelopes, transactions and segments."""
    ic, err = _parse_or_error(edi_text)
    return err or explain.outline(ic)


@mcp.tool(annotations=READ_ONLY)
def summarize_shipment_status(edi_text: str) -> dict:
    """Summarize 214 shipment status messages: references, parties and a status timeline."""
    ic, err = _parse_or_error(edi_text)
    return err or {"shipments": explain.summarize_shipment_status(ic)}


@mcp.tool(annotations=READ_ONLY)
def explain_segment(segment_id: str) -> str:
    """Explain what an X12 segment ID (such as AT7 or B10) is for."""
    return explain.describe_segment(segment_id)


def main() -> None:
    mcp.run()  # stdio transport, which Claude Code and Claude Desktop use


if __name__ == "__main__":
    main()
