# QT_CRM Research Blueprint

Date: 2026-05-20

This document captures the discovery work for a new robust, easy-to-interact Qt CRM version. It combines the current codebase audit with real estate CRM research, especially brokerage, rental, sale, property management, lead follow-up, documentation, and compliance workflows.

## Current App Baseline

The existing `RealEstate_CRM` project already has a meaningful foundation:

- PySide6 desktop app in `qt_crm_app.py` with dashboard, rent dealings, sale dealings, properties, clients, financials, employees, reports, AI insights, users, settings, local desktop API, and LAN browser server.
- FastAPI backend in `backend/` with auth, role permissions, records CRUD, public lead capture, reports, audit logs, backup scheduler, and SQLite/SQLAlchemy models.
- Core shared logic in `crm_core/` for reports, matching, persistence helpers, and intelligence reports.
- Existing data tables for rent requirements, rent availability, sale requirements, sale availability, clients, properties, income, expenses, employees, attendance, salary payments, users, settings, and audit logs.
- Local business assumptions already visible in the app: PKR currency, Karachi areas, Pakistani mobile validation, CNIC fields, owner/broker options, rental/sale workflows, staff/manager/admin roles, and LAN/offline-friendly deployment.

## Research Signals

Modern real estate CRMs are less about storing contacts and more about making the next action obvious. Strong systems connect lead source, client profile, property inventory, site visits, documents, communication history, commissions, and closing status in one flow.

Pakistan-focused and broker-focused tools emphasize WhatsApp/social lead capture, property listing management, reminders, visit scheduling, broker/channel partner management, commissions, property sharing, and analytics. BrokerFlow positions the problem as scattered WhatsApp chats, missed follow-ups, unorganized property details, and field-work-heavy brokers; its feature set includes lead-property matching, task/visit scheduling, WhatsApp/Telegram capture, co-broker tracking, commissions, and pipeline analytics. Source: https://brokerflow.app/

Pakistani property management tools add a second dimension: unit tracking, owner/tenant portals, rent collection, maintenance, payment proof uploads, financial statements, role-based access, and overdue tracking. DeskEstate specifically highlights properties, units, residents, payments, statements, multi-unit status, police verification documents, rent/security/maintenance payments, invoices, and granular permissions. Source: https://deskestate.com/

Larger Pakistan real estate ERP/CRM products go beyond brokerage into files, installment plans, recovery, allotment, dealer commissions, land procurement, customer portals, document verification, ledgers, payment gateways, and aging reports. Source: https://zameencrm.com/features/

International/U.S. real estate research reinforces the value of agents and repeat/referral relationships: NAR's 2025 profile says 88% of buyers and 91% of sellers used an agent or broker, while first-time buyers fell to 21%. Source: https://www.nar.realtor/blogs/economists-outlook/top-10-takeaways-from-nars-2025-profile-of-home-buyers-and-sellers

If U.S. brokerage/MLS workflows are in scope, the CRM should account for post-2024 NAR practice changes: offers of compensation are prohibited on MLSs, while agents working with buyers must have written buyer agreements before touring homes. Source: https://www.nar.realtor/newsroom/national-association-of-realtors-provides-final-reminder-of-august-17-nar-practice-change-implementation

If MLS/IDX integrations are ever in scope, the data model should not invent incompatible listing fields. RESO identifies the Web API as the common data transport standard for MLS systems and notes that RETS is deprecated. Source: https://www.reso.org/certification/ and https://www.reso.org/reso-web-api/

For Pakistan compliance, FBR treats real estate agents, developers, builders, housing societies, and title-transferring entities as DNFBPs because of high-value property and cash transaction risk. Sources: https://fbr.gov.pk/directorate-general-of-dnfbp/174294/174289 and https://www.fmu.gov.pk/docs/Guidelines_for_Real_Estate_Agents.pdf

The FMU real estate agent guidelines point to CRM requirements that are easy to overlook: customer identification, beneficial owner verification, risk monitoring, STR/CTR decision records, keeping transaction and KYC records for at least five years, internal controls, audit, and employee AML/CFT training. Source: https://www.fmu.gov.pk/docs/Guidelines_for_Real_Estate_Agents.pdf

For marketing, the CRM should store consent and opt-out status, especially for email/SMS/WhatsApp campaigns. U.S. CAN-SPAM guidance requires clear opt-out paths and honoring opt-outs within 10 business days. Source: https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business

If U.S. housing advertising or AI-assisted targeting is in scope, HUD guidance warns that digital targeting for housing ads can create Fair Housing Act risk, including steering, different terms, exclusion, or discriminatory ad delivery. Source: https://www.hud.gov/sites/dfiles/FHEO/documents/FHEO_Guidance_on_Advertising_through_Digital_Platforms.pdf

