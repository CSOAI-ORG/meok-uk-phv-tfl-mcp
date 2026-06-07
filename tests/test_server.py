import sys, os
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import (
    check_phv_driver_licence, check_phv_vehicle_licence, check_phv_operator_licence,
    check_dbs_enhanced_3year, check_meds_topographical, check_safeguarding_training,
    audit_journey_record_keeping, prepare_tfl_inspection_pack,
    DBS_VALIDITY_DAYS, TFL_PHV_INSPECTION_PACK, KILLER_TFL_FINDINGS,
)


def _call(t, **kw):
    fn = t.fn if hasattr(t, "fn") else t
    return fn(**kw)


def _future(days):
    return (date.today() + timedelta(days=days)).isoformat()


def _past(days):
    return (date.today() - timedelta(days=days)).isoformat()


def test_driver_valid_with_dbs():
    r = _call(check_phv_driver_licence, driver_id="PCO12345",
              licence_expiry=_future(400), has_dbs_enhanced=True)
    assert r["is_valid_today"] is True
    assert r["can_be_dispatched"] is True


def test_driver_expired():
    r = _call(check_phv_driver_licence, driver_id="PCO99999",
              licence_expiry=_past(10), has_dbs_enhanced=True)
    assert r["is_valid_today"] is False
    assert r["can_be_dispatched"] is False
    assert any("EXPIRED" in i for i in r["issues"])


def test_driver_no_dbs_blocks():
    r = _call(check_phv_driver_licence, driver_id="PCO50000",
              licence_expiry=_future(400), has_dbs_enhanced=False)
    assert r["can_be_dispatched"] is False


def test_vehicle_valid_with_inspection():
    r = _call(check_phv_vehicle_licence, vrn="LR70ABC",
              plate_expiry=_future(180), last_inspection_date=_past(100),
              has_topographical_test=True)
    assert r["can_be_dispatched"] is True


def test_vehicle_expired_plate():
    r = _call(check_phv_vehicle_licence, vrn="LR60XYZ",
              plate_expiry=_past(30), last_inspection_date=_past(100),
              has_topographical_test=True)
    assert r["can_be_dispatched"] is False


def test_vehicle_lapsed_inspection():
    r = _call(check_phv_vehicle_licence, vrn="LR65DEF",
              plate_expiry=_future(180), last_inspection_date=_past(400),
              has_topographical_test=True)
    assert r["can_be_dispatched"] is False


def test_operator_valid():
    r = _call(check_phv_operator_licence, operator_name="ACME Minicabs",
              licensing_authority="tfl", expiry_date=_future(800))
    assert any("5 years" in i or "5-year" in i for i in [r.get("advisory", "")])


def test_operator_expired():
    r = _call(check_phv_operator_licence, operator_name="ACME Minicabs",
              expiry_date=_past(10))
    assert any("EXPIRED" in i for i in r["issues"])


def test_dbs_post_2024_valid():
    r = _call(check_dbs_enhanced_3year, driver_id="P1",
              last_dbs_date=_past(500), authority="tfl",
              is_post_dec_2024_renewal=True)
    assert r["is_valid"] is True
    assert "post-Dec-2024" in r["regime"]


def test_dbs_post_2024_expired_at_3yr_plus():
    r = _call(check_dbs_enhanced_3year, driver_id="P2",
              last_dbs_date=_past(1200), authority="tfl",
              is_post_dec_2024_renewal=True)
    assert r["is_valid"] is False


def test_dbs_legacy_5yr_still_valid():
    r = _call(check_dbs_enhanced_3year, driver_id="P3",
              last_dbs_date=_past(1500), authority="tfl",
              is_post_dec_2024_renewal=False)
    assert r["is_valid"] is True


def test_meds_topographical_flags_missing_test():
    r = _call(check_meds_topographical, driver_id="D1",
              last_medical_date=_past(200), has_topographical_test=False)
    assert any("Topographical" in i for i in r["issues"])


def test_meds_old_medical_flagged():
    r = _call(check_meds_topographical, driver_id="D2",
              last_medical_date=_past(2200), has_topographical_test=True)
    assert any("medical" in i.lower() for i in r["issues"])


def test_safeguarding_valid():
    r = _call(check_safeguarding_training, driver_id="D1",
              completion_date=_past(500))
    assert r["is_valid"] is True


def test_safeguarding_expired():
    r = _call(check_safeguarding_training, driver_id="D2",
              completion_date=_past(1200))
    assert r["is_valid"] is False


def test_safeguarding_renewal_warning():
    r = _call(check_safeguarding_training, driver_id="D3",
              completion_date=_past(1010))  # ~85 days to expiry
    assert any("schedule refresher" in i.lower() or "expires" in i.lower() for i in r["issues"])


def test_journey_record_compliant_tfl():
    r = _call(audit_journey_record_keeping, operator_name="ACME",
              licensing_authority="tfl", earliest_record_date=_past(800))
    assert r["compliant"] is True
    assert r["required_retention_days"] == 730


def test_journey_record_short_of_2yr():
    r = _call(audit_journey_record_keeping, operator_name="ACME",
              licensing_authority="tfl", earliest_record_date=_past(400))
    assert r["compliant"] is False


def test_journey_record_council_1yr():
    r = _call(audit_journey_record_keeping, operator_name="Council Cabs",
              licensing_authority="council_standard",
              earliest_record_date=_past(400))
    assert r["required_retention_days"] == 365


def test_inspection_pack_includes_killers():
    r = _call(prepare_tfl_inspection_pack, operator_name="ACME",
              licence_number="LIC-1234567", fleet_size=120)
    assert len(r["evidence_checklist"]) >= 10
    assert len(r["killer_findings_to_pre_check"]) >= 5


def test_attestation_chain():
    r = _call(check_phv_driver_licence, driver_id="X",
              licence_expiry=_future(100), has_dbs_enhanced=True)
    assert r["issuer"] == "meok-uk-phv-tfl-mcp"
    assert "ts" in r and "sig" in r


def test_dbs_validity_table():
    assert DBS_VALIDITY_DAYS["tfl_post_2024"] == 1095


def test_inspection_pack_static_table_size():
    assert len(TFL_PHV_INSPECTION_PACK) >= 10
    assert len(KILLER_TFL_FINDINGS) >= 5


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
