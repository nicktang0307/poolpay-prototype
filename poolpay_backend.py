from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from typing import Any


CENT = Decimal("0.01")


def money(value: int | float | str | Decimal) -> Decimal:
    """Convert a value into a two-decimal Decimal for money calculations."""
    return Decimal(str(value)).quantize(CENT)


def rate(value: int | float | str | Decimal) -> Decimal:
    """Convert a percentage rate such as 0.005 into Decimal form."""
    return Decimal(str(value))


def create_pot(
    name: str,
    closing_date: str,
    description: str = "",
    auto_return: bool = True,
    spending_limit: int | float | str | Decimal | None = None,
    virtual_card_last4: str = "6489",
    interchange_share_rate: int | float | str | Decimal = "0.005",
    default_fx_spread_rate: int | float | str | Decimal = "0.005",
) -> dict[str, Any]:
    """Create and return a new PoolPay pot."""

    clean_name = name.strip()
    clean_description = description.strip()

    if not clean_name:
        raise ValueError("Pot name cannot be empty.")

    parsed_limit = None
    if spending_limit not in (None, "", 0, 0.0, "0", "0.00"):
        parsed_limit = money(spending_limit)
        if parsed_limit <= 0:
            raise ValueError("Spending limit must be greater than zero.")

    clean_last4 = str(virtual_card_last4).strip()
    if len(clean_last4) != 4 or not clean_last4.isdigit():
        raise ValueError("Virtual card last four digits must contain four numbers.")

    return {
        "name": clean_name,
        "description": clean_description,
        "closing_date": closing_date,
        "auto_return": bool(auto_return),
        "spending_limit": parsed_limit,
        "status": "Open",
        "card": {
            "last4": clean_last4,
            "status": "Active",
        },
        "members": {},
        "transactions": [],
        "settlement": None,
        "next_transaction_id": 1,
        "processed_keys": set(),
        "revenue_config": {
            "interchange_share_rate": rate(interchange_share_rate),
            "default_fx_spread_rate": rate(default_fx_spread_rate),
        },
    }


def update_pot_settings(
    pot: dict[str, Any],
    name: str,
    description: str,
    closing_date: str,
    auto_return: bool,
    spending_limit: int | float | str | Decimal | None,
) -> None:
    """Update the editable pot settings shown in the Figma prototype."""

    if pot["status"] != "Open":
        raise ValueError("Closed pots cannot be edited.")

    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Pot name cannot be empty.")

    parsed_limit = None
    if spending_limit not in (None, "", 0, 0.0, "0", "0.00"):
        parsed_limit = money(spending_limit)
        if parsed_limit <= 0:
            raise ValueError("Spending limit must be greater than zero.")

    pot["name"] = clean_name
    pot["description"] = description.strip()
    pot["closing_date"] = closing_date
    pot["auto_return"] = bool(auto_return)
    pot["spending_limit"] = parsed_limit

    _add_activity(
        pot,
        transaction_type="settings_updated",
        description=f"{clean_name} settings were updated",
    )


def set_card_frozen(pot: dict[str, Any], frozen: bool) -> None:
    """Freeze or unfreeze the simulated pot-linked virtual card."""

    if pot["status"] != "Open":
        raise ValueError("The card cannot be changed after the pot closes.")

    pot["card"]["status"] = "Frozen" if frozen else "Active"

    _add_activity(
        pot,
        transaction_type="card_status_changed",
        description=(
            "Pot card was frozen"
            if frozen
            else "Pot card was unfrozen"
        ),
    )


def _next_transaction_id(pot: dict[str, Any]) -> int:
    """Return the next transaction ID and update the counter."""

    transaction_id = pot["next_transaction_id"]
    pot["next_transaction_id"] += 1
    return transaction_id


def _check_idempotency(
    pot: dict[str, Any],
    idempotency_key: str | None,
) -> None:
    """Reject a duplicated action when the same key has already been processed."""

    if (
        idempotency_key is not None
        and idempotency_key in pot["processed_keys"]
    ):
        raise ValueError("Duplicate transaction rejected.")


def _remember_idempotency_key(
    pot: dict[str, Any],
    idempotency_key: str | None,
) -> None:
    """Store a processed idempotency key."""

    if idempotency_key is not None:
        pot["processed_keys"].add(idempotency_key)


