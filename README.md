# 🏢 Real Estate CRM System - Complete Documentation

## Overview
This is a comprehensive, production-ready **Real Estate Customer Relationship Management (CRM)** system built with Python, SQLite, and advanced NLP/ML capabilities. It handles rent management, financial tracking, employee management, and data analytics.

---

## 🎯 Key Features

### 1. **Intelligent Rent Search Engine** 🔍
- **Exact Matching**: Direct match on location, budget, property type
- **Fuzzy Matching**: Fallback algorithm for similar properties
- **NLP Integration**: Parse property descriptions and extract keywords
- **Multi-Filter Support**: Search by price range, location, property type, bedrooms, etc.
- **Scoring System**: Results ranked by relevance (0-100)
- **Data Sources**: Manual entry + CSV import

### 2. **Financial Management** 💰
#### Income Tracking
- Rental Income (primary)
- Deposit Returns
- Late Payment Penalties
- Maintenance Charges
- Brokerage Commissions
- Service Charges

#### Expense Tracking
- Property Maintenance & Repairs
- Utilities
- Property Taxes
- Insurance
- Marketing & Advertising
- Employee Salaries & Commissions

#### Analytics
- Monthly/Yearly profit & loss statements
- Income/expense breakdowns by category
- Trend analysis and forecasting
- Profitability reports

### 3. **Employee Management** 👥
- **Salary Management**: Base salary + commission structure
- **Commission Tracking**: % commission on successful deals
- **Payroll Processing**: Automated monthly payroll calculation
- **Attendance Tracking**: Daily attendance records
- **Performance Reviews**: Rating system and KPI tracking
- **Performance Analytics**: Top performers, commission trends

### 4. **Data Management** 📊
- **CSV Import**: Bulk import for properties, employees, transactions
- **Data Validation**: Error handling and logging
- **Import History**: Track all data imports with success/failure stats
- **Flexible Schema**: Extensible design for custom fields

### 5. **Reporting & Analytics** 📈
- Financial dashboards
- Employee performance metrics
- Property matching statistics
- Income/expense trends
- Profit forecasting

---

## 📦 Installation

### Prerequisites
- Python 3.7+
- pip (Python package manager)

### Setup

1. **Clone/Extract the project**
```bash
cd RealEstate_CRM
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Initialize the database**
```bash
python database_setup.py
```

4. **Run the application**
```bash
python main_app.py
```

---

## 🗄️ Database Schema

### Core Tables

#### Rent Management
- `rent_requirements` - Customer rent requirements
- `rent_availability` - Available properties for rent
- `rent_matches` - Matched properties with scores

#### Financial
- `income_transactions` - All income records
- `expense_transactions` - All expense records
- `financial_summary` - Monthly aggregated summaries

#### Employee
- `employees` - Employee master records
- `employee_commissions` - Commission records per deal
- `employee_payroll` - Monthly payroll records
- `employee_attendance` - Daily attendance logs
- `employee_performance` - Performance reviews

#### Admin
- `data_imports` - Import history and stats
- `audit_log` - System activity logs

---

## 🚀 Usage Examples

### 1. **Adding a Rent Requirement**

```python
from database_setup import DatabaseSetup

db = DatabaseSetup()
conn = db.get_connection()
c = conn.cursor()

c.execute('''
    INSERT INTO rent_requirements 
    (date_created, client_name, location, budget_max, property_type, size_beds)
    VALUES (?, ?, ?, ?, ?, ?)
''', ('2026-05-06', 'Ahmed Ali', 'Karachi', 500000, 'Apartment', 3))

conn.commit()
conn.close()
```

### 2. **Searching for Matching Properties**

```python
from search_module import PropertyMatcher

matcher = PropertyMatcher()

# Search with exact + fuzzy matching
matches = matcher.search_properties(
    requirement_id=1,
    match_threshold=60,
    fuzzy_fallback=True
)

for match in matches:
    print(f"Property: {match['property']['location']}")
    print(f"Score: {match['match_score']}")
    print(f"Rent: {match['property']['monthly_rent']}")
```

### 3. **Advanced Filtering**

```python
# Filter with multiple criteria
filters = {
    'price_range': (300000, 600000),
    'property_types': ['Apartment', 'Flat'],
    'min_beds': 2,
    'max_beds': 4
}

