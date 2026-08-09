from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import streamlit as st

from poolpay_backend import (
    add_contribution,
    add_member,
    build_demo_pot,
    calculate_balance,
    calculate_refunds,
    calculate_revenue_summary,
    calculate_total_contributed,
    calculate_total_discount,
    calculate_total_spent,
    close_pot,
    create_pot,
    get_transaction_details,
    leave_member,
    record_expense,
    set_card_frozen,
    transfer_admin,
    update_pot_settings,
)



# Page configuration


st.set_page_config(
    page_title="PoolPay Working Demo",
    page_icon="💸",
    layout="wide",
)



# Helpers


def format_money(amount: Decimal | int | float) -> str:
    """Format an amount as dollars."""
    return f"${amount:,.2f}"


def set_message(message: str, message_type: str = "success") -> None:
    """Store a message so it remains visible after Streamlit reruns."""
    st.session_state.flash_message = message
    st.session_state.flash_type = message_type


def show_message() -> None:
    """Display and remove the saved message."""
    message = st.session_state.pop("flash_message", None)
    message_type = st.session_state.pop("flash_type", "success")

    if not message:
        return

    if message_type == "success":
        st.success(message)
    elif message_type == "warning":
        st.warning(message)
    else:
        st.error(message)


def reset_demo() -> None:
    """Reset the app to the original Bangkok Trip scenario."""
    demo_data = build_demo_pot()
    st.session_state.pot = demo_data["pot"]
    st.session_state.selected_transaction_id = (
        demo_data["jetstar_transaction_id"]
    )
    set_message("Bangkok Trip has been reset.")


def get_active_members(pot: dict[str, Any]) -> list[str]:
    """Return all active member names."""
    return [
        name
        for name, details in pot["members"].items()
        if details["active"]
    ]