def _add_activity(
    pot: dict[str, Any],
    transaction_type: str,
    description: str,
    **extra_fields: Any,
) -> int:
    """Add one activity record to the pot ledger."""

    transaction_id = _next_transaction_id(pot)

    transaction = {
        "transaction_id": transaction_id,
        "type": transaction_type,
        "description": description,
        "date_time": datetime.now().strftime("%d %b %Y, %I:%M %p"),
        **extra_fields,
    }

    pot["transactions"].append(transaction)
    return transaction_id


def add_member(
    pot: dict[str, Any],
    member_name: str,
    role: str = "Member",
) -> None:
    """Add a new member to the pot."""

    if pot["status"] != "Open":
        raise ValueError("Cannot add members to a closed pot.")

    clean_name = member_name.strip()

    if not clean_name:
        raise ValueError("Member name cannot be empty.")

    if clean_name in pot["members"]:
        raise ValueError(f"{clean_name} is already in the pot.")

    if role not in {"Admin", "Member"}:
        raise ValueError("Role must be Admin or Member.")

    pot["members"][clean_name] = {
        "role": role,
        "active": True,
        "total_contributed": money(0),
    }

    _add_activity(
        pot,
        transaction_type="member_joined",
        member=clean_name,
        description=f"{clean_name} joined the pot",
    )


def transfer_admin(
    pot: dict[str, Any],
    current_admin: str,
    new_admin: str,
) -> None:
    """Transfer the admin role to another active member."""

    if pot["status"] != "Open":
        raise ValueError("Cannot transfer admin in a closed pot.")

    if current_admin not in pot["members"]:
        raise ValueError("Current admin is not a member of this pot.")

    if new_admin not in pot["members"]:
        raise ValueError("New admin is not a member of this pot.")

    if pot["members"][current_admin]["role"] != "Admin":
        raise ValueError("Only the current admin can transfer the role.")

    if not pot["members"][new_admin]["active"]:
        raise ValueError("The new admin must be an active member.")

    if current_admin == new_admin:
        raise ValueError("The new admin must be a different member.")

    pot["members"][current_admin]["role"] = "Member"
    pot["members"][new_admin]["role"] = "Admin"

    _add_activity(
        pot,
        transaction_type="admin_transferred",
        member=new_admin,
        description=(
            f"{current_admin} transferred the admin role to {new_admin}"
        ),
    )


def leave_member(pot: dict[str, Any], member_name: str) -> None:
    """
    Deactivate a member while keeping their contribution and refund entitlement.
    """

    if pot["status"] != "Open":
        raise ValueError("Cannot leave a closed pot.")

    if member_name not in pot["members"]:
        raise ValueError(f"{member_name} is not a member of this pot.")

    member = pot["members"][member_name]

    if not member["active"]:
        raise ValueError(f"{member_name} has already left the pot.")

    if member["role"] == "Admin":
        raise ValueError(
            "The admin must transfer the admin role before leaving."
        )

    member["active"] = False

    _add_activity(
        pot,
        transaction_type="member_left",
        member=member_name,
        description=f"{member_name} left the pot",
    )


def add_contribution(
    pot: dict[str, Any],
    member_name: str,
    amount: int | float | str | Decimal,
    idempotency_key: str | None = None,
) -> int:
    """Add a member's contribution to the pot."""

    if pot["status"] != "Open":
        raise ValueError("Cannot add money to a closed pot.")

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
        transaction_type="contribution",
        member=member_name,
        amount=contribution,
        description=f"{member_name} contributed ${contribution:,.2f}",
    )

    _remember_idempotency_key(pot, idempotency_key)
    return transaction_id


def calculate_total_contributed(pot: dict[str, Any]) -> Decimal:
    """Calculate the total amount contributed by all members."""

    total = sum(
        (
            member_details["total_contributed"]
            for member_details in pot["members"].values()
        ),
        Decimal("0.00"),
    )

    return money(total)


def calculate_total_spent(pot: dict[str, Any]) -> Decimal:
    """Calculate the total amount spent from the pot."""

    total = sum(
        (
            transaction["final_amount"]
            for transaction in pot["transactions"]
            if transaction["type"] == "expense"
        ),
        Decimal("0.00"),
    )

    return money(total)


