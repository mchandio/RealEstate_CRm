# 🗄️ DATABASE RELATIONSHIPS
## Real Estate CRM - Complete Entity Relationship Documentation

---

## 📊 Database Overview

**Database Engine:** SQLite with WAL mode
**ORM:** SQLAlchemy (backend) + Raw SQLite (CRM desktop)
**Total Tables:** 50+
**Total Models:** 30+ (SQLAlchemy)

---

## 🔗 ENTITY RELATIONSHIP DIAGRAM (Text)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              SYSTEM TABLES                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐                  │
│  │    users      │      │  login_logs  │      │  audit_logs  │                  │
│  │──────────────│      │──────────────│      │──────────────│                  │
│  │ id (PK)      │◄─────│ user_id (FK) │      │ id (PK)      │                  │
│  │ username     │      │ id (PK)      │      │ action       │                  │
│  │ password_hash│      │ login_time   │      │ performed_by │                  │
│  │ full_name    │      │ ip_address   │      │ reference_*  │                  │
│  │ email        │      │ success      │      │ old_value    │                  │
│  │ role         │      └──────────────┘      │ new_value    │                  │
│  │ is_active    │                            └──────────────┘                  │
│  └──────────────┘                                                               │
│                                                                                 │
│  ┌──────────────┐      ┌──────────────┐                                        │
│  │app_settings  │      │pending_appr  │                                        │
│  │──────────────│      │──────────────│                                        │
│  │ key (PK)     │      │ id (PK)      │                                        │
│  │ value        │      │ action       │                                        │
│  └──────────────┘      │ table_name   │                                        │
│                        │ record_id    │                                        │
│                        │ status       │                                        │
│                        └──────────────┘                                        │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DEAL TABLES                                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌────────────────────┐          ┌────────────────────┐                        │
│  │ rent_requirements  │          │ rent_availability  │                        │
│  │────────────────────│          │────────────────────│                        │
│  │ id (PK)            │          │ id (PK)            │                        │
│  │ client_name        │          │ owner_name         │                        │
│  │ contact            │          │ contact            │                        │
│  │ property_requires  │          │ property_availability│                       │
│  │ budget             │          │ monthly_rent       │                        │
│  │ location           │          │ location           │                        │
│  │ workflow_stage     │          │ status             │                        │
│  │ deal_probability   │          │ workflow_stage     │                        │
│  └─────────┬──────────┘          └─────────┬──────────┘                        │
│            │                               │                                    │
│            │         ┌─────────────────────┴─────────────────────┐              │
│            │         │                                           │              │
│            ▼         ▼                                           ▼              │
│  ┌────────────────────┐          ┌────────────────────┐                        │
│  │ rented_properties  │          │ sold_properties    │                        │
│  │────────────────────│          │────────────────────│                        │
│  │ id (PK)            │          │ id (PK)            │                        │
│  │ source_table       │          │ source_table       │                        │
│  │ source_id          │          │ source_id          │                        │
│  │ deal_type          │          │ deal_type          │                        │
│  │ closed_status      │          │ closed_status      │                        │
│  │ closed_at          │          │ closed_at          │                        │
│  │ archived_by        │          │ archived_by        │                        │
│  └────────────────────┘          └────────────────────┘                        │
│                                                                                 │
│  ┌────────────────────┐          ┌────────────────────┐                        │
│  │ sale_requirements  │          │ sale_availability  │                        │
│  │────────────────────│          │────────────────────│                        │
│  │ id (PK)            │          │ id (PK)            │                        │
│  │ client_name        │          │ owner_name         │                        │
│  │ contact            │          │ contact            │                        │
│  │ property_requires  │          │ property_availability│                       │
│  │ budget             │          │ demand             │                        │
│  │ location           │          │ location           │                        │
│  │ workflow_stage     │          │ status             │                        │
│  └────────────────────┘          └────────────────────┘                        │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           CRM TABLES                                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐                  │
│  │  properties  │      │   clients    │      │broker_contacts│                  │
│  │──────────────│      │──────────────│      │──────────────│                  │
│  │ id (PK)      │      │ id (PK)      │      │ id (PK)      │                  │
│  │ property_code│      │ name         │      │ name         │                  │
│  │ title        │      │ phone        │      │ contact      │                  │
│  │ property_type│      │ email        │      │ area         │                  │
│  │ status       │      │ client_type  │      │ office_address│                  │
│  │ owner_name   │      │ status       │      │ home_address │                  │
│  │ owner_contact│      └──────────────┘      └──────────────┘                  │
│  │ location     │                                                               │
│  │ area         │                                                               │
│  └──────────────┘                                                               │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           FINANCIAL TABLES                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌────────────────────┐          ┌────────────────────┐                        │
│  │income_transactions │          │expense_transactions│                        │
│  │────────────────────│          │────────────────────│                        │
│  │ id (PK)            │          │ id (PK)            │                        │
│  │ transaction_date   │          │ transaction_date   │                        │
│  │ amount             │          │ amount             │                        │
│  │ income_type        │          │ expense_category   │                        │
│  │ property_id        │          │ property_id        │                        │
│  │ recorded_by        │          │ recorded_by        │                        │
│  └────────────────────┘          └────────────────────┘                        │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           HR TABLES                                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐                  │
│  │  employees   │      │  attendance  │      │salary_payments│                  │
│  │──────────────│      │──────────────│      │──────────────│                  │
│  │ id (PK)      │◄─────│ employee_id  │◄─────│ employee_id  │                  │
│  │ full_name    │      │ id (PK)      │      │ id (PK)      │                  │
│  │ position     │      │ date         │      │ pay_period   │                  │
│  │ base_salary  │      │ status       │      │ amount       │                  │
│  │ commission_rate│    │ check_in     │      │ payment_date │                  │
│  └──────────────┘      │ check_out    │      └──────────────┘                  │
│                        └──────────────┘                                        │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                    SUCCESSFACTORS (SF) TABLES                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────┐      ┌────────────────────┐                                  │
│  │ sf_employees │      │sf_performance_goals │                                  │
│  │──────────────│      │────────────────────│                                  │
│  │ id (PK)      │◄─────│ employee_id (FK)    │                                  │
│  │ full_name    │      │ id (PK)             │                                  │
│  │ department   │      │ goal_title          │                                  │
│  └──────────────┘      │ status              │                                  │
│       │                └────────────────────┘                                  │
│       │                                                                        │
│       ├──────────────►┌──────────────┐      ┌──────────────┐                   │
│       │               │ sf_learning  │      │sf_compensation│                   │
│       │               │──────────────│      │──────────────│                   │
│       │               │ employee_id  │      │ employee_id  │                   │
│       │               │ course_title │      │ base_salary  │                   │
│       │               │ status       │      │ total_comp   │                   │
│       │               └──────────────┘      └──────────────┘                   │
│       │                                                                        │
│       └──────────────►┌──────────────┐                                         │
│                       │sf_onboarding │                                         │
│                       │──────────────│                                         │
│                       │ employee_id  │                                         │
│                       │ task_title   │                                         │
│                       │ status       │                                         │
│                       └──────────────┘                                         │
│                                                                                 │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐                  │
│  │ sf_positions │      │sf_must_win_  │      │   sf_kpis    │                  │
│  │──────────────│      │   battles    │      │──────────────│                  │
│  │ id (PK)      │      │──────────────│      │ id (PK)      │                  │
│  │ position_code│      │ id (PK)      │      │ kpi_name     │                  │
│  │ position_title│    │ battle_title │      │ target_value │                  │
│  │ status       │      │ status       │      │ actual_value │                  │
│  └──────────────┘      └──────────────┘      └──────────────┘                  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                      WORKFLOW (WF) TABLES                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────┐      ┌──────────────────┐                                    │
│  │ wf_workflows │      │wf_workflow_steps  │                                    │
│  │──────────────│      │──────────────────│                                    │
│  │ id (PK)      │◄─────│ workflow_id (FK)  │                                    │
│  │ workflow_name│      │ id (PK)           │                                    │
│  │ status       │      │ step_order        │                                    │
│  └──────┬───────┘      │ step_name         │                                    │
│         │              └──────────────────┘                                    │
│         │                                                                      │
│         ▼                                                                      │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐                  │
│  │ wf_instances │      │   wf_tasks   │      │ wf_approvals │                  │
│  │──────────────│      │──────────────│      │──────────────│                  │
│  │ id (PK)      │◄─────│ instance_id  │◄─────│ task_id      │                  │
│  │ workflow_id  │      │ id (PK)      │      │ id (PK)      │                  │
│  │ status       │      │ assigned_to  │      │ decision     │                  │
│  └──────────────┘      │ status       │      │ status       │                  │
│                        └──────────────┘      └──────────────┘                  │
│                                                                                 │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐                  │
│  │wf_notifications│    │  wf_sla_log  │      │wf_audit_log  │                  │
│  │──────────────│      │──────────────│      │──────────────│                  │
│  │ id (PK)      │      │ id (PK)      │      │ id (PK)      │                  │
│  │ recipient    │      │ instance_id  │      │ action       │                  │
│  │ subject      │      │ task_id      │      │ performed_by │                  │
│  │ status       │      │ breached     │      │ performed_at │                  │
│  └──────────────┘      └──────────────┘      └──────────────┘                  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔗 KEY RELATIONSHIPS

