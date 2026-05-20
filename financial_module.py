"""
═══════════════════════════════════════════════════════════════════════════════
    PROFESSIONAL ENTERPRISE FINANCIAL MODULE FOR CRM/ERP
    Complete accounting-style financial management system
    Build: May 2026 | Version: 2.0.0 Enterprise Edition
═══════════════════════════════════════════════════════════════════════════════
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext, simpledialog
import sqlite3
from datetime import datetime, timedelta
from functools import partial
import os
import csv
from enum import Enum

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS FOR FINANCIAL STATUS
# ═══════════════════════════════════════════════════════════════════════════════

class VoucherStatus(Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    REVERSED = "Reversed"

class PaymentMethod(Enum):
    CASH = "Cash"
    CHECK = "Check"
    BANK_TRANSFER = "Bank Transfer"
    CREDIT_CARD = "Credit Card"
    MOBILE = "Mobile Banking"

class ExpenseType(Enum):
    FIXED = "Fixed"
    VARIABLE = "Variable"
    UTILITY = "Utility"
    OPERATIONAL = "Operational"
    ASSET = "Asset"

class UserRole(Enum):
    SUPER_ADMIN = "Super Admin"
    FINANCE_ADMIN = "Finance Admin"
    MANAGER = "Manager"
    STAFF = "Staff"
    VIEWER = "Viewer"

# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

class FinancialDatabase:
    """Financial Database Management - Normalized Relational Schema"""
    
    DB_PATH = "financial_module.db"
    
    @staticmethod
    def get_connection():
        conn = sqlite3.connect(FinancialDatabase.DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    
    @staticmethod
    def init_database():
        """Initialize all financial tables with proper relationships"""
        conn = FinancialDatabase.get_connection()
        c = conn.cursor()
        
        # ────────────────────────────────────────────────────────────────────────
        # USERS AND ROLES (Role-Based Access Control)
        # ────────────────────────────────────────────────────────────────────────
        
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE,
            role TEXT NOT NULL,
            department TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # ────────────────────────────────────────────────────────────────────────
        # EXPENSE VOUCHER SYSTEM
        # ────────────────────────────────────────────────────────────────────────
        
        c.execute('''CREATE TABLE IF NOT EXISTS expense_categories (
            id INTEGER PRIMARY KEY,
            category_name TEXT UNIQUE NOT NULL,
            category_type TEXT NOT NULL,
            description TEXT,
            account_code TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS expense_vouchers (
            id INTEGER PRIMARY KEY,
            voucher_no TEXT UNIQUE NOT NULL,
            voucher_date TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            description TEXT,
            amount REAL NOT NULL,
            payment_method TEXT NOT NULL,
            vendor_name TEXT,
            reference_no TEXT,
            attachment_id INTEGER,
            entered_by INTEGER NOT NULL,
            approved_by INTEGER,
            approval_date TEXT,
            approval_notes TEXT,
            status TEXT NOT NULL DEFAULT 'Pending',
            branch_id INTEGER,
            closing_day_id INTEGER,
            remarks TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP,
            deleted_by INTEGER,
            FOREIGN KEY (category_id) REFERENCES expense_categories(id),
            FOREIGN KEY (entered_by) REFERENCES users(id),
            FOREIGN KEY (approved_by) REFERENCES users(id),
            FOREIGN KEY (attachment_id) REFERENCES attachments(id)
        )''')
        
        # ────────────────────────────────────────────────────────────────────────
        # INCOME VOUCHER SYSTEM
        # ────────────────────────────────────────────────────────────────────────
        
        c.execute('''CREATE TABLE IF NOT EXISTS income_sources (
            id INTEGER PRIMARY KEY,
            source_name TEXT UNIQUE NOT NULL,
            description TEXT,
            account_code TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS income_vouchers (
            id INTEGER PRIMARY KEY,
            voucher_no TEXT UNIQUE NOT NULL,
            voucher_date TEXT NOT NULL,
            income_source_id INTEGER NOT NULL,
            client_name TEXT,
            property_id INTEGER,
            invoice_no TEXT,
            description TEXT,
            amount REAL NOT NULL,
            payment_method TEXT NOT NULL,
            attachment_id INTEGER,
            received_by INTEGER NOT NULL,
            approved_by INTEGER,
            approval_date TEXT,
            approval_notes TEXT,
            status TEXT NOT NULL DEFAULT 'Pending',
            bank_deposit_date TEXT,
            remarks TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP,
            deleted_by INTEGER,
            FOREIGN KEY (income_source_id) REFERENCES income_sources(id),
            FOREIGN KEY (received_by) REFERENCES users(id),
            FOREIGN KEY (approved_by) REFERENCES users(id),
            FOREIGN KEY (attachment_id) REFERENCES attachments(id)
        )''')
        
        # ────────────────────────────────────────────────────────────────────────
        # DAILY CLOSING SYSTEM
        # ────────────────────────────────────────────────────────────────────────
        
        c.execute('''CREATE TABLE IF NOT EXISTS daily_closings (
            id INTEGER PRIMARY KEY,
            closing_date TEXT UNIQUE NOT NULL,
            total_income REAL DEFAULT 0,
            total_expense REAL DEFAULT 0,
            cash_in_hand REAL DEFAULT 0,
            bank_balance REAL DEFAULT 0,
            net_profit REAL DEFAULT 0,
            closing_notes TEXT,
            closed_by INTEGER NOT NULL,
            is_locked INTEGER DEFAULT 0,
            locked_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (closed_by) REFERENCES users(id)
        )''')
        
        # ────────────────────────────────────────────────────────────────────────
        # MONTHLY REPORTS
        # ────────────────────────────────────────────────────────────────────────
        
        c.execute('''CREATE TABLE IF NOT EXISTS monthly_reports (
            id INTEGER PRIMARY KEY,
            report_month TEXT NOT NULL,
            report_year INTEGER NOT NULL,
            total_income REAL DEFAULT 0,
            total_expense REAL DEFAULT 0,
            net_profit REAL DEFAULT 0,
            profit_margin REAL DEFAULT 0,
            cash_opening REAL DEFAULT 0,
            cash_closing REAL DEFAULT 0,
            bank_opening REAL DEFAULT 0,
            bank_closing REAL DEFAULT 0,
            generated_by INTEGER NOT NULL,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (generated_by) REFERENCES users(id),
            UNIQUE(report_month, report_year)
        )''')
        
        # ────────────────────────────────────────────────────────────────────────
        # ATTACHMENTS & BILLS MANAGEMENT
        # ────────────────────────────────────────────────────────────────────────
        
        c.execute('''CREATE TABLE IF NOT EXISTS attachments (
            id INTEGER PRIMARY KEY,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT,
            mime_type TEXT,
            file_size INTEGER,
            uploaded_by INTEGER NOT NULL,
            voucher_type TEXT,
            voucher_id INTEGER,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (uploaded_by) REFERENCES users(id)
        )''')
        
        # ────────────────────────────────────────────────────────────────────────
        # AUDIT TRAIL SYSTEM (Complete Activity Logging)
        # ────────────────────────────────────────────────────────────────────────
        
        c.execute('''CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            module TEXT NOT NULL,
            record_type TEXT,
            record_id INTEGER,
            old_value TEXT,
            new_value TEXT,
            ip_address TEXT,
            user_agent TEXT,
            status TEXT,
            remarks TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''')
        
        conn.commit()
        conn.close()
        
        # Insert default data
        FinancialDatabase.insert_default_data()
    
    @staticmethod
    def insert_default_data():
        """Insert default roles, permissions, and categories"""
        conn = FinancialDatabase.get_connection()
        c = conn.cursor()
        
        try:
            # Insert default expense categories
            default_categories = [
                ('Salaries', 'Fixed', 'Employee salaries and wages', '4001'),
                ('Electricity', 'Utility', 'Electricity bills', '4002'),
                ('Fuel', 'Variable', 'Vehicle fuel and petrol', '4003'),
                ('Food & Catering', 'Operational', 'Office food expenses', '4004'),
                ('Furniture & Fixtures', 'Asset', 'Office furniture and fixtures', '4005'),
                ('Maintenance', 'Operational', 'Building maintenance and repairs', '4006'),
                ('Marketing', 'Operational', 'Marketing and advertising', '4007'),
                ('Repairs', 'Variable', 'Equipment and property repairs', '4008'),
                ('Office Supplies', 'Operational', 'Stationery and office supplies', '4009'),
                ('Utilities', 'Utility', 'Water and other utilities', '4010'),
            ]
            
            for cat_name, cat_type, desc, code in default_categories:
                try:
                    c.execute('''INSERT INTO expense_categories 
                               (category_name, category_type, description, account_code)
                               VALUES (?,?,?,?)''', (cat_name, cat_type, desc, code))
                except sqlite3.IntegrityError:
                    pass
            
            # Insert default income sources
            default_sources = [
                ('Property Rent', 'Monthly rent income from properties', '3001'),
                ('Booking Fee', 'Booking and reservation fees', '3002'),
                ('Commission', 'Sales and brokerage commission', '3003'),
                ('Service Charges', 'Service charges income', '3004'),
                ('Advance Payments', 'Advance client payments', '3005'),
                ('Late Fees', 'Late payment penalty fees', '3006'),
                ('Utility Recharge', 'Utility bills recharge to tenants', '3007'),
                ('Maintenance Fee', 'Maintenance charges from clients', '3008'),
            ]
            
            for src_name, desc, code in default_sources:
                try:
                    c.execute('''INSERT INTO income_sources 
                               (source_name, description, account_code)
                               VALUES (?,?,?)''', (src_name, desc, code))
                except sqlite3.IntegrityError:
                    pass
            
            conn.commit()
        except Exception as e:
            print(f"Error inserting default data: {e}")
        finally:
            conn.close()
    
    @staticmethod
    def execute(query, params=(), fetch=False):
        """Execute database query safely"""
        try:
            conn = FinancialDatabase.get_connection()
            c = conn.cursor()
            c.execute(query, params)
            result = c.fetchall() if fetch else None
            conn.commit()
            conn.close()
            return result
        except Exception as e:
            print(f"Database error: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# FINANCIAL MODULE UI
# ═══════════════════════════════════════════════════════════════════════════════

class FinancialModule:
    """Main Financial Module Interface - Enterprise Grade"""
    
    def __init__(self, parent_frame, currency_symbol='Rs.', colors=None):
        self.parent = parent_frame
        self.currency_symbol = currency_symbol
        self.colors = colors or {
            'primary': '#2563eb',
            'success': '#16a34a',
            'danger': '#dc2626',
            'warning': '#ea580c',
            'secondary': '#64748b',
            'light': '#f8fafc',
            'dark': '#0f172a',
            'border': '#e2e8f0'
        }
        
        # Initialize database
        FinancialDatabase.init_database()
        
        # Create UI
        self.create_financial_dashboard()
    
    def create_financial_dashboard(self):
        """Create main financial dashboard with tabs"""
        # Create notebook for sections
        self.notebook = ttk.Notebook(self.parent)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Dashboard tab
        dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(dashboard_frame, text="📊 Dashboard")
        self.create_dashboard_view(dashboard_frame)
        
        # Expense Vouchers tab
        expense_frame = ttk.Frame(self.notebook)
        self.notebook.add(expense_frame, text="📤 Expense Vouchers")
        self.create_expense_voucher_view(expense_frame)
        
        # Income Vouchers tab
        income_frame = ttk.Frame(self.notebook)
        self.notebook.add(income_frame, text="📥 Income Vouchers")
        self.create_income_voucher_view(income_frame)
        
        # Daily Closing tab
        closing_frame = ttk.Frame(self.notebook)
        self.notebook.add(closing_frame, text="🔒 Daily Closing")
        self.create_daily_closing_view(closing_frame)
        
        # Reports tab
        reports_frame = ttk.Frame(self.notebook)
        self.notebook.add(reports_frame, text="📈 Reports & Analytics")
        self.create_reports_view(reports_frame)
        
        # Settings tab
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="⚙️ Settings")
        self.create_settings_view(settings_frame)
    
    def create_dashboard_view(self, parent):
        """Create Financial Dashboard with KPIs"""
        # Title
        title = ttk.Label(parent, text="💰 FINANCIAL DASHBOARD", 
                         font=('Segoe UI', 16, 'bold'), foreground=self.colors['primary'])
        title.pack(padx=20, pady=15)
        
        # Date range filter
        filter_frame = ttk.Frame(parent)
        filter_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Label(filter_frame, text="From:").pack(side='left', padx=(0, 5))
        from_date = ttk.Entry(filter_frame, width=15)
        from_date.pack(side='left', padx=(0, 20))
        from_date.insert(0, (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        
        ttk.Label(filter_frame, text="To:").pack(side='left', padx=(0, 5))
        to_date = ttk.Entry(filter_frame, width=15)
        to_date.pack(side='left', padx=(0, 20))
        to_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        ttk.Button(filter_frame, text="🔍 Refresh", 
                  command=lambda: self.refresh_dashboard(from_date.get(), to_date.get())).pack(side='left')
        
        # Dashboard cards
        stats_frame = ttk.Frame(parent)
        stats_frame.pack(fill='both', expand=True, padx=20, pady=15)
        
        # Get financial data
        income_total = self._get_total_income(from_date.get(), to_date.get())
        expense_total = self._get_total_expense(from_date.get(), to_date.get())
        profit = income_total - expense_total
        
        # Create stat cards
        self._create_stat_card(stats_frame, "💵 Total Income", 
                             self.format_currency(income_total), self.colors['success'], 0)
        self._create_stat_card(stats_frame, "💸 Total Expenses", 
                             self.format_currency(expense_total), self.colors['danger'], 1)
        self._create_stat_card(stats_frame, "📈 Net Profit", 
                             self.format_currency(profit), self.colors['primary'], 2)
        
        profit_margin = (profit / income_total * 100) if income_total > 0 else 0
        self._create_stat_card(stats_frame, "📊 Profit Margin", 
                             f"{profit_margin:.1f}%", self.colors['warning'], 3)
        
        # Recent transactions
        recent_frame = ttk.LabelFrame(parent, text="📋 Recent Transactions", padding=10)
        recent_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        tree = ttk.Treeview(recent_frame, 
                           columns=('Date', 'Type', 'Voucher No', 'Amount', 'Status'),
                           height=8, show='headings')
        
        tree.column('Date', width=120)
        tree.column('Type', width=120)
        tree.column('Voucher No', width=120)
        tree.column('Amount', width=120)
        tree.column('Status', width=100)
        
        for col in tree['columns']:
            tree.heading(col, text=col)
        
        # Get recent transactions
        income_result = FinancialDatabase.execute(
            """SELECT 'Income' as type, voucher_no, voucher_date, amount, status 
               FROM income_vouchers 
               WHERE voucher_date >= ? AND voucher_date <= ?
               ORDER BY voucher_date DESC LIMIT 10""",
            (from_date.get(), to_date.get()), fetch=True
        )
        
        expense_result = FinancialDatabase.execute(
            """SELECT 'Expense' as type, voucher_no, voucher_date, amount, status 
               FROM expense_vouchers 
               WHERE voucher_date >= ? AND voucher_date <= ?
               ORDER BY voucher_date DESC LIMIT 10""",
            (from_date.get(), to_date.get()), fetch=True
        )
        
        transactions = list(income_result or []) + list(expense_result or [])
        transactions.sort(key=lambda x: x['voucher_date'], reverse=True)
        
        for trans in transactions[:10]:
            tree.insert('', 'end', values=(
                trans['voucher_date'],
                trans['type'],
                trans['voucher_no'],
                self.format_currency(trans['amount']),
                trans['status']
            ))
        
        tree.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(recent_frame, orient='vertical', command=tree.yview)
        scrollbar.pack(side='right', fill='y')
        tree.config(yscrollcommand=scrollbar.set)
    
    def create_expense_voucher_view(self, parent):
        """Create Expense Voucher Management View"""
        # Header with buttons
        header = ttk.Frame(parent)
        header.pack(fill='x', padx=20, pady=15)
        
        title = ttk.Label(header, text="📤 EXPENSE VOUCHERS", 
                         font=('Segoe UI', 14, 'bold'), foreground=self.colors['primary'])
        title.pack(side='left')
        
        ttk.Button(header, text="➕ New Expense Voucher", 
                  command=self.open_expense_voucher_form).pack(side='right', padx=5)
        
        # Filter and search
        filter_frame = ttk.Frame(parent)
        filter_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Label(filter_frame, text="Category:").pack(side='left', padx=5)
        category_var = tk.StringVar()
        category_combo = ttk.Combobox(filter_frame, textvariable=category_var, width=20)
        self._load_categories_combo(category_combo)
        category_combo.pack(side='left', padx=(0, 20))
        
        ttk.Label(filter_frame, text="Status:").pack(side='left', padx=5)
        status_var = tk.StringVar()
        status_combo = ttk.Combobox(filter_frame, textvariable=status_var, 
                                   values=['All', 'Pending', 'Approved', 'Rejected', 'Reversed'],
                                   width=15)
        status_combo.set('All')
        status_combo.pack(side='left', padx=(0, 20))
        
        ttk.Button(filter_frame, text="🔍 Filter", 
                  command=lambda: self.load_expense_vouchers(parent, category_var.get(), status_var.get())).pack(side='left')
        
        # Treeview for vouchers
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        tree = ttk.Treeview(tree_frame,
                           columns=('Voucher No', 'Date', 'Category', 'Amount', 'Status', 'Entered By'),
                           height=15, show='headings')
        
        tree.column('Voucher No', width=120)
        tree.column('Date', width=100)
        tree.column('Category', width=150)
        tree.column('Amount', width=120)
        tree.column('Status', width=100)
        tree.column('Entered By', width=120)
        
        for col in tree['columns']:
            tree.heading(col, text=col)
        
        self.load_expense_vouchers(parent, '', 'All', tree)
        tree.pack(fill='both', expand=True)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side='right', fill='y')
        hsb.pack(side='bottom', fill='x')
    
    def create_income_voucher_view(self, parent):
        """Create Income Voucher Management View"""
        # Header with buttons
        header = ttk.Frame(parent)
        header.pack(fill='x', padx=20, pady=15)
        
        title = ttk.Label(header, text="📥 INCOME VOUCHERS", 
                         font=('Segoe UI', 14, 'bold'), foreground=self.colors['primary'])
        title.pack(side='left')
        
        ttk.Button(header, text="➕ New Income Voucher", 
                  command=self.open_income_voucher_form).pack(side='right', padx=5)
        
        # Filter and search
        filter_frame = ttk.Frame(parent)
        filter_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Label(filter_frame, text="Source:").pack(side='left', padx=5)
        source_var = tk.StringVar()
        source_combo = ttk.Combobox(filter_frame, textvariable=source_var, width=20)
        self._load_sources_combo(source_combo)
        source_combo.pack(side='left', padx=(0, 20))
        
        ttk.Label(filter_frame, text="Status:").pack(side='left', padx=5)
        status_var = tk.StringVar()
        status_combo = ttk.Combobox(filter_frame, textvariable=status_var, 
                                   values=['All', 'Pending', 'Approved', 'Rejected', 'Reversed'],
                                   width=15)
        status_combo.set('All')
        status_combo.pack(side='left', padx=(0, 20))
        
        ttk.Button(filter_frame, text="🔍 Filter", 
                  command=lambda: self.load_income_vouchers(parent, source_var.get(), status_var.get())).pack(side='left')
        
        # Treeview for vouchers
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        tree = ttk.Treeview(tree_frame,
                           columns=('Voucher No', 'Date', 'Source', 'Client', 'Amount', 'Status'),
                           height=15, show='headings')
        
        tree.column('Voucher No', width=120)
        tree.column('Date', width=100)
        tree.column('Source', width=130)
        tree.column('Client', width=120)
        tree.column('Amount', width=120)
        tree.column('Status', width=100)
        
        for col in tree['columns']:
            tree.heading(col, text=col)
        
        self.load_income_vouchers(parent, '', 'All', tree)
        tree.pack(fill='both', expand=True)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side='right', fill='y')
        hsb.pack(side='bottom', fill='x')
    
    def create_daily_closing_view(self, parent):
        """Create Daily Closing System"""
        header = ttk.Frame(parent)
        header.pack(fill='x', padx=20, pady=15)
        
        title = ttk.Label(header, text="🔒 DAILY CLOSING SYSTEM", 
                         font=('Segoe UI', 14, 'bold'), foreground=self.colors['primary'])
        title.pack(side='left')
        
        ttk.Button(header, text="➕ Close Today", command=self.open_daily_closing_form).pack(side='right', padx=5)
        
        # Closing history
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        tree = ttk.Treeview(tree_frame,
                           columns=('Date', 'Income', 'Expense', 'Profit', 'Cash', 'Bank', 'Status'),
                           height=15, show='headings')
        
        tree.column('Date', width=100)
        tree.column('Income', width=120)
        tree.column('Expense', width=120)
        tree.column('Profit', width=120)
        tree.column('Cash', width=120)
        tree.column('Bank', width=120)
        tree.column('Status', width=100)
        
        for col in tree['columns']:
            tree.heading(col, text=col)
        
        # Load closing history
        result = FinancialDatabase.execute(
            "SELECT * FROM daily_closings ORDER BY closing_date DESC LIMIT 30",
            fetch=True
        )
        
        if result:
            for row in result:
                status = "🔒 Locked" if row['is_locked'] else "⏳ Open"
                tree.insert('', 'end', values=(
                    row['closing_date'],
                    self.format_currency(row['total_income']),
                    self.format_currency(row['total_expense']),
                    self.format_currency(row['net_profit']),
                    self.format_currency(row['cash_in_hand']),
                    self.format_currency(row['bank_balance']),
                    status
                ))
        
        tree.pack(fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        scrollbar.pack(side='right', fill='y')
        tree.config(yscrollcommand=scrollbar.set)
    
    def create_reports_view(self, parent):
        """Create Reports & Analytics View"""
        header = ttk.Frame(parent)
        header.pack(fill='x', padx=20, pady=15)
        
        title = ttk.Label(header, text="📈 FINANCIAL REPORTS & ANALYTICS", 
                         font=('Segoe UI', 14, 'bold'), foreground=self.colors['primary'])
        title.pack(side='left')
        
        # Report buttons
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Button(btn_frame, text="📊 P&L Statement", command=self.generate_pl_report).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="💰 Monthly Summary", command=self.generate_monthly_report).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="📋 Category Analysis", command=self.generate_category_report).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="💳 Cash Flow", command=self.generate_cashflow_report).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="📤 Export to Excel", command=self.export_reports).pack(side='left', padx=5)
        
        # Report display area
        report_frame = ttk.LabelFrame(parent, text="Report Content", padding=10)
        report_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        self.report_text = scrolledtext.ScrolledText(report_frame, height=20, width=100)
        self.report_text.pack(fill='both', expand=True)
    
    def create_settings_view(self, parent):
        """Create Financial Settings"""
        header = ttk.Frame(parent)
        header.pack(fill='x', padx=20, pady=15)
        
        title = ttk.Label(header, text="⚙️ FINANCIAL SETTINGS", 
                         font=('Segoe UI', 14, 'bold'), foreground=self.colors['primary'])
        title.pack(side='left')
        
        # Create notebook for settings tabs
        settings_notebook = ttk.Notebook(parent)
        settings_notebook.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Expense Categories tab
        cat_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(cat_frame, text="📋 Expense Categories")
        self.create_categories_settings(cat_frame)
        
        # Income Sources tab
        src_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(src_frame, text="💵 Income Sources")
        self.create_sources_settings(src_frame)
        
        # Access Control tab
        access_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(access_frame, text="👥 Access Control")
        self.create_access_control_view(access_frame)
    
    def create_categories_settings(self, parent):
        """Manage expense categories"""
        header = ttk.Frame(parent)
        header.pack(fill='x', padx=15, pady=10)
        
        ttk.Button(header, text="➕ Add Category", command=self.add_expense_category).pack(side='left')
        ttk.Button(header, text="🗑️ Delete Category", command=self.delete_expense_category).pack(side='left', padx=5)
        
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill='both', expand=True, padx=15, pady=10)
        
        tree = ttk.Treeview(tree_frame,
                           columns=('Name', 'Type', 'Account Code', 'Status'),
                           height=12, show='headings')
        
        tree.column('Name', width=200)
        tree.column('Type', width=150)
        tree.column('Account Code', width=150)
        tree.column('Status', width=100)
        
        for col in tree['columns']:
            tree.heading(col, text=col)
        
        # Load categories
        result = FinancialDatabase.execute(
            "SELECT * FROM expense_categories ORDER BY category_name",
            fetch=True
        )
        
        if result:
            for row in result:
                status = "✓ Active" if row['is_active'] else "✗ Inactive"
                tree.insert('', 'end', values=(
                    row['category_name'],
                    row['category_type'],
                    row['account_code'],
                    status
                ))
        
        tree.pack(fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        scrollbar.pack(side='right', fill='y')
        tree.config(yscrollcommand=scrollbar.set)
    
    def create_sources_settings(self, parent):
        """Manage income sources"""
        header = ttk.Frame(parent)
        header.pack(fill='x', padx=15, pady=10)
        
        ttk.Button(header, text="➕ Add Source", command=self.add_income_source).pack(side='left')
        ttk.Button(header, text="🗑️ Delete Source", command=self.delete_income_source).pack(side='left', padx=5)
        
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill='both', expand=True, padx=15, pady=10)
        
        tree = ttk.Treeview(tree_frame,
                           columns=('Name', 'Account Code', 'Status'),
                           height=12, show='headings')
        
        tree.column('Name', width=250)
        tree.column('Account Code', width=150)
        tree.column('Status', width=150)
        
        for col in tree['columns']:
            tree.heading(col, text=col)
        
        # Load sources
        result = FinancialDatabase.execute(
            "SELECT * FROM income_sources ORDER BY source_name",
            fetch=True
        )
        
        if result:
            for row in result:
                status = "✓ Active" if row['is_active'] else "✗ Inactive"
                tree.insert('', 'end', values=(
                    row['source_name'],
                    row['account_code'],
                    status
                ))
        
        tree.pack(fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        scrollbar.pack(side='right', fill='y')
        tree.config(yscrollcommand=scrollbar.set)
    
    def create_access_control_view(self, parent):
        """Role-Based Access Control Information"""
        ttk.Label(parent, text="👥 ROLE-BASED ACCESS CONTROL MATRIX",
                 font=('Segoe UI', 12, 'bold')).pack(padx=20, pady=15)
        
        info_text = scrolledtext.ScrolledText(parent, height=20, width=100)
        info_text.pack(fill='both', expand=True, padx=20, pady=10)
        
        info_content = """
