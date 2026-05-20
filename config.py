"""
Real Estate CRM - Configuration Settings
"""

import os
from datetime import datetime

# ═════════════════════════════════════════════════════════════════
# DATABASE SETTINGS
# ═════════════════════════════════════════════════════════════════
DB_NAME = "real_estate_crm.db"
DB_PATH = os.path.join(os.path.dirname(__file__), DB_NAME)

# ═════════════════════════════════════════════════════════════════
# APPLICATION SETTINGS
# ═════════════════════════════════════════════════════════════════
APP_NAME = "Real Estate CRM System"
APP_VERSION = "1.0"
APP_AUTHOR = "Development Team"
RELEASE_DATE = "2026-05-06"

# ═════════════════════════════════════════════════════════════════
# LOGGING SETTINGS
# ═════════════════════════════════════════════════════════════════
LOG_FILE = "crm.log"
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ═════════════════════════════════════════════════════════════════
# SEARCH SETTINGS
# ═════════════════════════════════════════════════════════════════
# Minimum match score threshold (0-100)
MIN_MATCH_THRESHOLD = 60

# Enable fuzzy matching fallback
ENABLE_FUZZY_FALLBACK = True

# Fuzzy match threshold multiplier (reduces threshold by this factor)
FUZZY_THRESHOLD_MULTIPLIER = 0.7

# ═════════════════════════════════════════════════════════════════
# FINANCIAL SETTINGS
# ═════════════════════════════════════════════════════════════════
# Currency
CURRENCY = "PKR"
CURRENCY_SYMBOL = "Rs."

# Default profit growth forecast rate (5% = 0.05)
DEFAULT_GROWTH_RATE = 0.05

# ═════════════════════════════════════════════════════════════════
# EMPLOYEE SETTINGS
# ═════════════════════════════════════════════════════════════════
# Default commission rate (%)
DEFAULT_COMMISSION_RATE = 5.0

# Payroll processing day of month
PAYROLL_DAY = 28

# ═════════════════════════════════════════════════════════════════
# IMPORT SETTINGS
# ═════════════════════════════════════════════════════════════════
# Maximum records to import at once
MAX_BATCH_IMPORT = 1000

# Supported file types
SUPPORTED_FILE_TYPES = ['.csv', '.xlsx']

# ═════════════════════════════════════════════════════════════════
# REPORT SETTINGS
# ═════════════════════════════════════════════════════════════════
# Default report format
DEFAULT_REPORT_FORMAT = 'html'  # Options: 'html', 'pdf', 'excel'

# ═════════════════════════════════════════════════════════════════
# REAL ESTATE SPECIFIC SETTINGS
# ═════════════════════════════════════════════════════════════════

# Property Types
PROPERTY_TYPES = [
    'Apartment',
    'House',
    'Villa',
    'Studio',
    'Flat',
    'Townhouse',
    'Penthouse',
    'Bungalow',
    'Commercial',
    'Office'
]

# Income Categories
INCOME_CATEGORIES = {
    'rental_income': 'Primary Monthly Rent',
    'deposit_returned': 'Security Deposit Return',
    'late_payment_charge': 'Late Payment Penalty',
    'maintenance_charge': 'Tenant Maintenance Charge',
    'brokerage_commission': 'Brokerage Commission Earned',
    'service_charge': 'Additional Service Charges',
    'penalty_income': 'Other Penalties/Income'
}

# Expense Categories
EXPENSE_CATEGORIES = {
    'maintenance': 'Property Maintenance & Repairs',
    'utilities': 'Utilities (if landlord-covered)',
    'property_tax': 'Annual Property Taxes',
    'insurance': 'Property & Liability Insurance',
    'cleaning': 'Cleaning & Housekeeping',
    'marketing': 'Marketing & Advertising',
    'commissions': 'Employee Commissions',
    'staff_salary': 'Staff Salaries',
    'legal': 'Legal & Documentation Fees',
    'administration': 'Administrative & Office Costs',
    'utilities_repair': 'Utilities & Repairs',
    'other': 'Other Expenses'
}

# Facilities/Amenities
FACILITIES = [
    'Parking',
    'Gym',
    'Pool',
    'Security',
    'Garden',
    'Balcony',
    'Terrace',
    'Furnished',
    'Air Conditioning',
    'Water Supply',
    'Elevator',
    'Laundry'
]

# ═════════════════════════════════════════════════════════════════
# LOCATION SETTINGS
# ═════════════════════════════════════════════════════════════════

# Major cities in Pakistan
CITIES = [
    'Karachi',
    'Lahore',
    'Islamabad',
    'Rawalpindi',
    'Multan',
    'Faisalabad',
    'Hyderabad',
    'Peshawar',
    'Quetta',
    'Sukkur'
]

# Karachi areas
KARACHI_AREAS = [
    'DHA',
    'Clifton',
    'Banaras',
    'Gulshan-e-Iqbal',
    'North Karachi',
    'Korangi',
    'Federal B Area',
    'Malir',
    'Site',
    'Liaquatabad'
]

# ═════════════════════════════════════════════════════════════════
# VALIDATION SETTINGS
# ═════════════════════════════════════════════════════════════════

# Minimum budget for rent (PKR)
MIN_RENT_BUDGET = 5000

# Maximum budget for rent (PKR)
MAX_RENT_BUDGET = 10000000

# ═════════════════════════════════════════════════════════════════
# PERFORMANCE SETTINGS
# ═════════════════════════════════════════════════════════════════

# Query timeout (seconds)
QUERY_TIMEOUT = 30

# Cache search results (True/False)
ENABLE_SEARCH_CACHE = False

# ═════════════════════════════════════════════════════════════════
# FEATURE FLAGS
# ═════════════════════════════════════════════════════════════════

# Enable NLP text processing
ENABLE_NLP = True

# Enable fuzzy matching
ENABLE_FUZZY_MATCHING = True

# Enable audit logging
ENABLE_AUDIT_LOG = True

# ═════════════════════════════════════════════════════════════════
# EMAIL/NOTIFICATION SETTINGS (Future)
# ═════════════════════════════════════════════════════════════════

# SMTP Server
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Enable email notifications
ENABLE_EMAIL_NOTIFICATIONS = False

# ═════════════════════════════════════════════════════════════════
# Helper Functions
# ═════════════════════════════════════════════════════════════════

def get_config():
    """Get all configuration as dictionary"""
    return {
        'app_name': APP_NAME,
        'version': APP_VERSION,
        'database': DB_PATH,
        'currency': CURRENCY,
        'min_match_threshold': MIN_MATCH_THRESHOLD
    }

def validate_property_type(prop_type):
    """Validate if property type is valid"""
    return prop_type in PROPERTY_TYPES

def validate_income_type(income_type):
    """Validate if income type is valid"""
    return income_type in INCOME_CATEGORIES

def validate_expense_type(expense_type):
    """Validate if expense type is valid"""
    return expense_type in EXPENSE_CATEGORIES


if __name__ == "__main__":
    print("Real Estate CRM Configuration")
    print("=" * 50)
    print(f"App: {APP_NAME} v{APP_VERSION}")
    print(f"Database: {DB_PATH}")
    print(f"Property Types: {len(PROPERTY_TYPES)}")
    print(f"Income Categories: {len(INCOME_CATEGORIES)}")
    print(f"Expense Categories: {len(EXPENSE_CATEGORIES)}")
    print(f"Cities: {len(CITIES)}")
