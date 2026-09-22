import pytest
from app.sop_loader import load_sops, SOPLoaderError

VALID_TRIGGER_TYPES = {"numeric", "compound", "fuzzy"}


def test_load_sops_success():
    """Test that sops.yaml loads successfully and returns a list."""
    sops = load_sops()
    assert isinstance(sops, list)


def test_exactly_twelve_sops():
    """Test that exactly 12 SOPs are loaded."""
    sops = load_sops()
    assert len(sops) == 12, f"Expected 12 SOPs, but got {len(sops)}"


def test_every_sop_has_id():
    """Test that every SOP has a non-empty string ID."""
    sops = load_sops()
    for sop in sops:
        assert "id" in sop and isinstance(sop["id"], str) and len(sop["id"]) > 0


def test_every_sop_has_trigger_type():
    """Test that every SOP has a trigger_type."""
    sops = load_sops()
    for sop in sops:
        assert "trigger_type" in sop and isinstance(sop["trigger_type"], str)


def test_sop_ids_are_unique():
    """Test that all SOP IDs are unique."""
    sops = load_sops()
    sop_ids = [sop["id"] for sop in sops]
    assert len(sop_ids) == len(set(sop_ids)), f"Duplicate SOP IDs found: {sop_ids}"


def test_valid_trigger_types_only():
    """Test that trigger types are strictly numeric, compound, or fuzzy."""
    sops = load_sops()
    for sop in sops:
        assert sop["trigger_type"] in VALID_TRIGGER_TYPES, (
            f"SOP {sop.get('id')} has invalid trigger_type: {sop.get('trigger_type')}"
        )


def test_load_sops_non_existent_file():
    """Test that SOPLoaderError is raised when file does not exist."""
    with pytest.raises(SOPLoaderError):
        load_sops("non_existent_file.yaml")