╔════════════════════════════════════════════════════════════════════════════╗
║              ENTERPRISE ROLE-BASED ACCESS CONTROL MATRIX                  ║
╚════════════════════════════════════════════════════════════════════════════╝

ROLE DEFINITIONS:
─────────────────────────────────────────────────────────────────────────────

1. SUPER ADMIN (Full Authority)
   ✓ Full Access to all modules
   ✓ Create/modify/delete users and roles
   ✓ Approve/reject all vouchers
   ✓ Lock/unlock days
   ✓ View all reports and sensitive data
   ✓ Access complete audit logs
   ✓ System backups and maintenance

2. FINANCE ADMIN (Financial Management)
   ✓ Create expense/income vouchers
   ✓ Approve/reject vouchers
   ✓ View all financial reports
   ✓ Generate P&L statements
   ✓ Perform daily closing
   ✓ Access category and source management
   ✗ Cannot delete users
   ✗ Cannot access system settings

3. MANAGER (Limited Authority)
   ✓ Create voucher entries
   ✓ View limited financial reports
   ✓ View department expenses
   ✓ Export department reports
   ✗ Cannot approve vouchers
   ✗ Cannot perform daily closing
   ✗ Cannot view sensitive financial data

4. STAFF (Entry Level)
   ✓ Create voucher entries only
   ✓ View own submitted vouchers
   ✓ View transaction history
   ✗ Cannot approve
   ✗ Cannot edit submitted vouchers
   ✗ Cannot view financial reports

