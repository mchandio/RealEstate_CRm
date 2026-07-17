# 🖥️ UI FLOWS
## Real Estate CRM - Complete User Interface Flow Documentation

---

## 📊 Application Entry Points

### 1. Desktop Application (PySide6)
**Entry Point:** `CRM/main.py`
**Flow:**
```
main() → QApplication → StartupDialog → ensure_database() → CRMServices()
       → LoginDialog → ModernCRMWindow → app.exec()
```

### 2. Web API (FastAPI)
**Entry Point:** `backend/main.py`
**Flow:**
```
lifespan() → init_db() → create admin user → sync_deals()
           → start_backup_scheduler() → yield → shutdown
```

---

## 🗂️ NAVIGATION STRUCTURE

### Main Window Layout
```
┌─────────────────────────────────────────────────────────────┐
│  Menu Bar: File | Edit | View | Dealings | Records |       │
│            Reports | SuccessFactors | Workflow | Tools | Help│
├──────────────┬──────────────────────────────────────────────┤
│              │                                              │
│  Sidebar     │              Content Area                    │
│  (220px)     │              (Stacked Widget)                │
│              │                                              │
│  ┌────────┐  │  ┌────────────────────────────────────────┐  │
│  │ Brand  │  │  │                                        │  │
│  │ Card   │  │  │         Current Page                   │  │
│  ├────────┤  │  │                                        │  │
│  │ User   │  │  │                                        │  │
│  │ Card   │  │  │                                        │  │
│  ├────────┤  │  │                                        │  │
│  │ Nav    │  │  │                                        │  │
│  │ Items  │  │  │                                        │  │
│  │        │  │  │                                        │  │
│  │ QT CRM │  │  └────────────────────────────────────────┘  │
│  │ Desk   │  │                                              │
│  │────────│  ├──────────────────────────────────────────────┤
│  │ Over-  │  │  Status Bar: Page | User | Counts | DB | Web │
│  │ view   │  └──────────────────────────────────────────────┘
│  │ Dash-  │
│  │ board  │
│  │────────│
│  │ Deal   │
│  │ desk   │
│  │────────│
│  │ Records│
│  │────────│
│  │ Opera- │
│  │ tions  │
│  │────────│
│  │ Intelli│
│  │ gence  │
│  │────────│
│  │ Admin  │
│  └────────┘
│              │
└──────────────┴──────────────────────────────────────────────┘
```

---

## 📄 PAGE NAVIGATION

### Navigation Keys & Pages
| Key | Page | Module | Permission |
|-----|------|--------|------------|
| phase1 | QT_CRM Desk | PhaseOneDesk | All users |
| dashboard | Dashboard | DashboardWidget | Non-staff only |
| rent | Rent Dealings | DealModule | rent/rent_view |
| sale | Sale Dealings | DealModule | sale/sale_view |
| properties | Properties | DataTablePage | properties |
| clients | Clients | DataTablePage | clients |
| broker_contacts | Broker Contact List | DataTablePage | clients |
| financials | Financials | FinancialModule | financial/financial_view |
| employees | Employees | EmployeesModule | employees/employees_view |
| successfactors | SuccessFactors | SuccessFactorsModule | successfactors/sf_view |
| workflow | Workflow Engine | WorkflowModule | workflow/wf_view |
| reports | Reports | ReportsModule | reports |
| ai | AI Insights | AIInsightsModule | ai |
| users | Users | UsersModule | Super Admin/Admin |
| settings | Settings | SettingsModule | settings |

---

## 🔄 PAGE FLOW DIAGRAMS

### 1. Login Flow
```
┌─────────────┐
│  Start App  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Show Splash │
│  (StartupDialog)│
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Initialize │
│  Database   │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐
│  Show Login │────►│  Authenticate│
│  Dialog     │     │  (SHA-256)  │
└──────┬──────┘     └──────┬──────┘
       │                   │
       │    ┌──────────────┴──────────────┐
       │    │                             │
       ▼    ▼                             ▼
┌─────────────┐                    ┌─────────────┐
│  Success    │                    │  Failure    │
│  → Main Win │                    │  → Retry    │
└─────────────┘                    └─────────────┘
```

### 2. Deal Lifecycle Flow
```
┌─────────────────────────────────────────────────────────────┐
│                     DEAL LIFECYCLE                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │   Lead   │───►│Contacted │───►│ Meeting  │              │
│  └──────────┘    └──────────┘    └──────────┘              │
│       │                             │                       │
│       │                             ▼                       │
│       │                        ┌──────────┐                │
│       │                        │ Property │                │
│       │                        │  Visit   │                │
│       │                        └──────────┘                │
│       │                             │                       │
│       │                             ▼                       │
│       │                        ┌──────────┐                │
│       │                        │Negotiation│               │
│       │                        └──────────┘                │
│       │                             │                       │
│       │              ┌──────────────┴──────────────┐       │
│       │              │                             │       │
│       │              ▼                             ▼       │
│       │         ┌──────────┐                ┌──────────┐   │
│       │         │  Token   │                │  Lost    │   │
│       │         └──────────┘                └──────────┘   │
│       │              │                                      │
│       │              ▼                                      │
│       │         ┌──────────┐                               │
│       │         │ Booking  │                               │
│       │         └──────────┘                               │
│       │              │                                      │
│       │              ▼                                      │
│       │         ┌──────────┐                               │
│       │         │Installments│                              │
│       │         └──────────┘                               │
│       │              │                                      │
│       │              ▼                                      │
│       │         ┌──────────┐                               │
│       │         │   Deal   │                               │
│       │         │   Done   │                               │
│       │         └──────────┘                               │
│       │              │                                      │
│       │              ▼                                      │
│       │    ┌─────────────────────┐                         │
│       │    │ Archive to          │                         │
│       │    │ rented/sold_props   │                         │
│       │    └─────────────────────┘                         │
│       │                                                    │
└───────┴────────────────────────────────────────────────────┘
```

