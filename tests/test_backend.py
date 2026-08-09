from decimal import Decimal

import pytest

from poolpay_backend import (
    add_contribution,
    add_member,
    build_demo_pot,
    calculate_balance,
    calculate_refunds,
    calculate_total_contributed,
    calculate_total_spent,
    close_pot,
    create_pot,
    leave_member,
    record_expense,
)


def test_bangkok_demo_totals():
    pot = build_demo_pot()["pot"]
    assert calculate_total_contributed(pot) == Decimal("2340.50")
    assert calculate_total_spent(pot) == Decimal("1772.00")
    assert calculate_balance(pot) == Decimal("568.50")


def test_refunds_reconcile_to_remaining_balance():
    pot = build_demo_pot()["pot"]
    refunds = calculate_refunds(pot)
    total_refunds = sum(
        (item["refund_amount"] for item in refunds.values()),
        Decimal("0.00"),
    )
    assert total_refunds == Decimal("568.50")


def test_duplicate_contribution_is_rejected():
    pot = create_pot("Test", "2026-12-31")
    add_member(pot, "Nick", role="Admin")
    add_contribution(pot, "Nick", "100", idempotency_key="same-key")
    with pytest.raises(ValueError, match="Duplicate transaction rejected"):
        add_contribution(pot, "Nick", "100", idempotency_key="same-key")


def test_overspending_is_rejected():
    pot = create_pot("Test", "2026-12-31")
    add_member(pot, "Nick", role="Admin")
    add_contribution(pot, "Nick", "100")
    with pytest.raises(ValueError, match="insufficient pot balance"):
        record_expense(pot, "Nick", "Hotel", "101")


def test_inactive_member_cannot_spend():
    pot = create_pot("Test", "2026-12-31")
    add_member(pot, "Nick", role="Admin")
    add_member(pot, "Alex")
    add_contribution(pot, "Alex", "100")
    leave_member(pot, "Alex")
    with pytest.raises(ValueError, match="no longer an active member"):
        record_expense(pot, "Alex", "Cafe", "10")


def test_closed_pot_rejects_new_activity_and_finishes_at_zero():
    pot = build_demo_pot()["pot"]
    close_pot(pot)
    assert calculate_balance(pot) == Decimal("0.00")
    with pytest.raises(ValueError, match="closed pot"):
        add_contribution(pot, "Nick", "10")
    with pytest.raises(ValueError, match="closed pot"):
        record_expense(pot, "Nick", "Cafe", "10")
