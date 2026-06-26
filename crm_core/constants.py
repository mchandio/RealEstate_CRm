"""Shared constants and normalizers for QT_CRM."""

from __future__ import annotations

# =============================================================================
# DEAL WORKFLOW CONSTANTS
# =============================================================================

DEAL_STAGES = ["Lead", "Contacted", "Visit Scheduled", "Negotiation", "Pending", "Closed", "Deal Done"]
DEAL_PRIORITIES = ["Low", "Medium", "High", "Urgent"]

STAGE_PROBABILITY = {
    "Lead": 10.0,
    "Contacted": 25.0,
    "Visit Scheduled": 45.0,
    "Negotiation": 70.0,
    "Pending": 60.0,
    "Closed": 90.0,
    "Deal Done": 100.0,
}

PRIORITY_SCORE = {"Urgent": 1.0, "High": 0.82, "Medium": 0.55, "Low": 0.3}
STAGE_SCORE = {
    "Lead": 0.25,
    "Contacted": 0.42,
    "Visit Scheduled": 0.62,
    "Negotiation": 0.82,
    "Pending": 0.72,
    "Closed": 0.9,
    "Deal Done": 1.0,
}

# =============================================================================
# TABLE CONSTANTS
# =============================================================================

PHASE1_TABLES = ("rent_requirements", "rent_availability", "sale_requirements", "sale_availability")
PIPELINE_TABLES = ["rent_requirements", "rent_availability", "sale_requirements", "sale_availability"]

DEAL_TABLES = {
    "rent_requirements": ("client_name", "contact_phone", "property_requires", "budget"),
    "rent_availability": ("owner_name", "owner_phone", "property_availability", "monthly_rent"),
    "rented_properties": ("owner_name", "owner_phone", "property_availability", "monthly_rent"),
    "sale_requirements": ("client_name", "contact_phone", "property_requires", "budget"),
    "sale_availability": ("owner_name", "owner_phone", "property_availability", "demand"),
    "sold_properties": ("owner_name", "owner_phone", "property_availability", "demand"),
}

CLOSED_AVAILABILITY_ARCHIVES = {
    "rent_availability": ("Rented", "rented_properties", "rent"),
    "sale_availability": ("Sold", "sold_properties", "sale"),
}

# =============================================================================
# PROPERTY & FACILITY OPTIONS
# =============================================================================

COMMON_AREAS = [
    "Gizri", "DHA", "DHA Phase 1", "DHA Phase 2", "DHA Phase 4", "DHA Phase 5",
    "DHA Phase 6", "DHA Phase 7", "DHA Phase 8", "Defence", "Clifton",
    "Clifton Block 1", "Clifton Block 2", "Clifton Block 3", "Clifton Block 4",
    "Clifton Block 5", "Clifton Block 6", "Clifton Block 7", "Clifton Block 8",
    "Clifton Block 9", "Zamzama", "Boat Basin", "Sea View", "Marina",
    "Khayaban-e-Ittehad", "Khayaban-e-Bukhari", "Khayaban-e-Shahbaz",
    "Khayaban-e-Hafiz", "Khayaban-e-Rahat", "Khayaban-e-Sehar",
    "Khayaban-e-Tariq", "Khayaban-e-Muslim", "Khayaban-e-Jami",
    "Badar Commercial", "Bukhari Commercial", "Tauheed Commercial",
    "Zamzama Commercial", "Phase 5 Extension", "Phase 6 Commercial",
    "Qayumabad", "Korangi Road", "Cantt", "Saddar", "PECHS", "Tariq Road",
    "Bahadurabad", "KDA Scheme", "Gulshan", "Gulistan-e-Johar", "Scheme 33",
    "North Nazimabad", "Nazimabad", "FB Area", "Hyderi", "Water Pump",
    "Malir", "Airport",
]

FACILITY_OPTIONS = [
    "Light With Loadshedding",
    "Light 24/7",
    "Gas",
    "Sweet Water",
    "Salty Water",
    "Car Parking",
    "Bike Parking",
    "Lift",
    "CCTV Camera",
    "Watchman",
]

