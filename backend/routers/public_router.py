from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.database import get_db
from backend.models import Property, RentRequirement, SaleRequirement

router = APIRouter(prefix="/api/public", tags=["Public"])

@router.get("/properties")
def list_public_properties(db: Session = Depends(get_db)):
    properties = db.query(Property).filter(
        Property.status.in_(["Available", "Active", ""]) | Property.status.is_(None)
    ).order_by(desc(Property.id)).limit(50).all()
    
    return {"ok": True, "properties": [
        {
            "id": p.id,
            "title": p.title,
            "location": p.location,
            "property_type": p.property_type,
            "monthly_rent": p.monthly_rent,
            "sale_price": p.sale_price,
            "facilities": p.facilities,
            "description": p.description,
            "area": p.area,
            "floor": p.floor,
        } for p in properties
    ]}

@router.post("/leads")
def submit_public_lead(payload: dict, db: Session = Depends(get_db)):
    # Accept basic info from the public site and push to Requirements
    lead_type = payload.get("type", "rent") # 'rent' or 'sale'
    
    if lead_type == "rent":
        req = RentRequirement(
            client_name=payload.get("name", "Web Lead"),
            contact=payload.get("phone", ""),
            contact_email=payload.get("email", ""),
            property_requires=payload.get("property_type", ""),
            location=payload.get("location", ""),
            budget=payload.get("budget", 0),
            remarks=payload.get("message", ""),
            workflow_stage="Lead",
            date=datetime.now().strftime("%Y-%m-%d"),
            priority="High",
            created_by="Public Website"
        )
        db.add(req)
    else:
        req = SaleRequirement(
            client_name=payload.get("name", "Web Lead"),
            contact=payload.get("phone", ""),
            contact_email=payload.get("email", ""),
            property_requires=payload.get("property_type", ""),
            location=payload.get("location", ""),
            budget=payload.get("budget", 0),
            remarks=payload.get("message", ""),
            workflow_stage="Lead",
            date=datetime.now().strftime("%Y-%m-%d"),
            priority="High",
            created_by="Public Website"
        )
        db.add(req)
        
    db.commit()
    return {"ok": True, "message": "Lead submitted successfully"}