filtered = matcher.filter_by_criteria(requirement_id=1, filters=filters)
```

### 4. **Recording Financial Transactions**

```python
from financial_module import FinancialManager

fm = FinancialManager()

# Record monthly rent income
fm.record_income(
    transaction_date='2026-05-01',
    property_id=1,
    income_type='rental_income',
    amount=50000,
    tenant_name='John Doe',
    recorded_by='admin'
)

# Record maintenance expense
fm.record_expense(
    transaction_date='2026-05-05',
    property_id=1,
    expense_category='maintenance',
    amount=5000,
    vendor_name='Fix-It Services',
    recorded_by='admin'
)
```

### 5. **Employee Management**

```python
from employee_module import EmployeeManager

em = EmployeeManager()

# Add employee
emp_id = em.add_employee(
    full_name='Fatima Khan',
    position='Property Agent',
    hire_date='2026-01-15',
    base_salary=40000,
    commission_rate=5.0
)

# Record commission on successful deal
em.record_commission(
    employee_id=emp_id,
    commission_amount=15000,
    deal_type='rent',
    deal_id=101
)

# Process monthly payroll
em.process_payroll(month=5, year=2026)
```

### 6. **Importing Data from CSV**

```python
from data_import_module import DataImporter

importer = DataImporter()

# Import rent availability
result = importer.import_rent_availability('properties.csv')
print(f"Imported: {result['successful']} records")
print(f"Failed: {result['failed']} records")
```

### 7. **Financial Reports**

```python
fm = FinancialManager()

# Get monthly summary
summary = fm.calculate_monthly_summary(month=5, year=2026)
print(f"Income: {summary['total_income']}")
print(f"Expenses: {summary['total_expense']}")
print(f"Profit: {summary['net_profit']}")

# Get profitability report
report = fm.get_profitability_report(month=5, year=2026)
print(f"Profit Margin: {report['summary']['profit_margin']}%")

# Get income trends
trends = fm.get_income_trend(months=12)
for trend in trends:
    print(f"{trend['month']}: {trend['profit']}")
```

---

## 📋 CSV Import Format

### Rent Requirements CSV
```csv
date_created,client_name,contact_phone,location,budget_min,budget_max,property_type,size_beds,description
2026-05-06,Ahmed Ali,03001234567,Karachi,300000,500000,Apartment,3,Needs modern apartment
```

### Rent Availability CSV
```csv
date_posted,owner_name,contact_phone,location,monthly_rent,property_type,size_beds,description
2026-05-06,Hassan Tariq,03009876543,Karachi,45000,Apartment,3,Furnished apartment
```

### Employees CSV
```csv
full_name,position,hire_date,base_salary,commission_rate
Fatima Khan,Property Agent,2026-01-15,40000,5.0
Ahmed Malik,Senior Agent,2025-06-01,60000,7.5
```

### Income Transactions CSV
```csv
transaction_date,property_id,income_type,amount,tenant_name
2026-05-01,1,rental_income,50000,John Doe
2026-05-10,1,late_payment_charge,2000,John Doe
```

---

## 🔐 Security & Best Practices

1. **Database Backup**: Regular backups recommended
2. **Audit Logging**: All changes logged with timestamps
3. **User Permissions**: Implement role-based access control
4. **Data Validation**: CSV imports validated before insertion
5. **Error Handling**: Comprehensive exception handling throughout

---

## 🎓 Module Reference

### `database_setup.py`
- `DatabaseSetup`: Initialize and manage database schema
- Methods: `init_database()`, `get_connection()`, `drop_all_tables()`

### `search_module.py`
- `TextProcessing`: NLP text extraction and normalization
- `PropertyMatcher`: Intelligent property search and matching
- Methods: `search_properties()`, `filter_by_criteria()`

### `financial_module.py`
- `FinancialManager`: Income/expense tracking and analysis
- Methods: `record_income()`, `record_expense()`, `calculate_monthly_summary()`, `get_profitability_report()`

### `employee_module.py`
- `EmployeeManager`: Employee records and payroll management
- Methods: `add_employee()`, `record_commission()`, `process_payroll()`, `get_employee_stats()`

### `data_import_module.py`
- `DataImporter`: CSV data import utilities
- Methods: `import_rent_requirements()`, `import_employees()`, `import_income_transactions()`

### `main_app.py`
- `RealEstateCRMApp`: Tkinter GUI application
- Multi-tab interface for all CRM functions

---

## 📊 Performance Tips

1. **Indexing**: Frequent queries on location, budget, and dates are optimized
2. **Batch Operations**: Use batch imports for large datasets
3. **Archive Old Data**: Archive historical data to maintain performance
4. **Query Optimization**: Pre-calculated summaries for faster reporting

---

## 🐛 Troubleshooting

### Common Issues

1. **Database locked error**
   - Close all open database connections
   - Restart the application

2. **Import failures**
   - Verify CSV format matches specification
   - Check for empty or invalid rows
   - Review import history for detailed errors

3. **Search not finding matches**
   - Lower the match_threshold parameter
   - Verify property descriptions contain relevant keywords
   - Check that fuzzy_fallback=True is enabled

---

## 🧪 Development & Testing

### Setting Up Development Environment

1. **Clone the repository**
```bash
git clone <repository-url>
cd RealEstate_CRM
```

2. **Create virtual environment**
```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows
```

3. **Install dependencies**
```bash
# Install production dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

