# QT_CRM Ecosystem Research and Decisions

Date: 2026-05-21

## What QT_CRM Is Now

QT_CRM is an office data ecosystem, not only a desktop program.

- Desktop app: `qt_crm_app.py`
- Web API: `backend/main.py`
- Web UI: `frontend/index.html`, `frontend/app.js`, `frontend/styles.css`
- Shared database: `real_estate_crm.db`
- Shared core helpers: `crm_core/`
- Desktop auto-close backups: `backups/`
- LAN/Web backups: now also `backups/`

The most important operational rule is simple: Desktop and Web must show the same business truth from the same SQLite database.

## Deep Research Findings

The CRM already has the correct business heart for MBM Enterprises:

- Four Phase 1 sections are the daily work surface: Rent Requirements, Rent Availability, Sale Requirements, Sale Availability.
- Matching must prioritize location first, then budget/rent/demand, rooms, floor, and facilities.
- Staff need speed: add records, see records, search, match, print, import, export.
- Admin/manager need control: users, settings, pending approvals, recycle/restore, backups, audit.
- The full deal journey is intentionally later; Phase 1 is data/search/matching.

The main technical risk is duplicated rules. Fields, roles, settings, table counts, backup folders, and matching logic appear in Desktop, Web backend, and Web frontend. When those drift, the user sees “rubbish pitfall” behavior: one screen shows one truth and another screen shows another.

## Decisions

1. Keep `real_estate_crm.db` as the single source of data truth for now.
2. Keep Desktop and Web UI both active, but make them prove alignment through an ecosystem health check.
3. Keep Phase 1 lists unpaged for office use. Staff should see all active section records, sorted by serial number descending.
4. Keep recycle instead of hard delete for Phase 1 records.
5. Keep admin/manager visibility into ecosystem health; staff focus remains entry/search/matching.
6. Use one backup folder: `backups/`, with a 30-backup retention target.
7. Move shared contracts into `crm_core/` whenever practical, starting with the ecosystem health contract.

## Implemented In This Step

- Added `crm_core/ecosystem.py`
  - Defines Phase 1 table contract.
  - Audits required columns, active/recycled counts, serial ranges, settings, users, approvals, audit logs, database status, and backups.
  - Formats the same health report for Desktop.

- Added Web API route:
  - `GET /api/records/ecosystem/health`
  - Available to Super Admin, Admin, and Manager.

- Added Web Dashboard panel:
  - Shows Phase 1 active entries, recycled entries, pending approvals, backup count, database size, theme setting, table counts, latest backup, and issues.

- Added Desktop Tools menu action:
  - `Tools > Ecosystem Health`
  - Uses the same shared audit helper.

- Aligned Web backup folder with Desktop:
  - Backend backups now go to `backups/`.
  - Backend backup creation now trims the folder to 30 `.db` backups.

## Next Ecosystem Work

- Move Phase 1 field definitions into a shared contract module so Desktop, Web API, and Web UI cannot drift.
- Add a small automated smoke test that compares Web API counts against direct SQLite counts.
- Add a Desktop/Web visual label showing the same database path and last health status.
- Add import validation reports that show skipped rows and exact field errors before saving.
- Add serial-number policy if MBM wants each section to display independent user-facing serials instead of SQLite IDs.
