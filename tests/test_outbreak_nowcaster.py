"""
Automated Pytest Test Suite for Outbreak Nowcaster.
Domain: Antimicrobial Stewardship & Microbiology
Standard: CLSI M100 / EUCAST / CDC NHSN Guidelines
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agents.base import PHIGuard, AuditLogger, SecurityException, AuditTrail
from agents.models import SystemTaskPayload, UrgencyLevel, SystemIntegrityStatus
from agents.workers import InvariantQCWorker, SafetyEscalationWorker, ProtocolConformanceWorker
from agents.supervisor import SystemSupervisor
from cli import main, _safe_resolve_path


def test_phi_guard_enforcement():
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("Patient MRN-994827 blood culture positive for Staphylococcus")

    # Clean text passes
    PHIGuard.assert_no_phi("Analytical assay specimen KEY-001 optimal")


def test_specialized_workers():
    # Worker 1: QC Invariant
    p1 = SystemTaskPayload(task_id="T1", target_identifier="KEY-01", primary_metric=35.0)
    alerts1 = InvariantQCWorker.evaluate(p1)
    assert len(alerts1) == 1
    assert alerts1[0].urgency == UrgencyLevel.ELEVATED

    # Worker 2: Safety
    p2 = SystemTaskPayload(task_id="T2", target_identifier="KEY-02", primary_metric=10.0, is_critical_flag=True)
    alerts2 = SafetyEscalationWorker.evaluate(p2)
    assert len(alerts2) == 1
    assert alerts2[0].urgency == UrgencyLevel.CRITICAL_STAT

    # Worker 3: Protocol Conformance
    p3 = SystemTaskPayload(task_id="T3", target_identifier="KEY-03", primary_metric=10.0, status_descriptor="DISCORDANT_ANOMALY")
    alerts3 = ProtocolConformanceWorker.evaluate(p3)
    assert len(alerts3) == 1


def test_supervisor_consensus_and_audit():
    supervisor = SystemSupervisor(model_provider="mock")
    payload = SystemTaskPayload(
        task_id="TASK-PROD-01",
        target_identifier="KEY-PROD-01",
        primary_metric=12.0,
        secondary_metric=4.0,
        status_descriptor="NOMINAL"
    )
    dossier = supervisor.process_task(payload)
    assert dossier.overall_urgency == UrgencyLevel.ROUTINE
    assert dossier.integrity_status == SystemIntegrityStatus.VALIDATED
    assert dossier.audit_hash != ""

    # Verify cryptographic audit trail
    assert AuditLogger.verify_integrity() is True

    # CLI tests
    assert main(["audit", "--task-id", "CLI-TEST-01"]) == 0
    assert main(["chat", "Explain", "specifications"]) == 0
    assert main(["verify-audit"]) == 0


def test_phi_guard_ssn_detection():
    """Test PHI guard detects SSN patterns."""
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("Patient SSN: 123-45-6789")


def test_phi_guard_phone_detection():
    """Test PHI guard detects phone numbers."""
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("Contact: (555) 123-4567")


def test_phi_guard_email_detection():
    """Test PHI guard detects email addresses."""
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("Email: patient@hospital.org")


def test_phi_guard_dob_detection():
    """Test PHI guard detects date of birth patterns."""
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("DOB: 01/15/1985")


def test_phi_guard_name_detection():
    """Test PHI guard detects patient name patterns."""
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("Patient Name: John Smith")


def test_phi_guard_redaction():
    """Test PHI redaction replaces identifiers."""
    text = "Patient MRN-12345 has appointment"
    redacted = PHIGuard.redact_phi(text)
    assert "MRN-12345" not in redacted
    assert "REDACTED_IDENTIFIER" in redacted


def test_phi_guard_no_pattern_exposure():
    """Test that PHI error messages don't expose regex patterns."""
    try:
        PHIGuard.assert_no_phi("Patient MRN-12345")
        assert False, "Should have raised SecurityException"
    except SecurityException as e:
        error_msg = str(e)
        # Should not expose the regex pattern
        assert "MRN" not in error_msg or "pattern" not in error_msg.lower()
        assert "re.compile" not in error_msg


def test_phi_guard_empty_input():
    """Test PHI guard handles empty/None input gracefully."""
    PHIGuard.assert_no_phi("")
    PHIGuard.assert_no_phi(None)


def test_audit_trail_integrity():
    """Test HMAC audit trail integrity verification."""
    trail = AuditTrail(secret_key="test-key-for-testing")
    trail.log("test_actor", "tier1", "TEST_EVENT", {"data": "value1"})
    trail.log("test_actor", "tier1", "TEST_EVENT", {"data": "value2"})
    assert trail.verify_integrity() is True


def test_audit_trail_tamper_detection():
    """Test that audit trail detects tampering."""
    trail = AuditTrail(secret_key="test-key-for-testing")
    trail.log("test_actor", "tier1", "TEST_EVENT", {"data": "value1"})
    # Tamper with the entry
    if trail.logs:
        trail.logs[0]["payload_hash"] = "tampered_hash"
    assert trail.verify_integrity() is False


def test_audit_trail_chaining():
    """Test that audit trail entries are properly chained."""
    trail = AuditTrail(secret_key="test-key-for-testing")
    trail.log("actor1", "tier1", "EVENT1", {"a": 1})
    trail.log("actor2", "tier2", "EVENT2", {"b": 2})

    assert len(trail.logs) == 2
    assert trail.logs[1]["prev_hash"] == trail.logs[0]["current_hash"]


def test_safe_resolve_path():
    """Test safe path resolution."""
    from pathlib import Path
    result = _safe_resolve_path(".")
    assert isinstance(result, Path)
    assert result.is_absolute()