def calculate_total_discount(pot: dict[str, Any]) -> Decimal:
    """Calculate total customer discounts saved."""

    total = sum(
        (
            transaction["discount"]
            for transaction in pot["transactions"]
            if transaction["type"] == "expense"
        ),
        Decimal("0.00"),
    )

    return money(total)


def calculate_total_refunded(pot: dict[str, Any]) -> Decimal:
    """Calculate the total amount distributed through settlement refunds."""

    total = sum(
        (
            transaction["amount"]
            for transaction in pot["transactions"]
            if transaction["type"] == "refund"
        ),
        Decimal("0.00"),
    )

    return money(total)


def calculate_balance(pot: dict[str, Any]) -> Decimal:
    """Calculate the current available balance after spending and refunds."""

    return money(
        calculate_total_contributed(pot)
        - calculate_total_spent(pot)
        - calculate_total_refunded(pot)
    )


# ---------------------------------------------------------------------
# Revenue simulation functions
# These are scenario calculations, not claims about legal entitlement.
# ---------------------------------------------------------------------

def calculate_interchange_revenue(
    transaction_value: int | float | str | Decimal,
    revenue_share_rate: int | float | str | Decimal,
) -> Decimal:
    """Estimate PoolPay's interchange revenue share."""

    value = money(transaction_value)
    share_rate = rate(revenue_share_rate)

    if value < 0:
        raise ValueError("Transaction value cannot be negative.")

    if share_rate < 0:
        raise ValueError("Interchange rate cannot be negative.")

    return money(value * share_rate)


def calculate_fx_revenue(
    overseas_spend: int | float | str | Decimal,
    fx_spread_rate: int | float | str | Decimal,
) -> Decimal:
    """Estimate revenue from an overseas-spend FX spread."""

    value = money(overseas_spend)
    spread_rate = rate(fx_spread_rate)

    if value < 0:
        raise ValueError("Overseas spend cannot be negative.")

    if spread_rate < 0:
        raise ValueError("FX spread rate cannot be negative.")

    return money(value * spread_rate)


def calculate_marketplace_commission(
    booking_value: int | float | str | Decimal,
    commission_rate: int | float | str | Decimal,
) -> Decimal:
    """Estimate commission from a marketplace booking."""

    value = money(booking_value)
    take_rate = rate(commission_rate)

    if value < 0:
        raise ValueError("Booking value cannot be negative.")

    if take_rate < 0:
        raise ValueError("Commission rate cannot be negative.")

    return money(value * take_rate)


def calculate_float_income(
    average_safeguarded_balance: int | float | str | Decimal,
    annual_yield_rate: int | float | str | Decimal,
    days_held: int,
) -> Decimal:
    """
    Estimate potential float income.

    This is only a financial scenario. Real implementation would depend on
    the licensed partner, safeguarding structure, contracts, and regulation.
    """

    balance = money(average_safeguarded_balance)
    annual_rate = rate(annual_yield_rate)

    if balance < 0:
        raise ValueError("Average balance cannot be negative.")

    if annual_rate < 0:
        raise ValueError("Annual yield rate cannot be negative.")

    if days_held < 0:
        raise ValueError("Days held cannot be negative.")

    return money(balance * annual_rate * Decimal(days_held) / Decimal(365))


def calculate_subscription_revenue(
    premium_users: int,
    monthly_fee: int | float | str | Decimal,
    months: int = 1,
) -> Decimal:
    """Estimate premium subscription revenue."""

    fee = money(monthly_fee)

    if premium_users < 0 or months < 0:
        raise ValueError("Users and months cannot be negative.")

    if fee < 0:
        raise ValueError("Monthly fee cannot be negative.")

    return money(Decimal(premium_users) * fee * Decimal(months))


def calculate_embedded_finance_revenue(
    partner_count: int,
    monthly_platform_fee: int | float | str | Decimal,
    processed_value: int | float | str | Decimal,
    transaction_fee_rate: int | float | str | Decimal,
    months: int = 1,
) -> Decimal:
    """Estimate B2B platform and transaction revenue."""

    platform_fee = money(monthly_platform_fee)
    volume = money(processed_value)
    fee_rate = rate(transaction_fee_rate)

    if partner_count < 0 or months < 0:
        raise ValueError("Partners and months cannot be negative.")

    if platform_fee < 0 or volume < 0 or fee_rate < 0:
        raise ValueError("Revenue assumptions cannot be negative.")

    fixed_revenue = Decimal(partner_count) * platform_fee * Decimal(months)
    variable_revenue = volume * fee_rate

    return money(fixed_revenue + variable_revenue)


