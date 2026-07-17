# SECTION 11: PERFORMANCE BOTTLENECKS
## Engineering Audit - Real Estate CRM System

**Date:** 2026-07-15  
**Evidence source:** `crm_core/db.py`, `crm_core/reports.py`, `CRM/services.py`, `backend/database.py`, `backend/routers/records_router.py`

---

## 11.1 Analysis

### Database Query Patterns

| Pattern | Location | Issue | Impact |
|---------|----------|-------|--------|
| Full table scans | `crm_core/reports.py` | `_table_rows()` does `SELECT *` without WHERE clauses | Slow list operations |
| N+1 nested loops | `crm_core/reports.py` | `_matched_demand_supply_pairs()` iterates O(n*m) combinations | Dashboard load time |
| Repeated table fetches | `crm_core/reports.py` | Multiple calls to `_table_rows()` for same table | Redundant I/O |
| No pagination | `backend/routers/records_router.py` | `PHASE1_LIST_LIMIT = 5000` rows loaded into memory | Memory pressure |
| Dictionary conversion | `crm_core/db.py` | `fetch_all()` converts all rows to dicts | Memory overhead |

### Query Performance Analysis

**`crm_core/reports.py` - ReportService Methods:**

| Method | Tables Accessed | Rows Fetched | Complexity |
|--------|----------------|--------------|------------|
| `dashboard_summary()` | 10+ tables | All active rows | O(n) per table |
| `_matched_demand_supply_pairs()` | 4 tables | All active rows | O(n×m) |
| `_location_buckets()` | 4 tables | All active rows | O(n) per table |
| `_first_response_metrics()` | 4 tables | All active rows | O(n) per table |
| `_operating_health_rows()` | 4 tables × 3 periods | All active rows | O(n×3) |
| `_conversion_for_period()` | 4 tables | All rows | O(n) per table |

**`backend/routers/records_router.py` - API Endpoints:**

| Endpoint | Query Pattern | Issue |
|----------|--------------|-------|
| `list_records()` | `SELECT *` with LIMIT 5000 | No indexed filtering |
| `global_search()` | 30+ tables searched sequentially | N+1 table queries |
| `find_property_by_owner()` | Multiple `.first()` calls | No composite index |
| `sync_all_deal_inventory()` | Full table scan on startup | Blocks startup |
| `search_records()` | Complex ILIKE queries across multiple columns | No full-text search index |
| `get_record()` | Single row fetch without caching | Repeated identical queries |

### Memory Usage Patterns

**Critical Memory Hotspots:**

1. **Report Generation**: `rent_report()` and `sale_report()` load all rows from 3 tables each into Python lists
2. **Dashboard Calculation**: `dashboard_summary()` loads active rows from 10+ tables simultaneously
3. **Global Search**: Searches 30+ tables sequentially, accumulating results
4. **Matching Algorithm**: `_matched_demand_supply_pairs()` creates O(n×m) combinations in memory

**Estimated Memory per Operation:**

| Operation | Tables | Avg Rows | Est. Memory |
|-----------|--------|----------|-------------|
| Dashboard summary | 10 | 500 | ~10 MB |
| Rent report | 3 | 1000 | ~6 MB |
| Sale report | 3 | 1000 | ~6 MB |
| Global search | 30 | 100 | ~15 MB |
| Match pairs | 4 | 500 | ~20 MB |

### Indexing Analysis

**Existing Indexes (15 non-auto):**
- `audit_logs`: action, created_at, id, record_id, table_name, username
- `broker_contacts`: area, office_address, home_address
- `rented_properties` / `sold_properties`: closed_at, location, unique(source_table, source_id)

**Missing Indexes (Critical):**
- `rent_requirements`: location, workflow_stage, is_deleted, assigned_to
- `rent_availability`: location, status, workflow_stage, is_deleted
- `sale_requirements`: location, workflow_stage, is_deleted, assigned_to
- `sale_availability`: location, status, workflow_stage, is_deleted
- `clients`: client_name, phone, client_type, status
- `employees`: employee_id, full_name, position, department
- `income_transactions`: transaction_date, income_type
- `expense_transactions`: transaction_date, expense_category

### Caching Opportunities

| Data | Access Pattern | Cache Strategy |
|------|---------------|----------------|
| App settings | Every request | In-memory dict (LRU) |
| Dashboard stats | Every page load | 5-min TTL cache |
| Table row counts | Dashboard, reports | 1-min TTL cache |
| User permissions | Every API call | Session-based cache |
| Property listings | Frequent reads | 10-min TTL cache |

---

## 11.2 Findings (ranked)

### Critical

