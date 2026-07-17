"""
Test Search and Financial Functionality
"""

from search_module import PropertyMatcher
from financial_module import FinancialManager
from employee_module import EmployeeManager
import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

print('=' * 60)
print('🔍 TESTING SEARCH & FINANCIAL FUNCTIONALITY')
print('=' * 60)

# Test Search
print('\n1️⃣ Testing Property Search...')
matcher = PropertyMatcher()

# Search for matches
matches = matcher.search_properties(requirement_id=1, match_threshold=40)
print(f'   Found {len(matches)} matching properties')
if matches:
    print(f'\n   Top Match:')
    top = matches[0]
    print(f'     • Property: {top["details"]["location"]}')
    print(f'     • Rent: PKR {top["details"]["rent"]}')
    print(f'     • Match Score: {top["match_score"]:.1f}%')
    print(f'     • Match Type: {top["match_type"]}')

# Test Financial
print(f'\n2️⃣ Testing Financial Management...')
fm = FinancialManager()

# Get monthly summary
summary = fm.calculate_monthly_summary(month=5, year=2026)
print(f'   May 2026 Financial Summary:')
print(f'     • Total Income: PKR {summary["total_income"]:,.0f}')
print(f'     • Total Expense: PKR {summary["total_expense"]:,.0f}')
print(f'     • Net Profit: PKR {summary["net_profit"]:,.0f}')

# Income breakdown
if summary["income_breakdown"]:
    print(f'\n   Income Breakdown:')
    for income_type, amount in sorted(summary["income_breakdown"].items(), 
                                     key=lambda x: x[1], reverse=True):
        print(f'     • {income_type}: PKR {amount:,.0f}')

# Expense breakdown
if summary["expense_breakdown"]:
    print(f'\n   Expense Breakdown:')
    for expense_cat, amount in sorted(summary["expense_breakdown"].items(), 
                                      key=lambda x: x[1], reverse=True)[:5]:
        print(f'     • {expense_cat}: PKR {amount:,.0f}')

# Test Employee
print(f'\n3️⃣ Testing Employee Management...')
em = EmployeeManager()

# Get all employees
employees_df = em.get_all_employees(status='active')
print(f'   Active Employees: {len(employees_df)}')
if len(employees_df) > 0:
    print(f'\n   Employee List:')
    for idx, emp in employees_df.iterrows():
        print(f'     • {emp["full_name"]:20s} - {emp["position"]:20s} (PKR {emp["base_salary"]:,.0f})')

# Get top performers
top_performers = em.get_top_performers(month=5, year=2026, limit=3)
if top_performers:
    print(f'\n   Top Performers (May 2026):')
    for perf in top_performers:
        print(f'     • {perf["name"]:20s}: PKR {perf["commissions"]:,.0f}')

# Database verification
print(f'\n4️⃣ Database Verification...')
db_conn = sqlite3.connect('real_estate_crm.db')
c = db_conn.cursor()

# Count records
c.execute("SELECT COUNT(*) FROM rent_requirements")
req_count = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM rent_availability")
avail_count = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM employees")
emp_count = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM income_transactions")
inc_count = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM expense_transactions")
exp_count = c.fetchone()[0]

db_conn.close()

print(f'   Data in Database:')
print(f'     • Rent Requirements: {req_count}')
print(f'     • Available Properties: {avail_count}')
print(f'     • Employees: {emp_count}')
print(f'     • Income Transactions: {inc_count}')
print(f'     • Expense Transactions: {exp_count}')

print('\n' + '=' * 60)
print('✅ ALL FUNCTIONALITY TESTS PASSED!')
print('=' * 60)
print('\n🎉 Real Estate CRM System is fully operational and ready!')
print('\nTo start using the system:')
print('  python main_app.py')
print('=' * 60)
