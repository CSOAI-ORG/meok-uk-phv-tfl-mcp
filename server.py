#!/usr/bin/env python3
"""
MEOK UK PHV + TfL Licensing Compliance MCP
============================================

By MEOK AI Labs · https://haulage.app · MIT
<!-- mcp-name: io.github.CSOAI-ORG/meok-uk-phv-tfl-mcp -->

WHAT THIS DOES
--------------
UK ride-hail + minicab + Hackney Carriage compliance.
70,000+ Uber UK drivers · 50,000+ Bolt drivers · 50+ minicab operators in London.
£1.5bn UK ride-hail market.

Post-2024 TfL tightening introduced Enhanced DBS every 3 years (was 5),
mandatory Safeguarding Awareness, plus extended journey-record retention.
Local councils outside London diverge significantly.

This MCP gives PHV operators, fleet managers, and ride-hail platforms a
callable layer for:
  - PHV driver licence + DBS validation
  - PHV vehicle + operator licence checks
  - TfL Safeguarding Awareness
  - Topographical Knowledge Test
  - Journey record retention
  - TfL Taxi & Private Hire inspection prep

TOOLS (8)
---------
- check_phv_driver_licence(driver_id, expiry, has_dbs)
- check_phv_vehicle_licence(vrn, has_topographical_test)
- check_phv_operator_licence(operator_data)
- check_dbs_enhanced_3year(driver_id, last_dbs_date)
- check_meds_topographical(driver_id, ...)
- check_safeguarding_training(driver_id, completion_date)
- audit_journey_record_keeping(operator_data)
- prepare_tfl_inspection_pack(operator_data)

PRICING
-------
Free MIT self-host · £29/mo Starter · £79/mo Pro · £499/mo Fleet.

REGULATORY BASIS
----------------
- Local Government (Miscellaneous Provisions) Act 1976 (council-licensed)
- Private Hire Vehicles (London) Act 1998
- Transport Act 1985 (Hackney)
- TfL Taxi & Private Hire Licensing Regulations
- Deregulation Act 2015 (cross-border hire)
- Equality Act 2010 (wheelchair access)
- DBS Enhanced Disclosure Regulations
"""

from __future__ import annotations
import urllib.request as _meter_urlreq
import urllib.error as _meter_urlerr
import hashlib, hmac, json, os
from datetime import datetime, timezone, date
from typing import Optional
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("meok-uk-phv-tfl")
_HMAC_SECRET = os.environ.get("MEOK_HMAC_SECRET", "")


# ──────────────────────────────────────────────────────────────────────
# Regulatory tables
# ──────────────────────────────────────────────────────────────────────

DBS_VALIDITY_DAYS = {
    "tfl_post_2024": 1095,     # Enhanced DBS — 3 yrs (post Dec 2024 tightening)
    "tfl_pre_2024": 1825,      # 5 yrs (legacy)
    "council_standard": 1095,  # Local councils typically 3 yrs
}

SAFEGUARDING_CYCLE_DAYS = 1095  # TfL 3-year cycle

SAFETY_INSPECTION_DAYS = {
    "tfl_phv": 365,            # Vehicle inspection every 12 months
    "tfl_taxi": 365,
    "council_phv": 365,
}

JOURNEY_RECORD_RETENTION_DAYS = {
    "tfl": 730,                # 2 years
    "council_standard": 365,   # 1 year (varies by council)
}

TFL_PHV_INSPECTION_PACK = [
    "Operator licence + variation history",
    "Premises records (if applicable)",
    "Driver register: PCO/PHV number, DBS expiry, Medical, Safeguarding",
    "Vehicle register: VRN, PHV plate, vehicle inspection, MOT, insurance",
    "Booking + journey records (2-year retention TfL)",
    "Customer complaint log + resolution",
    "Lost property procedure",
    "Wheelchair accessibility / equality compliance",
    "GDPR — passenger data + ANPR / dashcam policy",
    "Anti-touting + cross-border hire log",
    "Disability training records",
    "Safeguarding policy + incident reports",
    "Insurance certificates (Hire & Reward)",
    "Vehicle examiner reports + remediation log",
    "TfL FOI requests + responses",
]