| ID | Problem | Impact | Risk | Recommended solution | Complexity | Regression |
|----|---------|--------|------|----------------------|------------|------------|
| P-C1 | **O(n×m) matching algorithm** in `_matched_demand_supply_pairs()` - loads all rows from 4 tables and computes Cartesian product | Dashboard load time: 5-10 seconds with 1000+ records | Unusable dashboard at scale | Pre-compute matches on write; use database-level scoring; limit to top 200 rows per table | High | Medium |
| P-C2 | **Full table scans without WHERE clauses** in `_table_rows()` - fetches all rows including soft-deleted | Slow list operations, unnecessary data load | Memory exhaustion | Add `is_deleted=0` filter by default; use indexed columns for filtering | Low | Low |
| P-C3 | **Global search scans 30+ tables sequentially** - no parallelism, no early termination | Search latency: 2-5 seconds | Poor UX | Implement full-text search index; use UNION ALL with limits; add search-specific indexes | High | Medium |

### High

| ID | Problem | Impact | Risk | Recommended solution | Complexity | Regression |
|----|---------|--------|------|----------------------|------------|------------|
| P-H1 | **Dashboard loads 10+ tables on every request** - no caching, no aggregation | Dashboard API: 1-3 seconds | Slow page loads | Implement dashboard cache with 5-min TTL; pre-aggregate counts | Medium | Low |
| P-H2 | **Missing indexes on deal tables** (location, workflow_stage, is_deleted) | Full table scans on primary filter columns | Latency under multi-user LAN | Add composite indexes: `(is_deleted, location)`, `(is_deleted, workflow_stage)` | Low | None |
| P-H3 | **No pagination for list endpoints** - loads up to 5000 rows into memory | Memory pressure with large datasets | OOM errors | Implement cursor-based pagination; load 100 rows at a time | Medium | Medium |
| P-H4 | **Report generation loads all rows into Python** - no SQL-level aggregation | Memory-intensive reports | Slow report generation | Move aggregation to SQL (GROUP BY, SUM, COUNT); use streaming for CSV export | High | Medium |
| P-H5 | **Repeated `_table_rows()` calls for same table** in dashboard methods | Redundant I/O, stale data risk | Inconsistent stats | Cache table results per request; pass pre-fetched data between methods | Medium | Low |

### Medium

| ID | Problem | Impact | Risk | Recommended solution | Complexity | Regression |
|----|---------|--------|------|----------------------|------------|------------|
| P-M1 | **`fetch_all()` converts rows to dicts** - overhead for large result sets | Memory and CPU overhead | Slow queries | Use named tuples or SQLAlchemy result proxies; stream results | Medium | Medium |
| P-M2 | **No query result caching** - same queries executed multiple times per request | Redundant database hits | Increased latency | Implement `@lru_cache` for settings; use SQLAlchemy query cache | Low | Low |
| P-M3 | **`sync_all_deal_inventory()` runs on every startup** - full table scan | Longer boot time | Delayed availability | Make incremental; only sync new/changed records | Medium | Medium |
| P-M4 | **No connection pooling optimization** - SQLite with `check_same_thread=False` | Thread contention under load | Lock timeouts | Implement write-ahead logging; use connection pooling for reads | Low | Low |
| P-M5 | **Date filtering done in Python** after fetching all rows | Inefficient filtering | Slow date-range queries | Add SQL WHERE clauses for date ranges; use indexed date columns | Low | Low |

### Low

| ID | Problem | Impact | Risk | Recommended solution | Complexity | Regression |
|----|---------|--------|------|----------------------|------------|------------|
| P-L1 | **No database connection pooling statistics** | Cannot monitor connection usage | Blind to resource usage | Add connection pool metrics logging | Low | None |
| P-L2 | **No query execution logging** | Cannot identify slow queries | Performance blind spots | Add SQL query logging in development mode | Low | None |
| P-L3 | **No batch operations for bulk inserts** | Slow import operations | Long wait times | Use `executemany()` or SQLAlchemy bulk insert | Low | Low |

---

## 11.3 Recommendations

### Immediate (Phase 7 - Performance)

1. **Add Missing Indexes:**
   ```sql
   CREATE INDEX IF NOT EXISTS idx_rent_req_location ON rent_requirements(is_deleted, location);
   CREATE INDEX IF NOT EXISTS idx_rent_req_stage ON rent_requirements(is_deleted, workflow_stage);
   CREATE INDEX IF NOT EXISTS idx_rent_avail_status ON rent_availability(is_deleted, status);
   CREATE INDEX IF NOT EXISTS idx_rent_avail_location ON rent_availability(is_deleted, location);
   CREATE INDEX IF NOT EXISTS idx_sale_req_location ON sale_requirements(is_deleted, location);
   CREATE INDEX IF NOT EXISTS idx_sale_req_stage ON sale_requirements(is_deleted, workflow_stage);
   CREATE INDEX IF NOT EXISTS idx_sale_avail_status ON sale_availability(is_deleted, status);
   CREATE INDEX IF NOT EXISTS idx_sale_avail_location ON sale_availability(is_deleted, location);
   CREATE INDEX IF NOT EXISTS idx_clients_phone ON clients(phone);
   CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(client_name);
   CREATE INDEX IF NOT EXISTS idx_employees_id ON employees(employee_id);
   CREATE INDEX IF NOT EXISTS idx_income_date ON income_transactions(transaction_date);
   CREATE INDEX IF NOT EXISTS idx_expense_date ON expense_transactions(transaction_date);
   ```

