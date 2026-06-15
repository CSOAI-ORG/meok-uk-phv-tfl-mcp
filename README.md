<!-- mcp-name: io.github.CSOAI-ORG/meok-uk-phv-tfl-mcp -->
[![MCP Scorecard: 90/100](https://img.shields.io/badge/proofof.ai-90%2F100-5b21b6)](https://proofof.ai/scorecard/meok-uk-phv-tfl-mcp.html)

# meok-uk-phv-tfl-mcp

> UK Private Hire Vehicle + Hackney Carriage + TfL licensing compliance. PHV driver + vehicle + operator licences, DBS, safeguarding, journey records, inspection prep. By **MEOK AI Labs**.

## Why this exists

70,000+ Uber UK drivers. 50,000+ Bolt drivers. 50+ minicab operators in London. £1.5bn UK ride-hail market.

Post-Dec-2024 TfL tightening introduced **Enhanced DBS every 3 years** (was 5), mandatory Safeguarding Awareness, extended journey-record retention. Council variations outside London matter.

This MCP gives ride-hail platforms, PHV operators, and fleet managers a callable compliance layer.

## Install

```bash
pip install meok-uk-phv-tfl-mcp
```

## Tools (8)

| Tool | Use case |
|------|----------|
| `check_phv_driver_licence` | PCO/PHV number + expiry + DBS in one call |
| `check_phv_vehicle_licence` | Plate + annual inspection + topographical |
| `check_phv_operator_licence` | TfL 5-yr or council variation |
| `check_dbs_enhanced_3year` | Post-Dec-2024 3-year cycle |
| `check_meds_topographical` | DfT Group 2 + London topographical |
| `check_safeguarding_training` | TfL 3-year safeguarding cycle |
| `audit_journey_record_keeping` | 2-year TfL / 1-year council retention |
| `prepare_tfl_inspection_pack` | Unannounced TfL TPH visit prep |

## Pricing

- **Free** — MIT self-host
- **Starter** — £29/mo
- **Pro** — £79/mo (multi-driver + multi-vehicle)
- **Fleet** — £499/mo (50+ drivers / vehicles, audit export)

## Regulatory basis

- Local Government (Miscellaneous Provisions) Act 1976
- Private Hire Vehicles (London) Act 1998
- Transport Act 1985 (Hackney)
- TfL Taxi & Private Hire Licensing Regulations (post-Dec 2024 tightening)
- Deregulation Act 2015 (cross-border hire)
- Equality Act 2010
- DBS Enhanced Disclosure Regulations

## License

MIT © 2026 Nicholas Templeman / MEOK AI Labs · [haulage.app](https://haulage.app)


## Configuration

Add to your `claude_desktop_config.json` (Claude Desktop) or your MCP client config:

```json
{
  "mcpServers": {
    "meok-uk-phv-tfl-mcp": {
      "command": "uvx",
      "args": ["meok-uk-phv-tfl-mcp"]
    }
  }
}
```

Or: `pip install meok-uk-phv-tfl-mcp` then run the `meok-uk-phv-tfl-mcp` command (stdio transport).

## Examples

Once configured, ask your assistant, for example:
- "Use `check_phv_driver_licence` to …"
- "Use `check_phv_vehicle_licence` to …"
- "Use `check_phv_operator_licence` to …"


<!-- GEO-FOOTER:v1 -->

---

### Part of the MEOK constellation

This MCP is one node in a connected ecosystem built by **MEOK AI LABS** around a single
sovereign AI core — governed agents with a hash-chained audit trail, mapped to the CSOAI
compliance charter.

- 🌐 The whole map: **<https://meok.ai/constellation>**
- 🛡️ AI governance & certification: **<https://councilof.ai>** · **<https://csoai.org>**
- ✅ Verify any signed report: **<https://meok.ai/verify>**

## See also

MEOK compliance MCP fleet:
[`meok-vehicle-handover-mcp`](https://github.com/CSOAI-ORG/meok-vehicle-handover-mcp)