### Using Makefile Commands

The project includes a Makefile with common development commands:

```bash
# Show available commands
make help

# Set up development environment
make setup

# Install all dependencies
make install-dev

# Run tests
make test

# Run tests with coverage
make test-coverage

# Run linting checks
make lint

# Auto-format code
make format

# Run type checking
make typecheck

# Check syntax of all Python files
make check-syntax

# Run all validation checks
make validate

# Clean up generated files
make clean
```

### Running Tests

**Using pytest:**
```bash
# Run all tests
python3 -m pytest tests/ -v

# Run tests with coverage report
python3 -m pytest tests/ -v --cov=backend --cov=crm_core --cov=CRM --cov-report=html

# Run specific test file
python3 -m pytest tests/test_reports_logic.py -v
```

**Using unittest:**
```bash
# Discover and run all tests
python3 -m unittest discover -s tests -v
```

### Code Quality

**Linting:**
```bash
# Check code style with flake8
flake8 backend/ crm_core/ CRM/ --max-line-length=100

# Check code formatting with black
black --check backend/ crm_core/ CRM/
```

**Formatting:**
```bash
# Auto-format code with black
black backend/ crm_core/ CRM/

# Sort imports with isort
isort backend/ crm_core/ CRM/
```

**Type Checking:**
```bash
# Run mypy type checker
mypy backend/ --ignore-missing-imports
```

### Syntax Validation

Before committing changes, validate that all Python files have correct syntax:

```bash
# Check syntax of key files
python3 -m py_compile backend/main.py
python3 -m py_compile backend/auth.py
python3 -m py_compile crm_core/reports.py
python3 -m py_compile CRM/app_window.py

# Or use the Makefile command
make check-syntax
```

### Pre-commit Hooks (Optional)

To set up pre-commit hooks for automatic code quality checks:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run hooks on all files
pre-commit run --all-files
```

### Documentation

To build documentation (if Sphinx is installed):

```bash
# Install documentation dependencies
pip install sphinx sphinx-rtd-theme

# Build documentation
sphinx-build -b html docs/ docs/_build/html
```

---

## 🔮 Future Enhancements

- ✨ Web-based dashboard (Flask/Django)
- 📱 Mobile app (React Native)
- 🤖 AI-powered property recommendations
- 🌍 Google Maps integration
- 📧 Email notifications
- 💬 WhatsApp integration
- 🎨 Advanced data visualization
- 🔄 Real-time sync with external APIs

---

## 📞 Support

For issues or feature requests, contact the development team.

---

## 📄 License

This project is proprietary and confidential.

---

## 👨‍💼 Version History

- **v1.0** (2026-05-06): Initial release with core features
  - Rent management with NLP search
  - Financial tracking and reporting
  - Employee management and payroll
  - Data import capabilities

---

**Happy Property Managing! 🏠🎉**