def record_expense(
    pot: dict[str, Any],
    member_name: str,
    merchant: str,
    original_amount: int | float | str | Decimal,
    discount: int | float | str | Decimal = 0,
    category: str = "Other",
    payment_method: str = "PoolPay virtual card",
    overseas: bool = False,
    marketplace_booking: bool = False,
    fx_spread_rate: int | float | str | Decimal | None = None,
    marketplace_commission_rate: int | float | str | Decimal = 0,
    idempotency_key: str | None = None,
) -> int:
    """Record an expense, customer saving, and simulated PoolPay revenue."""

    if pot["status"] != "Open":
        raise ValueError("Cannot record expenses in a closed pot.")

    if pot.get("card", {}).get("status") == "Frozen":
        raise ValueError("Transaction rejected: the pot card is frozen.")

    if member_name not in pot["members"]:
        raise ValueError(f"{member_name} is not a member of this pot.")

    if not pot["members"][member_name]["active"]:
        raise ValueError(f"{member_name} is no longer an active member.")

    _check_idempotency(pot, idempotency_key)

    clean_merchant = merchant.strip()

    if not clean_merchant:
        raise ValueError("Merchant name cannot be empty.")

    original_price = money(original_amount)
    saving = money(discount)

    if original_price <= 0:
        raise ValueError("Original amount must be greater than zero.")

    if saving < 0:
        raise ValueError("Discount cannot be negative.")

    if saving >= original_price:
        raise ValueError(
            "Discount must be lower than the original amount."
        )

    final_amount = money(original_price - saving)

    spending_limit = pot.get("spending_limit")
    if spending_limit is not None and final_amount > spending_limit:
        raise ValueError(
            "Transaction rejected: the amount exceeds the pot spending limit."
        )

    if final_amount > calculate_balance(pot):
        raise ValueError(
            "Transaction rejected: insufficient pot balance."
        )

    interchange_revenue = calculate_interchange_revenue(
        final_amount,
        pot["revenue_config"]["interchange_share_rate"],
    )

    chosen_fx_rate = (
        pot["revenue_config"]["default_fx_spread_rate"]
        if fx_spread_rate is None
        else rate(fx_spread_rate)
    )

    fx_revenue = (
        calculate_fx_revenue(final_amount, chosen_fx_rate)
        if overseas
        else money(0)
    )

    marketplace_commission = (
        calculate_marketplace_commission(
            final_amount,
            marketplace_commission_rate,
        )
        if marketplace_booking
        else money(0)
    )

    transaction_id = _add_activity(
        pot,
        transaction_type="expense",
        member=member_name,
        merchant=clean_merchant,
        category=category,
        original_amount=original_price,
        discount=saving,
        final_amount=final_amount,
        payment_method=payment_method,
        status="Completed",
        overseas=overseas,
        marketplace_booking=marketplace_booking,
        interchange_revenue=interchange_revenue,
        fx_revenue=fx_revenue,
        marketplace_commission=marketplace_commission,
        description=(
            f"{clean_merchant} · pot card used by {member_name} "
            f"${final_amount:,.2f}"
        ),
    )

    _remember_idempotency_key(pot, idempotency_key)
    return transaction_id


def get_transaction_details(
    pot: dict[str, Any],
    transaction_id: int,
) -> dict[str, Any]:
    """Return the full details of one expense transaction."""

    for transaction in pot["transactions"]:
        if (
            transaction["type"] == "expense"
            and transaction["transaction_id"] == transaction_id
        ):
            return transaction

    raise ValueError(f"Transaction {transaction_id} was not found.")


def calculate_total_interchange_revenue(
    pot: dict[str, Any],
) -> Decimal:
    """Calculate total simulated interchange revenue."""

    return money(
        sum(
            (
                transaction["interchange_revenue"]
                for transaction in pot["transactions"]
                if transaction["type"] == "expense"
            ),
            Decimal("0.00"),
        )
    )


