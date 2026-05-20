"""
Real Estate CRM - Main Application
Comprehensive GUI for Real Estate Management System
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sys
import os
from datetime import datetime
import logging

# Import CRM modules
from database_setup import DatabaseSetup
from search_module import PropertyMatcher
from financial_module import FinancialManager
from employee_module import EmployeeManager
from data_import_module import DataImporter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RealEstateCRMApp:
    """Main CRM Application"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Real Estate CRM - Management System")
        self.root.geometry("1200x700")
        
        # Initialize database
        db_setup = DatabaseSetup()
        db_setup.init_database()
        
        # Initialize modules
        self.matcher = PropertyMatcher()
        self.financial = FinancialManager()
        self.employee = EmployeeManager()
        self.importer = DataImporter()
        
        # Configure style
        self.setup_styles()
        
        # Create main UI
        self.create_main_ui()
        
        logger.info("Application started")
    
    def setup_styles(self):
        """Configure application styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Define colors
        bg_color = '#f0f0f0'
        accent_color = '#2c3e50'
        
        style.configure('Title.TLabel', font=('Helvetica', 16, 'bold'), foreground=accent_color)
        style.configure('Header.TLabel', font=('Helvetica', 12, 'bold'), foreground=accent_color)
        style.configure('Normal.TLabel', font=('Helvetica', 10))
    
    def create_main_ui(self):
        """Create main application interface"""
        # Top banner
        banner = ttk.Frame(self.root)
        banner.pack(side='top', fill='x', padx=10, pady=10)
        
        title = ttk.Label(banner, text="🏢 Real Estate CRM System", style='Title.TLabel')
        title.pack(side='left')
        
        version = ttk.Label(banner, text="v1.0", style='Normal.TLabel')
        version.pack(side='right')
        
        # Separator
        separator = ttk.Separator(self.root, orient='horizontal')
        separator.pack(fill='x', padx=10)
        
        # Main content area with notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs for different modules
        self.create_rent_management_tab()
        self.create_financial_tab()
        self.create_employee_tab()
        self.create_data_import_tab()
        self.create_reports_tab()
        self.create_settings_tab()
    
    def create_rent_management_tab(self):
        """Rent Management Tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🏠 Rent Management")
        
        # Left panel - Input section
        left_frame = ttk.LabelFrame(frame, text="Add/Search Rent Requirements")
        left_frame.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        
        # Form fields
        ttk.Label(left_frame, text="Client Name:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        client_name = ttk.Entry(left_frame, width=30)
        client_name.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(left_frame, text="Location:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        location = ttk.Entry(left_frame, width=30)
        location.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(left_frame, text="Budget Min:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
        budget_min = ttk.Entry(left_frame, width=30)
        budget_min.grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Label(left_frame, text="Budget Max:").grid(row=3, column=0, sticky='w', padx=5, pady=5)
        budget_max = ttk.Entry(left_frame, width=30)
        budget_max.grid(row=3, column=1, padx=5, pady=5)
        
        ttk.Label(left_frame, text="Property Type:").grid(row=4, column=0, sticky='w', padx=5, pady=5)
        prop_type = ttk.Combobox(left_frame, values=['Apartment', 'House', 'Villa', 'Studio', 'Flat'], width=27)
        prop_type.grid(row=4, column=1, padx=5, pady=5)
        
        ttk.Label(left_frame, text="Bedrooms:").grid(row=5, column=0, sticky='w', padx=5, pady=5)
        bedrooms = ttk.Spinbox(left_frame, from_=0, to=10, width=28)
        bedrooms.grid(row=5, column=1, padx=5, pady=5)
        
        ttk.Label(left_frame, text="Contact Phone:").grid(row=6, column=0, sticky='w', padx=5, pady=5)
        contact = ttk.Entry(left_frame, width=30)
        contact.grid(row=6, column=1, padx=5, pady=5)
        
        ttk.Label(left_frame, text="Description:").grid(row=7, column=0, sticky='w', padx=5, pady=5)
        desc = tk.Text(left_frame, height=4, width=35)
        desc.grid(row=7, column=1, padx=5, pady=5)
        
        # Button frame
        btn_frame = ttk.Frame(left_frame)
        btn_frame.grid(row=8, column=0, columnspan=2, pady=10)
        
        def save_requirement():
            if not client_name.get() or not location.get():
                messagebox.showwarning("Input Error", "Please fill required fields!")
                return
            
            try:
                conn = DatabaseSetup().get_connection()
                c = conn.cursor()
                c.execute('''
                    INSERT INTO rent_requirements 
                    (date_created, client_name, location, contact_phone, property_type, 
                     size_beds, budget_min, budget_max, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().strftime('%Y-%m-%d'),
                    client_name.get(),
                    location.get(),
                    contact.get(),
                    prop_type.get(),
                    bedrooms.get(),
                    budget_min.get() or None,
                    budget_max.get() or None,
                    desc.get("1.0", "end-1c")
                ))
                conn.commit()
                req_id = c.lastrowid
                conn.close()
                
                messagebox.showinfo("Success", f"Requirement saved! ID: {req_id}")
                client_name.delete(0, 'end')
                location.delete(0, 'end')
                budget_min.delete(0, 'end')
                budget_max.delete(0, 'end')
                contact.delete(0, 'end')
                desc.delete("1.0", "end")
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
        ttk.Button(btn_frame, text="Save Requirement", command=save_requirement).pack(side='left', padx=5)
        
        # Right panel - Results
        right_frame = ttk.LabelFrame(frame, text="Available Properties")
        right_frame.pack(side='right', fill='both', expand=True, padx=10, pady=10)
        
        # Results treeview
        tree_cols = ('ID', 'Location', 'Rent', 'Beds', 'Match Score')
        tree = ttk.Treeview(right_frame, columns=tree_cols, height=20)
        tree.column('#0', width=50)
        tree.column('ID', width=50)
        tree.column('Location', width=100)
        tree.column('Rent', width=80)
        tree.column('Beds', width=50)
        tree.column('Match Score', width=80)
        
        for col in tree_cols:
            tree.heading(col, text=col)
        
        tree.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(right_frame, orient='vertical', command=tree.yview)
        scrollbar.pack(side='right', fill='y')
        tree.config(yscrollcommand=scrollbar.set)
    
    def create_financial_tab(self):
        """Financial Management Tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="💰 Financial")
        
        # Summary section
        summary_frame = ttk.LabelFrame(frame, text="Monthly Summary")
        summary_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(summary_frame, text="Month:").pack(side='left', padx=5, pady=5)
        month_var = tk.StringVar(value=str(datetime.now().month))
        month_spin = ttk.Spinbox(summary_frame, from_=1, to=12, textvariable=month_var, width=5)
        month_spin.pack(side='left', padx=5)
        
        ttk.Label(summary_frame, text="Year:").pack(side='left', padx=5, pady=5)
        year_var = tk.StringVar(value=str(datetime.now().year))
        year_spin = ttk.Spinbox(summary_frame, from_=2020, to=2030, textvariable=year_var, width=6)
        year_spin.pack(side='left', padx=5)
        
        # Info labels
        info_frame = ttk.Frame(frame)
        info_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        ttk.Label(info_frame, text="Total Income: $0", font=('Helvetica', 12, 'bold')).pack(fill='x', pady=5)
        ttk.Label(info_frame, text="Total Expenses: $0", font=('Helvetica', 12, 'bold')).pack(fill='x', pady=5)
        ttk.Label(info_frame, text="Net Profit: $0", font=('Helvetica', 12, 'bold')).pack(fill='x', pady=5)
        
        # Chart placeholder
        ttk.Label(info_frame, text="📊 Charts coming soon...", font=('Helvetica', 10)).pack(fill='x', pady=20)
    
    def create_employee_tab(self):
        """Employee Management Tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="👥 Employees")
        
        # Add Employee section
        add_frame = ttk.LabelFrame(frame, text="Add New Employee")
        add_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(add_frame, text="Full Name:").pack(side='left', padx=5, pady=5)
        name_entry = ttk.Entry(add_frame, width=20)
        name_entry.pack(side='left', padx=5)
        
        ttk.Label(add_frame, text="Position:").pack(side='left', padx=5, pady=5)
        position_entry = ttk.Entry(add_frame, width=20)
        position_entry.pack(side='left', padx=5)
        
        ttk.Label(add_frame, text="Salary:").pack(side='left', padx=5, pady=5)
        salary_entry = ttk.Entry(add_frame, width=15)
        salary_entry.pack(side='left', padx=5)
        
        def add_employee():
            try:
                emp_id = self.employee.add_employee(
                    full_name=name_entry.get(),
                    position=position_entry.get(),
                    hire_date=datetime.now().strftime('%Y-%m-%d'),
                    base_salary=float(salary_entry.get())
                )
                messagebox.showinfo("Success", f"Employee added! ID: {emp_id}")
                name_entry.delete(0, 'end')
                position_entry.delete(0, 'end')
                salary_entry.delete(0, 'end')
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
        ttk.Button(add_frame, text="Add Employee", command=add_employee).pack(side='left', padx=5)
        
        # Employee list
        list_frame = ttk.LabelFrame(frame, text="Employees")
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        tree_cols = ('ID', 'Name', 'Position', 'Salary', 'Status')
        tree = ttk.Treeview(list_frame, columns=tree_cols, height=15)
        tree.column('#0', width=50)
        
        for col in tree_cols:
            tree.column(col, width=100)
            tree.heading(col, text=col)
        
        tree.pack(fill='both', expand=True, padx=5, pady=5)
    
    def create_data_import_tab(self):
        """Data Import Tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📥 Data Import")
        
        ttk.Label(frame, text="Import Data from CSV", style='Header.TLabel').pack(padx=10, pady=10)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x', padx=10, pady=10)
        
        def import_file(import_type):
            file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
            if not file_path:
                return
            
            try:
                if import_type == 'rent_req':
                    result = self.importer.import_rent_requirements(file_path)
                elif import_type == 'rent_avail':
                    result = self.importer.import_rent_availability(file_path)
                elif import_type == 'employees':
                    result = self.importer.import_employees(file_path)
                elif import_type == 'income':
                    result = self.importer.import_income_transactions(file_path)
                elif import_type == 'expenses':
                    result = self.importer.import_expense_transactions(file_path)
                
                msg = f"Status: {result['status']}\nSuccessful: {result.get('successful', 0)}\nFailed: {result.get('failed', 0)}"
                messagebox.showinfo("Import Result", msg)
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
        ttk.Button(btn_frame, text="Import Rent Requirements", 
                  command=lambda: import_file('rent_req')).pack(pady=5, fill='x')
        ttk.Button(btn_frame, text="Import Rent Availability", 
                  command=lambda: import_file('rent_avail')).pack(pady=5, fill='x')
        ttk.Button(btn_frame, text="Import Employees", 
                  command=lambda: import_file('employees')).pack(pady=5, fill='x')
        ttk.Button(btn_frame, text="Import Income Transactions", 
                  command=lambda: import_file('income')).pack(pady=5, fill='x')
        ttk.Button(btn_frame, text="Import Expense Transactions", 
                  command=lambda: import_file('expenses')).pack(pady=5, fill='x')
    
    def create_reports_tab(self):
        """Reports Tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📊 Reports")
        
        ttk.Label(frame, text="Reports & Analytics", style='Header.TLabel').pack(padx=10, pady=10)
        ttk.Label(frame, text="✓ Financial Summary Reports").pack(pady=5)
        ttk.Label(frame, text="✓ Employee Performance Reports").pack(pady=5)
        ttk.Label(frame, text="✓ Property Match Analytics").pack(pady=5)
        ttk.Label(frame, text="✓ Income/Expense Breakdowns").pack(pady=5)
    
    def create_settings_tab(self):
        """Settings Tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="⚙️ Settings")
        
        ttk.Label(frame, text="Application Settings", style='Header.TLabel').pack(padx=10, pady=10)
        ttk.Label(frame, text="Database: real_estate_crm.db").pack(pady=5)
        ttk.Label(frame, text="Version: 1.0").pack(pady=5)
        ttk.Label(frame, text="Last Updated: " + datetime.now().strftime('%Y-%m-%d')).pack(pady=5)
        
        def backup_database():
            messagebox.showinfo("Backup", "Database backup feature coming soon!")
        
        ttk.Button(frame, text="Backup Database", command=backup_database).pack(pady=10)


def main():
    """Run the application"""
    root = tk.Tk()
    app = RealEstateCRMApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