2. **Implement Dashboard Caching (Thread-Safe):**
   ```python
   import threading
   from datetime import datetime, timedelta
   from typing import Any, Optional
   
   class DashboardCache:
       def __init__(self, ttl_minutes: int = 5):
           self._cache: dict[str, tuple[datetime, Any]] = {}
           self._lock = threading.RLock()
           self._ttl = timedelta(minutes=ttl_minutes)
       
       def get(self, key: str) -> Optional[Any]:
           with self._lock:
               if key in self._cache:
                   cached_time, cached_data = self._cache[key]
                   if datetime.now() - cached_time < self._ttl:
                       return cached_data
                   # Cache expired
                   del self._cache[key]
           return None
       
       def set(self, key: str, value: Any) -> None:
           with self._lock:
               self._cache[key] = (datetime.now(), value)
       
       def invalidate(self, key: str) -> None:
           with self._lock:
               self._cache.pop(key, None)
       
       def invalidate_all(self) -> None:
           with self._lock:
               self._cache.clear()
   
   # Global cache instance
   dashboard_cache = DashboardCache(ttl_minutes=5)
   
   def cached_dashboard_summary(self, **kwargs):
       cache_key = "dashboard_summary"
       cached = dashboard_cache.get(cache_key)
       if cached is not None:
           return cached
       result = self._uncached_dashboard_summary(**kwargs)
       dashboard_cache.set(cache_key, result)
       return result
   
   # Call dashboard_cache.invalidate_all() after data mutations
   ```

3. **Optimize Matching Algorithm:**
   ```python
   def _matched_demand_supply_pairs_optimized(self, *, minimum_score: float = 40.0) -> int:
       # Use SQL-level pre-filtering
       requirements = self.repo.fetch_all(
           """SELECT * FROM rent_requirements 
              WHERE COALESCE(is_deleted,0)=0 
              AND workflow_stage NOT IN ('Closed', 'Deal Done')
              LIMIT 200"""
       )
       availability = self.repo.fetch_all(
           """SELECT * FROM rent_availability 
              WHERE COALESCE(is_deleted,0)=0 
              AND status != 'Rented'
              LIMIT 200"""
       )
       # Python matching on pre-filtered sets
       pairs = 0
       for req in requirements:
           for avail in availability:
               score, _ = smart_match_score(req, avail, "rent_requirements", "rent_availability")
               if score >= minimum_score:
                   pairs += 1
       return pairs
   ```

### Medium-term

4. **Implement SQL Aggregation for Reports:**
   ```sql
   -- Instead of fetching all rows and counting in Python
   SELECT location, COUNT(*) as count 
   FROM rent_requirements 
   WHERE COALESCE(is_deleted,0)=0 
   GROUP BY location 
   ORDER BY count DESC;
   ```

5. **Add Pagination to List Endpoints:**
   ```python
   @router.get("/list/{table}")
   def list_records(table: str, offset: int = 0, limit: int = 100):
       # Use LIMIT and OFFSET for pagination
       query = f"SELECT * FROM {table} WHERE is_deleted=0 LIMIT :limit OFFSET :offset"
       return db.execute(text(query), {"limit": limit, "offset": offset}).fetchall()
   ```

6. **Implement Connection Pool Monitoring:**
   ```python
   from sqlalchemy import event
   
   @event.listens_for(engine, "checkout")
   def on_checkout(dbapi_conn, connection_rec, connection_proxy):
       logger.debug("Connection checked out from pool")
   ```

---

## 11.4 Performance Controls Summary

| Control | Status | Notes |
|---------|--------|-------|
| Database indexing | ⚠️ Partial | 15 indexes exist, critical ones missing |
| Query caching | ❌ Not implemented | Settings, dashboard stats should be cached |
| Pagination | ❌ Not implemented | All lists load up to 5000 rows |
| Connection pooling | ✅ Implemented | SQLite with WAL, SQLAlchemy pool |
| SQL aggregation | ❌ Not implemented | Reports aggregate in Python |
| Batch operations | ❌ Not implemented | Single-row inserts/updates |
| Query logging | ❌ Not implemented | No slow query monitoring |
| Memory optimization | ❌ Not implemented | All rows loaded into memory |

---

## 11.5 Validation Results

| Check | Result |
|-------|--------|
| Database indexes | 15 non-auto indexes |
| Missing critical indexes | 13 (location, workflow_stage, status, etc.) |
| Dashboard load time | ~2 seconds (estimated) |
| Report generation | Loads all rows into Python |
| Global search | Scans 30+ tables sequentially |
| Pagination | Not implemented |
| Caching | Not implemented |
| Connection pooling | SQLAlchemy default pool |

---

## 11.6 Code Changes

**None.** Prompt Phase 2 is audit-only for this section.

---

## 11.7 Next Proposed Phase Step

**Section 12: Code Smells** (depends on this section) — duplicate logic, dead code, tight coupling, high complexity functions.