def calculate_total_fx_revenue(pot: dict[str, Any]) -> Decimal:
    """Calculate total simulated FX revenue."""

    return money(
        sum(
            (
                transaction["fx_revenue"]
                for transaction in pot["transactions"]
                if transaction["type"] == "expense"
            ),
            Decimal("0.00"),
        )
    )


def calculate_total_marketplace_commission(
    pot: dict[str, Any],
) -> Decimal:
    """Calculate total simulated marketplace commission."""

    return money(
        sum(
            (
                transaction["marketplace_commission"]
                for transaction in pot["transactions"]
                if transaction["type"] == "expense"
            ),
            Decimal("0.00"),
        )
    )


def calculate_transaction_revenue(pot: dict[str, Any]) -> Decimal:
    """Calculate transaction-related revenue in the current pot."""

    return money(
        calculate_total_interchange_revenue(pot)
        + calculate_total_fx_revenue(pot)
        + calculate_total_marketplace_commission(pot)
    )


def calculate_revenue_summary(
    pot: dict[str, Any],
    average_safeguarded_balance: int | float | str | Decimal = 0,
    annual_float_rate: int | float | str | Decimal = 0,
    days_held: int = 0,
    premium_users: int = 0,
    premium_monthly_fee: int | float | str | Decimal = 0,
    premium_months: int = 1,
    b2b_partner_count: int = 0,
    b2b_monthly_fee: int | float | str | Decimal = 0,
    b2b_processed_value: int | float | str | Decimal = 0,
    b2b_transaction_rate: int | float | str | Decimal = 0,
    b2b_months: int = 1,
) -> dict[str, Decimal]:
    """Return a configurable revenue simulation summary."""

    interchange = calculate_total_interchange_revenue(pot)
    fx = calculate_total_fx_revenue(pot)
    marketplace = calculate_total_marketplace_commission(pot)

    float_income = calculate_float_income(
        average_safeguarded_balance,
        annual_float_rate,
        days_held,
    )

    subscription = calculate_subscription_revenue(
        premium_users,
        premium_monthly_fee,
        premium_months,
    )

    embedded_finance = calculate_embedded_finance_revenue(
        b2b_partner_count,
        b2b_monthly_fee,
        b2b_processed_value,
        b2b_transaction_rate,
        b2b_months,
    )

    total = money(
        interchange
        + fx
        + marketplace
        + float_income
        + subscription
        + embedded_finance
    )

    return {
        "interchange": interchange,
        "fx": fx,
        "marketplace": marketplace,
        "float_income": float_income,
        "subscription": subscription,
        "embedded_finance": embedded_finance,
        "total_revenue": total,
    }


def list_activity(
    pot: dict[str, Any],
    activity_type: str = "all",
) -> None:
    """Display the pot's activity history."""

    valid_filters = {
        "all",
        "members",
        "contributions",
        "spending",
        "refunds",
    }

    if activity_type not in valid_filters:
        raise ValueError(
            "Activity type must be all, members, contributions, "
            "spending, or refunds."
        )

    print(f"\nAll Activity — {pot['name']}")
    print("-" * 60)

    activity_found = False

    for transaction in pot["transactions"]:
        transaction_type = transaction["type"]

        if (
            activity_type == "members"
            and transaction_type not in {
                "member_joined",
                "member_left",
                "admin_transferred",
            }
        ):
            continue

        if (
            activity_type == "contributions"
            and transaction_type != "contribution"
        ):
            continue

        if (
            activity_type == "spending"
            and transaction_type != "expense"
        ):
            continue

        if (
            activity_type == "refunds"
            and transaction_type != "refund"
        ):
            continue

        activity_found = True

        if transaction_type in {
            "member_joined",
            "member_left",
            "admin_transferred",
        }:
            print(f"Member activity: {transaction['description']}")

        elif transaction_type == "contribution":
            print(
                f"{transaction['member']} contributed "
                f"+${transaction['amount']:,.2f}"
            )

        elif transaction_type == "expense":
            print(
                f"{transaction['merchant']} · "
                f"pot card used by {transaction['member']} "
                f"-${transaction['final_amount']:,.2f}"
            )

            if transaction["discount"] > 0:
                print(
                    f"  Customer saving: "
                    f"-${transaction['discount']:,.2f}"
                )

            print(
                f"  Simulated PoolPay revenue: "
                f"${money(
                    transaction['interchange_revenue']
                    + transaction['fx_revenue']
                    + transaction['marketplace_commission']
                ):,.2f}"
            )

        elif transaction_type == "refund":
            print(
                f"{transaction['member']} received "
                f"${transaction['amount']:,.2f}"
            )

        elif transaction_type == "pot_closed":
            print(transaction["description"])

    if not activity_found:
        print("No activity found.")


