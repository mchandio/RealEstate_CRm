"""
Real Estate CRM - Employee Management Module
Features: Salary Management, Commission Tracking, Performance Records, Payroll
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from calendar import monthrange
import logging

logger = logging.getLogger(__name__)


class EmployeeManager:
    """Manage employee records, salaries, commissions, and performance"""
    
    def __init__(self, db_path="real_estate_crm.db"):
        self.db_path = db_path
    
    def _get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _table_columns(self, conn, table):
        c = conn.cursor()
        c.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in c.fetchall()}

    def _insert_row(self, conn, table, data):
        columns = self._table_columns(conn, table)
        clean = {k: v for k, v in data.items() if k in columns}
        keys = list(clean.keys())
        placeholders = ", ".join("?" for _ in keys)
        sql = f"INSERT INTO {table} ({', '.join(keys)}) VALUES ({placeholders})"
        cur = conn.cursor()
        cur.execute(sql, tuple(clean[k] for k in keys))
        return cur.lastrowid
    
    # ═════════════════════════════════════════════════════════════════
    # EMPLOYEE MANAGEMENT
    # ═════════════════════════════════════════════════════════════════
    
    def add_employee(self, full_name, position, hire_date, base_salary, 
                    contact_phone=None, email=None, commission_rate=5.0):
        """
        Add new employee
        
        Args:
            commission_rate: Default commission % on deals (5% default)
        """
        if base_salary <= 0:
            raise ValueError("Base salary must be positive")
        
        if commission_rate < 0 or commission_rate > 100:
            raise ValueError("Commission rate must be between 0-100%")
        
        conn = self._get_connection()
        c = conn.cursor()
        
        # Generate unique employee ID
        employee_id = f"EMP{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        self._insert_row(conn, "employees", {
            "employee_id": employee_id,
            "full_name": full_name,
            "position": position,
            "hire_date": hire_date,
            "base_salary": base_salary,
            "contact_phone": contact_phone,
            "phone": contact_phone,
            "email": email,
            "commission_rate": commission_rate,
            "status": "active",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        
        conn.commit()
        conn.close()
        
        logger.info(f"Employee added: {full_name} ({employee_id})")
        return employee_id
    
    def get_employee(self, employee_id):
        """Get employee details"""
        conn = self._get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM employees WHERE employee_id=?", (employee_id,))
        employee = c.fetchone()
        conn.close()
        return dict(employee) if employee else None
    
    def get_all_employees(self, status='active'):
        """Get all employees (active or all)"""
        conn = self._get_connection()
        
        if status:
            df = pd.read_sql_query(
                "SELECT * FROM employees WHERE lower(COALESCE(status,''))=?", 
                conn, 
                params=[status.lower()]
            )
        else:
            df = pd.read_sql_query("SELECT * FROM employees", conn)
        
        conn.close()
        return df
    
    def update_employee(self, employee_id, **kwargs):
        """Update employee information"""
        conn = self._get_connection()
        c = conn.cursor()
        
        allowed_fields = {'full_name', 'position', 'contact_phone', 'phone', 'email',
                         'base_salary', 'commission_rate', 'status'}
        
        for key in kwargs:
            if key not in allowed_fields:
                raise ValueError(f"Cannot update field: {key}")
        
        if 'base_salary' in kwargs and kwargs['base_salary'] <= 0:
            raise ValueError("Base salary must be positive")
        
        employee_cols = self._table_columns(conn, "employees")
        for field, value in kwargs.items():
            if field not in employee_cols:
                continue
            c.execute(f"UPDATE employees SET {field}=? WHERE employee_id=?",
                     (value, employee_id))
            if field == "contact_phone" and "phone" in employee_cols:
                c.execute("UPDATE employees SET phone=? WHERE employee_id=?", (value, employee_id))
        
        conn.commit()
        conn.close()
        logger.info(f"Employee {employee_id} updated")
    
    def deactivate_employee(self, employee_id, reason=None):
        """Deactivate employee (soft delete)"""
        self.update_employee(employee_id, status='inactive')
        logger.info(f"Employee {employee_id} deactivated. Reason: {reason}")
    
    # ═════════════════════════════════════════════════════════════════
    # COMMISSION MANAGEMENT
    # ═════════════════════════════════════════════════════════════════
    
    def record_commission(self, employee_id, commission_amount, deal_type=None, 
                         deal_id=None, deal_value=None, commission_date=None):
        """
        Record commission earned (on successful deal)
        
        Args:
            deal_type: 'rent' or 'sale'
            commission_date: Date earned (defaults to today)
        """
        if commission_amount <= 0:
            raise ValueError("Commission must be positive")
        
        if not commission_date:
            commission_date = datetime.now().strftime('%Y-%m-%d')
        
        conn = self._get_connection()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO employee_commissions 
            (employee_id, deal_type, deal_id, commission_amount, deal_value, 
             commission_date, status)
            VALUES (?, ?, ?, ?, ?, ?, 'earned')
        ''', (employee_id, deal_type, deal_id, commission_amount, deal_value, 
              commission_date))
        
        conn.commit()
        commission_id = c.lastrowid
        conn.close()
        
        logger.info(f"Commission recorded for {employee_id}: {commission_amount} on {commission_date}")
        return commission_id
    
    def get_employee_commissions(self, employee_id, start_date=None, end_date=None, status='earned'):
        """Get commissions earned by employee"""
        conn = self._get_connection()
        
        query = "SELECT * FROM employee_commissions WHERE employee_id=?"
        params = [employee_id]
        
        if start_date and end_date:
            query += " AND commission_date BETWEEN ? AND ?"
            params.extend([start_date, end_date])
        
        if status:
            query += " AND status=?"
            params.append(status)
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    
    def get_total_commissions(self, employee_id, month=None, year=None):
        """Get total commissions earned"""
        if month and year:
            start_date = f"{year:04d}-{month:02d}-01"
            days_in_month = monthrange(year, month)[1]
            end_date = f"{year:04d}-{month:02d}-{days_in_month}"
            df = self.get_employee_commissions(employee_id, start_date, end_date, status='earned')
        else:
            df = self.get_employee_commissions(employee_id, status='earned')
        
        return float(df['commission_amount'].sum()) if len(df) > 0 else 0
    
    # ═════════════════════════════════════════════════════════════════
    # PAYROLL MANAGEMENT
    # ═════════════════════════════════════════════════════════════════
    
    def calculate_monthly_salary(self, employee_id, month, year, bonuses=0, deductions=0):
        """
        Calculate monthly salary including commissions and deductions
        
        Args:
            bonuses: Additional bonus amount
            deductions: Tax/insurance deductions
        """
        conn = self._get_connection()
        c = conn.cursor()
        
        # Get employee base salary
        c.execute("SELECT base_salary FROM employees WHERE employee_id=?", (employee_id,))
        result = c.fetchone()
        
        if not result:
            raise ValueError(f"Employee {employee_id} not found")
        
        base_salary = float(result[0])
        
        # Get commissions for the month
        commissions = self.get_total_commissions(employee_id, month, year)
        
        # Calculate net salary
        gross_salary = base_salary + commissions + bonuses
        net_salary = gross_salary - deductions
        
        conn.close()
        
        return {
            'employee_id': employee_id,
            'month': f"{year:04d}-{month:02d}",
            'base_salary': base_salary,
            'commissions': commissions,
            'bonuses': bonuses,
            'deductions': deductions,
            'gross_salary': gross_salary,
            'net_salary': net_salary
        }
    
    def create_payroll_record(self, employee_id, month, year, bonuses=0, deductions=0):
        """Create payroll record for an employee"""
        salary_calc = self.calculate_monthly_salary(employee_id, month, year, bonuses, deductions)
        
        conn = self._get_connection()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO employee_payroll 
            (employee_id, payroll_month, payroll_year, base_salary, commissions_earned, 
             bonuses, deductions, net_salary, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        ''', (employee_id, month, year, salary_calc['base_salary'], 
              salary_calc['commissions'], bonuses, deductions, salary_calc['net_salary']))
        
        conn.commit()
        payroll_id = c.lastrowid
        conn.close()
        
        logger.info(f"Payroll created for {employee_id}: {month}/{year}")
        return payroll_id
    
    def process_payroll(self, month, year):
        """Process monthly payroll for all active employees"""
        employees_df = self.get_all_employees(status='active')
        
        payroll_records = []
        for _, emp in employees_df.iterrows():
            try:
                payroll_id = self.create_payroll_record(emp['employee_id'], month, year)
                payroll_records.append(payroll_id)
            except Exception as e:
                logger.error(f"Failed to process payroll for {emp['employee_id']}: {str(e)}")
        
        # Mark payroll as paid
        conn = self._get_connection()
        c = conn.cursor()
        payroll_cols = self._table_columns(conn, "employee_payroll")
        paid_col = "paid_on" if "paid_on" in payroll_cols else "paid_date"
        c.executemany(
            f"UPDATE employee_payroll SET status='paid', {paid_col}=? WHERE id=?",
            [(datetime.now().strftime('%Y-%m-%d'), pid) for pid in payroll_records]
        )
        conn.commit()
        conn.close()
        
        logger.info(f"Payroll processed for {len(payroll_records)} employees")
        return payroll_records
    
    def get_payroll_record(self, employee_id, month, year):
        """Get payroll record for employee"""
        conn = self._get_connection()
        df = pd.read_sql_query(
            "SELECT * FROM employee_payroll WHERE employee_id=? AND payroll_month=? AND payroll_year=?",
            conn,
            params=[employee_id, month, year]
        )
        conn.close()
        return dict(df.iloc[0]) if len(df) > 0 else None
    
    # ═════════════════════════════════════════════════════════════════
    # ATTENDANCE & PERFORMANCE
    # ═════════════════════════════════════════════════════════════════
    
    def record_attendance(self, employee_id, attendance_date, status='present', hours_worked=8, notes=None):
        """Record daily attendance"""
        valid_statuses = ['present', 'absent', 'leave', 'half-day']
        
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        
        conn = self._get_connection()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO employee_attendance 
            (employee_id, attendance_date, status, hours_worked, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (employee_id, attendance_date, status, hours_worked, notes))
        
        conn.commit()
        conn.close()
        logger.info(f"Attendance recorded for {employee_id} on {attendance_date}")
    
    def get_attendance_record(self, employee_id, start_date, end_date):
        """Get attendance records for a period"""
        conn = self._get_connection()
        df = pd.read_sql_query(
            "SELECT * FROM employee_attendance WHERE employee_id=? AND attendance_date BETWEEN ? AND ? ORDER BY attendance_date",
            conn,
            params=[employee_id, start_date, end_date]
        )
        conn.close()
        return df
    
    def get_attendance_summary(self, employee_id, month, year):
        """Get attendance summary for a month"""
        days_in_month = monthrange(year, month)[1]
        start_date = f"{year:04d}-{month:02d}-01"
        end_date = f"{year:04d}-{month:02d}-{days_in_month}"
        
        df = self.get_attendance_record(employee_id, start_date, end_date)
        
        if len(df) == 0:
            return {}
        
        summary = {
            'total_working_days': len(df),
            'present': len(df[df['status'] == 'present']),
            'absent': len(df[df['status'] == 'absent']),
            'leave': len(df[df['status'] == 'leave']),
            'half_day': len(df[df['status'] == 'half-day']),
            'total_hours': float(df['hours_worked'].sum()),
            'average_hours_per_day': float(df['hours_worked'].mean())
        }
        return summary
    
    def record_performance_review(self, employee_id, review_date, rating, deals_closed=0, 
                                 revenue_generated=0, notes=None, reviewed_by=None):
        """Record performance review"""
        if not (0 <= rating <= 5):
            raise ValueError("Rating must be between 0-5")
        
        conn = self._get_connection()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO employee_performance 
            (employee_id, review_date, rating, deals_closed, revenue_generated, notes, reviewed_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (employee_id, review_date, rating, deals_closed, revenue_generated, notes, reviewed_by))
        
        conn.commit()
        conn.close()
        logger.info(f"Performance review recorded for {employee_id}")
    
    def get_performance_history(self, employee_id):
        """Get performance review history"""
        conn = self._get_connection()
        df = pd.read_sql_query(
            "SELECT * FROM employee_performance WHERE employee_id=? ORDER BY review_date DESC",
            conn,
            params=[employee_id]
        )
        conn.close()
        return df
    
    # ═════════════════════════════════════════════════════════════════
    # EMPLOYEE ANALYTICS
    # ═════════════════════════════════════════════════════════════════
    
    def get_employee_stats(self, employee_id, month=None, year=None):
        """Get comprehensive employee statistics"""
        employee = self.get_employee(employee_id)
        
        if not employee:
            return None
        
        if month and year:
            salary_info = self.calculate_monthly_salary(employee_id, month, year)
            attendance = self.get_attendance_summary(employee_id, month, year)
        else:
            salary_info = None
            attendance = None
        
        performance_df = self.get_performance_history(employee_id)
        latest_performance = dict(performance_df.iloc[0]) if len(performance_df) > 0 else None
        
        stats = {
            'employee': {
                'id': employee['employee_id'],
                'name': employee['full_name'],
                'position': employee['position'],
                'hire_date': employee['hire_date'],
                'base_salary': employee['base_salary'],
                'commission_rate': employee['commission_rate'],
                'status': employee['status']
            },
            'salary': salary_info,
            'attendance': attendance,
            'performance': latest_performance,
            'total_reviews': len(performance_df)
        }
        
        return stats
    
    def get_top_performers(self, month=None, year=None, limit=5):
        """Get top performing employees by commissions"""
        employees_df = self.get_all_employees(status='active')
        
        performers = []
        for _, emp in employees_df.iterrows():
            if month and year:
                commissions = self.get_total_commissions(emp['employee_id'], month, year)
            else:
                commissions = self.get_total_commissions(emp['employee_id'])
            
            performers.append({
                'employee_id': emp['employee_id'],
                'name': emp['full_name'],
                'position': emp['position'],
                'commissions': commissions,
                'base_salary': emp['base_salary']
            })
        
        # Sort by commissions
        performers.sort(key=lambda x: x['commissions'], reverse=True)
        return performers[:limit]


if __name__ == "__main__":
    em = EmployeeManager()
    print("✅ Employee Manager initialized!")
