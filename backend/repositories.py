"""Backend Repository Layer for RealEstate_CRM.

This module provides repository implementations for the FastAPI backend,
wrapping SQLAlchemy ORM operations and providing a clean data access layer.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator, Generic, Sequence, TypeVar

from sqlalchemy import func, or_, cast, String
from sqlalchemy.orm import Session

from backend.database import get_db, engine
from backend.models import (
    User, Client, BrokerContact, Property, AuditLog, PendingApproval, AppSetting,
    RentRequirement, RentAvailability, SaleRequirement, SaleAvailability,
    RentedProperty, SoldProperty, IncomeTransaction, ExpenseTransaction,
    Employee, Attendance, SalaryPayment,
    SFEmployee, SFPosition, SFPerformanceGoal, SFMustWinBattle, SFKPI,
    SFLearning, SFRecruiting, SFCompensation, SFOnboarding,
    WFWorkflow, WFWorkflowStep, WFInstance, WFTask, WFApproval,
    WFNotification, WFSlaLog, WFAuditLog,
)

T = TypeVar("T")


# =============================================================================
# Base Repository
# =============================================================================

class BaseSQLAlchemyRepository(Generic[T]):
    """Base repository using SQLAlchemy ORM.
    
    Provides common database operations using SQLAlchemy sessions,
    following the Repository Pattern for the FastAPI backend.
    """
    
    def __init__(self, db: Session, model: type[T]):
        self.db = db
        self.model = model
    
    def get_by_id(self, id: int) -> T | None:
        """Get a single record by its ID."""
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_all(self, limit: int = 5000, offset: int = 0) -> list[T]:
        """Get all records with pagination."""
        return self.db.query(self.model).order_by(self.model.id.desc()).offset(offset).limit(limit).all()
    
    def count(self) -> int:
        """Get the total number of records."""
        return self.db.query(self.model).count()
    
    def create(self, data: dict[str, Any]) -> T:
        """Create a new record."""
        instance = self.model(**data)
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance
    
    def update(self, id: int, data: dict[str, Any]) -> T | None:
        """Update an existing record."""
        instance = self.get_by_id(id)
        if not instance:
            return None
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        self.db.commit()
        self.db.refresh(instance)
        return instance
    
    def delete(self, id: int) -> bool:
        """Delete a record by ID."""
        instance = self.get_by_id(id)
        if not instance:
            return False
        self.db.delete(instance)
        self.db.commit()
        return True
    
    def filter_by(self, **kwargs: Any) -> list[T]:
        """Filter records by field values."""
        query = self.db.query(self.model)
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        return query.all()
    
    def search(self, query: str, fields: list[str] | None = None) -> list[T]:
        """Search records by query string."""
        if not fields:
            # Get all string columns
            fields = [
                c.name for c in self.model.__table__.columns
                if str(c.type).upper() in ("TEXT", "VARCHAR", "CHAR")
            ]
        
        if not fields:
            return []
        
        # Build search condition
        conditions = [
            cast(getattr(self.model, field), String).ilike(f"%{query}%")
            for field in fields
            if hasattr(self.model, field)
        ]
        
        if not conditions:
            return []
        
        return self.db.query(self.model).filter(or_(*conditions)).limit(500).all()
    
    def exists(self, **kwargs: Any) -> bool:
        """Check if record exists with given criteria."""
        query = self.db.query(self.model)
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        return query.first() is not None


# =============================================================================
# Domain-Specific Repositories
# =============================================================================

class DealRepository(BaseSQLAlchemyRepository):
    """Repository for deal-related operations."""
    
    def get_active_deals(self, limit: int = 5000) -> list:
        """Get active (non-deleted) deals."""
        query = self.db.query(self.model)
        if hasattr(self.model, "is_deleted"):
            query = query.filter(
                (self.model.is_deleted == False) | 
                (self.model.is_deleted == 0) | 
                (self.model.is_deleted.is_(None))
            )
        return query.order_by(self.model.id.desc()).limit(limit).all()
    
    def get_by_stage(self, stage: str) -> list:
        """Get deals by workflow stage."""
        query = self.db.query(self.model)
        if hasattr(self.model, "workflow_stage"):
            query = query.filter(self.model.workflow_stage == stage)
        if hasattr(self.model, "is_deleted"):
            query = query.filter(
                (self.model.is_deleted == False) | 
                (self.model.is_deleted == 0) | 
                (self.model.is_deleted.is_(None))
            )
        return query.order_by(self.model.id.desc()).all()
    
    def soft_delete(self, id: int, deleted_by: str) -> bool:
        """Soft delete a deal."""
        from datetime import datetime
        instance = self.get_by_id(id)
        if not instance:
            return False
        if hasattr(instance, "is_deleted"):
            instance.is_deleted = True
        if hasattr(instance, "deleted_by"):
            instance.deleted_by = deleted_by
        if hasattr(instance, "deleted_at"):
            instance.deleted_at = datetime.now().isoformat(timespec="seconds")
        self.db.commit()
        return True


class ClientRepository(BaseSQLAlchemyRepository[Client]):
    """Repository for client operations."""
    
    def __init__(self, db: Session):
        super().__init__(db, Client)
    
    def get_by_phone(self, phone: str) -> Client | None:
        """Get client by phone number."""
        return self.db.query(Client).filter(Client.phone == phone).first()
    
    def get_by_name(self, name: str) -> Client | None:
        """Get client by name (case-insensitive)."""
        return self.db.query(Client).filter(
            func.lower(Client.client_name) == name.lower()
        ).first()
    
    def upsert_from_deal(self, deal_data: dict[str, Any], deal_table: str) -> Client | None:
        """Create or update client from deal data."""
        phone = deal_data.get("contact_phone") or deal_data.get("owner_phone") or ""
        name = deal_data.get("client_name") or deal_data.get("owner_name") or ""
        
        if not phone and not name:
            return None
        
        # Try to find existing client
        existing = None
        if phone:
            existing = self.get_by_phone(phone)
        if not existing and name:
            existing = self.get_by_name(name)
        
        if existing:
            # Update existing client
            if name and not existing.client_name:
                existing.client_name = name
            if phone and not existing.phone:
                existing.phone = phone
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create new client
            client = Client(
                client_name=name,
                phone=phone,
                client_type="Tenant" if "rent" in deal_table else "Buyer",
                status="Active",
                notes=f"Auto-synced from {deal_table}"
            )
            self.db.add(client)
            self.db.commit()
            self.db.refresh(client)
            return client


class PropertyRepository(BaseSQLAlchemyRepository[Property]):
    """Repository for property operations."""
    
    def __init__(self, db: Session):
        super().__init__(db, Property)
    
    def get_by_code(self, code: str) -> Property | None:
        """Get property by code."""
        return self.db.query(Property).filter(Property.property_code == code).first()
    
    def get_by_location(self, location: str) -> list[Property]:
        """Get properties by location."""
        return self.db.query(Property).filter(
            Property.location.like(f"%{location}%")
        ).order_by(Property.id.desc()).all()


class UserRepository(BaseSQLAlchemyRepository[User]):
    """Repository for user operations."""
    
    def __init__(self, db: Session):
        super().__init__(db, User)
    
    def get_by_username(self, username: str) -> User | None:
        """Get user by username."""
        return self.db.query(User).filter(
            func.lower(User.username) == username.lower()
        ).first()
    
    def authenticate(self, username: str, password_hash: str) -> User | None:
        """Authenticate user by username and password hash."""
        return self.db.query(User).filter(
            func.lower(User.username) == username.lower(),
            User.password_hash == password_hash,
            User.is_active == True
        ).first()


class AuditRepository(BaseSQLAlchemyRepository[AuditLog]):
    """Repository for audit log operations."""
    
    def __init__(self, db: Session):
        super().__init__(db, AuditLog)
    
    def log_action(
        self,
        table_name: str,
        record_id: int | None,
        action: str,
        username: str,
        summary: str = "",
        details: dict[str, Any] | None = None
    ) -> AuditLog:
        """Log an audit action."""
        import json
        from datetime import datetime
        
        audit_log = AuditLog(
            table_name=table_name,
            record_id=record_id,
            action=action,
            username=username,
            summary=summary or f"{action} on {table_name} #{record_id}",
            details=json.dumps(details or {}, default=str),
            created_at=datetime.now()
        )
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        return audit_log
    
    def get_by_table(self, table_name: str, limit: int = 100) -> list[AuditLog]:
        """Get audit logs for a specific table."""
        return self.db.query(AuditLog).filter(
            AuditLog.table_name == table_name
        ).order_by(AuditLog.id.desc()).limit(limit).all()
    
    def get_by_record(self, table_name: str, record_id: int) -> list[AuditLog]:
        """Get audit logs for a specific record."""
        return self.db.query(AuditLog).filter(
            AuditLog.table_name == table_name,
            AuditLog.record_id == record_id
        ).order_by(AuditLog.id.desc()).all()


class SettingRepository(BaseSQLAlchemyRepository[AppSetting]):
    """Repository for app settings operations."""
    
    def __init__(self, db: Session):
        super().__init__(db, AppSetting)
    
    def get_value(self, key: str, default: str = "") -> str:
        """Get setting value by key."""
        row = self.db.query(AppSetting).filter(AppSetting.key == key).first()
        return str(row.value) if row and row.value is not None else default
    
    def set_value(self, key: str, value: str) -> None:
        """Set setting value."""
        row = self.db.query(AppSetting).filter(AppSetting.key == key).first()
        if row:
            row.value = value
        else:
            self.db.add(AppSetting(key=key, value=value))
        self.db.commit()


# =============================================================================
# Repository Factory
# =============================================================================

class RepositoryFactory:
    """Factory for creating repository instances."""
    
    def __init__(self, db: Session):
        self.db = db
        self._repositories: dict[str, BaseSQLAlchemyRepository] = {}
    
    def get_repository(self, table_name: str) -> BaseSQLAlchemyRepository:
        """Get or create repository for a table."""
        if table_name not in self._repositories:
            # Map table names to models
            model_map = {
                "rent_requirements": RentRequirement,
                "rent_availability": RentAvailability,
                "sale_requirements": SaleRequirement,
                "sale_availability": SaleAvailability,
                "rented_properties": RentedProperty,
                "sold_properties": SoldProperty,
                "income_transactions": IncomeTransaction,
                "expense_transactions": ExpenseTransaction,
                "clients": Client,
                "broker_contacts": BrokerContact,
                "properties": Property,
                "employees": Employee,
                "attendance": Attendance,
                "salary_payments": SalaryPayment,
                "sf_employees": SFEmployee,
                "sf_positions": SFPosition,
                "sf_performance_goals": SFPerformanceGoal,
                "sf_must_win_battles": SFMustWinBattle,
                "sf_kpis": SFKPI,
                "sf_learning": SFLearning,
                "sf_recruiting": SFRecruiting,
                "sf_compensation": SFCompensation,
                "sf_onboarding": SFOnboarding,
                "wf_workflows": WFWorkflow,
                "wf_workflow_steps": WFWorkflowStep,
                "wf_instances": WFInstance,
                "wf_tasks": WFTask,
                "wf_approvals": WFApproval,
                "wf_notifications": WFNotification,
                "wf_sla_log": WFSlaLog,
                "wf_audit_log": WFAuditLog,
                "users": User,
                "audit_logs": AuditLog,
                "pending_approvals": PendingApproval,
                "app_settings": AppSetting,
            }
            
            model = model_map.get(table_name)
            if model is None:
                raise ValueError(f"Unknown table: {table_name}")
            
            # Use domain-specific repositories where available
            if table_name == "clients":
                self._repositories[table_name] = ClientRepository(self.db)
            elif table_name == "properties":
                self._repositories[table_name] = PropertyRepository(self.db)
            elif table_name == "users":
                self._repositories[table_name] = UserRepository(self.db)
            elif table_name == "audit_logs":
                self._repositories[table_name] = AuditRepository(self.db)
            elif table_name == "app_settings":
                self._repositories[table_name] = SettingRepository(self.db)
            elif table_name in {"rent_requirements", "rent_availability", 
                                "sale_requirements", "sale_availability"}:
                self._repositories[table_name] = DealRepository(self.db, model)
            else:
                self._repositories[table_name] = BaseSQLAlchemyRepository(self.db, model)
        
        return self._repositories[table_name]
    
    @property
    def clients(self) -> ClientRepository:
        """Get client repository."""
        return self.get_repository("clients")  # type: ignore
    
    @property
    def properties(self) -> PropertyRepository:
        """Get property repository."""
        return self.get_repository("properties")  # type: ignore
    
    @property
    def users(self) -> UserRepository:
        """Get user repository."""
        return self.get_repository("users")  # type: ignore
    
    @property
    def audit(self) -> AuditRepository:
        """Get audit repository."""
        return self.get_repository("audit_logs")  # type: ignore
    
    @property
    def settings(self) -> SettingRepository:
        """Get settings repository."""
        return self.get_repository("app_settings")  # type: ignore
