"""
Real Estate CRM - Data Import Module
Features: CSV Import for properties, employees, and transactions
"""

import sqlite3
import pandas as pd
import csv
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DataImporter:
    """Handle CSV imports for various CRM data"""
    
    def __init__(self, db_path="real_estate_crm.db"):
        self.db_path = db_path
    
    def _get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _log_import(self, import_type, file_name, total, successful, failed, status='completed'):
        """Log import activity"""
        conn = self._get_connection()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO data_imports 
            (import_type, file_name, total_records, successful_records, failed_records, 
             import_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (import_type, file_name, total, successful, failed, 
              datetime.now().strftime('%Y-%m-%d %H:%M:%S'), status))
        
        conn.commit()
        conn.close()

    def _columns(self, cursor, table):
        cursor.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in cursor.fetchall()}

    def _insert_dynamic(self, cursor, table, data):
        columns = self._columns(cursor, table)
        clean = {k: v for k, v in data.items() if k in columns}
        keys = list(clean.keys())
        placeholders = ", ".join("?" for _ in keys)
        cursor.execute(
            f"INSERT INTO {table} ({', '.join(keys)}) VALUES ({placeholders})",
            tuple(clean[k] for k in keys)
        )

    def _sync_legacy_fields(self):
        """Keep imported legacy CSV fields visible in the professional CRM UI."""
        conn = self._get_connection()
        c = conn.cursor()
        try:
            rr = self._columns(c, "rent_requirements")
            if {"date", "date_created"} <= rr:
                c.execute("UPDATE rent_requirements SET date=date_created WHERE (date IS NULL OR date='') AND date_created IS NOT NULL")
            if {"contact", "contact_phone"} <= rr:
                c.execute("UPDATE rent_requirements SET contact=contact_phone WHERE (contact IS NULL OR contact='') AND contact_phone IS NOT NULL")
            if {"property_requires", "property_type"} <= rr:
                c.execute("UPDATE rent_requirements SET property_requires=property_type WHERE (property_requires IS NULL OR property_requires='') AND property_type IS NOT NULL")
            if {"budget", "budget_max"} <= rr:
                c.execute("UPDATE rent_requirements SET budget=budget_max WHERE budget IS NULL AND budget_max IS NOT NULL")
            if {"size", "size_beds"} <= rr:
                c.execute("UPDATE rent_requirements SET size=CAST(size_beds AS TEXT) || '-bed' WHERE (size IS NULL OR size='') AND size_beds IS NOT NULL")
            if {"remarks", "description"} <= rr:
                c.execute("UPDATE rent_requirements SET remarks=description WHERE (remarks IS NULL OR remarks='') AND description IS NOT NULL")

            ra = self._columns(c, "rent_availability")
            if {"date", "date_posted"} <= ra:
                c.execute("UPDATE rent_availability SET date=date_posted WHERE (date IS NULL OR date='') AND date_posted IS NOT NULL")
            if {"contact", "contact_phone"} <= ra:
                c.execute("UPDATE rent_availability SET contact=contact_phone WHERE (contact IS NULL OR contact='') AND contact_phone IS NOT NULL")
            if {"property_availability", "property_type"} <= ra:
                c.execute("UPDATE rent_availability SET property_availability=property_type WHERE (property_availability IS NULL OR property_availability='') AND property_type IS NOT NULL")
            if {"size", "size_beds"} <= ra:
                c.execute("UPDATE rent_availability SET size=CAST(size_beds AS TEXT) || '-bed' WHERE (size IS NULL OR size='') AND size_beds IS NOT NULL")
            if {"remarks", "description"} <= ra:
                c.execute("UPDATE rent_availability SET remarks=description WHERE (remarks IS NULL OR remarks='') AND description IS NOT NULL")

            emp = self._columns(c, "employees")
            if {"phone", "contact_phone"} <= emp:
                c.execute("UPDATE employees SET phone=contact_phone WHERE (phone IS NULL OR phone='') AND contact_phone IS NOT NULL")
            conn.commit()
        finally:
            conn.close()
    
    # ═════════════════════════════════════════════════════════════════
    # RENT REQUIREMENTS IMPORT
    # ═════════════════════════════════════════════════════════════════
    
    def import_rent_requirements(self, csv_file_path):
        """
        Import rent requirements from CSV
        
        Expected CSV columns:
        - date_created, client_name, contact_phone, contact_email
        - property_type, size_beds, size_bath, sq_ft, floor_no
        - location, budget_min, budget_max, maintenance_budget
        - facilities, description, preferred_broker
        """
        successful = 0
        failed = 0
        errors = []
        
        try:
            df = pd.read_csv(csv_file_path)
            conn = self._get_connection()
            c = conn.cursor()
            
            for idx, row in df.iterrows():
                try:
                    date_value = row.get('date_created', datetime.now().strftime('%Y-%m-%d'))
                    property_type = row.get('property_type', None)
                    budget_max = float(row.get('budget_max', 0)) if pd.notna(row.get('budget_max')) else None
                    size_beds = int(row.get('size_beds', 0)) if pd.notna(row.get('size_beds')) else None
                    self._insert_dynamic(c, 'rent_requirements', {
                        'date_created': date_value,
                        'date': date_value,
                        'client_name': row.get('client_name', 'N/A'),
                        'contact_phone': row.get('contact_phone', None),
                        'contact': row.get('contact_phone', None),
                        'contact_email': row.get('contact_email', None),
                        'property_type': property_type,
                        'property_requires': property_type,
                        'size_beds': size_beds,
                        'size': f"{size_beds}-bed" if size_beds else None,
                        'size_bath': int(row.get('size_bath', 0)) if pd.notna(row.get('size_bath')) else None,
                        'sq_ft': float(row.get('sq_ft', 0)) if pd.notna(row.get('sq_ft')) else None,
                        'floor_no': int(row.get('floor_no', 0)) if pd.notna(row.get('floor_no')) else None,
                        'floor': row.get('floor_no', None),
                        'location': row.get('location', 'Unknown'),
                        'budget_min': float(row.get('budget_min', 0)) if pd.notna(row.get('budget_min')) else None,
                        'budget_max': budget_max,
                        'budget': budget_max,
                        'maintenance_budget': float(row.get('maintenance_budget', 0)) if pd.notna(row.get('maintenance_budget')) else None,
                        'facilities': row.get('facilities', None),
                        'description': row.get('description', None),
                        'remarks': row.get('description', None),
                        'preferred_broker': row.get('preferred_broker', None),
                        'client_status': 'Client',
                        'broker': row.get('preferred_broker', None),
                        'client_broker': row.get('preferred_broker', None),
                        'workflow_stage': 'Lead',
                        'priority': 'Medium',
                        'expected_close_value': budget_max or 0,
                    })
                    successful += 1
                except Exception as e:
                    failed += 1
                    errors.append(f"Row {idx+1}: {str(e)}")
            
            conn.commit()
            conn.close()
            self._sync_legacy_fields()
            
            self._log_import('rent_requirements', csv_file_path, len(df), successful, failed)
            
            result = {
                'status': 'success',
                'total': len(df),
                'successful': successful,
                'failed': failed,
                'errors': errors[:10]  # Return first 10 errors
            }
            
        except Exception as e:
            logger.error(f"Failed to import rent requirements: {str(e)}")
            self._log_import('rent_requirements', csv_file_path, 0, 0, 0, 'failed')
            result = {
                'status': 'error',
                'message': str(e)
            }
        
        return result
    
    # ═════════════════════════════════════════════════════════════════
    # RENT AVAILABILITY IMPORT
    # ═════════════════════════════════════════════════════════════════
    
    def import_rent_availability(self, csv_file_path):
        """
        Import rent availability from CSV
        
        Expected CSV columns:
        - date_posted, owner_name, contact_phone, contact_email
        - property_type, size_beds, size_bath, sq_ft, floor_no
        - location, monthly_rent, maintenance_charge
        - facilities, description, posted_by_broker
        """
        successful = 0
        failed = 0
        errors = []
        
        try:
            df = pd.read_csv(csv_file_path)
            conn = self._get_connection()
            c = conn.cursor()
            
            for idx, row in df.iterrows():
                try:
                    date_value = row.get('date_posted', datetime.now().strftime('%Y-%m-%d'))
                    property_type = row.get('property_type', None)
                    monthly_rent = float(row.get('monthly_rent', 0)) if pd.notna(row.get('monthly_rent')) else None
                    size_beds = int(row.get('size_beds', 0)) if pd.notna(row.get('size_beds')) else None
                    self._insert_dynamic(c, 'rent_availability', {
                        'date_posted': date_value,
                        'date': date_value,
                        'owner_name': row.get('owner_name', 'N/A'),
                        'contact_phone': row.get('contact_phone', None),
                        'contact': row.get('contact_phone', None),
                        'contact_email': row.get('contact_email', None),
                        'property_type': property_type,
                        'property_availability': property_type,
                        'size_beds': size_beds,
                        'size': f"{size_beds}-bed" if size_beds else None,
                        'size_bath': int(row.get('size_bath', 0)) if pd.notna(row.get('size_bath')) else None,
                        'sq_ft': float(row.get('sq_ft', 0)) if pd.notna(row.get('sq_ft')) else None,
                        'floor_no': int(row.get('floor_no', 0)) if pd.notna(row.get('floor_no')) else None,
                        'floor': row.get('floor_no', None),
                        'location': row.get('location', 'Unknown'),
                        'monthly_rent': monthly_rent,
                        'maintenance_charge': float(row.get('maintenance_charge', 0)) if pd.notna(row.get('maintenance_charge')) else None,
                        'facilities': row.get('facilities', None),
                        'description': row.get('description', None),
                        'remarks': row.get('description', None),
                        'posted_by_broker': row.get('posted_by_broker', None),
                        'posted_by': row.get('posted_by_broker', None),
                        'workflow_stage': 'Lead',
                        'priority': 'Medium',
                        'expected_close_value': monthly_rent or 0,
                    })
                    successful += 1
                except Exception as e:
                    failed += 1
                    errors.append(f"Row {idx+1}: {str(e)}")
            
            conn.commit()
            conn.close()
            self._sync_legacy_fields()
            
            self._log_import('rent_availability', csv_file_path, len(df), successful, failed)
            
            result = {
                'status': 'success',
                'total': len(df),
                'successful': successful,
                'failed': failed,
                'errors': errors[:10]
            }
            
        except Exception as e:
            logger.error(f"Failed to import rent availability: {str(e)}")
            self._log_import('rent_availability', csv_file_path, 0, 0, 0, 'failed')
            result = {
                'status': 'error',
                'message': str(e)
            }
        
        return result
    
    # ═════════════════════════════════════════════════════════════════
    # EMPLOYEE IMPORT
    # ═════════════════════════════════════════════════════════════════
    
    def import_employees(self, csv_file_path):
        """
        Import employees from CSV
        
        Expected CSV columns:
        - full_name, position, hire_date, base_salary
        - contact_phone, email, commission_rate (optional)
        """
        successful = 0
        failed = 0
        errors = []
        employee_ids = []
        
        try:
            df = pd.read_csv(csv_file_path)
            conn = self._get_connection()
            c = conn.cursor()
            
            for idx, row in df.iterrows():
                try:
                    employee_id = f"EMP{datetime.now().strftime('%Y%m%d')}{idx:04d}"
                    
                    contact_phone = row.get('contact_phone', None)
                    self._insert_dynamic(c, 'employees', {
                        'employee_id': employee_id,
                        'full_name': row.get('full_name', 'N/A'),
                        'position': row.get('position', 'N/A'),
                        'hire_date': row.get('hire_date', datetime.now().strftime('%Y-%m-%d')),
                        'base_salary': float(row.get('base_salary', 0)) if pd.notna(row.get('base_salary')) else 0,
                        'contact_phone': contact_phone,
                        'phone': contact_phone,
                        'email': row.get('email', None),
                        'commission_rate': float(row.get('commission_rate', 5.0)) if pd.notna(row.get('commission_rate')) else 5.0,
                        'status': 'active',
                        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    })
                    successful += 1
                    employee_ids.append(employee_id)
                except Exception as e:
                    failed += 1
                    errors.append(f"Row {idx+1}: {str(e)}")
            
            conn.commit()
            conn.close()
            self._sync_legacy_fields()
            
            self._log_import('employees', csv_file_path, len(df), successful, failed)
            
            result = {
                'status': 'success',
                'total': len(df),
                'successful': successful,
                'failed': failed,
                'employee_ids': employee_ids,
                'errors': errors[:10]
            }
            
        except Exception as e:
            logger.error(f"Failed to import employees: {str(e)}")
            self._log_import('employees', csv_file_path, 0, 0, 0, 'failed')
            result = {
                'status': 'error',
                'message': str(e)
            }
        
        return result
    
    # ═════════════════════════════════════════════════════════════════
    # INCOME TRANSACTIONS IMPORT
    # ═════════════════════════════════════════════════════════════════
    
    def import_income_transactions(self, csv_file_path):
        """
        Import income transactions from CSV
        
        Expected CSV columns:
        - transaction_date, property_id, income_type, amount
        - tenant_name, description, receipt_no (optional)
        """
        successful = 0
        failed = 0
        errors = []
        
        try:
            df = pd.read_csv(csv_file_path)
            conn = self._get_connection()
            c = conn.cursor()
            
            for idx, row in df.iterrows():
                try:
                    self._insert_dynamic(c, 'income_transactions', {
                        'transaction_date': row.get('transaction_date', datetime.now().strftime('%Y-%m-%d')),
                        'property_id': int(row.get('property_id', 0)) if pd.notna(row.get('property_id')) else None,
                        'income_type': row.get('income_type', 'other'),
                        'amount': float(row.get('amount', 0)) if pd.notna(row.get('amount')) else 0,
                        'tenant_name': row.get('tenant_name', None),
                        'description': row.get('description', None),
                        'receipt_no': row.get('receipt_no', None),
                        'payment_method': row.get('payment_method', 'Cash'),
                        'recorded_by': row.get('recorded_by', None),
                        'created_by': row.get('recorded_by', None),
                        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    })
                    successful += 1
                except Exception as e:
                    failed += 1
                    errors.append(f"Row {idx+1}: {str(e)}")
            
            conn.commit()
            conn.close()
            
            self._log_import('income_transactions', csv_file_path, len(df), successful, failed)
            
            result = {
                'status': 'success',
                'total': len(df),
                'successful': successful,
                'failed': failed,
                'errors': errors[:10]
            }
            
        except Exception as e:
            logger.error(f"Failed to import income transactions: {str(e)}")
            self._log_import('income_transactions', csv_file_path, 0, 0, 0, 'failed')
            result = {
                'status': 'error',
                'message': str(e)
            }
        
        return result
    
    # ═════════════════════════════════════════════════════════════════
    # EXPENSE TRANSACTIONS IMPORT
    # ═════════════════════════════════════════════════════════════════
    
    def import_expense_transactions(self, csv_file_path):
        """
        Import expense transactions from CSV
        
        Expected CSV columns:
        - transaction_date, property_id, expense_category, amount
        - vendor_name, description, invoice_no (optional)
        """
        successful = 0
        failed = 0
        errors = []
        
        try:
            df = pd.read_csv(csv_file_path)
            conn = self._get_connection()
            c = conn.cursor()
            
            for idx, row in df.iterrows():
                try:
                    self._insert_dynamic(c, 'expense_transactions', {
                        'transaction_date': row.get('transaction_date', datetime.now().strftime('%Y-%m-%d')),
                        'property_id': int(row.get('property_id', 0)) if pd.notna(row.get('property_id')) else None,
                        'expense_category': row.get('expense_category', 'other'),
                        'amount': float(row.get('amount', 0)) if pd.notna(row.get('amount')) else 0,
                        'vendor_name': row.get('vendor_name', None),
                        'description': row.get('description', None),
                        'invoice_no': row.get('invoice_no', None),
                        'payment_method': row.get('payment_method', 'Cash'),
                        'recorded_by': row.get('recorded_by', None),
                        'created_by': row.get('recorded_by', None),
                        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    })
                    successful += 1
                except Exception as e:
                    failed += 1
                    errors.append(f"Row {idx+1}: {str(e)}")
            
            conn.commit()
            conn.close()
            
            self._log_import('expense_transactions', csv_file_path, len(df), successful, failed)
            
            result = {
                'status': 'success',
                'total': len(df),
                'successful': successful,
                'failed': failed,
                'errors': errors[:10]
            }
            
        except Exception as e:
            logger.error(f"Failed to import expense transactions: {str(e)}")
            self._log_import('expense_transactions', csv_file_path, 0, 0, 0, 'failed')
            result = {
                'status': 'error',
                'message': str(e)
            }
        
        return result
    
    def get_import_history(self):
        """Get all import records"""
        conn = self._get_connection()
        df = pd.read_sql_query(
            "SELECT * FROM data_imports ORDER BY import_date DESC",
            conn
        )
        conn.close()
        return df


if __name__ == "__main__":
    importer = DataImporter()
    print("✅ Data Importer initialized!")