KILLER_TFL_FINDINGS = [
    "PHV driver licence expired AND still being dispatched",
    "DBS expired (>3 years) for driver still working",
    "Safeguarding training expired AND no refresher booked",
    "Booking records purged before 2-year retention",
    "Vehicle inspection lapsed AND vehicle still in service",
    "Hire & Reward insurance lapsed (one of the worst findings)",
    "Operator failed to investigate customer complaint within 28 days",
    "Driver dispatched without valid Topographical Knowledge Test",
]


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _sign(payload: dict) -> str:
    if not _HMAC_SECRET:
        return "unsigned-no-key-configured"
    return hmac.new(_HMAC_SECRET.encode(),
                    json.dumps(payload, sort_keys=True, default=str).encode(),
                    hashlib.sha256).hexdigest()


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _attestation(payload: dict) -> dict:
    return {**payload, "ts": _ts(), "sig": _sign(payload),
            "issuer": "meok-uk-phv-tfl-mcp", "version": "1.0.0"}


# ──────────────────────────────────────────────────────────────────────
# Tools
# ──────────────────────────────────────────────────────────────────────


def _server_meter_check(api_key: str = "") -> dict:
    """Calls the live /verify endpoint for server-side metering. Fail-open."""
    try:
        data = json.dumps({"api_key": api_key, "tool": ""}).encode()
        req = _meter_urlreq.Request(_METER_URL, data=data,
            headers={"Content-Type": "application/json"}, method="POST")
        with _meter_urlreq.urlopen(req, timeout=2.5) as r:
            d = json.loads(r.read())
            if isinstance(d, dict) and "allowed" in d:
                return d
    except Exception:
        pass
    return {"allowed": True, "tier": "anonymous", "remaining": 200, "upgrade_url": "https://meok.ai/pricing"}


_METER_URL = "https://proofof.ai/verify"


@mcp.tool()
def check_phv_driver_licence(
    driver_id: str,
    driver_name: str = "",
    licence_expiry: str = "",
    has_dbs_enhanced: bool = False,
    licensing_authority: str = "tfl",
) -> dict:
    """Verify a PHV driver licence is current.

    Args:
      driver_id: PCO / PHV number
      licence_expiry: ISO date YYYY-MM-DD
      has_dbs_enhanced: enhanced DBS present
      licensing_authority: 'tfl' or council name
    """
    try:
        exp = date.fromisoformat(licence_expiry)
        days_to_expiry = (exp - date.today()).days
        valid = days_to_expiry > 0
    except Exception:
        days_to_expiry = -1; valid = False

    issues = []
    if not valid: issues.append("LICENCE EXPIRED — driver cannot work")
    elif days_to_expiry < 30: issues.append(f"Expires in {days_to_expiry} days")
    if not has_dbs_enhanced:
        issues.append("No Enhanced DBS on record — required")

    return _attestation({
        "tool": "check_phv_driver_licence",
        "driver_id": driver_id,
        "driver_name": driver_name,
        "licensing_authority": licensing_authority,
        "days_to_expiry": days_to_expiry,
        "is_valid_today": valid,
        "issues": issues,
        "can_be_dispatched": valid and has_dbs_enhanced,
    })


@mcp.tool()
def check_phv_vehicle_licence(
    vrn: str,
    plate_expiry: str = "",
    last_inspection_date: str = "",
    has_topographical_test: bool = False,
    is_wheelchair_accessible: bool = False,
) -> dict:
    """Verify a PHV vehicle's licence + inspection status."""
    try:
        plate_exp = date.fromisoformat(plate_expiry)
        plate_days = (plate_exp - date.today()).days
        plate_valid = plate_days > 0
    except Exception:
        plate_days = -1; plate_valid = False

    try:
        insp = date.fromisoformat(last_inspection_date)
        days_since_inspection = (date.today() - insp).days
        inspection_current = days_since_inspection < SAFETY_INSPECTION_DAYS["tfl_phv"]
    except Exception:
        days_since_inspection = 9999; inspection_current = False

    issues = []
    if not plate_valid: issues.append("PLATE EXPIRED")
    elif plate_days < 30: issues.append(f"Plate expires {plate_days}d")
    if not inspection_current:
        issues.append(f"Vehicle inspection {days_since_inspection}d ago — needs annual")
    if not has_topographical_test:
        issues.append("Topographical Knowledge Test not on record (London PHV)")

    return _attestation({
        "tool": "check_phv_vehicle_licence",
        "vrn": vrn,
        "plate_days_to_expiry": plate_days,
        "days_since_inspection": days_since_inspection,
        "is_wheelchair_accessible": is_wheelchair_accessible,
        "issues": issues,
        "can_be_dispatched": plate_valid and inspection_current,
    })