### 1. User Authentication
```
users ──(1:N)──► login_logs
  │
  └──(1:N)──► audit_logs (via performed_by)
```

### 2. Deal Lifecycle
```
rent_requirements ──(1:1)──► rented_properties
  │                          (via source_table, source_id)
  │
  └──(N:M)──► rent_availability (via matching logic)

sale_requirements ──(1:1)──► sold_properties
  │                          (via source_table, source_id)
  │
  └──(N:M)──► sale_availability (via matching logic)
```

### 3. HR Management
```
employees ──(1:N)──► attendance
  │
  ├──(1:N)──► salary_payments
  │
  └──(1:N)──► sf_employees
                │
                ├──(1:N)──► sf_performance_goals
                ├──(1:N)──► sf_learning
                ├──(1:N)──► sf_compensation
                └──(1:N)──► sf_onboarding
```

### 4. Workflow Engine
```
wf_workflows ──(1:N)──► wf_workflow_steps
  │
  └──(1:N)──► wf_instances
                │
                ├──(1:N)──► wf_tasks
                │             │
                │             └──(1:N)──► wf_approvals
                │
                └──(1:N)──► wf_sla_log
```

### 5. Financial Tracking
```
properties ──(1:N)──► income_transactions
  │
  └──(1:N)──► expense_transactions
```

