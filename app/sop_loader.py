import os
from pathlib import Path
import yaml


class SOPLoaderError(Exception):
    """Custom exception raised when SOP definitions cannot be loaded or parsed."""
    pass


DEFAULT_SOP_PATH = Path(__file__).parent.parent / "data" / "sops.yaml"


def load_sops(sop_path=None):
    """
    Loads and parses the SOPs YAML file.

    Args:
        sop_path (str or Path, optional): Path to the sops.yaml file.
                                          Defaults to data/sops.yaml in project root.

    Returns:
        list[dict]: A list of SOP dictionary definitions.

    Raises:
        SOPLoaderError: If file is missing, invalid YAML, or improper schema structure.
    """
    path = Path(sop_path) if sop_path else DEFAULT_SOP_PATH

    if not path.exists():
        raise SOPLoaderError(f"SOP file not found at path: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise SOPLoaderError(f"Failed to parse SOP YAML file at {path}: {exc}") from exc
    except Exception as exc:
        raise SOPLoaderError(f"Error reading SOP file at {path}: {exc}") from exc

    if not isinstance(data, dict) or "sops" not in data or not isinstance(data["sops"], list):
        raise SOPLoaderError(f"Invalid SOP file format at {path}: expected top-level 'sops' key containing a list of SOPs.")

    return data["sops"]