def calculate_refunds(
    pot: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """
    Calculate proportional refunds.

    Refunds are rounded down first. Remaining cents are assigned to members
    with the largest decimal remainders so refunds exactly match the balance.
    """

    if pot["status"] == "Closed" and pot["settlement"] is not None:
        return pot["settlement"]["refunds"]

    total_contributed = calculate_total_contributed(pot)
    remaining_balance = calculate_balance(pot)

    if total_contributed <= 0:
        raise ValueError("Cannot calculate refunds without contributions.")

    raw_refunds: dict[str, Decimal] = {}

    for member_name, member_details in pot["members"].items():
        contribution = member_details["total_contributed"]

        if contribution > 0:
            raw_refunds[member_name] = (
                remaining_balance
                * contribution
                / total_contributed
            )

    rounded_refunds = {
        member_name: refund.quantize(CENT, rounding=ROUND_DOWN)
        for member_name, refund in raw_refunds.items()
    }

    allocated = sum(rounded_refunds.values(), Decimal("0.00"))
    cents_remaining = int((remaining_balance - allocated) / CENT)

    ranked_members = sorted(
        raw_refunds,
        key=lambda name: raw_refunds[name] - rounded_refunds[name],
        reverse=True,
    )

    for member_name in ranked_members[:cents_remaining]:
        rounded_refunds[member_name] += CENT

    refunds: dict[str, dict[str, Any]] = {}

    for member_name, refund_amount in rounded_refunds.items():
        contribution = pot["members"][member_name]["total_contributed"]
        contribution_share = contribution / total_contributed

        refunds[member_name] = {
            "contribution": money(contribution),
            "contribution_share": contribution_share,
            "refund_amount": money(refund_amount),
        }

    return refunds


def close_pot(
    pot: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Close the pot, record refunds, and reduce the available balance to zero."""

    if pot["status"] != "Open":
        raise ValueError("This pot is already closed.")

    refunds = calculate_refunds(pot)

    total_refunds = money(
        sum(
            (
                refund_details["refund_amount"]
                for refund_details in refunds.values()
            ),
            Decimal("0.00"),
        )
    )

    remaining_balance = calculate_balance(pot)

    if total_refunds != remaining_balance:
        raise ValueError(
            "Settlement error: refunds do not match the remaining balance."
        )

    pot["settlement"] = {
        "remaining_balance": remaining_balance,
        "total_refunds": total_refunds,
        "refunds": refunds,
    }

    for member_name, refund_details in refunds.items():
        _add_activity(
            pot,
            transaction_type="refund",
            member=member_name,
            amount=refund_details["refund_amount"],
            description=(
                f"{member_name} received "
                f"${refund_details['refund_amount']:,.2f}"
            ),
        )

    pot["status"] = "Closed"

    _add_activity(
        pot,
        transaction_type="pot_closed",
        amount=total_refunds,
        description=f"{pot['name']} was closed and settled",
    )

    if calculate_balance(pot) != money(0):
        raise ValueError(
            "Settlement error: closed pot balance did not reduce to zero."
        )

    return refunds


def print_members(pot: dict[str, Any]) -> None:
    """Display members, roles, status, and contributions."""

    print(f"\nMembers — {pot['name']}")
    print("-" * 60)

    for member_name, details in pot["members"].items():
        status = "Active" if details["active"] else "Left"

        print(
            f"{member_name}: "
            f"{details['role']} · {status} · "
            f"${details['total_contributed']:,.2f} contributed"
        )


def print_summary(pot: dict[str, Any]) -> None:
    """Display current pot totals and simulated transaction revenue."""

    print(f"\nPot Summary — {pot['name']}")
    print("-" * 60)
    print(f"Status: {pot['status']}")
    print(
        f"Total contributed: "
        f"${calculate_total_contributed(pot):,.2f}"
    )
    print(
        f"Total spent: "
        f"${calculate_total_spent(pot):,.2f}"
    )
    print(
        f"Total refunded: "
        f"${calculate_total_refunded(pot):,.2f}"
    )
    print(
        f"Available balance: "
        f"${calculate_balance(pot):,.2f}"
    )
    print(
        f"Customer discounts saved: "
        f"${calculate_total_discount(pot):,.2f}"
    )
    print(
        f"Simulated transaction revenue: "
        f"${calculate_transaction_revenue(pot):,.2f}"
    )


def build_demo_pot() -> dict[str, Any]:
    """Build the Bangkok Trip demo used by the terminal and Streamlit."""

    bangkok_trip = create_pot(
        name="Bangkok Trip",
        description="Thailand trip - July 2025",
        closing_date="2025-05-16",
        auto_return=True,
        spending_limit=None,
        virtual_card_last4="6489",
        interchange_share_rate="0.005",
        default_fx_spread_rate="0.005",
    )

    add_member(bangkok_trip, "Nick", role="Admin")
    add_member(bangkok_trip, "Conner")
    add_member(bangkok_trip, "Gianni")
    add_member(bangkok_trip, "Divya")
    add_member(bangkok_trip, "Jiayun")

    add_contribution(
        bangkok_trip,
        "Nick",
        480.00,
        idempotency_key="seed-contribution-nick",
    )
    add_contribution(
        bangkok_trip,
        "Conner",
        600.00,
        idempotency_key="seed-contribution-conner",
    )
    add_contribution(
        bangkok_trip,
        "Gianni",
        350.00,
        idempotency_key="seed-contribution-gianni",
    )
    add_contribution(
        bangkok_trip,
        "Divya",
        500.00,
        idempotency_key="seed-contribution-divya",
    )
    add_contribution(
        bangkok_trip,
        "Jiayun",
        410.50,
        idempotency_key="seed-contribution-jiayun",
    )

    jetstar_transaction_id = record_expense(
        bangkok_trip,
        member_name="Nick",
        merchant="Jetstar",
        original_amount=920.00,
        discount=30.00,
        category="Travel",
        marketplace_booking=False,
        marketplace_commission_rate="0",
        idempotency_key="seed-expense-jetstar",
    )

    record_expense(
        bangkok_trip,
        member_name="Conner",
        merchant="Airbnb",
        original_amount=645.00,
        category="Accommodation",
        marketplace_booking=False,
        marketplace_commission_rate="0",
        idempotency_key="seed-expense-airbnb",
    )

    record_expense(
        bangkok_trip,
        member_name="Gianni",
        merchant="Bangkok Restaurant",
        original_amount=237.00,
        category="Dining",
        overseas=True,
        fx_spread_rate="0.005",
        idempotency_key="seed-expense-restaurant",
    )

    return {
        "pot": bangkok_trip,
        "jetstar_transaction_id": jetstar_transaction_id,
    }


def run_demo() -> None:
    """Run the updated Bangkok Trip terminal demonstration."""

    demo_data = build_demo_pot()
    pot = demo_data["pot"]

    print_members(pot)
    print_summary(pot)
    list_activity(pot)

    revenue_summary = calculate_revenue_summary(
        pot,
        average_safeguarded_balance="1200.00",
        annual_float_rate="0.04",
        days_held=60,
        premium_users=1,
        premium_monthly_fee="5.99",
        premium_months=1,
    )

    print("\nRevenue Simulation")
    print("-" * 60)

    for revenue_name, amount in revenue_summary.items():
        print(
            f"{revenue_name.replace('_', ' ').title()}: "
            f"${amount:,.2f}"
        )

    refund_preview = calculate_refunds(pot)

    print("\nSettlement Preview")
    print("-" * 60)

    for member_name, details in refund_preview.items():
        print(
            f"{member_name}: "
            f"{details['contribution_share']:.1%} share "
            f"→ receives ${details['refund_amount']:,.2f}"
        )

    close_pot(pot)

    print("\nAfter Settlement")
    print("-" * 60)
    print_summary(pot)
    list_activity(pot, activity_type="refunds")


if __name__ == "__main__":
    run_demo()