def get_expense_transactions(
    pot: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return all expense transactions."""
    return [
        transaction
        for transaction in pot["transactions"]
        if transaction["type"] == "expense"
    ]


def get_current_admin(pot: dict[str, Any]) -> str | None:
    """Return the current active admin."""
    for name, details in pot["members"].items():
        if details["role"] == "Admin" and details["active"]:
            return name
    return None



# Session state


if "pot" not in st.session_state:
    demo_data = build_demo_pot()
    st.session_state.pot = demo_data["pot"]
    st.session_state.selected_transaction_id = (
        demo_data["jetstar_transaction_id"]
    )

pot = st.session_state.pot



# Styling


st.markdown(
    """
    <style>
        .block-container {
            max-width: 1180px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        .poolpay-note {
            padding: 0.9rem 1rem;
            border: 1px solid rgba(200, 155, 44, 0.45);
            border-radius: 0.75rem;
            background: rgba(200, 155, 44, 0.10);
        }

        .revenue-note {
            padding: 0.9rem 1rem;
            border: 1px solid rgba(80, 130, 200, 0.35);
            border-radius: 0.75rem;
            background: rgba(80, 130, 200, 0.08);
        }
    </style>
    """,
    unsafe_allow_html=True,
)



# Header


header_left, header_right = st.columns([5, 1])

with header_left:
    st.title("💸 PoolPay")
    st.subheader(pot["name"])

    status_icon = "🟢" if pot["status"] == "Open" else "🔒"

    st.write(
        f"{status_icon} Status: **{pot['status']}**  |  "
        f"Closing date: **{pot['closing_date']}**"
    )

with header_right:
    st.write("")
    st.write("")

    if st.button("Reset demo", use_container_width=True):
        reset_demo()
        st.rerun()

show_message()



# Summary metrics

metric_1, metric_2, metric_3, metric_4 = st.columns(4)

with metric_1:
    st.metric(
        "Total funded",
        format_money(calculate_total_contributed(pot)),
    )

with metric_2:
    st.metric(
        "Total spent",
        format_money(calculate_total_spent(pot)),
    )

with metric_3:
    st.metric(
        "Available balance",
        format_money(calculate_balance(pot)),
    )

with metric_4:
    st.metric(
        "Customer savings",
        format_money(calculate_total_discount(pot)),
    )

if pot["name"] == "Bangkok Trip":
    prototype_note = (
        "This working prototype uses the same Bangkok Trip data "
        "shown in the PoolPay Figma prototype."
    )
else:
    prototype_note = (
        "This is a newly created prototype pot. Use Reset demo "
        "to return to the original Bangkok Trip scenario."
    )

st.markdown(
    f'<div class="poolpay-note">{prototype_note}</div>',
    unsafe_allow_html=True,
)

st.divider()



# Main tabs

(
    create_tab,
    overview_tab,
    money_tab,
    expense_tab,
    activity_tab,
    members_tab,
    settings_tab,
    card_tab,
    settlement_tab,
    marketplace_tab,
    revenue_tab,
) = st.tabs(
    [
        "Create pot",
        "Overview",
        "Add money",
        "Record expense",
        "Activity",
        "Members",
        "Pot settings",
        "Card details",
        "Settlement",
        "Marketplace · Phase 2",
        "Revenue simulation",
    ]
)



# Create pot


with create_tab:
    st.header("Create a new pot")

    st.info(
        "This prototype supports one active pot at a time. "
        "Creating a new pot replaces the current demo pot, "
        "but you can restore Bangkok Trip with Reset demo."
    )

    with st.form("create_pot_form"):
        new_pot_name = st.text_input(
            "Pot name",
            placeholder="Example: Japan Trip",
        )

        new_description = st.text_input(
            "Description",
            placeholder="Example: Thailand trip - July 2025",
        )

        new_closing_date = st.date_input(
            "Closing date",
            value=date(2025, 5, 16),
        )

        new_auto_return = st.checkbox(
            "Return unused funds when the pot closes",
            value=True,
        )

        new_spending_limit = st.number_input(
            "Spending limit per transaction (0 = no limit)",
            min_value=0.00,
            value=0.00,
            step=50.00,
        )

        new_admin_name = st.text_input(
            "Admin name",
            placeholder="Example: Nick",
        )

        create_pot_submitted = st.form_submit_button(
            "Create pot",
            type="primary",
            use_container_width=True,
        )

    if create_pot_submitted:
        try:
            new_pot = create_pot(
                name=new_pot_name,
                description=new_description,
                closing_date=new_closing_date.isoformat(),
                auto_return=new_auto_return,
                spending_limit=(
                    None
                    if new_spending_limit <= 0
                    else new_spending_limit
                ),
            )

            add_member(
                new_pot,
                member_name=new_admin_name,
                role="Admin",
            )

            st.session_state.pot = new_pot
            st.session_state.pop(
                "selected_transaction_id",
                None,
            )

            set_message(
                f"{new_pot_name.strip()} was created. "
                f"{new_admin_name.strip()} is the admin."
            )
            st.rerun()

        except ValueError as error:
            st.error(str(error))


# --------------------------------------------------# Overview


with overview_tab:
    st.header(f"{pot['name']} overview")

    overview_left, overview_right = st.columns(2)

    with overview_left:
        st.subheader("Pot details")
        st.write(f"**Pot name:** {pot['name']}")
        st.write(
            f"**Description:** {pot.get('description') or 'Not provided'}"
        )
        st.write(f"**Status:** {pot['status']}")
        st.write(f"**Closing date:** {pot['closing_date']}")
        st.write(
            "**Return unused funds:** "
            + ("On" if pot.get("auto_return", True) else "Off")
        )
        spending_limit = pot.get("spending_limit")
        st.write(
            f"**Spending limit:** "
            f"{format_money(spending_limit) if spending_limit else 'No limit'}"
        )
        st.write(
            f"**Pot card:** •••• {pot.get('card', {}).get('last4', '6489')} "
            f"· {pot.get('card', {}).get('status', 'Active')}"
        )
        st.write(f"**Members:** {len(pot['members'])}")
        st.write(
            f"**Active members:** {len(get_active_members(pot))}"
        )

    with overview_right:
        st.subheader("Core backend logic")
        st.write("✅ Contributions update the shared balance")
        st.write("✅ Expenses deduct from the shared balance")
        st.write("✅ Customer discounts reduce final payments")
        st.write("✅ Overspending is blocked")
        st.write("✅ Duplicate transactions can be rejected")
        st.write("✅ Remaining funds settle by contribution share")
        st.write("✅ Closed pots reject new activity")

    st.subheader("Contribution breakdown")

    total_contributed = calculate_total_contributed(pot)

    for member_name, member_details in pot["members"].items():
        contribution = member_details["total_contributed"]
        share = (
            contribution / total_contributed
            if total_contributed > 0
            else Decimal("0")
        )
        status = "Active" if member_details["active"] else "Left"

        row_1, row_2, row_3, row_4 = st.columns([2, 1, 1, 1])

        with row_1:
            st.write(
                f"**{member_name}** · {member_details['role']}"
            )
        with row_2:
            st.write(format_money(contribution))
        with row_3:
            st.write(f"{share:.1%}")
        with row_4:
            st.write(status)



# Add money


with money_tab:
    st.header("Add money")

    if pot["status"] != "Open":
        st.warning("This pot is closed. New contributions are disabled.")
    else:
        active_members = get_active_members(pot)

        with st.form("add_money_form"):
            contribution_member = st.selectbox(
                "Member",
                active_members,
            )

            contribution_amount = st.number_input(
                "Contribution amount",
                min_value=1.00,
                value=100.00,
                step=10.00,
            )

            contribution_reference = st.text_input(
                "Unique reference",
                placeholder="Example: contribution-001",
                help=(
                    "Using the same reference twice demonstrates "
                    "duplicate-transaction protection."
                ),
            )

            add_money_submitted = st.form_submit_button(
                "Add money",
                type="primary",
                use_container_width=True,
            )

        if add_money_submitted:
            try:
                add_contribution(
                    pot,
                    member_name=contribution_member,
                    amount=contribution_amount,
                    idempotency_key=(
                        contribution_reference.strip() or None
                    ),
                )

                set_message(
                    f"{contribution_member} added "
                    f"${contribution_amount:,.2f}."
                )
                st.rerun()

            except ValueError as error:
                st.error(str(error))



# Record expense


with expense_tab:
    st.header("Record expense")

    if pot["status"] != "Open":
        st.warning("This pot is closed. New expenses are disabled.")
    else:
        active_members = get_active_members(pot)

        with st.form("expense_form"):
            expense_member = st.selectbox(
                "Card used by",
                active_members,
            )

            merchant = st.text_input(
                "Merchant",
                placeholder="Example: Jetstar",
            )

            category = st.selectbox(
                "Category",
                [
                    "Travel",
                    "Accommodation",
                    "Dining",
                    "Shopping",
                    "Transport",
                    "Other",
                ],
            )

            amount_column, discount_column = st.columns(2)

            with amount_column:
                original_amount = st.number_input(
                    "Original price",
                    min_value=0.01,
                    value=100.00,
                    step=10.00,
                )

            with discount_column:
                discount = st.number_input(
                    "Customer discount",
                    min_value=0.00,
                    value=0.00,
                    step=5.00,
                )

            overseas = st.checkbox(
                "Overseas transaction",
                value=False,
            )

            marketplace_booking = st.checkbox(
                "Booked through PoolPay marketplace",
                value=False,
            )

            rate_column_1, rate_column_2 = st.columns(2)

            with rate_column_1:
                fx_spread_percent = st.number_input(
                    "FX spread (%)",
                    min_value=0.00,
                    value=0.50,
                    step=0.10,
                    disabled=not overseas,
                )

            with rate_column_2:
                marketplace_rate_percent = st.number_input(
                    "Marketplace commission (%)",
                    min_value=0.00,
                    value=4.00,
                    step=0.50,
                    disabled=not marketplace_booking,
                )

            expense_reference = st.text_input(
                "Unique transaction reference",
                placeholder="Example: expense-001",
            )

            final_amount = original_amount - discount

            if discount > 0 and final_amount > 0:
                st.info(
                    f"Original price: ${original_amount:,.2f}\n\n"
                    f"Customer discount: −${discount:,.2f}\n\n"
                    f"Final payment: ${final_amount:,.2f}"
                )

            expense_submitted = st.form_submit_button(
                "Record expense",
                type="primary",
                use_container_width=True,
            )

        if expense_submitted:
            try:
                transaction_id = record_expense(
                    pot,
                    member_name=expense_member,
                    merchant=merchant,
                    original_amount=original_amount,
                    discount=discount,
                    category=category,
                    overseas=overseas,
                    marketplace_booking=marketplace_booking,
                    fx_spread_rate=(
                        Decimal(str(fx_spread_percent)) / Decimal("100")
                    ),
                    marketplace_commission_rate=(
                        Decimal(str(marketplace_rate_percent))
                        / Decimal("100")
                    ),
                    idempotency_key=(
                        expense_reference.strip() or None
                    ),
                )

                st.session_state.selected_transaction_id = (
                    transaction_id
                )

                set_message(
                    f"{merchant} payment recorded successfully. "
                    f"Transaction ID: {transaction_id}."
                )
                st.rerun()

            except ValueError as error:
                st.error(str(error))



# Activity


with activity_tab:
    st.header("All activity")

    activity_filter = st.radio(
        "Filter",
        [
            "All",
            "Spending",
            "Contributions",
            "Members",
            "Refunds",
        ],
        horizontal=True,
    )

    filtered_transactions = []

    for transaction in reversed(pot["transactions"]):
        transaction_type = transaction["type"]

        if (
            activity_filter == "Spending"
            and transaction_type != "expense"
        ):
            continue

        if (
            activity_filter == "Contributions"
            and transaction_type != "contribution"
        ):
            continue

        if (
            activity_filter == "Members"
            and transaction_type not in {
                "member_joined",
                "member_left",
                "admin_transferred",
            }
        ):
            continue

        if (
            activity_filter == "Refunds"
            and transaction_type != "refund"
        ):
            continue

        filtered_transactions.append(transaction)

    if not filtered_transactions:
        st.info("No activity found.")
    else:
        for transaction in filtered_transactions:
            transaction_type = transaction["type"]
            left, right = st.columns([5, 1])

            with left:
                if transaction_type == "expense":
                    st.markdown(f"**{transaction['merchant']}**")

                    subtitle = (
                        f"Pot card used by {transaction['member']} · "
                        f"{transaction['category']} · "
                        f"{transaction['date_time']}"
                    )

                    if transaction["discount"] > 0:
                        subtitle += (
                            f" · Saved "
                            f"{format_money(transaction['discount'])}"
                        )

                    st.caption(subtitle)

                elif transaction_type == "contribution":
                    st.markdown(
                        f"**{transaction['member']} contributed**"
                    )
                    st.caption(transaction["date_time"])

                elif transaction_type in {
                    "member_joined",
                    "member_left",
                    "admin_transferred",
                }:
                    st.markdown(f"**{transaction['description']}**")
                    st.caption(transaction["date_time"])

                elif transaction_type == "refund":
                    st.markdown(
                        f"**{transaction['member']} received a refund**"
                    )
                    st.caption(transaction["date_time"])

                elif transaction_type == "pot_closed":
                    st.markdown(f"**{transaction['description']}**")
                    st.caption(transaction["date_time"])

            with right:
                if transaction_type == "expense":
                    st.write(
                        f"**−{format_money(transaction['final_amount'])}**"
                    )

                    if st.button(
                        "Details",
                        key=f"details_{transaction['transaction_id']}",
                    ):
                        st.session_state.selected_transaction_id = (
                            transaction["transaction_id"]
                        )
                        st.rerun()

                elif transaction_type == "contribution":
                    st.write(
                        f"**+{format_money(transaction['amount'])}**"
                    )

                elif transaction_type == "refund":
                    st.write(
                        f"**−{format_money(transaction['amount'])}**"
                    )

            st.divider()

    st.subheader("Transaction details")

    expense_transactions = get_expense_transactions(pot)

    if not expense_transactions:
        st.info("No expense transactions are available.")
    else:
        expense_options = {
            (
                f"#{transaction['transaction_id']} · "
                f"{transaction['merchant']} · "
                f"{format_money(transaction['final_amount'])}"
            ): transaction["transaction_id"]
            for transaction in expense_transactions
        }

        option_labels = list(expense_options.keys())

        current_id = st.session_state.get(
            "selected_transaction_id",
            expense_transactions[0]["transaction_id"],
        )

        default_index = 0

        for index, label in enumerate(option_labels):
            if expense_options[label] == current_id:
                default_index = index
                break

        selected_label = st.selectbox(
            "Select transaction",
            option_labels,
            index=default_index,
        )

        selected_transaction_id = expense_options[selected_label]
        st.session_state.selected_transaction_id = (
            selected_transaction_id
        )

        transaction = get_transaction_details(
            pot,
            selected_transaction_id,
        )

        detail_left, detail_right = st.columns(2)

        with detail_left:
            st.write(f"**Merchant:** {transaction['merchant']}")
            st.write(f"**Card used by:** {transaction['member']}")
            st.write(f"**Category:** {transaction['category']}")
            st.write(f"**Status:** {transaction['status']}")
            st.write(
                f"**Date and time:** {transaction['date_time']}"
            )

        with detail_right:
            st.write(
                f"**Original price:** "
                f"{format_money(transaction['original_amount'])}"
            )
            st.write(
                f"**Customer discount:** "
                f"−{format_money(transaction['discount'])}"
            )
            st.write(
                f"**Final payment:** "
                f"{format_money(transaction['final_amount'])}"
            )
            st.write(
                f"**Interchange revenue:** "
                f"{format_money(transaction['interchange_revenue'])}"
            )
            st.write(
                f"**FX revenue:** "
                f"{format_money(transaction['fx_revenue'])}"
            )
            st.write(
                f"**Marketplace commission:** "
                f"{format_money(transaction['marketplace_commission'])}"
            )

        if st.button(
            "Report an issue",
            key=f"report_issue_{selected_transaction_id}",
        ):
            set_message(
                "Issue report recorded for prototype demonstration.",
                "warning",
            )
            st.rerun()



# Member management


with members_tab:
    st.header("Member management")

    st.caption(
        "Role and admin-transfer logic are simulated in this prototype. "
        "A production version would enforce these permissions through "
        "authenticated user accounts."
    )

    for member_name, member_details in pot["members"].items():
        status = "Active" if member_details["active"] else "Left"

        member_1, member_2, member_3, member_4 = st.columns(
            [2, 1, 1, 1]
        )

        with member_1:
            st.write(
                f"**{member_name}** · {member_details['role']}"
            )
        with member_2:
            st.write(status)
        with member_3:
            st.write(
                format_money(member_details["total_contributed"])
            )
        with member_4:
            if (
                pot["status"] == "Open"
                and member_details["active"]
                and member_details["role"] != "Admin"
            ):
                if st.button(
                    "Leave",
                    key=f"leave_{member_name}",
                ):
                    try:
                        leave_member(pot, member_name)
                        set_message(f"{member_name} left the pot.")
                        st.rerun()
                    except ValueError as error:
                        st.error(str(error))

        st.divider()

    st.subheader("Invite a new member")

    if pot["status"] != "Open":
        st.warning("This pot is closed. New members cannot be invited.")
    else:
        with st.form("invite_member_form"):
            new_member_name = st.text_input(
                "Member name",
                placeholder="Example: Sarah",
            )

            invite_submitted = st.form_submit_button(
                "Add member",
                type="primary",
                use_container_width=True,
            )

        if invite_submitted:
            try:
                add_member(
                    pot,
                    member_name=new_member_name,
                    role="Member",
                )

                set_message(
                    f"{new_member_name} joined {pot['name']}."
                )
                st.rerun()

            except ValueError as error:
                st.error(str(error))

    st.subheader("Transfer admin")

    current_admin = get_current_admin(pot)
    eligible_admins = [
        name
        for name in get_active_members(pot)
        if name != current_admin
    ]

    if pot["status"] != "Open":
        st.warning("Admin transfer is disabled after the pot closes.")
    elif current_admin is None:
        st.error("No active admin was found.")
    elif not eligible_admins:
        st.info("No other active member can become admin.")
    else:
        with st.form("transfer_admin_form"):
            st.write(f"Current admin: **{current_admin}**")

            new_admin = st.selectbox(
                "New admin",
                eligible_admins,
            )

            transfer_submitted = st.form_submit_button(
                "Transfer admin role",
                use_container_width=True,
            )

        if transfer_submitted:
            try:
                transfer_admin(
                    pot,
                    current_admin=current_admin,
                    new_admin=new_admin,
                )

                set_message(
                    f"Admin role transferred from "
                    f"{current_admin} to {new_admin}."
                )
                st.rerun()

            except ValueError as error:
                st.error(str(error))



# Pot settings

with settings_tab:
    st.header("Pot settings")

    if pot["status"] != "Open":
        st.warning("This pot is closed. Settings can no longer be changed.")
    else:
        with st.form("pot_settings_form"):
            settings_name = st.text_input(
                "Pot name",
                value=pot["name"],
            )

            settings_description = st.text_input(
                "Description",
                value=pot.get("description", ""),
            )

            settings_closing_date = st.date_input(
                "Closing date",
                value=date.fromisoformat(pot["closing_date"]),
            )

            settings_auto_return = st.checkbox(
                "Return unused funds when the pot closes",
                value=pot.get("auto_return", True),
            )

            current_limit = pot.get("spending_limit")
            settings_spending_limit = st.number_input(
                "Spending limit per transaction (0 = no limit)",
                min_value=0.00,
                value=(
                    float(current_limit)
                    if current_limit is not None
                    else 0.00
                ),
                step=50.00,
            )

            settings_submitted = st.form_submit_button(
                "Save settings",
                type="primary",
                use_container_width=True,
            )

        if settings_submitted:
            try:
                update_pot_settings(
                    pot,
                    name=settings_name,
                    description=settings_description,
                    closing_date=settings_closing_date.isoformat(),
                    auto_return=settings_auto_return,
                    spending_limit=(
                        None
                        if settings_spending_limit <= 0
                        else settings_spending_limit
                    ),
                )
                set_message("Pot settings were updated.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))

    st.divider()
    st.subheader("Close and settle pot")
    st.write(
        "Review each member's refund in the Settlement tab before "
        "closing the pot. Closing blocks new contributions and spending."
    )


# --------------------------------------------------
# Card details
# --------------------------------------------------

with card_tab:
    st.header("Card details")

    card = pot.get("card", {"last4": "6489", "status": "Active"})
    st.write(f"**PoolPay virtual card:** •••• {card['last4']}")
    st.write(f"**Linked pot:** {pot['name']}")
    st.write(f"**Card status:** {card['status']}")
    st.caption(
        "This is a simulated pot-linked card. A production card would "
        "be issued through a licensed payment partner."
    )

    if pot["status"] != "Open":
        st.warning("The pot is closed, so the card is no longer active.")
    elif card["status"] == "Active":
        if st.button(
            "Freeze pot card",
            use_container_width=True,
        ):
            try:
                set_card_frozen(pot, True)
                set_message("The pot card was frozen.", "warning")
                st.rerun()
            except ValueError as error:
                st.error(str(error))
    else:
        if st.button(
            "Unfreeze pot card",
            use_container_width=True,
        ):
            try:
                set_card_frozen(pot, False)
                set_message("The pot card is active again.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))


# --------------------------------------------------
# Settlement
# --------------------------------------------------

with settlement_tab:
    st.header("Refund preview by contribution share")

    if calculate_total_contributed(pot) <= 0:
        st.warning("Settlement requires at least one contribution.")

    elif pot["status"] == "Open":
        refund_preview = calculate_refunds(pot)

        st.subheader("Settlement preview")

        st.write(
            "The remaining balance will be returned according "
            "to each member's contribution share."
        )

        for member_name, details in refund_preview.items():
            refund_1, refund_2, refund_3 = st.columns([2, 1, 1])

            with refund_1:
                status = (
                    "Active"
                    if pot["members"][member_name]["active"]
                    else "Left"
                )
                st.write(f"**{member_name}** · {status}")

            with refund_2:
                st.write(f"{details['contribution_share']:.1%}")

            with refund_3:
                st.write(
                    f"**{format_money(details['refund_amount'])}**"
                )

        st.divider()

        st.write(
            f"**Remaining balance:** "
            f"{format_money(calculate_balance(pot))}"
        )

        confirm_close = st.checkbox(
            "I understand that closing the pot blocks "
            "new contributions and expenses."
        )

        if st.button(
            "Close pot and settle",
            type="primary",
            use_container_width=True,
            disabled=not confirm_close,
        ):
            try:
                close_pot(pot)
                set_message(
                    f"{pot['name']} was closed and settled."
                )
                st.rerun()

            except ValueError as error:
                st.error(str(error))

    else:
        st.success(f"{pot['name']} has been closed successfully.")

        settlement = pot["settlement"]
        refunds = settlement["refunds"]

        settlement_metric_1, settlement_metric_2 = st.columns(2)

        with settlement_metric_1:
            st.metric(
                "Distributed balance",
                format_money(settlement["remaining_balance"]),
            )

        with settlement_metric_2:
            st.metric(
                "Available balance after settlement",
                format_money(calculate_balance(pot)),
            )

        for member_name, details in refunds.items():
            settlement_1, settlement_2, settlement_3 = st.columns(
                [2, 1, 1]
            )

            with settlement_1:
                st.write(f"**{member_name}**")

            with settlement_2:
                st.write(f"{details['contribution_share']:.1%}")

            with settlement_3:
                st.write(
                    f"**{format_money(details['refund_amount'])}**"
                )

        st.info(
            "Use Reset demo at the top of the page to reopen "
            "the original Bangkok Trip scenario."
        )


# --------------------------------------------------
# Travel marketplace — Phase 2
# --------------------------------------------------

with marketplace_tab:
    st.header("Travel marketplace")

    st.markdown(
        """
        <div class="revenue-note">
            <strong>Phase 2 / future revenue stream.</strong>
            This is a simulated marketplace journey, not a live Jetstar,
            hotel, affiliate or payment-provider integration. It shows how
            a future customer could search, receive a partner discount and
            pay for a booking from the shared pot.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    st.write(
        "**Future journey:** Search trip → Select offer → "
        "See PoolPay discount → Pay from pot"
    )

    marketplace_offers = {
        "Jetstar group flight": {
            "destination": "Bangkok",
            "merchant": "Jetstar Group Fare",
            "category": "Travel",
            "description": "One-way group flight offer",
            "original_amount": Decimal("520.00"),
            "discount": Decimal("30.00"),
            "commission_rate": Decimal("0.04"),
            "overseas": True,
        },
        "Bangkok Riverside Hotel": {
            "destination": "Bangkok",
            "merchant": "Bangkok Riverside Hotel",
            "category": "Accommodation",
            "description": "Two-night group room package",
            "original_amount": Decimal("420.00"),
            "discount": Decimal("25.00"),
            "commission_rate": Decimal("0.04"),
            "overseas": True,
        },
        "Airport transfer": {
            "destination": "Bangkok",
            "merchant": "Bangkok Airport Transfer",
            "category": "Transport",
            "description": "Private airport transfer for the group",
            "original_amount": Decimal("120.00"),
            "discount": Decimal("10.00"),
            "commission_rate": Decimal("0.04"),
            "overseas": True,
        },
        "Sydney festival package": {
            "destination": "Sydney",
            "merchant": "PoolPay Events Partner",
            "category": "Travel",
            "description": "Illustrative group event package",
            "original_amount": Decimal("280.00"),
            "discount": Decimal("20.00"),
            "commission_rate": Decimal("0.04"),
            "overseas": False,
        },
    }

    search_destination = st.text_input(
        "Search destination",
        value="Bangkok",
        key="marketplace_destination",
    )

    filtered_offers = {
        name: details
        for name, details in marketplace_offers.items()
        if (
            not search_destination.strip()
            or search_destination.strip().lower()
            in details["destination"].lower()
        )
    }

    if not filtered_offers:
        st.info(
            "No illustrative offers match this destination. "
            "Try Bangkok or Sydney."
        )

    elif pot["status"] != "Open":
        st.warning(
            "This pot is closed. Marketplace bookings are disabled."
        )

    elif not get_active_members(pot):
        st.warning(
            "Add an active member before making a marketplace booking."
        )

    else:
        selected_offer_name = st.selectbox(
            "Select travel offer",
            list(filtered_offers.keys()),
        )

        selected_offer = filtered_offers[selected_offer_name]

        offer_left, offer_right = st.columns([2, 1])

        final_booking_amount = (
            selected_offer["original_amount"]
            - selected_offer["discount"]
        )

        estimated_commission = (
            final_booking_amount
            * selected_offer["commission_rate"]
        ).quantize(Decimal("0.01"))

        with offer_left:
            st.subheader(selected_offer_name)
            st.write(selected_offer["description"])
            st.write(
                f"**Destination:** "
                f"{selected_offer['destination']}"
            )
            st.write(
                f"**Original price:** "
                f"{format_money(selected_offer['original_amount'])}"
            )
            st.write(
                f"**PoolPay partner discount:** "
                f"−{format_money(selected_offer['discount'])}"
            )
            st.write(
                f"**Pay from pot:** "
                f"{format_money(final_booking_amount)}"
            )

        with offer_right:
            st.metric(
                "You save",
                format_money(selected_offer["discount"]),
            )
            st.metric(
                "Illustrative commission",
                format_money(estimated_commission),
            )
            st.metric(
                "Current pot balance",
                format_money(calculate_balance(pot)),
            )

        with st.form("marketplace_booking_form"):
            marketplace_payer = st.selectbox(
                "Booked by",
                get_active_members(pot),
            )

            confirm_marketplace = st.checkbox(
                "I understand this is a simulated Phase 2 booking."
            )

            marketplace_submitted = st.form_submit_button(
                "Book using pot balance",
                type="primary",
                use_container_width=True,
                disabled=not confirm_marketplace,
            )

        if marketplace_submitted:
            try:
                transaction_id = record_expense(
                    pot,
                    member_name=marketplace_payer,
                    merchant=selected_offer["merchant"],
                    original_amount=(
                        selected_offer["original_amount"]
                    ),
                    discount=selected_offer["discount"],
                    category=selected_offer["category"],
                    overseas=selected_offer["overseas"],
                    marketplace_booking=True,
                    fx_spread_rate=Decimal("0.005"),
                    marketplace_commission_rate=(
                        selected_offer["commission_rate"]
                    ),
                    idempotency_key=(
                        f"marketplace-"
                        f"{pot['next_transaction_id']}"
                    ),
                )

                st.session_state.selected_transaction_id = (
                    transaction_id
                )

                set_message(
                    f"{selected_offer_name} was booked from "
                    f"{pot['name']} for "
                    f"{format_money(final_booking_amount)}."
                )
                st.rerun()

            except ValueError as error:
                st.error(str(error))

    st.caption(
        "The MVP validates pooling, spending and settlement. "
        "Supplier search, live inventory and direct travel partnerships "
        "remain part of the Phase 2 roadmap."
    )



# Revenue simulation

with revenue_tab:
    st.header("Revenue simulation")

    st.caption(
        "Interchange and FX estimates are tied to simulated payment activity. "
        "Marketplace commission appears only when a simulated Phase 2 "
        "marketplace booking is recorded. Float, subscription and "
        "embedded-finance revenue remain scale-stage assumptions."
    )

    st.markdown(
        """
        <div class="revenue-note">
            These values are scenario estimates for the capstone financial
            model. They do not represent confirmed commercial terms or legal
            entitlement to customer-fund interest.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Current simulated transaction revenue")

    base_summary = calculate_revenue_summary(pot)

    current_1, current_2, current_3, current_4 = st.columns(4)

    with current_1:
        st.metric(
            "Interchange",
            format_money(base_summary["interchange"]),
        )

    with current_2:
        st.metric(
            "FX revenue",
            format_money(base_summary["fx"]),
        )

    with current_3:
        st.metric(
            "Marketplace commission",
            format_money(base_summary["marketplace"]),
        )

    with current_4:
        st.metric(
            "Transaction revenue",
            format_money(
                base_summary["interchange"]
                + base_summary["fx"]
                + base_summary["marketplace"]
            ),
        )

    st.divider()
    st.subheader("Scale-stage assumptions")

    assumption_1, assumption_2 = st.columns(2)

    with assumption_1:
        average_balance = st.number_input(
            "Average safeguarded balance",
            min_value=0.00,
            value=1200.00,
            step=100.00,
        )

        annual_float_percent = st.number_input(
            "Annual float yield (%)",
            min_value=0.00,
            value=4.00,
            step=0.25,
        )

        days_held = st.number_input(
            "Average days held",
            min_value=0,
            value=60,
            step=5,
        )

        premium_users = st.number_input(
            "Premium users",
            min_value=0,
            value=1,
            step=1,
        )

        premium_monthly_fee = st.number_input(
            "Premium monthly fee",
            min_value=0.00,
            value=5.99,
            step=1.00,
        )

    with assumption_2:
        b2b_partner_count = st.number_input(
            "B2B partners",
            min_value=0,
            value=0,
            step=1,
        )

        b2b_monthly_fee = st.number_input(
            "Monthly platform fee per partner",
            min_value=0.00,
            value=500.00,
            step=100.00,
        )

        b2b_processed_value = st.number_input(
            "B2B processed value",
            min_value=0.00,
            value=0.00,
            step=1000.00,
        )

        b2b_transaction_percent = st.number_input(
            "B2B transaction fee (%)",
            min_value=0.00,
            value=0.25,
            step=0.05,
        )

    revenue_summary = calculate_revenue_summary(
        pot,
        average_safeguarded_balance=average_balance,
        annual_float_rate=(
            Decimal(str(annual_float_percent)) / Decimal("100")
        ),
        days_held=int(days_held),
        premium_users=int(premium_users),
        premium_monthly_fee=premium_monthly_fee,
        premium_months=1,
        b2b_partner_count=int(b2b_partner_count),
        b2b_monthly_fee=b2b_monthly_fee,
        b2b_processed_value=b2b_processed_value,
        b2b_transaction_rate=(
            Decimal(str(b2b_transaction_percent))
            / Decimal("100")
        ),
        b2b_months=1,
    )

    st.divider()
    st.subheader("Estimated revenue")

    revenue_1, revenue_2, revenue_3 = st.columns(3)

    with revenue_1:
        st.metric(
            "Float income",
            format_money(revenue_summary["float_income"]),
        )

    with revenue_2:
        st.metric(
            "Subscription revenue",
            format_money(revenue_summary["subscription"]),
        )

    with revenue_3:
        st.metric(
            "Embedded-finance revenue",
            format_money(revenue_summary["embedded_finance"]),
        )

    st.metric(
        "Total estimated revenue",
        format_money(revenue_summary["total_revenue"]),
    )

    st.caption(
        "Float, subscription and embedded-finance values are "
        "future-stage scenarios rather than MVP revenue."
    )