5. VIEWER (Read-Only)
   ✓ View non-sensitive reports
   ✓ View public transaction history
   ✓ View summary dashboards
   ✗ Cannot create any entries
   ✗ Cannot approve
   ✗ Cannot modify any data

PERMISSION MATRIX BY MODULE:
─────────────────────────────────────────────────────────────────────────────
Module                  Super Admin  Finance Admin  Manager  Staff  Viewer
─────────────────────────────────────────────────────────────────────────────
Expense Vouchers            ✓             ✓           ✓        ✓      ✗
Income Vouchers             ✓             ✓           ✓        ✓      ✗
Approval Workflow           ✓             ✓           ✗        ✗      ✗
Daily Closing               ✓             ✓           ✗        ✗      ✗
Financial Dashboard         ✓             ✓           ✓        ✗      △
Profit & Loss Statement     ✓             ✓           △        ✗      ✗
Category Management         ✓             ✓           ✗        ✗      ✗
User Management             ✓             ✗           ✗        ✗      ✗
Audit Trail Access          ✓             △           ✗        ✗      ✗

Note: 
✓ = Full Access
△ = Limited/Summary Access
✗ = No Access

BUSINESS RULES FOR FINANCIAL SECURITY:
─────────────────────────────────────────────────────────────────────────────

