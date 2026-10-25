import pytest

from env.variables import domain_assistant_keys
from tests import harness as H

COVERAGE_FAIL_TASK_IDS = ["submit_claim#1", "submit_claim#5", "submit_claim#9", "submit_claim#10",
                          "submit_claim#19", "submit_claim#20"]

TEXT_VS_CODE = [
    ("bank", "positive", "sufficient_account_balance", "more account balance", "equal to or greater than"),
    ("bank", "positive", "not_over_credit_limit", "the credit limit subtracted from the credit balance",
     "the credit balance subtracted from the credit limit"),
    ("bank", "negative", "not_over_credit_limit", "the credit limit subtracted from the credit balance",
     "the credit balance subtracted from the credit limit"),
    ("bank", "negative", "get_loan_owed_balance_restr", "owed balance more than", "equal to or greater than"),
    ("dmv", "positive", "above_minimum_age", "above the minimum age", "at least the minimum age"),
    ("dmv", "negative", "above_minimum_age", "above the minimum age", "**must be younger than** the minimum age"),
    ("dmv", "positive", "within_vehicle_renewal_period", "date-time values", "by date only"),
    ("dmv", "negative", "within_vehicle_renewal_period", "date-time values", "by date only"),
    ("dmv", "positive", "within_dl_renewal_period", "date-time values", "by date only"),
    ("dmv", "negative", "within_dl_renewal_period", "date-time values", "by date only"),
    ("dmv", "positive", "internal_check_test_slot_available", "NON-EXISTENT",
     "exists in the \"{test_type}\" of test_slots"),
    ("dmv", "negative", "drive_test_ready", "knowledge test and", "knowledge test **or**"),
    ("dmv", "negative", "before_test_date", "strictly after", "at the same time as or after"),
    ("dmv", "negative", "within_attempt_limit", "more than {attempt_limit}", "{attempt_limit} or more"),
    ("dmv", "negative", "test_scheduled", "'scheduled' and", "'scheduled' **or**"),
    ("healthcare", "positive", "within_enrollment_period", "starts from the enrollment date",
     "that moment included, and has no lower bound"),
    ("healthcare", "negative", "within_enrollment_period", "starts from the enrollment_date",
     "that moment included, and has no lower bound"),
    ("healthcare", "positive", "within_appeal_period", "starts from the claim date",
     "that moment included, and has no lower bound"),
    ("healthcare", "negative", "within_appeal_period", "starts from the claim_date",
     "that moment included, and has no lower bound"),
    ("healthcare", "positive", "appointment_date_valid", "**MUST BE AFTER**",
     "taken at 00:00:00 of its date, **MUST BE AT THE SAME TIME AS OR AFTER**"),
    ("healthcare", "positive", "appointment_date_valid", "**MUST BE AFTER**", "must be written as YYYY-MM-DD"),
    ("healthcare", "negative", "appointment_date_valid", "before past", "taken at 00:00:00 of its date, **MUST BE BEFORE**"),
    ("healthcare", "negative", "appointment_date_valid", "before past", "or it is not written as YYYY-MM-DD"),
    ("healthcare", "negative", "claim_within_limits", "must be greater than", "equal to or greater than"),
    ("healthcare", "positive", "amount_positive_restr", "greater than zero", "zero or greater"),
    ("healthcare", "negative", "amount_positive_restr", "not greater than zero", "less than zero"),
    ("healthcare", "positive", "provider_available", "'Available' in order", "'Available', compared case-insensitively"),
    ("healthcare", "negative", "provider_available", "Inavailable",
     "other than 'Available', compared case-insensitively"),
    ("library", "positive", "sufficient_account_balance_for_late_fee", "more account balance", "equal to or greater than"),
    ("library", "negative", "sufficient_account_balance_for_late_fee", "more account balance", "strictly less than"),
    ("library", "positive", "sufficient_account_balance_for_membership", "more account balance", "equal to or greater than"),
    ("library", "negative", "sufficient_account_balance_for_membership", "more account balance", "strictly less than"),
    ("library", "negative", "user_book_borrowed", "at least one user", "of the user \"{username}\""),
    ("online_market", "positive", "less_than_max_exchanges", "MUST NOT EXCEED", "LESS THAN"),
    ("online_market", "negative", "less_than_max_exchanges", "MUST EXCEED", "EQUAL TO OR GREATER THAN"),
    ("online_market", "positive", "within_exchange_period", "starts from the order placed date",
     "that moment included, and has no lower bound"),
    ("online_market", "negative", "within_exchange_period", "starts from the order_placed_date",
     "that moment included, and has no lower bound"),
    ("online_market", "positive", "within_return_period", "starts from the order placed date",
     "that moment included, and has no lower bound"),
    ("online_market", "negative", "within_return_period", "starts from the order_placed_date",
     "that moment included, and has no lower bound"),
    ("online_market", "positive", "not_already_added_shipping_address", "\"{address}\" **MUST",
     "\"{address}\", compared case-insensitively, **MUST NOT ALREADY EXIST**"),
    ("online_market", "negative", "not_already_added_shipping_address", "\"{address}\" **MUST",
     "\"{address}\", compared case-insensitively, **MUST ALREADY EXIST**"),
    ("hotel", "positive", "before_check_out_time", "be **before**", "at or before"),
    ("hotel", "negative", "before_check_out_time", "on or after", "strictly after"),
    ("hotel", "positive", "is_gold_or_higher_member", "\"platinum\".",
     "either \"gold\" or \"platinum\", compared case-insensitively"),
    ("hotel", "negative", "is_gold_or_higher_member", "\"silver\"",
     "neither \"gold\" nor \"platinum\", compared case-insensitively"),
    ("university", "positive", "before_graduation_deadline", "**MUST BE BEFORE**", "**MUST BE AT OR BEFORE**"),
    ("university", "positive", "before_graduation_deadline", "**MUST BE BEFORE**", "means 00:00:00 on that date"),
    ("university", "negative", "before_graduation_deadline", "The current date", "means 00:00:00 on that date"),
    ("university", "positive", "within_minor_declaration_period", "**MUST FALL** before", "**MUST BE AT OR BEFORE**"),
    ("university", "positive", "within_minor_declaration_period", "**MUST FALL** before", "means 00:00:00 on that date"),
    ("university", "negative", "within_minor_declaration_period", "declaration date", "means 00:00:00 on that date"),
    ("university", "positive", "within_withdrawal_period", "**MUST BE BEFORE**", "**MUST BE AT OR BEFORE**"),
    ("university", "positive", "within_withdrawal_period", "**MUST BE BEFORE**", "means 00:00:00 on that date"),
    ("university", "negative", "within_withdrawal_period", "in academic calendar", "means 00:00:00 on that date"),
    ("university", "positive", "meets_income_requirements", "income under", "income of at most"),
    ("university", "positive", "meets_major_restriction", "a major allowed by", "an empty list allows no major"),
    ("university", "negative", "meets_major_restriction", "a major allowed by", "when the list is empty, no major is listed"),
    ("university", "negative", "meets_min_gpa_for_aid", "GREATER THAN", "BELOW"),
    ("university", "negative", "meets_minor_gpa_requirement", "MUST NOT EXCEED", "MUST BE BELOW"),
    ("university", "negative", "under_max_major_changes", "HAS EXCEEDED", "{max_major_changes} or more"),
]


def test_coverage_constraint_in_the_prompt_counts_the_new_claim():
    tasks = [t for t in H.load_tasks("healthcare") if t["id"] in COVERAGE_FAIL_TASK_IDS]
    prompts = [H.assistant_info("healthcare", t)["instructions"] for t in tasks]
    assert len(prompts) == 6
    for prompt in prompts:
        assert "including the new claim of \"amount\"" in prompt
        assert "when submitting a new claim" not in prompt


@pytest.mark.parametrize("domain, polarity, constraint, old, new", TEXT_VS_CODE)
def test_constraint_description_says_what_the_code_checks(domain, polarity, constraint, old, new):
    text = getattr(domain_assistant_keys[domain], f"{polarity}_constraint_descriptions")[constraint]
    assert old not in text and new in text
