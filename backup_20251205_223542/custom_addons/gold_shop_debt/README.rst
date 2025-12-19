=========================
Gold Shop Debt Management
=========================

This module provides specialized debt management features for Gold Shops, focusing on "Special Partners" (Gold Partners) who have frequent buying and selling transactions.

Features
========

*   **Gold Partner Identification**: Mark specific partners as "Gold Partners" to enable specialized debt tracking.
*   **Net Debt Calculation**: Automatically calculates "Net Debt" (Receivable - Payable) for Gold Partners, providing a single view of the financial standing.
*   **Debt Offset Wizard**: A tool to automatically offset Receivable (Customer Debt) and Payable (Vendor Debt) amounts for a partner, simplifying accounting.
*   **Debt Reports**:
    *   **Summary Report**: Shows opening balance, period transactions (debit/credit), and closing balance.
    *   **Detailed Report**: Lists specific transactions (Invoices, Bills, Trade-ins) within a period.

Usage
=====

Configuration
-------------

1.  Go to **Debt Management > Debt Partners**.
2.  Open a Partner record.
3.  Check the **Is Gold Partner** box.
4.  The **Net Debt** field will appear, showing the calculated debt.

Offsetting Debt
---------------

1.  Go to **Debt Management > Debt Offset**.
2.  Select the **Partner**.
3.  The wizard will show:
    *   Total Receivable
    *   Total Payable
    *   Offset Amount (the lower of the two)
4.  Click **Confirm Offset** to create the accounting entries.

Reporting
---------

1.  Go to **Debt Management > Debt Reports**.
2.  Select the **Start Date** and **End Date**.
3.  Select one or more **Partners**.
4.  Click **Print Summary** or **Print Detail** to generate the PDF report.

Technical Details
=================

Dependencies
------------
*   ``base``
*   ``account``
*   ``sale_trade_in``
*   ``stock``

Models
------
*   ``res.partner``: Extended to add ``is_gold_partner`` and ``current_net_debt``.
*   ``gold.debt.offset.wizard``: Transient model for the offset logic.
*   ``gold.debt.report.wizard``: Transient model for report generation.

Author
======
QLV Development Team