## Product Direction

Phase 1 confirmed scope:

- QT_CRM should handle only data entry, search, and matching for the first new version.
- Full deal journey features such as negotiation, documents, commission, visit tracking, closing, and deal-done workflows are intentionally deferred to a later stage.
- The first version must therefore be extremely fast for office staff to capture rent/sale/purchase requirements, capture availability/data from owners and brokers, search records instantly, and match client demand against available property data.
- Search priority confirmed by the business owner: staff usually search by client, broker, or owner name first, then narrow by other details such as area, budget, type, size, floor, facilities, and remarks.
- Matching direction confirmed by the business owner: Phase 1 should mainly match client requirements to available properties. Reverse matching from owner/property to waiting clients can be considered later.
- Matching criteria confirmed by the business owner: location, budget/rent/demand, rooms, floor, and facilities all matter.
- Matching weight confirmed by the business owner: location is the most important matching factor.
- Phase 1 must keep four separate sections: Rent Requirement, Rent Availability, Sale Requirement, and Sale Availability.
- Broker/owner/client status should use simple readable choices: Client, Broker, Owner. Avoid shorthand-only labels such as O/B in the new UI.

The new QT_CRM Phase 1 should feel like a calm, fast property data desk:

- One-screen dashboard: due follow-ups, hot leads, visits today, pending approvals, overdue payments, listings needing verification, and monthly income/expense.
- Lead inbox: capture from manual entry, public portal, WhatsApp/social imports, CSV, phone calls, and web forms.
- Contact hub: clients, owners, tenants, buyers, sellers, investors, brokers, channel partners, and family/authorized representatives where needed.
- Property inventory: rent, sale, managed units, photos, documents, location, amenities, verification status, occupancy, owner, broker, price/rent history, and listing quality score.
- Requirements and matching: buyer/tenant needs, budget, area, size, facilities, urgency, family/bachelor, matching suggestions, and shared-property history.
- Deferred later: visit management, negotiation pipeline, document workflow, commissions, closing, agreement tracking, ledger-heavy finance, and advanced compliance workflow.
- Still useful in Phase 1: basic audit, roles, backups, exports, clean data validation, duplicate detection, and record source tracking.

## Suggested New Modules

1. Command Center
   - Daily tasks, follow-ups, visits, approvals, overdue payments, and hot leads.

2. Lead Inbox
   - Source, urgency, assignment, first response time, status, duplicate detection, and conversion path.

3. Contacts
   - Unified profile for client/owner/tenant/buyer/seller/investor/broker with communication history and documents.

4. Properties and Units
   - Separate property master from units/listings where multi-unit buildings, shops, flats, floors, and portions matter.

5. Requirements and Matching
   - Rent Requirement and Sale Requirement records connected to suggested Rent Availability and Sale Availability records. Primary workflow is "select client requirement, show best available property matches."
   - Matching score should consider location, budget/rent/demand fit, rooms, floor, and facility overlap. Location should have the strongest weight.
   - Location matching should support nearby/similar areas, not exact-only matching.
   - Match results should show both a match score and clear reasons, such as same location, rent within budget, matching rooms, matching floor, and number of facilities matched.
   - Staff must be able to print match results through a printer selection dialog each time. Printer output is the first priority for sharing match results.
   - Printed match sheet header should include agency name/logo, client requirement details, date/time, and staff name.

6. Visits and Follow-ups
   - Calendar-like daily work board plus list/table mode for fast office data entry.

7. Deals and Closings
   - Negotiation, token/booking, agreement, handover, commission, final status, and lost reasons.

8. Documents and Verification
   - KYC, ownership, tenancy/sale documents, file attachments, status, expiry/renewal dates, and remarks.

9. Finance and Ledgers
   - Receipts, payments, expenses, salary, commissions, customer/owner ledgers, payment proofs, and PDF exports.

10. Admin, Security, and Audit
    - Users, roles, automatic backups, import/export, audit history, branch/team settings, and data retention.

## Phase 1 Field Schema

Confirmed section fields for the new simplified Phase 1 forms:

### Rent Requirement

- Serial No.
- Date
- Name
- Contact
- Rooms
- Floor
- Location
- Family / Bachelor / Other
- Persons
- Facilities

### Rent Availability

- Serial No.
- Date
- Name
- Contact
- Rooms
- Floor
- Rent
- Advance
- Maintenance
- Location
- Building Name
- Family / Bachelor / Other
- Persons
- Facilities

