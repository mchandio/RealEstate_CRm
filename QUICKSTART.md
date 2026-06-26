# 🚀 Quick Start Guide - Real Estate CRM System

## Step 1: Installation (2 minutes)

### Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Initialize Database
```bash
python database_setup.py
```

You should see: ✅ Database schema created successfully!

---

## Step 2: Start the Application

```bash
python main_app.py
```

The GUI will launch with multiple tabs for different functions.

### Multiuser Browser Clients

On the main/server computer, run the Qt CRM host app:

```bash
python qt_crm_app.py
```

After login, client computers on the same network can open:

```text
http://<server-ip-address>:6090
```

The host desktop app keeps the browser login server running while staff work.

---

## Step 3: First-Time Setup - Sample Data

### Option A: Import Sample Data (Recommended for Testing)

1. Click **"📥 Data Import"** tab
2. Click **"Import Rent Requirements"** → Select `sample_rent_requirements.csv`
3. Click **"Import Rent Availability"** → Select `sample_rent_availability.csv`
4. Click **"Import Employees"** → Select `sample_employees.csv`
5. Click **"Import Income Transactions"** → Select `sample_income.csv`
6. Click **"Import Expense Transactions"** → Select `sample_expenses.csv`

You'll see success messages showing how many records were imported!

### Option B: Manual Data Entry

Use the GUI tabs to manually enter:
- Rent requirements
- Employee information
- Financial transactions

---

## Step 4: Using the System

### 🏠 Rent Management

**To Find Properties:**
1. Go to "🏠 Rent Management" tab
2. Fill in the requirement form:
   - Client Name: *Ahmed Ali*
   - Location: *Karachi*
   - Budget Max: *500000*
   - Property Type: *Apartment*
   - Bedrooms: *3*
3. Click **"Save Requirement"**
4. System automatically searches for matching properties
5. Results appear in "Available Properties" list with match scores

### 💰 Financial Tracking

**To View Financial Summary:**
1. Go to "💰 Financial" tab
2. Select Month and Year
3. View automatically calculated:
   - Total Income
   - Total Expenses
   - Net Profit

**To Record Transactions:**
- Use Python API (see code examples below)

### 👥 Employee Management

**To Add Employee:**
1. Go to "👥 Employees" tab
2. Fill in:
   - Full Name: *Fatima Khan*
   - Position: *Property Agent*
   - Salary: *40000*
3. Click **"Add Employee"**
4. Employee ID generated automatically

---

## Quick Code Examples

### Example 1: Search for Properties Programmatically

```python
from search_module import PropertyMatcher

matcher = PropertyMatcher()
matches = matcher.search_properties(requirement_id=1)

for match in matches:
    print(f"Property at {match['details']['location']}")
    print(f"Match Score: {match['match_score']}")
    print(f"Rent: PKR {match['details']['rent']}")
    print("---")
```

### Example 2: Get Financial Report

```python
from financial_module import FinancialManager

fm = FinancialManager()

# Get May 2026 summary
report = fm.get_profitability_report(month=5, year=2026)

print(f"Total Income: PKR {report['summary']['total_income']}")
print(f"Total Expenses: PKR {report['summary']['total_expense']}")
print(f"Net Profit: PKR {report['summary']['net_profit']}")
print(f"Profit Margin: {report['summary']['profit_margin']}%")
```

### Example 3: Calculate Employee Salary

```python
from employee_module import EmployeeManager

em = EmployeeManager()

# Calculate May 2026 salary for employee
salary = em.calculate_monthly_salary('EMP202605001', month=5, year=2026)

print(f"Base Salary: PKR {salary['base_salary']}")
print(f"Commissions: PKR {salary['commissions']}")
print(f"Gross: PKR {salary['gross_salary']}")
print(f"Net: PKR {salary['net_salary']}")
```

---

## 📊 Understanding Match Scores

The rent search engine returns results with **match scores 0-100**:

- **90-100**: Excellent match - nearly perfect
- **75-89**: Good match - most criteria aligned
- **60-74**: Fair match - some criteria misaligned
- **40-59**: Fuzzy match - similar but not exact
- **Below 40**: Poor match - consider adjusting criteria

---

## 🎯 Common Tasks Workflow

### Workflow 1: Finding Properties for a Customer

1. Customer provides requirements (budget, location, size)
2. Enter requirement in "Rent Management" tab
3. System performs NLP analysis of property descriptions
4. Exact matches ranked first, then fuzzy matches
5. Show top 3-5 matches to customer with details
6. Record which property was selected

### Workflow 2: Monthly Financial Close

1. All transactions recorded (income/expenses)
2. Go to "💰 Financial" tab
3. Select the month
4. System auto-calculates all summaries
5. Review profitability and categories
6. Export report if needed

### Workflow 3: Payroll Processing

```python
from employee_module import EmployeeManager

em = EmployeeManager()

# Process entire payroll for May 2026
payroll_ids = em.process_payroll(month=5, year=2026)

print(f"Payroll processed for {len(payroll_ids)} employees")
```

---

## 🔍 Search Filters Example

```python
filters = {
    'price_range': (30000, 60000),           # Monthly rent range
    'property_types': ['Apartment', 'Flat'],  # Only apartments/flats
    'min_beds': 2,                           # Minimum 2 bedrooms
    'max_beds': 4,                           # Maximum 4 bedrooms
    'min_sq_ft': 1000,                       # Minimum 1000 sq ft
}

matches = matcher.filter_by_criteria(
    requirement_id=1,
    filters=filters
)
```

---

## 📁 File Structure

```
RealEstate_CRM/
├── database_setup.py          # Database initialization
├── search_module.py           # NLP & property search
├── financial_module.py        # Income/expense tracking
├── employee_module.py         # Employee management
├── data_import_module.py      # CSV import utilities
├── main_app.py               # GUI application
├── requirements.txt          # Python dependencies
├── README.md                 # Full documentation
├── QUICKSTART.md            # This file
├── real_estate_crm.db       # SQLite database (created on first run)
├── sample_rent_requirements.csv
├── sample_rent_availability.csv
├── sample_employees.csv
├── sample_income.csv
└── sample_expenses.csv
```

---

## ⚡ Performance Tips

1. **Searching**: For faster results, reduce match_threshold from 60 to 40
2. **Imports**: Import large datasets outside business hours
3. **Reports**: Pre-calculate monthly summaries at month-end
4. **Backup**: Regular database backups recommended

---

## 🆘 Troubleshooting

### Issue: "No matches found"
**Solution**: Lower the match_threshold or enable fuzzy_fallback
```python
matches = matcher.search_properties(requirement_id=1, match_threshold=40)
```

### Issue: "CSV import failed"
**Solution**: Verify CSV format matches specifications:
- Use commas as delimiter
- No extra spaces in column headers
- Remove non-numeric characters from numeric fields

### Issue: "Database locked"
**Solution**: Close all connections and restart the application

---

## 📞 Need Help?

- Check README.md for detailed documentation
- Review Python code examples in this guide
- Check database logs: `crm.log`
- Verify CSV format in sample files

---

## 🎓 Next Steps

1. ✅ Import sample data
2. ✅ Test property search
3. ✅ Review financial reports
4. ✅ Add a new employee
5. ✅ Create custom reports

---

**You're all set! Start managing properties like a pro! 🏢✨**
