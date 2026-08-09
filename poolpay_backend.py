from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from typing import Any

CENT = Decimal("0.01")


def money(value: int | float | str | Decimal) -> Decimal:
    """Convert a value to a two-decimal Decimal for financial calculations."""
    return Decimal(str(value)).quantize(CENT)


def create_pot(
    name: str,
    closing_date: str,
    description: str = "",
    spending_limit: int | float | str | Decimal | None = None,
    virtual_card_last4: str = "6489",
) -> dict[str, Any]:
    """Create an in-memory shared pot for the prototype."""
    if not name.strip():
        raise ValueError("Pot name cannot be empty.")

    limit = None
    if spending_limit not in (None, "", 0, "0", "0.00"):
        limit = money(spending_limit)
        if limit <= 0:
            raise ValueError("Spending limit must be greater than zero.")

    return {
        "name": name.strip(),
        "description": description.strip(),
        "closing_date": closing_date,
        "status": "Open",
        "spending_limit": limit,
        "card": {"last4": str(virtual_card_last4), "status": "Active"},
        "members": {},
        "transactions": [],
        "processed_keys": set(),
        "settlement": None,
        "next_transaction_id": 1,
    }


def _next_id(pot: dict[str, Any]) -> int:
    transaction_id = pot["next_transaction_id"]
    pot["next_transaction_id"] += 1
    return transaction_id


def _add_activity(pot: dict[str, Any], transaction_type: str, **fields: Any) -> int:
    transaction_id = _next_id(pot)
    pot["transactions"].append(
        {
            "transaction_id": transaction_id,
            "type": transaction_type,
            "date_time": datetime.now().isoformat(timespec="seconds"),
            **fields,
        }
    )
    return transaction_id


def _check_open(pot: dict[str, Any]) -> None:
    if pot["status"] != "Open":
        raise ValueError("Cannot perform this action on a closed pot.")


def _check_idempotency(pot: dict[str, Any], key: str | None) -> None:
    if key is not None and key in pot["processed_keys"]:
        raise ValueError("Duplicate transaction rejected.")


def _remember_key(pot: dict[str, Any], key: str | None) -> None:
    if key is not None:
        pot["processed_keys"].add(key)


def add_member(pot: dict[str, Any], member_name: str, role: str = "Member") -> None:
    _check_open(pot)
    name = member_name.strip()
    if not name:
        raise ValueError("Member name cannot be empty.")
    if name in pot["members"]:
        raise ValueError(f"{name} is already in the pot.")
    if role not in {"Admin", "Member"}:
        raise ValueError("Role must be Admin or Member.")

    pot["members"][name] = {
        "role": role,
        "active": True,
        "total_contributed": money(0),
    }
    _add_activity(pot, "member_joined", member=name)


def transfer_admin(pot: dict[str, Any], current_admin: str, new_admin: str) -> None:
    _check_open(pot)
    if current_admin not in pot["members"] or new_admin not in pot["members"]:
        raise ValueError("Both users must belong to the pot.")
    if pot["members"][current_admin]["role"] != "Admin":
        raise ValueError("Only the current admin can transfer the role.")
    if not pot["members"][new_admin]["active"]:
        raise ValueError("The new admin must be active.")

    pot["members"][current_admin]["role"] = "Member"
    pot["members"][new_admin]["role"] = "Admin"
    _add_activity(pot, "admin_transferred", member=new_admin)


def leave_member(pot: dict[str, Any], member_name: str) -> None:
    _check_open(pot)
    if member_name not in pot["members"]:
        raise ValueError(f"{member_name} is not a member of this pot.")
    member = pot["members"][member_name]
    if member["role"] == "Admin":
        raise ValueError("The admin must transfer the admin role before leaving.")
    if not member["active"]:
        raise ValueError(f"{member_name} has already left the pot.")

    member["active"] = False
    _add_activity(pot, "member_left", member=member_name)


def set_card_frozen(pot: dict[str, Any], frozen: bool) -> None:
    _check_open(pot)
    pot["card"]["status"] = "Frozen" if frozen else "Active"
    _add_activity(pot, "card_status_changed", status=pot["card"]["status"])


def add_contribution(
    pot: dict[str, Any],
    member_name: str,
    amount: int | float | str | Decimal,
    idempotency_key: str | None = None,
) -> int:
    _check_open(pot)
    if member_name not in pot["members"]:
        raise ValueError(f"{member_name} is not a member of this pot.")
    if not pot["members"][member_name]["active"]:
        raise ValueError(f"{member_name} is no longer an active member.")

    _check_idempotency(pot, idempotency_key)
    contribution = money(amount)
    if contribution <= 0:
        raise ValueError("Contribution amount must be greater than zero.")

    pot["members"][member_name]["total_contributed"] += contribution
    transaction_id = _add_activity(
        pot,
        "contribution",
        member=member_name,
        amount=contribution,
    )
    _remember_key(pot, idempotency_key)
    return transaction_id


def calculate_total_contributed(pot: dict[str, Any]) -> Decimal:
    return money(
        sum(
            (member["total_contributed"] for member in pot["members"].values()),
            Decimal("0.00"),
        )
    )


def calculate_total_spent(pot: dict[str, Any]) -> Decimal:
    return money(
        sum(
            (
                transaction["final_amount"]
                for transaction in pot["transactions"]
                if transaction["type"] == "expense"
            ),
            Decimal("0.00"),
        )
    )


def calculate_total_refunded(pot: dict[str, Any]) -> Decimal:
    return money(
        sum(
            (
                transaction["amount"]
                for transaction in pot["transactions"]
                if transaction["type"] == "refund"
            ),
            Decimal("0.00"),
        )
    )


