LibreOffice Base conversion helper

What I generated
- `schema.sql` — simplified SQLite schema for the core CRM tables used by the Qt app.
- `sample_brokers.csv` — example data for `broker_contacts` table.
- `import_to_sqlite.py` — Python script to create a SQLite DB from `schema.sql` and import any CSVs found.

Quick start

1) Create the SQLite DB and import sample CSVs:

```bash
python import_to_sqlite.py --db crm_base.db
```

2) Open LibreOffice Base:
- Choose "Connect to an existing database" -> "SQLite".
- Browse to the created `crm_base.db` file and finish the wizard.
- LibreOffice will show the tables (rent_requirements, rent_availability, sale_requirements, sale_availability, broker_contacts, etc.).

3) Create forms and navigation:
- Use the "Forms" designer in Base to create simple forms for `rent_requirements`, `rent_availability`, `sale_requirements`, `sale_availability`, `broker_contacts`, and `properties`.
- For each form: add fields, set required fields, and use ComboBox controls for option lists (e.g., `measurement_unit`, `client_status`).

Automation & macros
- The project UI in `qt_crm_app.py` includes workflows and business logic; for parity you can:
  - Add Basic or Python macros in Base to run simple checks (e.g., normalize phone numbers) when saving a record.
  - Or keep app logic in external Python scripts that operate directly on the SQLite DB (recommended for complex business rules).

Macros included
- `macros/validate_fields.py` — Python UNO macros for basic validation: `validate_phone`, `validate_cnic`, `validate_date`, plus `xs_` wrappers suitable for attaching to form events.

Forms plan
- See `forms_plan.md` for a recommended list of forms, required fields, and event bindings to attach the macros.

How to install and use the macros
1) Copy `libreoffice_base_export/macros/validate_fields.py` into your LibreOffice Python scripts folder (user macros):
  - Linux: `~/.config/libreoffice/4/user/Scripts/python/`
  - Windows: `%APPDATA%\\LibreOffice\\4\\user\\Scripts\\python\\`
2) Or import the module into the `.odb` via Tools → Macros → Organize Macros → Python → Add Module.
3) Test macros at Tools → Macros → Organize Macros → Python → Run.
4) Attach a macro to a control or form event: open the form in edit mode, right-click the control → Control Properties → Events, assign `xs_validate_phone`, `xs_validate_cnic`, or `xs_validate_date` as needed.

Creating the Base `.odb`
- After running `import_to_sqlite.py` and creating `crm_base.db`, open LibreOffice Base and choose "Connect to an existing database" → "SQLite" and point to `crm_base.db`.
- Use the Forms designer to create forms as laid out in `forms_plan.md`. Attach macros to events for validation.

Next steps I can do for you
- Generate LibreOffice Base `.odb` template with pre-built forms and simple macros for the key tables.
- Create Python/UNO macros to validate fields (phone, CNIC) on form submit.
- Create SQL views and saved queries mapping the app's reports for one-click exports.

Tell me which next step you'd like me to do and I will proceed.

Auto-generate forms macro
 - `macros/generate_forms.py` — a best-effort UNO Python macro that attempts to create simple forms for core tables when run inside a connected `.odb` (Tools → Macros → Organize Macros → Python → Run `generate_forms.create_basic_forms`).

How to auto-create forms
1) Open the `crm_base.db` in LibreOffice Base (Connect to existing SQLite DB).
2) Tools → Macros → Organize Macros → Python → Select `generate_forms.create_basic_forms` and Run.
3) The macro will attempt to add simple form documents for common tables; review them in the Forms section and use the Form designer to add/arrange fields.

Notes
- Programmatic form creation via UNO can be fragile across LibreOffice versions; the macro is best-effort. If it fails, follow the manual steps in `forms_plan.md` to build the forms with the designer and attach macros for validation.
