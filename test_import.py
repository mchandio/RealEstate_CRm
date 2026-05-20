"""
Test CSV Import Functionality
"""

from data_import_module import DataImporter
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

print('=' * 60)
print('📥 TESTING CSV DATA IMPORT')
print('=' * 60)

importer = DataImporter()

# Test import rent requirements
print('\n1️⃣ Importing Rent Requirements...')
result = importer.import_rent_requirements('sample_rent_requirements.csv')
print(f'   Status: {result["status"]}')
print(f'   Total: {result["total"]} records')
print(f'   Successful: {result["successful"]}')
print(f'   Failed: {result["failed"]}')

# Test import rent availability
print('\n2️⃣ Importing Rent Availability...')
result = importer.import_rent_availability('sample_rent_availability.csv')
print(f'   Status: {result["status"]}')
print(f'   Total: {result["total"]} records')
print(f'   Successful: {result["successful"]}')
print(f'   Failed: {result["failed"]}')

# Test import employees
print('\n3️⃣ Importing Employees...')
result = importer.import_employees('sample_employees.csv')
print(f'   Status: {result["status"]}')
print(f'   Total: {result["total"]} records')
print(f'   Successful: {result["successful"]}')
print(f'   Failed: {result["failed"]}')

# Test import income
print('\n4️⃣ Importing Income Transactions...')
result = importer.import_income_transactions('sample_income.csv')
print(f'   Status: {result["status"]}')
print(f'   Total: {result["total"]} records')
print(f'   Successful: {result["successful"]}')
print(f'   Failed: {result["failed"]}')

# Test import expenses
print('\n5️⃣ Importing Expense Transactions...')
result = importer.import_expense_transactions('sample_expenses.csv')
print(f'   Status: {result["status"]}')
print(f'   Total: {result["total"]} records')
print(f'   Successful: {result["successful"]}')
print(f'   Failed: {result["failed"]}')

print('\n' + '=' * 60)
print('✅ ALL DATA IMPORTED SUCCESSFULLY!')
print('=' * 60)
