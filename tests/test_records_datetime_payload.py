from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import BrokerContact, RentRequirement
from backend.routers.records_router import clean_payload, validate_record_payload


class DummyUser:
    username = "remote-user"


def rent_requirement_payload(**overrides):
    payload = {
        "date": "2026-06-01",
        "client_name": "Remote Tenant",
        "client_status": "Client",
        "contact": "03001234567",
        "property_requires": "Flat",
        "size": "2",
        "floor": "1st",
        "location": "DHA",
        "budget": 50000,
    }
    payload.update(overrides)
    return payload


def flush_rent_requirement(data):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        record = RentRequirement(**data)
        db.add(record)
        db.flush()
        return record.id
    finally:
        db.rollback()
        db.close()
        engine.dispose()


def test_create_payload_uses_datetime_for_rent_requirement_created_at():
    data = clean_payload(
        RentRequirement,
        rent_requirement_payload(),
        user=DummyUser(),
        creating=True,
        table="rent_requirements",
    )

    validate_record_payload("rent_requirements", data, creating=True)

    assert isinstance(data["created_at"], datetime)
    assert flush_rent_requirement(data) == 1


def test_iso_datetime_payload_is_coerced_before_insert():
    data = clean_payload(
        RentRequirement,
        rent_requirement_payload(created_at="2026-06-01T12:34:56"),
        user=DummyUser(),
        creating=True,
        table="rent_requirements",
    )

    validate_record_payload("rent_requirements", data, creating=True)

    assert data["created_at"] == datetime(2026, 6, 1, 12, 34, 56)
    assert flush_rent_requirement(data) == 1


def test_broker_contact_payload_and_area_sorting():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        first = clean_payload(
            BrokerContact,
            {"name": "Z Broker", "contact": "03001234567", "area": "Clifton", "remarks": "Evenings"},
            user=DummyUser(),
            creating=True,
            table="broker_contacts",
        )
        second = clean_payload(
            BrokerContact,
            {"name": "A Broker", "contact": "03007654321", "area": "DHA", "remarks": ""},
            user=DummyUser(),
            creating=True,
            table="broker_contacts",
        )
        validate_record_payload("broker_contacts", first, creating=True)
        validate_record_payload("broker_contacts", second, creating=True)

        db.add_all([BrokerContact(**second), BrokerContact(**first)])
        db.flush()

        rows = db.query(BrokerContact).order_by(BrokerContact.area.asc(), BrokerContact.name.asc()).all()
        assert [(row.area, row.name) for row in rows] == [("Clifton", "Z Broker"), ("DHA", "A Broker")]
    finally:
        db.rollback()
        db.close()
        engine.dispose()