1. Voucher Approval Workflow:
   - Staff creates vouchers → Marked as "Pending"
   - Finance Admin reviews and approves
   - Only "Approved" vouchers affect reports
   - Approval requires justification for rejection

2. Daily Closing Lock:
   - Once day is closed, no more vouchers can be added
   - Only reversal entries allowed after lock
   - Lock is permanent (cannot be reversed without audit trail)
   - Only Finance Admin can perform daily closing

3. Audit Trail Requirements:
   - All transactions logged with user, timestamp, and action
   - Old and new values recorded for modifications
   - Soft deletes required (never permanently delete)
   - IP address and user agent captured

4. Data Integrity:
   - Foreign key relationships enforced
   - Normalized database schema
   - Account codes for GL integration
   - Automatic totals calculation

5. Reporting Security:
   - Sensitive reports visible only to authorized roles
   - Profit/Loss hidden from Staff and Viewer roles
   - Export restricted based on user role
   - Report generation logged

═════════════════════════════════════════════════════════════════════════════
"""
        
        info_text.insert('1.0', info_content)
        info_text.config(state='disabled')
    
    # ───────────────────────────────────────────────────────────────────────────
    # FORM DIALOGS
    # ───────────────────────────────────────────────────────────────────────────
    
    def open_expense_voucher_form(self):
        """Open expense voucher creation form"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("➕ New Expense Voucher")
        dialog.geometry("700x750")
        dialog.resizable(False, False)
        
        form = ttk.Frame(dialog, padding=25)
        form.pack(fill='both', expand=True)
        
        # Auto-generate voucher number
        voucher_no = f"EXP-{datetime.now().strftime('%Y')}-{self._get_next_voucher_no('EXP'):04d}"
        
        fields = [
            ("Voucher No:", "voucher_no", "entry_readonly", voucher_no),
            ("Date:", "voucher_date", "entry", datetime.now().strftime("%Y-%m-%d")),
            ("Category:", "category_id", "combo", ""),
            ("Vendor Name:", "vendor_name", "entry", ""),
            ("Amount:", "amount", "entry", ""),
            ("Payment Method:", "payment_method", "combo", ""),
            ("Reference/Invoice No:", "reference_no", "entry", ""),
            ("Description:", "description", "text", ""),
            ("Remarks:", "remarks", "text", ""),
        ]
        
        entries = {}
        row = 0
        
        for label, key, ftype, default in fields:
            ttk.Label(form, text=label, font=('Segoe UI', 10)).grid(row=row, column=0, sticky='nw', pady=12)
            
            if ftype == "entry":
                entry = ttk.Entry(form, width=40, font=('Segoe UI', 10))
                if default:
                    entry.insert(0, default)
                entry.grid(row=row, column=1, sticky='ew', pady=12, padx=10)
            
            elif ftype == "entry_readonly":
                entry = ttk.Entry(form, width=40, font=('Segoe UI', 10), state='readonly')
                entry.insert(0, default)
                entry.grid(row=row, column=1, sticky='ew', pady=12, padx=10)
            
            elif ftype == "combo":
                if key == "category_id":
                    entry = ttk.Combobox(form, width=37, font=('Segoe UI', 10))
                    self._load_categories_combo(entry)
                elif key == "payment_method":
                    entry = ttk.Combobox(form, values=[m.value for m in PaymentMethod],
                                       width=37, font=('Segoe UI', 10))
                entry.grid(row=row, column=1, sticky='ew', pady=12, padx=10)
            
            elif ftype == "text":
                entry = tk.Text(form, height=3, width=40, font=('Segoe UI', 10))
                entry.grid(row=row, column=1, sticky='ew', pady=12, padx=10)
            
            entries[key] = entry
            row += 1
        
        # Button frame
        btn_frame = ttk.Frame(form)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=25)
        
        def save_voucher():
            if not all([entries['voucher_date'].get(), entries['category_id'].get(), entries['amount'].get()]):
                messagebox.showwarning("Incomplete", "Please fill all required fields!")
                return
            
            try:
                amount = float(entries['amount'].get())
                FinancialDatabase.execute(
                    """INSERT INTO expense_vouchers 
                       (voucher_no, voucher_date, category_id, vendor_name, amount, 
                        payment_method, reference_no, description, remarks, entered_by, status)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (entries['voucher_no'].get(), entries['voucher_date'].get(),
                     self._get_category_id(entries['category_id'].get()),
                     entries['vendor_name'].get(), amount,
                     entries['payment_method'].get(), entries['reference_no'].get(),
                     entries['description'].get('1.0', 'end-1c'), 
                     entries['remarks'].get('1.0', 'end-1c') if isinstance(entries['remarks'], tk.Text) else entries['remarks'].get(),
                     1, 'Pending')
                )
                messagebox.showinfo("✅ Success", f"Expense voucher {entries['voucher_no'].get()} created!\n\nStatus: PENDING APPROVAL")
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Amount must be a valid number!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {str(e)}")
        
        ttk.Button(btn_frame, text="💾 Save", command=save_voucher).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="❌ Cancel", command=dialog.destroy).pack(side='left', padx=10)
    
    def open_income_voucher_form(self):
        """Open income voucher creation form"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("➕ New Income Voucher")
        dialog.geometry("700x700")
        dialog.resizable(False, False)
        
        form = ttk.Frame(dialog, padding=25)
        form.pack(fill='both', expand=True)
        
        # Auto-generate voucher number
        voucher_no = f"INC-{datetime.now().strftime('%Y')}-{self._get_next_voucher_no('INC'):04d}"
        
        fields = [
            ("Voucher No:", "voucher_no", "entry_readonly", voucher_no),
            ("Date:", "voucher_date", "entry", datetime.now().strftime("%Y-%m-%d")),
            ("Income Source:", "income_source_id", "combo", ""),
            ("Client Name:", "client_name", "entry", ""),
            ("Invoice No:", "invoice_no", "entry", ""),
            ("Amount:", "amount", "entry", ""),
            ("Payment Method:", "payment_method", "combo", ""),
            ("Description:", "description", "text", ""),
            ("Remarks:", "remarks", "text", ""),
        ]
        
        entries = {}
        row = 0
        
        for label, key, ftype, default in fields:
            ttk.Label(form, text=label, font=('Segoe UI', 10)).grid(row=row, column=0, sticky='nw', pady=12)
            
            if ftype == "entry":
                entry = ttk.Entry(form, width=40, font=('Segoe UI', 10))
                if default:
                    entry.insert(0, default)
                entry.grid(row=row, column=1, sticky='ew', pady=12, padx=10)
            
            elif ftype == "entry_readonly":
                entry = ttk.Entry(form, width=40, font=('Segoe UI', 10), state='readonly')
                entry.insert(0, default)
                entry.grid(row=row, column=1, sticky='ew', pady=12, padx=10)
            
            elif ftype == "combo":
                if key == "income_source_id":
                    entry = ttk.Combobox(form, width=37, font=('Segoe UI', 10))
                    self._load_sources_combo(entry)
                elif key == "payment_method":
                    entry = ttk.Combobox(form, values=[m.value for m in PaymentMethod],
                                       width=37, font=('Segoe UI', 10))
                entry.grid(row=row, column=1, sticky='ew', pady=12, padx=10)
            
            elif ftype == "text":
                entry = tk.Text(form, height=3, width=40, font=('Segoe UI', 10))
                entry.grid(row=row, column=1, sticky='ew', pady=12, padx=10)
            
            entries[key] = entry
            row += 1
        
        # Button frame
        btn_frame = ttk.Frame(form)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=25)
        
        def save_voucher():
            if not all([entries['voucher_date'].get(), entries['income_source_id'].get(), entries['amount'].get()]):
                messagebox.showwarning("Incomplete", "Please fill all required fields!")
                return
            
            try:
                amount = float(entries['amount'].get())
                FinancialDatabase.execute(
                    """INSERT INTO income_vouchers 
                       (voucher_no, voucher_date, income_source_id, client_name, invoice_no, 
                        amount, payment_method, description, remarks, received_by, status)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (entries['voucher_no'].get(), entries['voucher_date'].get(),
                     self._get_source_id(entries['income_source_id'].get()),
                     entries['client_name'].get(), entries['invoice_no'].get(),
                     amount, entries['payment_method'].get(),
                     entries['description'].get('1.0', 'end-1c'),
                     entries['remarks'].get('1.0', 'end-1c') if isinstance(entries['remarks'], tk.Text) else entries['remarks'].get(),
                     1, 'Pending')
                )
                messagebox.showinfo("✅ Success", f"Income voucher {entries['voucher_no'].get()} created!\n\nStatus: PENDING APPROVAL")
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Amount must be a valid number!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {str(e)}")
        
        ttk.Button(btn_frame, text="💾 Save", command=save_voucher).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="❌ Cancel", command=dialog.destroy).pack(side='left', padx=10)
    
    def open_daily_closing_form(self):
        """Open daily closing form"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("🔒 Daily Closing")
        dialog.geometry("600x600")
        dialog.resizable(False, False)
        
        form = ttk.Frame(dialog, padding=25)
        form.pack(fill='both', expand=True)
        
        closing_date = datetime.now().strftime("%Y-%m-%d")
        
        # Get today's totals
        income_total = self._get_total_income(closing_date, closing_date)
        expense_total = self._get_total_expense(closing_date, closing_date)
        profit = income_total - expense_total
        
        # Display summary
        summary_text = f"""
╔════════════════════════════════════════════════════════════════╗
║          DAILY CLOSING SUMMARY - {closing_date}           ║
╚════════════════════════════════════════════════════════════════╝

Total Approved Income:  {self.format_currency(income_total)}
Total Approved Expense: {self.format_currency(expense_total)}
───────────────────────────────────────────────────────────────
Net Profit/Loss:        {self.format_currency(profit)}

⚠️  IMPORTANT: After closing this day:
    • No new vouchers can be added
    • Only reversal entries allowed
    • Day will be permanently locked
    • Only Finance Admin can close days
        """
        
        summary_label = tk.Label(form, text=summary_text, font=('Courier', 10),
                                justify='left', bg=self.colors['light'],
                                relief='solid', bd=1, padx=15, pady=15)
        summary_label.pack(fill='x', pady=15)
        
        # Input fields
        ttk.Label(form, text="Cash in Hand:", font=('Segoe UI', 10)).pack(pady=10)
        cash_entry = ttk.Entry(form, width=40, font=('Segoe UI', 10))
        cash_entry.pack(pady=5)
        cash_entry.insert(0, str(income_total - expense_total))
        
        ttk.Label(form, text="Bank Balance:", font=('Segoe UI', 10)).pack(pady=10)
        bank_entry = ttk.Entry(form, width=40, font=('Segoe UI', 10))
        bank_entry.pack(pady=5)
        
        ttk.Label(form, text="Closing Notes:", font=('Segoe UI', 10)).pack(pady=10)
        notes = tk.Text(form, height=4, width=50, font=('Segoe UI', 10))
        notes.pack(pady=5, fill='both', expand=True)
        
        # Button frame
        btn_frame = ttk.Frame(form)
        btn_frame.pack(fill='x', pady=25)
        
        def save_closing():
            try:
                FinancialDatabase.execute(
                    """INSERT INTO daily_closings 
                       (closing_date, total_income, total_expense, cash_in_hand, 
                        bank_balance, net_profit, closing_notes, closed_by, is_locked)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (closing_date, income_total, expense_total, float(cash_entry.get()) or 0,
                     float(bank_entry.get()) or 0, profit, notes.get('1.0', 'end-1c'), 1, 1)
                )
                messagebox.showinfo("✅ Success", f"Daily closing completed for {closing_date}!\n\n✓ All vouchers locked\n✓ No new entries allowed")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to close day: {str(e)}")
        
        ttk.Button(btn_frame, text="🔒 Close & Lock", command=save_closing).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="❌ Cancel", command=dialog.destroy).pack(side='left', padx=10)
    
    # ───────────────────────────────────────────────────────────────────────────
    # REPORT GENERATION
    # ───────────────────────────────────────────────────────────────────────────
    
    def generate_pl_report(self):
        """Generate Profit & Loss Statement"""
        report = f"""
╔════════════════════════════════════════════════════════════════════════════╗
║                    PROFIT & LOSS STATEMENT                                 ║
║                         {datetime.now().strftime("%B %Y")}                 ║
╚════════════════════════════════════════════════════════════════════════════╝

Generated: {datetime.now().strftime("%d %B %Y at %H:%M")}
Report Type: Accounting Standard Format

REVENUE SECTION
───────────────────────────────────────────────────────────────────────────────
"""
        
        result = FinancialDatabase.execute(
            """SELECT income_sources.source_name, SUM(income_vouchers.amount) as total
               FROM income_vouchers
               JOIN income_sources ON income_vouchers.income_source_id = income_sources.id
               WHERE income_vouchers.status = 'Approved'
               GROUP BY income_sources.source_name
               ORDER BY total DESC""",
            fetch=True
        )
        
        total_income = 0
        if result:
            for row in result:
                amount = row['total'] or 0
                total_income += amount
                report += f"{row['source_name']:<60} {self.format_currency(amount):>20}\n"
        
        report += f"\n{'TOTAL REVENUE':<60} {self.format_currency(total_income):>20}\n"
        
        report += """
EXPENSES SECTION
───────────────────────────────────────────────────────────────────────────────
"""
        
        result = FinancialDatabase.execute(
            """SELECT expense_categories.category_name, SUM(expense_vouchers.amount) as total
               FROM expense_vouchers
               JOIN expense_categories ON expense_vouchers.category_id = expense_categories.id
               WHERE expense_vouchers.status = 'Approved'
               GROUP BY expense_categories.category_name
               ORDER BY total DESC""",
            fetch=True
        )
        
        total_expense = 0
        if result:
            for row in result:
                amount = row['total'] or 0
                total_expense += amount
                report += f"{row['category_name']:<60} {self.format_currency(amount):>20}\n"
        
        report += f"\n{'TOTAL EXPENSES':<60} {self.format_currency(total_expense):>20}\n"
        
        net_profit = total_income - total_expense
        profit_margin = (net_profit / total_income * 100) if total_income > 0 else 0
        
        report += f"""
SUMMARY
───────────────────────────────────────────────────────────────────────────────
{'GROSS PROFIT':<60} {self.format_currency(net_profit):>20}
{'Profit Margin':<60} {profit_margin:>19.1f}%

═════════════════════════════════════════════════════════════════════════════
"""
        
        self.report_text.delete('1.0', 'end')
        self.report_text.insert('1.0', report)
    
    def generate_monthly_report(self):
        """Generate Monthly Financial Summary"""
        current_month = datetime.now().strftime("%Y-%m")
        
        report = f"""
╔════════════════════════════════════════════════════════════════════════════╗
║              MONTHLY FINANCIAL SUMMARY - {current_month}                  ║
╚════════════════════════════════════════════════════════════════════════════╝

Generated: {datetime.now().strftime("%d %B %Y at %H:%M")}

MONTHLY OVERVIEW
───────────────────────────────────────────────────────────────────────────────
"""
        
        income_total = self._get_total_income(f"{current_month}-01", 
                                             f"{current_month}-31")
        expense_total = self._get_total_expense(f"{current_month}-01",
                                              f"{current_month}-31")
        profit = income_total - expense_total
        margin = (profit / income_total * 100) if income_total > 0 else 0
        
        report += f"""
Total Income:         {self.format_currency(income_total)}
Total Expenses:       {self.format_currency(expense_total)}
────────────────────────────────────────────────────────────────────────
Net Profit/Loss:      {self.format_currency(profit)}
Profit Margin:        {margin:.1f}%

DAILY BREAKDOWN
───────────────────────────────────────────────────────────────────────────────
Date                 Income              Expense             Profit
───────────────────────────────────────────────────────────────────────────────
"""
        
        result = FinancialDatabase.execute(
            f"""SELECT closing_date, total_income, total_expense, net_profit
               FROM daily_closings
               WHERE closing_date LIKE '{current_month}%'
               ORDER BY closing_date""",
            fetch=True
        )
        
        if result:
            for row in result:
                report += f"{row['closing_date']}       {self.format_currency(row['total_income']):>18}  {self.format_currency(row['total_expense']):>18}  {self.format_currency(row['net_profit']):>18}\n"
        
        report += f"\n{'═' * 80}\n"
        
        self.report_text.delete('1.0', 'end')
        self.report_text.insert('1.0', report)
    
    def generate_category_report(self):
        """Generate Category-wise Analysis"""
        report = """
╔════════════════════════════════════════════════════════════════════════════╗
║                     CATEGORY-WISE ANALYSIS REPORT                          ║
╚════════════════════════════════════════════════════════════════════════════╝

Generated: """ + datetime.now().strftime("%d %B %Y at %H:%M") + """

EXPENSE CATEGORIES BREAKDOWN
───────────────────────────────────────────────────────────────────────────────
Category Name                    Type              Amount           % of Total
───────────────────────────────────────────────────────────────────────────────
"""
        
        result = FinancialDatabase.execute(
            """SELECT expense_categories.category_name, 
                      expense_categories.category_type,
                      SUM(expense_vouchers.amount) as total
               FROM expense_vouchers
               JOIN expense_categories ON expense_vouchers.category_id = expense_categories.id
               WHERE expense_vouchers.status = 'Approved'
               GROUP BY expense_categories.id
               ORDER BY total DESC""",
            fetch=True
        )
        
        total_expense = self._get_total_expense("", "")
        
        if result and total_expense > 0:
            for row in result:
                amount = row['total'] or 0
                percentage = (amount / total_expense * 100) if total_expense > 0 else 0
                report += f"{row['category_name']:<30} {row['category_type']:<15} {self.format_currency(amount):>18} {percentage:>9.1f}%\n"
        
        report += f"""
{'─' * 80}
{'TOTAL EXPENSES':<30} {self.format_currency(total_expense):>46}

INCOME SOURCES BREAKDOWN
───────────────────────────────────────────────────────────────────────────────
Source Name                           Amount           % of Total
───────────────────────────────────────────────────────────────────────────────
"""
        
        result = FinancialDatabase.execute(
            """SELECT income_sources.source_name,
                      SUM(income_vouchers.amount) as total
               FROM income_vouchers
               JOIN income_sources ON income_vouchers.income_source_id = income_sources.id
               WHERE income_vouchers.status = 'Approved'
               GROUP BY income_sources.id
               ORDER BY total DESC""",
            fetch=True
        )
        
        total_income = self._get_total_income("", "")
        
        if result and total_income > 0:
            for row in result:
                amount = row['total'] or 0
                percentage = (amount / total_income * 100) if total_income > 0 else 0
                report += f"{row['source_name']:<40} {self.format_currency(amount):>18} {percentage:>9.1f}%\n"
        
        report += f"""
{'─' * 80}
{'TOTAL INCOME':<40} {self.format_currency(total_income):>18}
"""
        
        self.report_text.delete('1.0', 'end')
        self.report_text.insert('1.0', report)
    
    def generate_cashflow_report(self):
        """Generate Cash Flow Report"""
        report = """
╔════════════════════════════════════════════════════════════════════════════╗
║                        CASH FLOW STATEMENT                                 ║
╚════════════════════════════════════════════════════════════════════════════╝

Generated: """ + datetime.now().strftime("%d %B %Y at %H:%M") + """

DAILY CASH INFLOW & OUTFLOW (Last 90 Days)
───────────────────────────────────────────────────────────────────────────────
Date            Inflow                Outflow              Net Flow
───────────────────────────────────────────────────────────────────────────────
"""
        
        result = FinancialDatabase.execute(
            """SELECT closing_date, total_income, total_expense, net_profit
               FROM daily_closings
               ORDER BY closing_date DESC LIMIT 90""",
            fetch=True
        )
        
        if result:
            for row in result:
                report += f"{row['closing_date']}     {self.format_currency(row['total_income']):>18}  {self.format_currency(row['total_expense']):>18}  {self.format_currency(row['net_profit']):>18}\n"
        
        report += f"""
{'─' * 80}

CASH FLOW ANALYSIS
───────────────────────────────────────────────────────────────────────────────
This report shows the movement of cash in and out of the organization.

Positive Net Flow: Cash inflow exceeded outflow (surplus)
Negative Net Flow: Cash outflow exceeded inflow (deficit)

═════════════════════════════════════════════════════════════════════════════
"""
        
        self.report_text.delete('1.0', 'end')
        self.report_text.insert('1.0', report)
    
    def export_reports(self):
        """Export current report to CSV"""
        report_content = self.report_text.get('1.0', 'end-1c')
        
        if not report_content.strip():
            messagebox.showwarning("Empty Report", "Please generate a report first!")
            return
        
        file_path = filedialog.asksaveasfilename(defaultextension=".csv",
                                                filetypes=[("CSV Files", "*.csv"), ("Text Files", "*.txt")])
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                messagebox.showinfo("✅ Export Success", f"Report exported to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed: {str(e)}")
    
    # ───────────────────────────────────────────────────────────────────────────
    # HELPER METHODS
    # ───────────────────────────────────────────────────────────────────────────
    
    def _get_total_income(self, from_date="", to_date=""):
        """Get total approved income"""
        if from_date and to_date:
            result = FinancialDatabase.execute(
                """SELECT SUM(amount) as total FROM income_vouchers 
                   WHERE status='Approved' AND voucher_date >= ? AND voucher_date <= ?""",
                (from_date, to_date), fetch=True
            )
        else:
            result = FinancialDatabase.execute(
                "SELECT SUM(amount) as total FROM income_vouchers WHERE status='Approved'",
                fetch=True
            )
        return result[0]['total'] or 0 if result else 0
    
    def _get_total_expense(self, from_date="", to_date=""):
        """Get total approved expenses"""
        if from_date and to_date:
            result = FinancialDatabase.execute(
                """SELECT SUM(amount) as total FROM expense_vouchers 
                   WHERE status='Approved' AND voucher_date >= ? AND voucher_date <= ?""",
                (from_date, to_date), fetch=True
            )
        else:
            result = FinancialDatabase.execute(
                "SELECT SUM(amount) as total FROM expense_vouchers WHERE status='Approved'",
                fetch=True
            )
        return result[0]['total'] or 0 if result else 0
    
    def _create_stat_card(self, parent, label, value, color, column):
        """Create a statistics card"""
        card = tk.Frame(parent, bg='white', relief='flat', bd=1)
        card.grid(row=0, column=column, padx=10, pady=10, sticky='ew')
        parent.grid_columnconfigure(column, weight=1)
        
        # Header bar
        header = tk.Frame(card, bg=color, height=4)
        header.pack(fill='x')
        
        # Content
        content = tk.Frame(card, bg='white', padx=15, pady=15)
        content.pack(fill='both', expand=True)
        
        label_widget = tk.Label(content, text=label, font=('Segoe UI', 10),
                              fg=self.colors['secondary'], bg='white')
        label_widget.pack()
        
        value_widget = tk.Label(content, text=value, font=('Segoe UI', 14, 'bold'),
                              fg=color, bg='white')
        value_widget.pack()
    
    def _load_categories_combo(self, combo):
        """Load expense categories into combobox"""
        result = FinancialDatabase.execute(
            "SELECT id, category_name FROM expense_categories WHERE is_active=1 ORDER BY category_name",
            fetch=True
        )
        
        if result:
            combo['values'] = [row['category_name'] for row in result]
    
    def _load_sources_combo(self, combo):
        """Load income sources into combobox"""
        result = FinancialDatabase.execute(
            "SELECT id, source_name FROM income_sources WHERE is_active=1 ORDER BY source_name",
            fetch=True
        )
        
        if result:
            combo['values'] = [row['source_name'] for row in result]
    
    def _get_category_id(self, category_name):
        """Get category ID from name"""
        result = FinancialDatabase.execute(
            "SELECT id FROM expense_categories WHERE category_name=?",
            (category_name,), fetch=True
        )
        return result[0]['id'] if result else 1
    
    def _get_source_id(self, source_name):
        """Get income source ID from name"""
        result = FinancialDatabase.execute(
            "SELECT id FROM income_sources WHERE source_name=?",
            (source_name,), fetch=True
        )
        return result[0]['id'] if result else 1
    
    def _get_next_voucher_no(self, prefix):
        """Get next voucher number"""
        current_year = datetime.now().strftime("%Y")
        result = FinancialDatabase.execute(
            f"""SELECT COUNT(*) as count FROM (
                SELECT id FROM expense_vouchers WHERE voucher_no LIKE '{prefix}-{current_year}-%' 
                UNION 
                SELECT id FROM income_vouchers WHERE voucher_no LIKE '{prefix}-{current_year}-%'
            )""",
            fetch=True
        )
        return (result[0]['count'] if result else 0) + 1
    
    def load_expense_vouchers(self, parent, category="", status="All", tree=None):
        """Load expense vouchers into treeview"""
        if tree is None:
            return
        
        # Clear existing items
        for item in tree.get_children():
            tree.delete(item)
        
        # Build query
        query = "SELECT * FROM expense_vouchers WHERE deleted_at IS NULL"
        params = []
        
        if category and category != "":
            query += " AND category_id = (SELECT id FROM expense_categories WHERE category_name=?)"
            params.append(category)
        
        if status != "All":
            query += " AND status=?"
            params.append(status)
        
        query += " ORDER BY voucher_date DESC"
        
        result = FinancialDatabase.execute(query, tuple(params), fetch=True)
        
        if result:
            for row in result:
                cat_result = FinancialDatabase.execute(
                    "SELECT category_name FROM expense_categories WHERE id=?",
                    (row['category_id'],), fetch=True
                )
                cat_name = cat_result[0]['category_name'] if cat_result else ""
                
                tree.insert('', 'end', values=(
                    row['voucher_no'],
                    row['voucher_date'],
                    cat_name,
                    self.format_currency(row['amount']),
                    row['status'],
                    row['entered_by']
                ))
    
    def load_income_vouchers(self, parent, source="", status="All", tree=None):
        """Load income vouchers into treeview"""
        if tree is None:
            return
        
        # Clear existing items
        for item in tree.get_children():
            tree.delete(item)
        
        # Build query
        query = "SELECT * FROM income_vouchers WHERE deleted_at IS NULL"
        params = []
        
        if source and source != "":
            query += " AND income_source_id = (SELECT id FROM income_sources WHERE source_name=?)"
            params.append(source)
        
        if status != "All":
            query += " AND status=?"
            params.append(status)
        
        query += " ORDER BY voucher_date DESC"
        
        result = FinancialDatabase.execute(query, tuple(params), fetch=True)
        
        if result:
            for row in result:
                src_result = FinancialDatabase.execute(
                    "SELECT source_name FROM income_sources WHERE id=?",
                    (row['income_source_id'],), fetch=True
                )
                src_name = src_result[0]['source_name'] if src_result else ""
                
                tree.insert('', 'end', values=(
                    row['voucher_no'],
                    row['voucher_date'],
                    src_name,
                    row['client_name'] or "",
                    self.format_currency(row['amount']),
                    row['status']
                ))
    
    def add_expense_category(self):
        """Add new expense category"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("➕ Add Expense Category")
        dialog.geometry("500x400")
        dialog.resizable(False, False)
        
        form = ttk.Frame(dialog, padding=20)
        form.pack(fill='both', expand=True)
        
        ttk.Label(form, text="Category Name:").grid(row=0, column=0, sticky='w', pady=10)
        name_entry = ttk.Entry(form, width=40)
        name_entry.grid(row=0, column=1, sticky='ew', pady=10)
        
        ttk.Label(form, text="Category Type:").grid(row=1, column=0, sticky='w', pady=10)
        type_combo = ttk.Combobox(form, values=[t.value for t in ExpenseType], width=37)
        type_combo.grid(row=1, column=1, sticky='ew', pady=10)
        
        ttk.Label(form, text="Account Code:").grid(row=2, column=0, sticky='w', pady=10)
        code_entry = ttk.Entry(form, width=40)
        code_entry.grid(row=2, column=1, sticky='ew', pady=10)
        
        ttk.Label(form, text="Description:").grid(row=3, column=0, sticky='nw', pady=10)
        desc_text = tk.Text(form, height=4, width=40)
        desc_text.grid(row=3, column=1, sticky='ew', pady=10)
        
        def save():
            if not name_entry.get() or not type_combo.get():
                messagebox.showwarning("Incomplete", "Fill required fields!")
                return
            
            FinancialDatabase.execute(
                """INSERT INTO expense_categories 
                   (category_name, category_type, account_code, description, is_active)
                   VALUES (?,?,?,?,?)""",
                (name_entry.get(), type_combo.get(), code_entry.get(),
                 desc_text.get('1.0', 'end-1c'), 1)
            )
            messagebox.showinfo("✅ Success", "Category added successfully!")
            dialog.destroy()
        
        ttk.Button(form, text="Save", command=save).grid(row=4, column=0, pady=20)
        ttk.Button(form, text="Cancel", command=dialog.destroy).grid(row=4, column=1)
    
    def delete_expense_category(self):
        messagebox.showinfo("Delete", "Select a category from the list and click delete")
    
    def add_income_source(self):
        """Add new income source"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("➕ Add Income Source")
        dialog.geometry("500x350")
        dialog.resizable(False, False)
        
        form = ttk.Frame(dialog, padding=20)
        form.pack(fill='both', expand=True)
        
        ttk.Label(form, text="Source Name:").grid(row=0, column=0, sticky='w', pady=10)
        name_entry = ttk.Entry(form, width=40)
        name_entry.grid(row=0, column=1, sticky='ew', pady=10)
        
        ttk.Label(form, text="Account Code:").grid(row=1, column=0, sticky='w', pady=10)
        code_entry = ttk.Entry(form, width=40)
        code_entry.grid(row=1, column=1, sticky='ew', pady=10)
        
        ttk.Label(form, text="Description:").grid(row=2, column=0, sticky='nw', pady=10)
        desc_text = tk.Text(form, height=3, width=40)
        desc_text.grid(row=2, column=1, sticky='ew', pady=10)
        
        def save():
            if not name_entry.get():
                messagebox.showwarning("Incomplete", "Enter source name!")
                return
            
            FinancialDatabase.execute(
                """INSERT INTO income_sources 
                   (source_name, account_code, description, is_active)
                   VALUES (?,?,?,?)""",
                (name_entry.get(), code_entry.get(), desc_text.get('1.0', 'end-1c'), 1)
            )
            messagebox.showinfo("✅ Success", "Income source added successfully!")
            dialog.destroy()
        
        ttk.Button(form, text="Save", command=save).grid(row=3, column=0, pady=20)
        ttk.Button(form, text="Cancel", command=dialog.destroy).grid(row=3, column=1)
    
    def delete_income_source(self):
        messagebox.showinfo("Delete", "Select a source from the list and click delete")
    
    def refresh_dashboard(self, from_date, to_date):
        """Refresh dashboard with new date range"""
        for widget in self.parent.winfo_children():
            if isinstance(widget, ttk.Notebook):
                dash_frame = widget.tabs()[0]
                for child in widget.winfo_children():
                    child.destroy()
                self.create_dashboard_view(self.parent)
                break
    
    def format_currency(self, amount):
        """Format amount as currency"""
        return f"{self.currency_symbol} {amount:,.2f}"


class FinancialManager:
    """Programmatic income/expense manager used by tests, docs, and legacy UI."""

    INCOME_CATEGORIES = {
        'rental_income': 'Primary Monthly Rent',
        'deposit_returned': 'Security Deposit Return',
        'late_payment_charge': 'Late Payment Penalty',
        'maintenance_charge': 'Tenant Maintenance Charge',
        'brokerage_commission': 'Brokerage Commission Earned',
        'service_charge': 'Additional Service Charges',
        'penalty_income': 'Other Penalties/Income',
        'other': 'Other Income',
    }
    EXPENSE_CATEGORIES = {
        'maintenance': 'Property Maintenance & Repairs',
        'utilities': 'Utilities',
        'property_tax': 'Property Taxes',
        'insurance': 'Insurance',
        'cleaning': 'Cleaning & Housekeeping',
        'marketing': 'Marketing & Advertising',
        'commissions': 'Employee Commissions',
        'staff_salary': 'Staff Salaries',
        'legal': 'Legal & Documentation Fees',
        'administration': 'Administrative & Office Costs',
        'other': 'Other Expenses',
    }

    def __init__(self, db_path="real_estate_crm.db"):
        self.db_path = db_path
        self._ensure_schema()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _table_columns(self, conn, table):
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in cur.fetchall()}

    def _ensure_column(self, conn, table, column, ddl):
        if column not in self._table_columns(conn, table):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")

    def _ensure_schema(self):
        conn = self._get_connection()
        try:
            conn.execute('''CREATE TABLE IF NOT EXISTS income_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_date TEXT NOT NULL,
                property_id INTEGER,
                income_type TEXT NOT NULL,
                amount REAL NOT NULL,
                tenant_name TEXT,
                description TEXT,
                receipt_no TEXT,
                payment_method TEXT DEFAULT 'Cash',
                recorded_by TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            conn.execute('''CREATE TABLE IF NOT EXISTS expense_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_date TEXT NOT NULL,
                property_id INTEGER,
                expense_category TEXT NOT NULL,
                amount REAL NOT NULL,
                vendor_name TEXT,
                description TEXT,
                invoice_no TEXT,
                payment_method TEXT DEFAULT 'Cash',
                approved_by TEXT,
                recorded_by TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            conn.execute('''CREATE TABLE IF NOT EXISTS financial_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT NOT NULL,
                year INTEGER NOT NULL,
                total_income REAL DEFAULT 0,
                total_expense REAL DEFAULT 0,
                net_profit REAL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(month, year)
            )''')
            for table in ("income_transactions", "expense_transactions"):
                self._ensure_column(conn, table, "payment_method", "TEXT DEFAULT 'Cash'")
                self._ensure_column(conn, table, "created_by", "TEXT")
                self._ensure_column(conn, table, "recorded_by", "TEXT")
                self._ensure_column(conn, table, "status", "TEXT")
            conn.commit()
        finally:
            conn.close()

    def _insert(self, table, data):
        conn = self._get_connection()
        try:
            columns = self._table_columns(conn, table)
            clean = {k: v for k, v in data.items() if k in columns}
            keys = list(clean.keys())
            placeholders = ", ".join("?" for _ in keys)
            sql = f"INSERT INTO {table} ({', '.join(keys)}) VALUES ({placeholders})"
            cur = conn.cursor()
            cur.execute(sql, tuple(clean[k] for k in keys))
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def record_income(self, transaction_date, amount, income_type='rental_income',
                      property_id=None, tenant_name=None, description=None,
                      receipt_no=None, payment_method='Cash', recorded_by=None,
                      created_by=None):
        if amount is None or float(amount) <= 0:
            raise ValueError("Income amount must be positive")
        if not income_type:
            income_type = 'other'
        return self._insert("income_transactions", {
            "transaction_date": transaction_date,
            "property_id": property_id,
            "income_type": income_type,
            "amount": float(amount),
            "tenant_name": tenant_name,
            "description": description,
            "receipt_no": receipt_no,
            "payment_method": payment_method,
            "recorded_by": recorded_by or created_by,
            "created_by": created_by or recorded_by,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

    def record_expense(self, transaction_date, amount, expense_category='other',
                       property_id=None, vendor_name=None, description=None,
                       invoice_no=None, payment_method='Cash', approved_by=None,
                       recorded_by=None, created_by=None):
        if amount is None or float(amount) <= 0:
            raise ValueError("Expense amount must be positive")
        if not expense_category:
            expense_category = 'other'
        return self._insert("expense_transactions", {
            "transaction_date": transaction_date,
            "property_id": property_id,
            "expense_category": expense_category,
            "amount": float(amount),
            "vendor_name": vendor_name,
            "description": description,
            "invoice_no": invoice_no,
            "payment_method": payment_method,
            "approved_by": approved_by,
            "recorded_by": recorded_by or created_by,
            "created_by": created_by or recorded_by,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

    def _sum_by_category(self, table, category_col, month=None, year=None,
                         start_date=None, end_date=None):
        conn = self._get_connection()
        try:
            where = []
            params = []
            if month and year:
                where.append("substr(transaction_date, 1, 7)=?")
                params.append(f"{int(year):04d}-{int(month):02d}")
            if start_date:
                where.append("transaction_date>=?")
                params.append(start_date)
            if end_date:
                where.append("transaction_date<=?")
                params.append(end_date)
            where_sql = " WHERE " + " AND ".join(where) if where else ""
            rows = conn.execute(
                f"""SELECT COALESCE(NULLIF({category_col}, ''), 'other') AS category,
                           SUM(COALESCE(amount, 0)) AS total
                    FROM {table}
                    {where_sql}
                    GROUP BY COALESCE(NULLIF({category_col}, ''), 'other')""",
                params,
            ).fetchall()
            return {row['category']: float(row['total'] or 0) for row in rows}
        finally:
            conn.close()

    def calculate_monthly_summary(self, month, year):
        income_breakdown = self._sum_by_category("income_transactions", "income_type", month, year)
        expense_breakdown = self._sum_by_category("expense_transactions", "expense_category", month, year)
        total_income = sum(income_breakdown.values())
        total_expense = sum(expense_breakdown.values())
        net_profit = total_income - total_expense

        conn = self._get_connection()
        try:
            conn.execute(
                """INSERT INTO financial_summary (month, year, total_income, total_expense, net_profit, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(month, year) DO UPDATE SET
                       total_income=excluded.total_income,
                       total_expense=excluded.total_expense,
                       net_profit=excluded.net_profit,
                       updated_at=excluded.updated_at""",
                (f"{int(month):02d}", int(year), total_income, total_expense,
                 net_profit, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            conn.commit()
        finally:
            conn.close()

        return {
            "month": int(month),
            "year": int(year),
            "total_income": total_income,
            "total_expense": total_expense,
            "net_profit": net_profit,
            "profit_margin": (net_profit / total_income * 100) if total_income else 0,
            "income_breakdown": income_breakdown,
            "expense_breakdown": expense_breakdown,
        }

    def get_profitability_report(self, start_date=None, end_date=None):
        income_breakdown = self._sum_by_category(
            "income_transactions", "income_type", start_date=start_date, end_date=end_date)
        expense_breakdown = self._sum_by_category(
            "expense_transactions", "expense_category", start_date=start_date, end_date=end_date)
        total_income = sum(income_breakdown.values())
        total_expense = sum(expense_breakdown.values())
        return {
            "from_date": start_date,
            "to_date": end_date,
            "total_income": total_income,
            "total_expense": total_expense,
            "net_profit": total_income - total_expense,
            "income_breakdown": income_breakdown,
            "expense_breakdown": expense_breakdown,
        }


if __name__ == "__main__":
    # Test the financial module
    root = tk.Tk()
    root.title("Financial Module Test")
    root.geometry("1400x900")
    
    fm = FinancialModule(root, currency_symbol='Rs.')
    root.mainloop()