FACILITY_ALIASES = {
    "parking": "Car Parking",
    "car park": "Car Parking",
    "bike": "Bike Parking",
    "bike parking": "Bike Parking",
    "cctv": "CCTV Camera",
    "camera": "CCTV Camera",
    "electricity 24/7": "Light 24/7",
    "electric 24/7": "Light 24/7",
    "light 24/7": "Light 24/7",
    "electricity with load shedding": "Light With Loadshedding",
    "electricity with loadshading": "Light With Loadshedding",
    "electric with load shedding": "Light With Loadshedding",
    "electric with loadshading": "Light With Loadshedding",
    "light with load shedding": "Light With Loadshedding",
    "load shedding": "Light With Loadshedding",
    "loadshading": "Light With Loadshedding",
    "sweet water": "Sweet Water",
    "salty water": "Salty Water",
    "watchman": "Watchman",
    "security": "Watchman",
    "lift": "Lift",
    "gas": "Gas",
}

FLOOR_OPTIONS = ["Basement", "Ground", "Mezzanine", "1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th", "Top"]
PROPERTY_TYPE_OPTIONS = ["Flat", "Bungalow", "House", "Shop", "Office", "Warehouse", "Plot", "Building", "Villa"]
MEASUREMENT_UNIT_OPTIONS = ["Sq Ft", "Yards"]
OWNER_BROKER_OPTIONS = ["Client", "Broker", "Owner"]
FAMILY_OPTIONS = ["Family", "Bachelor", "Other"]

# =============================================================================
# CONTACT & STATUS CONSTANTS
# =============================================================================

CONTACT_ROLES = ("Client", "Broker", "Owner")
AVAILABILITY_STATUSES = ("Available", "Pending", "Rented", "Sold", "Reserved", "Withdrawn", "Inactive")

# =============================================================================
# EXPENSE CATEGORIES
# =============================================================================
EXPENSE_CATEGORIES = (
    "Petty Cash",
    "Office Rent",
    "PTCL BILL",
    "Electric Bill",
    "Jazz Bill",
    "Salaries",
    "Food & Hygine",
    "Labour",
    "Advance",
    "Fuel",
    "Staff Residence Rent",
    "Staff Water bill",
    "Office expenses",
    "Maintenance",
    "Utilities",
    "Repair",
    "Salary",
    "Commission",
    "Tax",
    "Legal",
    "Marketing",
    "Other",
)

# =============================================================================
# ROLE PERMISSIONS
# =============================================================================

ROLE_PERMISSIONS = {
    "Super Admin": [
        "dashboard", "rent", "sale", "properties", "clients", "financial",
        "employees", "reports", "ai", "settings", "users", "backup", "delete",
        "successfactors", "sf_view", "workflow", "wf_view", "wf_admin",
    ],
    "Admin": [
        "dashboard", "rent", "sale", "properties", "clients", "financial",
        "employees", "reports", "ai", "settings", "users", "backup", "delete",
        "successfactors", "sf_view", "workflow", "wf_view", "wf_admin",
    ],
    "Manager": [
        "dashboard", "rent", "sale", "properties", "clients", "financial",
        "employees", "reports", "ai",
        "successfactors", "sf_view", "workflow", "wf_view",
    ],
    "Staff": ["dashboard", "rent", "sale", "reports", "wf_view"],
    "Viewer": ["dashboard", "rent_view", "sale_view", "reports"],
}

ADMIN_ROLES = {"Super Admin", "Admin"}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    return permission in ROLE_PERMISSIONS.get(role, [])


def is_admin_role(role: str) -> bool:
    """Check if role is an admin role."""
    return role in ADMIN_ROLES


def normalize_contact_role(value: object, default: str = "Client") -> str:
    text = str(value or "").strip().lower()
    aliases = {
        "c": "Client",
        "client": "Client",
        "customer": "Client",
        "b": "Broker",
        "broker": "Broker",
        "agent": "Broker",
        "o": "Owner",
        "owner": "Owner",
        "seller": "Owner",
    }
    if not text:
        return default
    if text in aliases:
        return aliases[text]
    for role in CONTACT_ROLES:
        if text == role.lower():
            return role
    raise ValueError(f"Invalid contact status: {value}")


def normalize_availability_status(value: object, default: str = "Available") -> str:
    text = str(value or "").strip().lower()
    if not text:
        return default
    aliases = {
        "available": "Available",
        "pending": "Pending",
        "follow up": "Pending",
        "follow-up": "Pending",
        "hold pending": "Pending",
        "rented": "Rented",
        "rent": "Rented",
        "sold": "Sold",
        "sale": "Sold",
        "reserved": "Reserved",
        "hold": "Reserved",
        "withdrawn": "Withdrawn",
        "inactive": "Inactive",
    }
    if text in aliases:
        return aliases[text]
    for status in AVAILABILITY_STATUSES:
        if text == status.lower():
            return status
    raise ValueError(f"Invalid availability status: {value}")
