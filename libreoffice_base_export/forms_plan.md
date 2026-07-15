Forms Plan for LibreOffice Base (from `qt_crm_app.py`)

Overview
- Create a Base `.odb` connected to the SQLite DB generated from `schema.sql`.
- Build forms for core workflows: Rent requirements, Rent availability, Sale requirements, Sale availability, Broker contacts, Properties, Clients.
- Use the `macros/validate_fields.py` Python macros for field validation (phone, CNIC, dates).

Form: Rent Requirement (table: `rent_requirements`)
- Fields (required marked *):
  - `client_name` *
  - `client_status` (combo: Client, Broker, Owner)
  - `contact` * (validate_phone)
  - `date` * (validate_date)
  - `property_requires` * (combo: property types)
  - `size` *
  - `measurement` (numeric)
  - `measurement_unit` (combo: Sq Ft, Yards, ...)
  - `floor` (multiselect recommended; Base supports list controls)
  - `location` * (combo/autocomplete list)
  - `budget` (numeric)
  - `facilities` (multi select or text)
  - `remarks` (long text)
- Validation: attach `xs_validate_phone` to `contact` on "Current value modified" or "Before record update"; attach `xs_validate_date` to `date`.

Form: Rent Availability (table: `rent_availability`)
- Fields:
  - `owner_name` *
  - `client_broker` (combo)
  - `contact` * (validate_phone)
  - `owner_phone` (normalize_phone)
  - `date` * (validate_date)
  - `property_availability` * (combo)
  - `monthly_rent` * (numeric)
  - `deposit`, `maintenance_charge` (numeric)
  - `status` (combo: Available, Reserved, Rented, Withdrawn)
  - `facilities`, `location`, `floor`, `size`
- Attach phone and date validations as above.

Form: Sale Requirement / Sale Availability
- Mirror fields from rent forms but use `budget`/`demand` numeric fields and `verification_status` combo where applicable.

Form: Broker Contacts (`broker_contacts`)
- Fields: `name` *, `contact` (validate_phone), `area` (combo), `office_address`, `home_address`, `remarks`.

Form: Properties (`properties`)
- Fields: `title` *, `owner_name`, `owner_phone`, `contact_phone`, `property_type`, `size`, `measurement_unit`, `floor`, `location`, `facilities`, `remarks`.

Form behaviors and attachments
- Use Form → Assign Macro to run validations on `Before record` or on control change.
- Use combo boxes populated from `app_settings` views or static lists (areas, floors, facility options) — create simple lookup tables or use list values in the control's properties.
- For multi-select `floor` or `facilities`, use list boxes with multiple selection when possible, or a comma-separated text field.

Reports and Views
- Create saved queries matching the Report sections in `qt_crm_app.py` (Rent report, Sale report, Financial summary).
- Create a summary form with subforms for quick dashboard metrics (counts of open requirements/availabilities).

Attachment and deployment notes
- Copy `libreoffice_base_export/macros/validate_fields.py` into LibreOffice user macros folder or import into the `.odb`.
- Test macros via Tools → Macros → Organize Macros → Python.
- Attach macros to form events: Right-click form → Edit → Form Properties → Events.

Next: I can generate a sample `.odb` template with the forms and macro pre-attached (requires LibreOffice UNO environment to programmatically create). Tell me to proceed if you'd like an `.odb` file generated next.
