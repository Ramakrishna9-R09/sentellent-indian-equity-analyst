from app.services.profiles import default_profile, extract_profile_patch


def test_explicit_conservative_income_profile_is_extracted() -> None:
    patch = extract_profile_patch(
        "I am a conservative, dividend-focused investor and I avoid high-debt companies."
    )

    assert patch["risk_tolerance"] == "conservative"
    assert patch["objectives"] == ["income"]
    assert patch["avoid_high_debt"] is True
    assert patch["max_debt_to_equity"] == 1.0


def test_non_preference_question_is_not_written_to_memory() -> None:
    assert extract_profile_patch("Show me dividend stocks with lower debt.") == {}


def test_moderate_balanced_profile_is_extracted() -> None:
    patch = extract_profile_patch("I'm a moderate investor looking for growth.")
    assert patch["risk_tolerance"] == "moderate"
    assert patch["objectives"] == ["growth"]


def test_aggressive_high_risk_profile_is_extracted() -> None:
    patch = extract_profile_patch("I am an aggressive investor with high risk tolerance.")
    assert patch["risk_tolerance"] == "aggressive"


def test_long_term_horizon_is_extracted() -> None:
    patch = extract_profile_patch("I want long term investments for growth.")
    assert patch["horizon"] == "long_term"
    assert patch["objectives"] == ["growth"]


def test_short_term_horizon_is_extracted() -> None:
    patch = extract_profile_patch("I prefer short term trading opportunities.")
    assert patch["horizon"] == "short_term"


def test_value_objective_is_extracted() -> None:
    patch = extract_profile_patch("I am a value investor.")
    assert patch["objectives"] == ["value"]


def test_multiple_objectives_are_extracted() -> None:
    patch = extract_profile_patch("I want income and growth stocks.")
    assert "income" in patch["objectives"]
    assert "growth" in patch["objectives"]


def test_default_profile_has_expected_keys() -> None:
    profile = default_profile()
    assert "risk_tolerance" in profile
    assert "objectives" in profile
    assert "avoid_high_debt" in profile
    assert "max_debt_to_equity" in profile
    assert "horizon" in profile
    assert "excluded_sectors" in profile
    assert profile["risk_tolerance"] is None
    assert profile["objectives"] == []
    assert profile["avoid_high_debt"] is False


def test_empty_message_returns_empty_patch() -> None:
    assert extract_profile_patch("") == {}
    assert extract_profile_patch("   ") == {}