### Sale Requirement

- Serial No.
- Date
- Name
- Contact
- Rooms
- Floor
- Budget
- Maintenance
- Location
- Required Property
- Family / Bachelor / Other
- Facilities

### Sale Availability

- Serial No.
- Date
- Name
- Contact
- Rooms
- Floor
- Demand
- Maintenance
- Building Name
- Facilities

Field behavior notes:

- Serial No. should be simple numbers generated automatically, visible, and searchable. Each section should have its own serial number sequence starting from 1.
- Date should default to today's date and remain editable.
- Rooms should be a simple typed field.
- Floor should be a select list. Do not include "Any" as an option. Starter options: Basement, Ground, Mezzanine, 1st, 2nd, 3rd, 4th, 5th, 6th, 7th, 8th, 9th, 10th, Top.
- Admin users should be able to edit the Floor options inside QT_CRM settings.
- Family / Bachelor / Other should be a simple select field.
- Facilities should be a multi-select field using these options: Light With Loadshedding, Light 24/7, Gas, Sweet Water, Salty Water, Car Parking, Bike Parking, Lift, CCTV Camera, Watchman.
- Admin users should be able to edit the Facilities options inside QT_CRM settings.
- Money fields should let staff type numbers only and display automatically as PKR with `Rs.` and comma formatting, for example `Rs. 120,000`.
- Keep these forms lean for Phase 1. Extra deal, document, visit, commission, and closing fields belong to later stages.

## Built-in Karachi Area List

Starter location list for Phase 1, with Gizri and nearby consultancy areas first:

- Gizri
- DHA
- DHA Phase 1
- DHA Phase 2
- DHA Phase 4
- DHA Phase 5
- DHA Phase 6
- DHA Phase 7
- DHA Phase 8
- Defence
- Clifton
- Clifton Block 1
- Clifton Block 2
- Clifton Block 3
- Clifton Block 4
- Clifton Block 5
- Clifton Block 6
- Clifton Block 7
- Clifton Block 8
- Clifton Block 9
- Zamzama
- Boat Basin
- Sea View
- Marina
- Khayaban-e-Ittehad
- Khayaban-e-Bukhari
- Khayaban-e-Shahbaz
- Khayaban-e-Hafiz
- Khayaban-e-Rahat
- Khayaban-e-Sehar
- Khayaban-e-Tariq
- Khayaban-e-Muslim
- Khayaban-e-Jami
- Badar Commercial
- Bukhari Commercial
- Tauheed Commercial
- Zamzama Commercial
- Phase 5 Extension
- Phase 6 Commercial
- Qayumabad
- Korangi Road
- Cantt
- Saddar
- PECHS
- Tariq Road
- Bahadurabad
- KDA Scheme
- Gulshan
- Gulistan-e-Johar
- Scheme 33
- North Nazimabad
- Nazimabad
- FB Area
- Hyderi
- Water Pump
- Malir
- Airport

Location field behavior:

- Show built-in suggestions.
- Allow staff to type a custom location if it is not listed.
- Admin users should be able to edit the built-in area list inside QT_CRM settings.
- Nearby/similar matching should understand common proximity around Gizri, DHA, Clifton, Zamzama, Boat Basin, and Sea View.

## Data Model Direction

Keep the current tables where they are useful, but introduce a cleaner core model:

- `contacts`: all people and companies, with contact type tags instead of separate disconnected person fields.
- `properties`: physical property/location master.
- `units`: rentable/saleable portions, shops, flats, floors, rooms, plots, or offices under a property.
- `listings`: active rent/sale availability with price, status, source, owner, broker, and verification.
- `requirements`: tenant/buyer demand records.
- `interactions`: call, WhatsApp, SMS, email, meeting, visit, note, property share.
- `tasks`: next actions, reminders, due dates, assignment, completion.
- `deals`: active transaction pipeline with linked buyer/tenant, owner/seller, listing/unit, commission, and documents.
- `documents`: file metadata, document type, expiry, verification status, related entity.
- `payments`: income/expense/commission/rent/security/maintenance records with proof attachment and ledger links.
- `consents`: channel consent, opt-out, source, timestamp.
- `kyc_checks`: identity, beneficial owner, PEP/sanctions/manual risk status if compliance is in scope.
- `audit_logs`: who changed what and when.

## UX Principles

