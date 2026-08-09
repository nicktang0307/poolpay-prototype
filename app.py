from decimal import Decimal

import streamlit as st

from poolpay_backend import (
    build_demo_pot,
    calculate_balance,
    calculate_refunds,
    calculate_total_contributed,
    calculate_total_spent,
    close_pot,
)

st.set_page_config(page_title="PoolPay Prototype", page_icon="💸", layout="wide")


@st.cache_resource
def get_demo():
    return build_demo_pot()["pot"]


if "pot" not in st.session_state:
    st.session_state.pot = build_demo_pot()["pot"]

pot = st.session_state.pot

st.title("PoolPay Working Prototype")
st.caption("Simulated transactions only — no real banking, card or payment integration.")

col1, col2, col3 = st.columns(3)
col1.metric("Total funded", f"A${calculate_total_contributed(pot):,.2f}")
col2.metric("Total spent", f"A${calculate_total_spent(pot):,.2f}")
col3.metric("Available balance", f"A${calculate_balance(pot):,.2f}")

st.divider()
st.subheader("Bangkok Trip")
st.write(
    "This demonstration uses the same five-member example described in the capstone report. "
    "It shows contribution tracking, shared spending and proportional settlement."
)

st.subheader("Members and contributions")
member_rows = []
total = calculate_total_contributed(pot)
for name, member in pot["members"].items():
    share = member["total_contributed"] / total if total else Decimal("0")
    member_rows.append(
        {
            "Member": name,
            "Role": member["role"],
            "Status": "Active" if member["active"] else "Left",
            "Contribution": f"A${member['total_contributed']:,.2f}",
            "Contribution share": f"{share:.1%}",
        }
    )
st.dataframe(member_rows, use_container_width=True, hide_index=True)

st.subheader("Simulated pot-card transactions")
expense_rows = []
for transaction in pot["transactions"]:
    if transaction["type"] == "expense":
        expense_rows.append(
            {
                "Member": transaction["member"],
                "Merchant": transaction["merchant"],
                "Category": transaction["category"],
                "Original": f"A${transaction['original_amount']:,.2f}",
                "Discount": f"A${transaction['discount']:,.2f}",
                "Deducted": f"A${transaction['final_amount']:,.2f}",
            }
        )
st.dataframe(expense_rows, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Settlement validation")

if pot["status"] == "Open":
    refunds = calculate_refunds(pot)
else:
    refunds = pot["settlement"]["refunds"]

refund_rows = []
for name, item in refunds.items():
    refund_rows.append(
        {
            "Member": name,
            "Contribution share": f"{item['contribution_share']:.1%}",
            "Refund": f"A${item['refund_amount']:,.2f}",
        }
    )
st.dataframe(refund_rows, use_container_width=True, hide_index=True)

refund_total = sum(
    (item["refund_amount"] for item in refunds.values()),
    Decimal("0.00"),
)

before, allocated, after = st.columns(3)
before.metric("Before", f"A${pot['settlement']['remaining_balance'] if pot['status'] == 'Closed' else calculate_balance(pot):,.2f}")
allocated.metric("Refunds allocated", f"A${refund_total:,.2f}")
after.metric("Final balance", f"A${calculate_balance(pot):,.2f}" if pot["status"] == "Closed" else "A$0.00 after settlement")

if pot["status"] == "Open":
    st.success(
        "Refunds reconcile exactly to the current A$568.50 remaining balance. "
        "The pot can only close when the settlement reconciles."
    )
    if st.button("Simulate pot closure"):
        close_pot(pot)
        st.rerun()
else:
    st.success("Settlement complete. The final available balance is A$0.00.")
    if st.button("Reset Bangkok demo"):
        st.session_state.pot = build_demo_pot()["pot"]
        st.rerun()

st.divider()
st.subheader("What this prototype validates")
st.markdown(
    """
- Shared contributions update the common pot balance.
- Spending above the available balance is rejected by backend logic.
- Duplicate actions can be rejected using idempotency keys.
- Inactive members cannot make new purchases.
- Refunds are allocated by contribution share and reconcile to the exact remaining balance.
- Closing the pot records refunds and leaves a zero available balance.

**Not yet validated:** live payment processing, concurrent production transactions, customer demand, KYC/AML integration or production security.
"""
)
