# PoolPay Prototype

PoolPay is a **pre-funded shared-spending prototype** for planned group expenses. Instead of one person paying first and chasing repayments later, members contribute to a shared pot before spending begins. The prototype demonstrates pot creation, contributions, shared spending, transaction controls and proportional settlement of unused funds.

> **Academic prototype:** This repository supports the FINS5548 Capstone Project Proposal. It uses simulated transactions only. It does **not** process real money, connect to live bank accounts or card networks, or provide production-grade security/KYC/AML.

## Prototype links

- **Interactive Figma customer journey:** [PoolPay Interactive Figma Prototype](https://www.figma.com/proto/pLUCIUEyBaLJxCRiEr3Gcz/%F0%9F%92%B8-Banking-App-Mobile-UI-design--Community-?node-id=1-63682&p=f&t=kcBSW3jqeFMoH2sg-0&scaling=min-zoom&content-scaling=fixed&page-id=1%3A63682&starting-point-node-id=110%3A394)
- **Python/Streamlit prototype:** run locally using the instructions below.

## What is implemented

- Create and configure a shared pot
- Add members and transfer administrator role
- Add contributions and maintain contribution shares
- Record simulated pot-card expenses
- Reject spending above the available balance
- Enforce an optional spending limit and card freeze
- Reject duplicate actions using idempotency keys
- Prevent inactive members from contributing or spending
- Block new activity after pot closure
- Calculate proportional settlement refunds
- Reconcile refunds so the final pot balance reaches zero

## Bangkok demo validation

The built-in Bangkok Trip scenario uses the same figures shown in the report and Figma prototype:

| Measure | Amount |
|---|---:|
| Total funded | A$2,340.50 |
| Total spent | A$1,772.00 |
| Remaining before settlement | A$568.50 |
| Refunds allocated | A$568.50 |
| Final balance after settlement | A$0.00 |

## Repository structure

```text
poolpay-prototype/
├── app.py                    # Streamlit interface
├── poolpay_backend.py        # Core shared-pot and settlement logic
├── requirements.txt          # Python dependencies
├── tests/
│   └── test_backend.py       # Validation tests for key controls
├── .gitignore
└── README.md
```

## Run locally

Python 3.10+ is recommended.

```bash
python -m venv .venv
```

Activate the environment, then install dependencies:

```bash
pip install -r requirements.txt
```

Run the Streamlit demonstration:

```bash
python -m streamlit run app.py
```

## Run validation tests

```bash
pytest -q
```

The tests cover the main controls used as technical validation in the report, including demo-balance reconciliation, duplicate rejection, overspending rejection, inactive-member restrictions and post-closure restrictions.

## Prototype vs production

The current version stores active state in Streamlit session memory and is intended only for demonstration. A production version would require persistent storage, authenticated users, atomic database transactions, secure backend APIs, audit logging, monitoring, reconciliation and integration with licensed payment/card partners. PoolPay would not directly safeguard customer funds in the proposed early-stage model.

## Security note

No API keys, payment credentials or real customer data should be committed to this repository. Secrets should be stored outside source control (for example in environment variables or a managed secrets service) in any future integration.
