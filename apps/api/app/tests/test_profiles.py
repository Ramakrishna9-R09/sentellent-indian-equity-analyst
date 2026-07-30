from app.services.profiles import extract_profile_patch


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
