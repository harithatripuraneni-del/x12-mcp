# x12-mcp

**Give Claude the ability to read, validate and explain X12 EDI.**

X12 EDI still moves most of the world's freight, purchase orders and invoices, but AI assistants don't understand it out of the box. `x12-mcp` is a small [Model Context Protocol](https://modelcontextprotocol.io) server that teaches Claude (or any MCP client) to work with X12 files safely.

Ask Claude things like:

- *"Is this 204 valid? What's wrong with it?"*
- *"Where is this shipment right now?"* (with a 214 pasted in)
- *"What does the AT7 segment mean?"*

## Tools

| Tool | What it does |
| --- | --- |
| `validate_edi` | Checks ISA/IEA, GS/GE and ST/SE control numbers and counts, segments outside envelopes, and required segments for 204, 210, 214, 990 and 997 |
| `parse_edi` | Breaks a file into envelopes, transactions and segments, with delimiters read from the ISA header |
| `summarize_shipment_status` | Turns a 214 into references, parties and a plain-English status timeline |
| `explain_segment` | Explains what a segment ID is for |

## Design choices

- **Read-only by design.** Every tool takes text and returns data. The server never opens files, calls the network or changes anything, and each tool is annotated as read-only for the client.
- **Deterministic verdicts.** Pass or fail comes from plain, tested code, not from the model. Claude explains the results; it doesn't decide them.
- **No assumptions about delimiters.** Separators are read from the ISA header, so files using `|`, `:` or newline terminators work too.
- **Zero-dependency core.** The parser and validator are pure Python; only the server layer needs the MCP SDK.

## Quick start

Requires Python 3.10+.

```bash
git clone https://github.com/harithatripuraneni-del/x12-mcp.git
cd x12-mcp
pip install -e ".[dev]"
pytest
```

### Connect it to Claude Code

```bash
claude mcp add x12 -- python -m x12_mcp.server
```

### Connect it to Claude Desktop

Add this to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "x12": {
      "command": "python",
      "args": ["-m", "x12_mcp.server"]
    }
  }
}
```

Then try it with the files in [`samples/`](samples/): one valid 214 shipment status and one deliberately broken 204 load tender.

## Example

Validating `samples/load_tender_204_broken.edi` returns:

```json
{
  "valid": false,
  "errors": [
    {"code": "SE_SEGMENT_COUNT", "message": "SE01 says 7 segments but the transaction has 6.", "position": 8},
    {"code": "SE_CONTROL_MISMATCH", "message": "SE02 '0002' does not match ST02 '0001'.", "position": 8},
    {"code": "IEA_CONTROL_MISMATCH", "message": "IEA02 '000000999' does not match ISA13 '000000202'.", "position": 10}
  ],
  "warnings": []
}
```

## Project layout

```
src/x12_mcp/
  parser.py      read delimiters, split segments, build ISA/GS/ST envelopes
  validator.py   deterministic envelope and structure checks
  dictionary.py  reference data: segments, transaction sets, status codes
  explain.py     plain-English summaries and a JSON outline
  server.py      the MCP server and its four tools
tests/           pytest suite
samples/         synthetic example files (no real trading-partner data)
```

## Limitations and next steps

This is a focused starting point, not a full X12 implementation. It does not validate element-level rules from implementation guides (lengths, code lists, loops). Ideas for what's next:

- Summaries for 204 load tenders and 210 invoices
- Generating a 997 acknowledgment from validation results
- Loading partner-specific rules from a simple config file

## License

MIT. Sample files are synthetic and contain no real company data.