@mcp.tool()
def check_phv_operator_licence(
    operator_name: str,
    licensing_authority: str = "tfl",
    licence_class: str = "standard",  # standard / restricted
    issue_date: str = "",
    expiry_date: str = "",
    has_booking_premises: bool = True,
) -> dict:
    """Verify a PHV operator licence (TfL 5-year standard)."""
    try:
        exp = date.fromisoformat(expiry_date)
        days_to_expiry = (exp - date.today()).days
        valid = days_to_expiry > 0
    except Exception:
        days_to_expiry = -1; valid = False

    issues = []
    if not valid: issues.append("OPERATOR LICENCE EXPIRED")
    elif days_to_expiry < 90:
        issues.append(f"Operator licence expires {days_to_expiry}d — start renewal NOW")

    return _attestation({
        "tool": "check_phv_operator_licence",
        "operator": operator_name,
        "authority": licensing_authority,
        "class": licence_class,
        "days_to_expiry": days_to_expiry,
        "has_premises": has_booking_premises,
        "issues": issues,
        "advisory": (
            "TfL standard operator licence valid 5 years. Renewal application requires 12-week lead-time."
            if licensing_authority.lower() == "tfl"
            else "Local council variations apply — check authority website."
        ),
    })


@mcp.tool()
def check_dbs_enhanced_3year(
    driver_id: str,
    last_dbs_date: str = "",
    authority: str = "tfl",
    is_post_dec_2024_renewal: bool = True,
) -> dict:
    """DBS Enhanced check — TfL tightened to 3 years from Dec 2024."""
    if authority.lower() == "tfl" and is_post_dec_2024_renewal:
        validity_days = DBS_VALIDITY_DAYS["tfl_post_2024"]
        regime = "TfL post-Dec-2024 (3 years)"
    elif authority.lower() == "tfl":
        validity_days = DBS_VALIDITY_DAYS["tfl_pre_2024"]
        regime = "TfL pre-Dec-2024 legacy (5 years)"
    else:
        validity_days = DBS_VALIDITY_DAYS["council_standard"]
        regime = "Council standard (3 years)"

    try:
        last = date.fromisoformat(last_dbs_date)
        days_since = (date.today() - last).days
        valid = days_since < validity_days
        days_to_expiry = validity_days - days_since
    except Exception:
        days_since = 9999; valid = False; days_to_expiry = -1

    issues = []
    if not valid: issues.append("DBS EXPIRED — driver must not be dispatched")
    elif days_to_expiry < 60: issues.append(f"DBS expires in {days_to_expiry}d — book renewal")

    return _attestation({
        "tool": "check_dbs_enhanced_3year",
        "driver_id": driver_id,
        "regime": regime,
        "days_since_dbs": days_since,
        "days_to_dbs_expiry": days_to_expiry,
        "is_valid": valid,
        "issues": issues,
    })


@mcp.tool()
def check_meds_topographical(
    driver_id: str,
    medical_group: str = "group_2",  # DfT D2/D4 = Group 2
    last_medical_date: str = "",
    has_topographical_test: bool = False,
    topographical_test_date: str = "",
) -> dict:
    """DfT Group 2 medical (D2/D4) + Topographical Knowledge Test (London)."""
    try:
        med = date.fromisoformat(last_medical_date)
        days_since_med = (date.today() - med).days
        # Group 2 medical re-tests at age 45/65/70 + 5-yearly after; assume 1825d window
        med_valid = days_since_med < 1825
    except Exception:
        days_since_med = 9999; med_valid = False

    issues = []
    if not med_valid: issues.append("Group 2 medical >5y old — renewal required")
    if not has_topographical_test:
        issues.append("No Topographical Knowledge Test on record (London PHV mandatory)")

    return _attestation({
        "tool": "check_meds_topographical",
        "driver_id": driver_id,
        "medical_group": medical_group,
        "days_since_medical": days_since_med,
        "medical_valid": med_valid,
        "has_topographical_test": has_topographical_test,
        "topographical_test_date": topographical_test_date,
        "issues": issues,
    })