### 3. Record Management Flow
```
┌─────────────┐
│  List View  │ (DataTablePage)
└──────┬──────┘
       │
       ├─────────────────────────────────────────┐
       │                                         │
       ▼                                         ▼
┌─────────────┐                          ┌─────────────┐
│  Add Record │                          │Edit Record  │
│  (Dialog)   │                          │  (Dialog)   │
└──────┬──────┘                          └──────┬──────┘
       │                                        │
       ▼                                        ▼
┌─────────────┐                          ┌─────────────┐
│  Validate   │                          │  Validate   │
│  Input      │                          │  Input      │
└──────┬──────┘                          └──────┬──────┘
       │                                        │
       ├─────────────────────────────────────────┤
       │                                         │
       ▼                                         ▼
┌─────────────┐                          ┌─────────────┐
│  Insert     │                          │  Update     │
│  Database   │                          │  Database   │
└──────┬──────┘                          └──────┬──────┘
       │                                        │
       └─────────────────────────────────────────┘
                        │
                        ▼
                 ┌─────────────┐
                 │  Refresh    │
                 │  List View  │
                 └─────────────┘
```

### 4. Report Generation Flow
```
┌─────────────┐
│  Select     │
│  Report Type│
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Set Date   │
│  Range      │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Generate   │
│  Report     │
└──────┬──────┘
       │
       ├─────────────────────────────────────────┐
       │                                         │
       ▼                                         ▼
┌─────────────┐                          ┌─────────────┐
│  Preview    │                          │  Export     │
│  (Dialog)   │                          │  PDF/CSV    │
└──────┬──────┘                          └──────┬──────┘
       │                                        │
       ▼                                        ▼
┌─────────────┐                          ┌─────────────┐
│  Print      │                          │  Save File  │
└─────────────┘                          └─────────────┘
```

### 5. Search Flow
```
┌─────────────┐
│  Open Search │ (Ctrl+F)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Search     │
│  Dialog     │
└──────┬──────┘
       │
       ├─────────────────────────────────────────┐
       │                                         │
       ▼                                         ▼
┌─────────────┐                          ┌─────────────┐
│  Enter      │                          │  Select     │
│  Query      │                          │  Category   │
└──────┬──────┘                          └──────┬──────┘
       │                                        │
       └─────────────────────────────────────────┘
                        │
                        ▼
                 ┌─────────────┐
                 │  Execute    │
                 │  Search     │
                 └──────┬──────┘
                        │
                        ▼
                 ┌─────────────┐
                 │  Display    │
                 │  Results    │
                 └──────┬──────┘
                        │
                        ▼
                 ┌─────────────┐
                 │  Double-    │
                 │  Click →    │
                 │  Open Record│
                 └─────────────┘
```

---

## 📱 DIALOG TYPES

### 1. Login Dialog
- Username/Password fields
- Remember me checkbox
- Login/Cancel buttons

### 2. Record Edit Dialog
- Dynamic form based on TableSpec
- Field validation
- Save/Cancel buttons

### 3. Search Dialog
- Search input
- Category filter (All, Rent, Sale, etc.)
- Results table
- Double-click to open

### 4. Report Preview Dialog
- Text/HTML preview
- Print button
- Export PDF/CSV buttons

### 5. Startup Dialog
- Progress bar
- Status messages
- Splash screen

---

## ⌨️ KEYBOARD SHORTCUTS

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New Record |
| Ctrl+S | Save |
| Ctrl+F | Find/Search |
| Ctrl+E | Edit |
| Ctrl+R | Refresh |
| Ctrl+B | Backup |
| Ctrl+L | Logout |
| Ctrl+Q | Exit |
| Ctrl+1-9 | Switch Pages |
| F1 | User Guide |
| F5 | Refresh All |
| F11 | Full Screen |
| Shift+F11 | Exit Full Screen |

---

## 📊 STATUS BAR

**Components:**
1. **Page Label:** Current page name
2. **User Label:** Current user and role
3. **Counts Label:** Rent/Sale requirement/availability counts
4. **DB Label:** Database file size
5. **API Label:** Web server address

---

## 🎨 UI THEMES

**Available Themes:**
- Light (default)
- Dark

**Theme Application:**
- Applied via `app.setStyleSheet()`
- Stored in `app_settings` as `phase1_theme`
- Can be changed in Settings module

---

## 📝 EMPTY STATES

**Handled in:**
- DataTablePage: "No records found" message
- Search: "No results found" message
- Reports: "No data for this period" message

**Loading Indicators:**
- Progress bar during startup
- Status bar messages during operations

---

**Status:** Phase 1 - UI Flows Documented
