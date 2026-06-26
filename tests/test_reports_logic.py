from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import (
    RentAvailability,
    RentRequirement,
    RentedProperty,
    SaleAvailability,
    SaleRequirement,
)
from backend.routers.reports_router import (
    count_matched_demand_supply_pairs,
    dashboard_stats,
)
from crm_core.reports import ReportService, export_report_pdf


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    return engine, db


def test_matched_demand_supply_pairs_use_active_requirement_availability_matches():
    engine, db = make_db()
    try:
        db.add(
            RentRequirement(
                date="2026-06-01",
                client_name="Tenant",
                contact="03001234567",
                property_requires="Flat",
                size="2",
                floor="1st",
                location="DHA",
                budget=50000,
                workflow_stage="Lead",
                is_deleted=False,
            )
        )
        db.add_all(
            [
                RentAvailability(
                    date="2026-06-01",
                    owner_name="Owner",
                    contact="03007654321",
                    property_availability="Flat",
                    size="2",
                    floor="1st",
                    location="DHA",
                    monthly_rent=45000,
                    status="Available",
                    workflow_stage="Lead",
                    is_deleted=False,
                ),
                RentAvailability(
                    date="2026-06-01",
                    owner_name="Closed Owner",
                    property_availability="Flat",
                    size="2",
                    floor="1st",
                    location="DHA",
                    monthly_rent=45000,
                    status="Rented",
                    workflow_stage="Deal Done",
                    is_deleted=True,
                ),
            ]
        )
        db.add(
            SaleRequirement(
                date="2026-06-01",
                client_name="Buyer",
                property_requires="Plot",
                location="Clifton",
                budget=1000000,
                workflow_stage="Lead",
                is_deleted=False,
            )
        )
        db.add(
            SaleAvailability(
                date="2026-06-01",
                owner_name="Seller",
                property_availability="Shop",
                location="Bahria",
                demand=5000000,
                status="Available",
                workflow_stage="Lead",
                is_deleted=False,
            )
        )
        db.commit()

        assert count_matched_demand_supply_pairs(db) == 1
    finally:
        db.close()
        engine.dispose()


def test_dashboard_conversion_uses_closed_deals_over_matched_pair_opportunities():
    engine, db = make_db()
    try:
        db.add(
            RentRequirement(
                date="2026-06-01",
                client_name="Tenant",
                contact="03001234567",
                property_requires="Flat",
                size="2",
                floor="1st",
                location="DHA",
                budget=50000,
                workflow_stage="Lead",
                is_deleted=False,
            )
        )
        db.add(
            RentAvailability(
                date="2026-06-01",
                owner_name="Owner",
                contact="03007654321",
                property_availability="Flat",
                size="2",
                floor="1st",
                location="DHA",
                monthly_rent=45000,
                status="Available",
                workflow_stage="Lead",
                is_deleted=False,
            )
        )
        db.add(
            RentedProperty(
                source_table="rent_availability",
                source_id=99,
                deal_type="rent",
                closed_status="Rented",
                closed_at="2026-06-02",
                owner_name="Converted Owner",
                property_availability="Flat",
                monthly_rent=40000,
            )
        )
        db.commit()

        user = SimpleNamespace(role="Admin", full_name="Admin User", username="admin")
        response = dashboard_stats(db=db, user=user)

        assert response["active_matched_pairs"] == 1
        assert response["closed_deals"] == 1
        assert response["matched_pairs"] == 2
        assert response["conversion_rate"] == 50
    finally:
        db.close()
        engine.dispose()


def test_rent_report_exports_real_pdf(tmp_path):
    db_path = tmp_path / "crm_reports.db"
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        db.add(
            RentRequirement(
                date="2026-06-01",
                client_name="Tenant",
                contact="03001234567",
                property_requires="Flat",
                size="2",
                floor="1st",
                location="DHA",
                budget=50000,
                workflow_stage="Lead",
                is_deleted=False,
            )
        )
        db.add(
            RentAvailability(
                date="2026-06-01",
                owner_name="Owner",
                contact="03007654321",
                property_availability="Flat",
                size="2",
                floor="1st",
                location="DHA",
                monthly_rent=45000,
                status="Available",
                workflow_stage="Lead",
                is_deleted=False,
            )
        )
        db.commit()

        result = ReportService(db_path, company_name="MBM Enterprises").rent_report()
        pdf_path = export_report_pdf(result, tmp_path / "rent_report.pdf")

        assert pdf_path.exists()
        assert pdf_path.read_bytes().startswith(b"%PDF")
        assert pdf_path.stat().st_size > 1000
    finally:
        db.close()
        engine.dispose()