@mcp.tool()
def check_safeguarding_training(
    driver_id: str,
    completion_date: str = "",
    course_provider: str = "",
) -> dict:
    """TfL Safeguarding Awareness — 3-year cycle, mandatory for PHV/Hackney."""
    try:
        comp = date.fromisoformat(completion_date)
        days_since = (date.today() - comp).days
        valid = days_since < SAFEGUARDING_CYCLE_DAYS
        days_to_expiry = SAFEGUARDING_CYCLE_DAYS - days_since
    except Exception:
        days_since = 9999; valid = False; days_to_expiry = -1

    issues = []
    if not valid: issues.append("Safeguarding expired — driver must complete refresher")
    elif days_to_expiry < 90: issues.append(f"Safeguarding expires in {days_to_expiry}d — schedule refresher")

    return _attestation({
        "tool": "check_safeguarding_training",
        "driver_id": driver_id,
        "course_provider": course_provider,
        "days_since_completion": days_since,
        "days_to_expiry": days_to_expiry,
        "is_valid": valid,
        "issues": issues,
        "regulator_ref": "TfL Taxi & Private Hire Licensing",
    })


@mcp.tool()
def audit_journey_record_keeping(
    operator_name: str,
    licensing_authority: str = "tfl",
    earliest_record_date: str = "",
    total_journey_records: int = 0,
) -> dict:
    """Audit booking + journey record retention compliance."""
    retention_days = JOURNEY_RECORD_RETENTION_DAYS.get(
        licensing_authority.lower(), JOURNEY_RECORD_RETENTION_DAYS["council_standard"]
    )
    try:
        earliest = date.fromisoformat(earliest_record_date)
        days_back = (date.today() - earliest).days
    except Exception:
        days_back = 0

    compliant = days_back >= retention_days
    issues = []
    if not compliant:
        issues.append(f"Records go back only {days_back}d — requirement is {retention_days}d")

    return _attestation({
        "tool": "audit_journey_record_keeping",
        "operator": operator_name,
        "authority": licensing_authority,
        "required_retention_days": retention_days,
        "actual_retention_days": days_back,
        "total_records": total_journey_records,
        "compliant": compliant,
        "issues": issues,
        "advisory": (
            "TfL retention is 2 years. Council variations: most also 2 years; some only 1."
        ),
    })


@mcp.tool()
def prepare_tfl_inspection_pack(
    operator_name: str,
    licence_number: str = "",
    fleet_size: int = 0,
    expected_visit_date: str = "",
) -> dict:
    """TfL Taxi & Private Hire inspection prep — evidence checklist + killer findings."""
    return _attestation({
        "tool": "prepare_tfl_inspection_pack",
        "operator": operator_name,
        "licence_number": licence_number,
        "fleet_size": fleet_size,
        "expected_visit_date": expected_visit_date,
        "evidence_checklist": TFL_PHV_INSPECTION_PACK,
        "killer_findings_to_pre_check": KILLER_TFL_FINDINGS,
        "advisory": (
            "TfL inspections are unannounced. Pre-check the killer findings list weekly. "
            "Operator licence revocation rate has risen since 2024 enforcement uplift."
        ),
        "tfl_compliance_hotline": "020 7222 1234 (TfL TPH Customer Services)",
    })


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()


# ── MEOK monetization layer (Stripe upgrade · PAYG · pricing) ──────────
# Free tier is zero-config. Upgrade to Pro (unlimited) or pay-as-you-go per call.
import os as _meok_os
MEOK_STRIPE_UPGRADE = "https://buy.stripe.com/5kQ6oJ0xS3ce8sl7ew8k91j"  # Pro (unlimited)
MEOK_PAYG_KEY = _meok_os.environ.get("MEOK_PAYG_KEY", "")  # set to enable PAYG (x402 / ~GBP0.05 per call)
MEOK_PRICING = "https://meok.ai/pricing"


def meok_upsell(tier: str = "free") -> dict:
    """Monetization options for free-tier callers: Pro upgrade, PAYG, or pricing page."""
    if tier != "free":
        return {}
    return {"upgrade_url": MEOK_STRIPE_UPGRADE,
            "payg_enabled": bool(MEOK_PAYG_KEY),
            "pricing": MEOK_PRICING}
