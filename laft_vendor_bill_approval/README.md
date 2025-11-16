# Vendor Bill Multi‑stage Approval (Odoo 18)
States: Draft → PM Review → BD Review → Finance Pending → Paid.
Rejection from PM/BD returns to Draft and requires a reason.

## Install
1. Copy the folder `laft_vendor_bill_approval` into your addons path.
2. Update apps list and install the module.
   Or from CLI:
   ```bash
   /odoo/odoo-server/odoo-bin -c /etc/odoo-server.conf -d <DB> -i laft_vendor_bill_approval --stop-after-init
   ```

## Configure
- Assign users to groups:
  - Bills: Projects Manager Reviewer
  - Bills: Business Development Reviewer
  - Bills: Finance Team

## Use
- On vendor bills only (Vendor Bills / Vendor Credit Notes):
  - Click **Send to PM Review** from Draft.
  - PM: **PM Approve** or **PM Reject** (requires reason).
  - BD: **BD Approve** or **BD Reject** (requires reason).
  - Finance: **Mark Paid (Finance)** (optional; auto-sets to Paid when payment_state becomes paid).
