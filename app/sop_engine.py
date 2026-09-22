"""
Deterministic SOP Engine for WeatherGuide.
Evaluates numeric and compound weather SOPs against live weather metrics.
Fuzzy SOPs are skipped (deferred to LLM layer).
"""

SEVERITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3
}


def evaluate_condition(condition: dict, weather: dict) -> bool:
    """
    Evaluates a single condition dictionary against weather metrics.

    Args:
        condition (dict): Contains 'field', 'operator', and 'value'.
        weather (dict): Weather metrics dictionary.

    Returns:
        bool: True if condition is satisfied, False otherwise.
    """
    if not isinstance(condition, dict):
        return False

    field = condition.get("field")
    operator = condition.get("operator")
    target_value = condition.get("value")

    if not field or not operator or target_value is None:
        return False

    if field not in weather or weather[field] is None:
        return False

    actual_value = weather[field]

    try:
        if operator == ">=":
            return actual_value >= target_value
        elif operator == "<=":
            return actual_value <= target_value
        elif operator == ">":
            return actual_value > target_value
        elif operator == "<":
            return actual_value < target_value
        elif operator == "==":
            return actual_value == target_value
        else:
            return False
    except TypeError:
        return False


def is_sop_matching(sop: dict, weather: dict) -> bool:
    """
    Determines if a given SOP matches the weather data.

    Args:
        sop (dict): SOP definition dictionary.
        weather (dict): Weather metrics dictionary.

    Returns:
        bool: True if SOP is numeric/compound and matches, False otherwise.
    """
    trigger_type = sop.get("trigger_type")

    # Skip fuzzy SOPs
    if trigger_type == "fuzzy":
        return False

    raw_conditions = sop.get("conditions")
    if not raw_conditions:
        return False

    # Normalize single dict condition to a list for unified processing
    if isinstance(raw_conditions, dict):
        conditions_list = [raw_conditions]
    elif isinstance(raw_conditions, list):
        conditions_list = raw_conditions
    else:
        return False

    if len(conditions_list) == 0:
        return False

    # Compound & Numeric require ALL conditions to evaluate to True (AND semantics)
    for cond in conditions_list:
        if not evaluate_condition(cond, weather):
            return False

    return True


def match_sops(sops: list, weather: dict) -> list:
    """
    Return deterministic SOPs that match the supplied weather data.

    Fuzzy SOPs are skipped.
    Matching SOPs are sorted by severity (critical > high > medium > low).
    Same-severity SOPs preserve their original input order.

    Args:
        sops (list[dict]): List of SOP definitions.
        weather (dict): Weather metrics dictionary.

    Returns:
        list[dict]: Matching SOPs ordered by severity.
    """
    if not isinstance(sops, list) or not isinstance(weather, dict):
        return []

    matching = [sop for sop in sops if is_sop_matching(sop, weather)]

    # Sort matching SOPs stably by severity order
    matching.sort(
        key=lambda sop: SEVERITY_ORDER.get(str(sop.get("severity", "low")).lower(), 99)
    )

    return matching