---

## 📊 TABLE COUNTS

| Category | Tables | Key Entities |
|----------|--------|--------------|
| System | 5 | users, login_logs, audit_logs, app_settings, pending_approvals |
| Deals | 6 | rent/sale requirements/availability, rented/sold properties |
| CRM | 3 | properties, clients, broker_contacts |
| Financial | 2 | income_transactions, expense_transactions |
| HR | 3 | employees, attendance, salary_payments |
| SuccessFactors | 9 | sf_employees, sf_positions, sf_performance_goals, etc. |
| Workflow | 8 | wf_workflows, wf_instances, wf_tasks, etc. |
| **Total** | **36+** | |

---

## 📝 SOFT DELETE STRATEGY

**Implementation:** `is_deleted` column (INTEGER DEFAULT 0)
**Tables with soft delete:**
- rent_requirements
- rent_availability
- sale_requirements
- sale_availability
- properties
- clients
- employees

**Archive Strategy:**
- Closed deals move to rented_properties/sold_properties
- Original records marked as deleted
- Source tracking via source_table, source_id

---

## 📊 INDEXES

**Existing Indexes:**
- idx_broker_contacts_area
- idx_broker_contacts_office_address
- idx_broker_contacts_home_address
- idx_rented_properties_closed_at
- idx_rented_properties_location
- idx_sold_properties_closed_at
- idx_sold_properties_location

**Recommended Additional Indexes:**
- rent_requirements(location, workflow_stage)
- rent_availability(location, status)
- sale_requirements(location, workflow_stage)
- sale_availability(location, status)
- clients(phone, name)
- properties(location, status)
- employees(department, status)
- income_transactions(transaction_date)
- expense_transactions(transaction_date)

---

**Status:** Phase 1 - Database Relationships Documented
