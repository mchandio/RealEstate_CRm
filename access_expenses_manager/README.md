# Expenses Manager for Microsoft Access

The database is simplified to exactly three business tables:

- `Capital Balance`: `ID`, `Date`, `Description`, `Amount`
- `Expenses`: `ID`, `Date`, `Description`, `Amount`, `Upload Bill`
- `Remaining Balance`: `ID`, `Date`, `VoucherID`, `Remaining Balance`

`Upload Bill` is a real Microsoft Access Attachment field. Use the `Expenses / Bills` form to add expenses and attach bill files.

The database opens to `frmDashboard`, which shows:

- Capital balance
- Total expenses
- Cash in hand
- Voucher count
- Recent expenses
- Running remaining balance

Amount fields are formatted as plain numbers (`#,##0.00`) without a currency symbol.

## Balance Logic

`Capital Balance` stores available cash/capital.

`Expenses` stores vouchers/expense entries.

`Remaining Balance` stores cash in hand after each voucher:

```text
Remaining Balance = Capital Balance - running Expenses
```

The balance rebuilds automatically when capital or expense records are saved/deleted through the forms. The dashboard also refreshes the balance when it opens or when you return to it.

The current seed data preserves the original expense rows and creates one opening capital balance that matches the total expenses, so the running remaining balance starts at `0`.

## Regenerate Command

From the project root:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\access_expenses_manager\Build-ExpensesManagerAccess.ps1
```