- Data entry must be fast from keyboard, with defaults, autocomplete, duplicate warnings, and save-and-new flow.
- Search should be people-first: the primary search bar must quickly find client, broker, and owner names, then expose secondary filters for area, budget, property type, size, floor, facilities, and record type.
- Date range filters are not needed in Phase 1 search.
- Search should run only after staff presses a Search button, not live while typing.
- Search should support all four sections and allow results to be sorted/filtered by Rent Requirement, Rent Availability, Sale Requirement, and Sale Availability.
- Search results should be grouped under four headings instead of shown as one mixed list.
- Location should use a built-in Karachi area list with custom typing allowed when a location is not in the list.
- Forms should use clear business labels. For party status, show Client, Broker, and Owner instead of abbreviations.
- The default landing screen should be a four-card launcher with large buttons/cards for Rent Requirement, Rent Availability, Sale Requirement, and Sale Availability.
- Clicking a section card should open the existing records table first, with a clear Add New button.
- Add New and Edit should use full-page forms, not small popup dialogs.
- After saving a new record, the app should stay on a blank form for fast next entry until the user chooses to exit/back.
- If a duplicate Name + Contact is found, the system should show a warning with an "Are you sure?" confirmation instead of blocking the save outright.
- Staff can edit and delete records in Phase 1. Changes should still be traceable through audit history where practical.
- Delete should recycle records instead of permanently removing them. Recycled records should be restorable later.
- Only admin users can restore recycled records.
- Users must log in before doing anything in QT_CRM.
- Phase 1 roles should include Super Admin, Admin, Manager, Staff, and Viewer.
- Viewer role is read-only: can see/search records but cannot add, edit, delete, or restore.
- Manager can manage broadly, but protected actions need admin approval.
- Admin approval should happen inside QT_CRM through a pending approvals workflow.
- Admin approval is required for deleting records, restoring records, editing records, and creating users.
- Staff/manager edits and deletes should be submitted as pending approval. The official record should remain unchanged until an admin approves the change.
- New records added by staff should save immediately and do not need admin approval.
- Every record should visibly show who created it and when it was created.
- Records should also show Last Edited By and Last Edited At after admin-approved edits.
- UI should support both light and dark themes.
- UI language should be English only for Phase 1.
- App header and printed sheets should show both the product name `QT_CRM` and the agency name/logo. Agency name and logo should be stored/configured in settings, not hardcoded.
- The main work view should show what to do next, not just tables.
- Tables stay important for brokerage offices, but every table needs filters, quick actions, and printable/exportable output.
- Every client/property/deal should have a timeline so history is never lost in remarks fields.
- Use role-based visibility so staff can work leads and deals without seeing salary/admin data.
- Make offline/LAN operation first-class if the business uses multiple office PCs.

## Build Phasing

Phase 1: Data, search, and matching desk
- Improved navigation, faster table/filter experience, separate Rent Requirement, Rent Availability, Sale Requirement, and Sale Availability sections, Excel/CSV import, instant global search, duplicate detection, smart matching with explanations, automatic match-result printing, saved filters, export/print, and safer data validation.
- Automatic database backups are required in Phase 1. Backups should run every time the app closes and save to a default local `backups` folder. Keep the latest 30 backups.

Import behavior:

- Excel and CSV import are required for the four core sections.
- QT_CRM should provide downloadable Excel templates for Rent Requirement, Rent Availability, Sale Requirement, and Sale Availability.
- Import should show a preview table before saving rows into QT_CRM.
- When duplicates are found during import, QT_CRM should ask the user what to do instead of skipping or importing automatically.
- Records should also be exportable to Excel/CSV from all four core sections.

Phase 2: Core brokerage workflow
- Lead inbox, contact hub, property/unit/listing model, visit scheduling, deal pipeline, commission tracking.

Phase 3: Documents and finance
- Attachments, verification checklist, receipts/invoices, ledgers, payment aging, salary/commission reporting.

Phase 4: Portal and automation
- Public portal improvements, WhatsApp/social import hooks, property sharing, message templates, consent logs, reminders.

Phase 5: Compliance and enterprise hardening
- KYC/AML workflow if Pakistan scope, U.S. buyer agreement/MLS-safe fields if U.S. scope, advanced audit, backups, multi-branch/team controls.

## Immediate Clarification Needed

Confirmed by the business owner:

- Agency location: Gizri, Karachi.
- Business type: estate agency / consultancy group.
- Core service: provide rent, sale, and purchase data to clients, brokers, and owners.
- Primary market assumption: Karachi/Pakistan brokerage and property data workflows.
- U.S. MLS/NAR workflows should not drive the first version. They remain only optional future ideas if the product is later adapted for U.S. use.

This means the new QT_CRM should prioritize local data capture, fast search, matching, verification, broker/owner/client records, follow-ups, property sharing, commission/expense tracking, and Pakistan/Karachi compliance-friendly records.