def calculate_balance(pot: dict[str, Any]) -> Decimal:
    return money(
        calculate_total_contributed(pot)
        - calculate_total_spent(pot)
        - calculate_total_refunded(pot)
    )


def record_expense(
    pot: dict[str, Any],
    member_name: str,
    merchant: str,
    original_amount: int | float | str | Decimal,
    discount: int | float | str | Decimal = 0,
    category: str = "Other",
    idempotency_key: str | None = None,
    **_: Any,
) -> int:
    _check_open(pot)
    if member_name not in pot["members"]:
        raise ValueError(f"{member_name} is not a member of this pot.")
    if not pot["members"][member_name]["active"]:
        raise ValueError(f"{member_name} is no longer an active member.")
    if pot["card"]["status"] == "Frozen":
        raise ValueError("The pot card is frozen.")

    _check_idempotency(pot, idempotency_key)

    original = money(original_amount)
    saving = money(discount)
    final_amount = money(original - saving)

    if original <= 0 or final_amount <= 0:
        raise ValueError("Expense amount must be greater than zero.")
    if saving < 0 or saving >= original:
        raise ValueError("Discount must be smaller than the original amount.")
    if pot["spending_limit"] is not None and final_amount > pot["spending_limit"]:
        raise ValueError("Payment exceeds the pot spending limit.")
    if final_amount > calculate_balance(pot):
        raise ValueError("Payment rejected because of insufficient pot balance.")

    transaction_id = _add_activity(
        pot,
        "expense",
        member=member_name,
        merchant=merchant,
        category=category,
        original_amount=original,
        discount=saving,
        final_amount=final_amount,
    )
    _remember_key(pot, idempotency_key)
    return transaction_id


def calculate_refunds(pot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return unused funds in proportion to each member's contribution share."""
    if pot["status"] == "Closed" and pot["settlement"] is not None:
        return pot["settlement"]["refunds"]

    total_contributed = calculate_total_contributed(pot)
    remaining = calculate_balance(pot)
    if total_contributed <= 0:
        raise ValueError("Cannot calculate refunds without contributions.")

    raw: dict[str, Decimal] = {}
    for name, member in pot["members"].items():
        contribution = member["total_contributed"]
        if contribution > 0:
            raw[name] = remaining * contribution / total_contributed

    rounded = {
        name: amount.quantize(CENT, rounding=ROUND_DOWN)
        for name, amount in raw.items()
    }
    allocated = sum(rounded.values(), Decimal("0.00"))
    cents_remaining = int((remaining - allocated) / CENT)
    ranked = sorted(raw, key=lambda name: raw[name] - rounded[name], reverse=True)

    for name in ranked[:cents_remaining]:
        rounded[name] += CENT

    return {
        name: {
            "contribution": money(pot["members"][name]["total_contributed"]),
            "contribution_share": pot["members"][name]["total_contributed"] / total_contributed,
            "refund_amount": money(refund),
        }
        for name, refund in rounded.items()
    }


def close_pot(pot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    _check_open(pot)
    refunds = calculate_refunds(pot)
    remaining = calculate_balance(pot)
    total_refunds = money(
        sum((item["refund_amount"] for item in refunds.values()), Decimal("0.00"))
    )

    if total_refunds != remaining:
        raise ValueError("Settlement error: refunds do not match the remaining balance.")

    pot["settlement"] = {
        "remaining_balance": remaining,
        "total_refunds": total_refunds,
        "refunds": refunds,
    }

    for member_name, item in refunds.items():
        _add_activity(
            pot,
            "refund",
            member=member_name,
            amount=item["refund_amount"],
        )

    pot["status"] = "Closed"
    _add_activity(pot, "pot_closed", amount=total_refunds)

    if calculate_balance(pot) != money(0):
        raise ValueError("Settlement error: closed pot balance did not reduce to zero.")

    return refunds


def build_demo_pot() -> dict[str, Any]:
    """Build the Bangkok Trip scenario used in the report and presentation."""
    pot = create_pot(
        name="Bangkok Trip",
        description="Thailand group trip",
        closing_date="2026-08-31",
    )

    add_member(pot, "Nick", role="Admin")
    add_member(pot, "Conner")
    add_member(pot, "Gianni")
    add_member(pot, "Divya")
    add_member(pot, "Jiayun")

    contributions = {
        "Nick": "480.00",
        "Conner": "600.00",
        "Gianni": "350.00",
        "Divya": "500.00",
        "Jiayun": "410.50",
    }
    for name, amount in contributions.items():
        add_contribution(pot, name, amount, idempotency_key=f"seed-{name}")

    jetstar_transaction_id = record_expense(
        pot,
        "Nick",
        "Jetstar",
        "920.00",
        discount="30.00",
        category="Travel",
        idempotency_key="seed-jetstar",
    )
    record_expense(
        pot,
        "Conner",
        "Airbnb",
        "645.00",
        category="Accommodation",
        idempotency_key="seed-airbnb",
    )
    record_expense(
        pot,
        "Gianni",
        "Bangkok Restaurant",
        "237.00",
        category="Dining",
        idempotency_key="seed-restaurant",
    )

    return {"pot": pot, "jetstar_transaction_id": jetstar_transaction_id}


if __name__ == "__main__":
    demo = build_demo_pot()["pot"]
    print("PoolPay Bangkok Trip demo")
    print(f"Total funded: A${calculate_total_contributed(demo):,.2f}")
    print(f"Total spent: A${calculate_total_spent(demo):,.2f}")
    print(f"Remaining: A${calculate_balance(demo):,.2f}")
    print("Refund preview:")
    for name, item in calculate_refunds(demo).items():
        print(f"  {name}: A${item['refund_amount']:,.2f}")
