# 🏗️ ARCHITECTURE DIAGRAM
## Real Estate CRM - Complete System Architecture

---

## 📊 HIGH-LEVEL ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           REAL ESTATE CRM SYSTEM                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                         CLIENT LAYER                                    │    │
│  ├─────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                         │    │
│  │  ┌──────────────────────┐          ┌──────────────────────┐            │    │
│  │  │   DESKTOP CLIENT     │          │    WEB CLIENT        │            │    │
│  │  │   (PySide6/Qt6)      │          │   (Browser SPA)      │            │    │
│  │  │                      │          │                      │            │    │
│  │  │  ┌────────────────┐  │          │  ┌────────────────┐  │            │    │
│  │  │  │ ModernCRMWindow│  │          │  │  index.html    │  │            │    │
│  │  │  │    (Main UI)   │  │          │  │  app.js        │  │            │    │
│  │  │  └────────────────┘  │          │  │  styles.css    │  │            │    │
│  │  │          │           │          │  └────────────────┘  │            │    │
│  │  │          ▼           │          │          │           │            │    │
│  │  │  ┌────────────────┐  │          │          ▼           │            │    │
│  │  │  │   Modules      │  │          │  ┌────────────────┐  │            │    │
│  │  │  │   Dialogs      │  │          │  │  HTTP/REST     │  │            │    │
│  │  │  │   Widgets      │  │          │  │  Requests      │  │            │    │
│  │  │  └────────────────┘  │          │  └────────────────┘  │            │    │
│  │  │          │           │          │          │           │            │    │
│  │  └──────────┼───────────┘          └──────────┼───────────┘            │    │
│  │             │                                 │                        │    │
│  └─────────────┼─────────────────────────────────┼────────────────────────┘    │
│                │                                 │                              │
│                ▼                                 ▼                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                         SERVER LAYER                                    │    │
│  ├─────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                         │    │
│  │  ┌──────────────────────┐          ┌──────────────────────┐            │    │
│  │  │   DESKTOP SERVER     │          │    WEB API           │            │    │
│  │  │   (HTTPServer)       │          │   (FastAPI)          │            │    │
│  │  │                      │          │                      │            │    │
│  │  │  ┌────────────────┐  │          │  ┌────────────────┐  │            │    │
│  │  │  │ CRMApiHandler  │  │          │  │    app.py      │  │            │    │
│  │  │  │ (Port 6091)    │  │          │  │  (Port 6090)   │  │            │    │
│  │  │  └────────────────┘  │          │  └────────────────┘  │            │    │
│  │  │          │           │          │          │           │            │    │
│  │  └──────────┼───────────┘          └──────────┼───────────┘            │    │
│  │             │                                 │                        │    │
│  └─────────────┼─────────────────────────────────┼────────────────────────┘    │
│                │                                 │                              │
│                ▼                                 ▼                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                        BUSINESS LOGIC LAYER                             │    │
│  ├─────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                         │    │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │    │
│  │  │                    CRM SERVICES (CRM/services.py)              │   │    │
│  │  │                                                                 │   │    │
│  │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────┐ │   │    │
│  │  │  │  Database   │ │    Auth     │ │  Settings   │ │ Workflow │ │   │    │
│  │  │  │  Operations │ │  Management │ │  Management │ │ Approval │ │   │    │
│  │  │  └─────────────┘ └─────────────┘ └─────────────┘ └──────────┘ │   │    │
│  │  └─────────────────────────────────────────────────────────────────┘   │    │
│  │                                  │                                      │    │
│  │  ┌───────────────────────────────┼──────────────────────────────────┐   │    │
│  │  │                               │                                  │   │    │
│  │  ▼                               ▼                                  │   │    │
│  │  ┌─────────────────────┐ ┌─────────────────────┐ ┌──────────────┐  │   │    │
│  │  │   CRM MODULES       │ │   CRM CORE          │ │  BACKEND     │  │   │    │
│  │  │   (CRM/modules/)    │ │   (crm_core/)       │ │  (backend/)  │  │   │    │
│  │  │                     │ │                     │ │              │  │   │    │
│  │  │  ┌───────────────┐  │ │  ┌───────────────┐  │ │ ┌──────────┐│  │   │    │
│  │  │  │ deals.py      │  │ │  │ reports.py    │  │ │ │ auth.py  ││  │   │    │
│  │  │  │ financial.py  │  │ │  │ matching.py   │  │ │ │ models.py││  │   │    │
│  │  │  │ employees.py  │  │ │  │ intelligence.py│ │ │ │ routers/ ││  │   │    │
│  │  │  │ reports.py    │  │ │  │ db.py         │  │ │ │          ││  │   │    │
│  │  │  │ ai_insights.py│  │ │  │ constants.py  │  │ │ └──────────┘│  │   │    │
│  │  │  │ users.py      │  │ │  └───────────────┘  │ │              │  │   │    │
│  │  │  │ settings.py   │  │ │                     │ └──────────────┘  │   │    │
│  │  │  │ property_sync │  │ └─────────────────────┘                   │   │    │
│  │  │  │ report_helpers│  │                                           │   │    │
│  │  │  └───────────────┘  │                                           │   │    │
│  │  └─────────────────────┘                                           │   │    │
│  │                                  │                                  │   │    │
│  └──────────────────────────────────┼──────────────────────────────────┘   │    │
│                                     │                                      │    │
│                                     ▼                                      │    │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                         DATA LAYER                                      │    │
│  ├─────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                         │    │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │    │
│  │  │                    SQLite Database                               │   │    │
│  │  │                    (real_estate_crm.db)                          │   │    │
│  │  │                                                                 │   │    │
│  │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────┐ │   │    │
│  │  │  │   System    │ │    Deals    │ │    CRM      │ │Financial │ │   │    │
│  │  │  │   Tables    │ │   Tables    │ │   Tables    │ │  Tables  │ │   │    │
│  │  │  │             │ │             │ │             │ │          │ │   │    │
│  │  │  │ users       │ │ rent_req    │ │ properties  │ │ income   │ │   │    │
│  │  │  │ login_logs  │ │ rent_avail  │ │ clients     │ │ expense  │ │   │    │
│  │  │  │ audit_logs  │ │ sale_req    │ │ broker_     │ │          │ │   │    │
│  │  │  │ app_settings│ │ sale_avail  │ │  contacts   │ │          │ │   │    │
│  │  │  │ pending_    │ │ rented_     │ │             │ │          │ │   │    │
│  │  │  │  approvals  │ │  properties │ │             │ │          │ │   │    │
│  │  │  │             │ │ sold_       │ │             │ │          │ │   │    │
│  │  │  │             │ │  properties │ │             │ │          │ │   │    │
│  │  │  └─────────────┘ └─────────────┘ └─────────────┘ └──────────┘ │   │    │
│  │  │                                                                 │   │    │
│  │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐              │   │    │
│  │  │  │     HR      │ │ SuccessFactors│ │  Workflow  │              │   │    │
│  │  │  │   Tables    │ │    Tables    │ │   Tables   │              │   │    │
│  │  │  │             │ │              │ │            │              │   │    │
│  │  │  │ employees   │ │ sf_employees │ │ wf_        │              │   │    │
│  │  │  │ attendance  │ │ sf_positions │ │  workflows │              │   │    │
│  │  │  │ salary_     │ │ sf_goals     │ │ wf_instances│             │   │    │
│  │  │  │  payments   │ │ sf_kpis      │ │ wf_tasks   │              │   │    │
│  │  │  │             │ │ sf_learning  │ │ wf_approvals│             │   │    │
│  │  │  │             │ │ sf_recruiting│ │ wf_audit   │              │   │    │
│  │  │  │             │ │ sf_comp      │ │            │              │   │    │
│  │  │  │             │ │ sf_onboard   │ │            │              │   │    │
│  │  │  └─────────────┘ └─────────────┘ └─────────────┘              │   │    │
│  │  └─────────────────────────────────────────────────────────────────┘   │    │
│  │                                                                         │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 COMPONENT INTERACTION DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        COMPONENT INTERACTIONS                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                    │
│  │  ModernCRM  │      │  CRMServices│      │  SQLite     │                    │
│  │  Window     │◄────►│             │◄────►│  Repository │                    │
│  └──────┬──────┘      └──────┬──────┘      └─────────────┘                    │
│         │                    │                                                  │
│         │                    │                                                  │
│         ▼                    ▼                                                  │
│  ┌─────────────┐      ┌─────────────┐                                         │
│  │   Modules   │      │   Report    │                                         │
│  │   (Feature) │      │   Service   │                                         │
│  └──────┬──────┘      └──────┬──────┘                                         │
│         │                    │                                                  │
│         │                    │                                                  │
│         ▼                    ▼                                                  │
│  ┌─────────────┐      ┌─────────────┐                                         │
│  │   Tables    │      │  Matching   │                                         │
│  │   (UI)      │      │  Engine     │                                         │
│  └─────────────┘      └─────────────┘                                         │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 DATA FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DATA FLOW                                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  USER INPUT                                                                    │
│      │                                                                          │
│      ▼                                                                          │
│  ┌─────────────┐                                                               │
│  │  UI Widget  │ (QLineEdit, QComboBox, etc.)                                  │
│  └──────┬──────┘                                                               │
│         │                                                                       │
│         ▼                                                                       │
│  ┌─────────────┐                                                               │
│  │  Validation │ (Input validation, sanitization)                              │
│  └──────┬──────┘                                                               │
│         │                                                                       │
│         ▼                                                                       │
│  ┌─────────────┐                                                               │
│  │   Module    │ (Business logic processing)                                   │
│  └──────┬──────┘                                                               │
│         │                                                                       │
│         ▼                                                                       │
│  ┌─────────────┐                                                               │
│  │  Services   │ (CRMServices methods)                                         │
│  └──────┬──────┘                                                               │
│         │                                                                       │
│         ▼                                                                       │
│  ┌─────────────┐                                                               │
│  │  Repository │ (SQLiteRepository)                                            │
│  └──────┬──────┘                                                               │
│         │                                                                       │
│         ▼                                                                       │
│  ┌─────────────┐                                                               │
│  │  Database   │ (SQLite queries)                                              │
│  └──────┬──────┘                                                               │
│         │                                                                       │
│         ▼                                                                       │
│  ┌─────────────┐                                                               │
│  │   Result    │ (Query results, rowcount, etc.)                              │
│  └──────┬──────┘                                                               │
│         │                                                                       │
│         ▼                                                                       │
│  ┌─────────────┐                                                               │
│  │  UI Update  │ (Refresh table, show message)                                │
│  └─────────────┘                                                               │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 MODULE DEPENDENCY GRAPH

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        MODULE DEPENDENCIES                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  CRM/app_window.py                                                             │
│       │                                                                         │
│       ├──► CRM/services.py                                                     │
│       │         │                                                               │
│       │         └──► crm_core/db.py                                            │
│       │                   │                                                     │
│       │                   └──► SQLite Database                                  │
│       │                                                                       │
│       ├──► CRM/modules/deals.py                                                │
│       │         │                                                               │
│       │         └──► CRM/services.py                                           │
│       │                                                                       │
│       ├──► CRM/modules/financial.py                                            │
│       │         │                                                               │
│       │         └──► CRM/services.py                                           │
│       │                                                                       │
│       ├──► CRM/modules/employees.py                                            │
│       │         │                                                               │
│       │         └──► CRM/services.py                                           │
│       │                                                                       │
│       ├──► CRM/modules/reports.py                                              │
│       │         │                                                               │
│       │         ├──► CRM/services.py                                           │
│       │         └──► crm_core/reports.py                                       │
│       │                                                                       │
│       ├──► CRM/modules/ai_insights.py                                          │
│       │         │                                                               │
│       │         └──► crm_core/intelligence.py                                  │
│       │                                                                       │
│       ├──► CRM/modules/property_sync.py                                        │
│       │         │                                                               │
│       │         └──► CRM/services.py                                           │
│       │                                                                       │
│       └──► CRM/modules/report_helpers.py                                       │
│                 │                                                               │
│                 └──► CRM/services.py                                           │
│                                                                                 │
│  backend/main.py                                                               │
│       │                                                                         │
│       ├──► backend/routers/auth_router.py                                      │
│       │         │                                                               │
│       │         ├──► backend/auth.py                                           │
│       │         └──► backend/models.py                                         │
│       │                                                                       │
│       ├──► backend/routers/records_router.py                                   │
│       │         │                                                               │
│       │         ├──► backend/models.py                                         │
│       │         └──► crm_core/*                                                │
│       │                                                                       │
│       ├──► backend/routers/reports_router.py                                   │
│       │         │                                                               │
│       │         ├──► backend/models.py                                         │
│       │         └──► crm_core/reports.py                                       │
│       │                                                                       │
│       └──► backend/routers/public_router.py                                    │
│                 │                                                               │
│                 └──► backend/models.py                                         │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 TECHNOLOGY STACK

### Desktop Application
| Layer | Technology | Purpose |
|-------|-----------|---------|
| UI Framework | PySide6 (Qt6) | Cross-platform GUI |
| Language | Python 3.12 | Application logic |
| Database | SQLite | Local data storage |
| PDF Generation | fpdf2 | Report export |
| Data Processing | pandas, numpy | Analytics |
| Machine Learning | scikit-learn | AI insights |

### Web API
| Layer | Technology | Purpose |
|-------|-----------|---------|
| Framework | FastAPI | REST API |
| ORM | SQLAlchemy | Database access |
| Authentication | JWT (python-jose) | Token-based auth |
| Validation | Pydantic | Request validation |
| Server | Uvicorn | ASGI server |

### Shared Components
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Database | SQLite (WAL mode) | Shared data store |
| Business Logic | Python modules | Domain rules |
| Reports | fpdf2, ReportService | Report generation |

---

## 📊 SECURITY ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        SECURITY LAYERS                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  AUTHENTICATION                                                        │   │
│  │  • JWT Token-based authentication                                     │   │
│  │  • SHA-256 password hashing                                           │   │
│  │  • Session management via tokens                                      │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  AUTHORIZATION                                                         │   │
│  │  • Role-Based Access Control (RBAC)                                   │   │
│  │  • 5 roles: Super Admin, Admin, Manager, Staff, Viewer                │   │
│  │  • Permission-based access to features                                │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  DATA PROTECTION                                                       │   │
│  │  • Input validation (Pydantic)                                        │   │
│  │  • SQL injection prevention (parameterized queries)                   │   │
│  │  • CORS configuration                                                 │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  AUDIT & LOGGING                                                       │   │
│  │  • Login attempt logging                                              │   │
│  │  • Audit trail for data changes                                       │   │
│  │  • IP address tracking                                                │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 DEPLOYMENT ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        DEPLOYMENT OPTIONS                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  OPTION 1: Standalone Desktop                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  User's Computer                                                       │   │
│  │  ┌─────────────────┐                                                   │   │
│  │  │ PySide6 Desktop │                                                   │   │
│  │  │     App         │                                                   │   │
│  │  └────────┬────────┘                                                   │   │
│  │           │                                                             │   │
│  │           ▼                                                             │   │
│  │  ┌─────────────────┐                                                   │   │
│  │  │ SQLite Database │                                                   │   │
│  │  │ (Local File)    │                                                   │   │
│  │  └─────────────────┘                                                   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  OPTION 2: LAN Multi-User                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  Server Computer                                                       │   │
│  │  ┌─────────────────┐                                                   │   │
│  │  │ FastAPI Server  │                                                   │   │
│  │  │ (Port 6090)     │                                                   │   │
│  │  └────────┬────────┘                                                   │   │
│  │           │                                                             │   │
│  │           ▼                                                             │   │
│  │  ┌─────────────────┐                                                   │   │
│  │  │ SQLite Database │                                                   │   │
│  │  │ (Shared File)   │                                                   │   │
│  │  └─────────────────┘                                                   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│           │                                                                     │
│           │ LAN                                                                 │
│           ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  Client Computers                                                      │   │
│  │  ┌─────────────────┐                                                   │   │
│  │  │ Web Browser     │                                                   │   │
│  │  │ (SPA Client)    │                                                   │   │
│  │  └─────────────────┘                                                   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 PERFORMANCE CHARACTERISTICS

### Database Performance
- **WAL Mode:** Enabled for concurrent reads
- **Connection Pooling:** SQLAlchemy engine pool
- **Query Optimization:** Parameterized queries
- **Indexing:** Strategic indexes on frequently queried columns

### Application Performance
- **Lazy Loading:** Pages loaded on demand
- **Caching:** Settings cached in memory
- **Background Tasks:** Backup scheduler runs in background
- **UI Responsiveness:** Non-blocking operations

---

## 📊 SCALABILITY CONSIDERATIONS

### Current Limitations
1. **SQLite:** Single-file database (concurrent write limitations)
2. **Single Server:** LAN deployment only
3. **No Load Balancing:** Single instance deployment

### Scaling Options
1. **Database Migration:** PostgreSQL for multi-user
2. **Containerization:** Docker deployment
3. **Load Balancing:** Multiple FastAPI instances
4. **Caching Layer:** Redis for session/data caching

---

**Status:** Phase 1 - Architecture Diagram Complete
