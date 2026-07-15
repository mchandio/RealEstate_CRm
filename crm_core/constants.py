"""Shared constants and normalizers for QT_CRM - Karachi Real Estate Edition."""

from __future__ import annotations

# =============================================================================
# DEAL WORKFLOW CONSTANTS
# =============================================================================

DEAL_STAGES = [
    "Lead", "Contacted", "Visit Scheduled", "Negotiation", "Title Verified",
    "Pending", "Closed", "Deal Done"
]
DEAL_PRIORITIES = ["Low", "Medium", "High", "Urgent"]

STAGE_PROBABILITY = {
    "Lead": 10.0,
    "Contacted": 25.0,
    "Visit Scheduled": 45.0,
    "Negotiation": 70.0,
    "Title Verified": 80.0,
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
    "Title Verified": 0.88,
    "Pending": 0.72,
    "Closed": 0.9,
    "Deal Done": 1.0,
}

# =============================================================================
# PROPERTY VERIFICATION STATUS (Karachi-specific)
# =============================================================================

VERIFICATION_STATUSES = [
    "Unverified",
    "Documents Pending",
    "Title Clear",
    "NOC Obtained",
    "Registry Done",
    "Transfer Complete",
]

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

# =============================================================================
# PROPERTY & FACILITY OPTIONS - Karachi Real Estate
# =============================================================================

# Areas organized by price tier (2026 Karachi market)
# Premium: PKR 80k-160k/sq yard
# Upper-Mid: PKR 40k-80k/sq yard
# Mid: PKR 15k-40k/sq yard
# Emerging: PKR 8k-20k/sq yard

COMMON_AREAS = [
    # DHA Phases (Premium)
    "DHA Phase 1", "DHA Phase 2", "DHA Phase 4", "DHA Phase 5",
    "DHA Phase 6", "DHA Phase 7", "DHA Phase 8",
    # DHA Commercial
    "DHA Phase 1 Commercial", "DHA Phase 2 Commercial", "DHA Phase 5 Commercial",
    "DHA Phase 6 Commercial", "DHA Phase 8 Commercial",
    # Clifton & Surrounding (Premium)
    "Clifton", "Clifton Block 1", "Clifton Block 2", "Clifton Block 3",
    "Clifton Block 4", "Clifton Block 5", "Clifton Block 6",
    "Clifton Block 7", "Clifton Block 8", "Clifton Block 9",
    "Zamzama", "Boat Basin", "Sea View", "Marina",
    "Gizri", "Cantt", "Civil Lines",
    # DHA Khayabans (Premium)
    "Khayaban-e-Ittehad", "Khayaban-e-Bukhari", "Khayaban-e-Shahbaz",
    "Khayaban-e-Hafiz", "Khayaban-e-Rahat", "Khayaban-e-Sehar",
    "Khayaban-e-Tariq", "Khayaban-e-Muslim", "Khayaban-e-Jami",
    "Khayaban-e-Ameer Khusro", "Khayaban-e-Roomi",
    # Askari (Premium)
    "Askari 1", "Askari 2", "Askari 3", "Askari 4", "Askari 5",
    # Commercial Areas
    "Badar Commercial", "Bukhari Commercial", "Tauheed Commercial",
    "Zamzama Commercial", "Shaheen Complex",
    # Upper-Mid (PKR 40k-80k/sq yard)
    "PECHS", "Tariq Road", "Bahadurabad", "KDA Scheme",
    "Gulshan-e-Iqbal", "Gulshan-e-Jauhar", "Gulshan 13", "Gulshan 14",
    "FB Area", "North Nazimabad", "Nazimabad",
    # Mid-Range (PKR 15k-40k/sq yard)
    "Gulistan-e-Johar", "Gulistan-e-Maymar", "Scheme 33",
    "Korangi", "Korangi Road", "Landhi",
    "Malir", "Malir Cantt", "Airport",
    "Lyari", "Saddar", "M A Jinnah Road",
    # Bahria Town (Mid-Range)
    "Bahria Town Karachi", "Bahria Sports City",
    "Bahria Precinct 1", "Bahria Precinct 2", "Bahria Precinct 5",
    "Bahria Precinct 8", "Bahria Precinct 10", "Bahria Precinct 15",
    "Bahria Jinnah Commercial", "Bahria Midway Commercial",
    # Emerging Areas (PKR 8k-20k/sq yard)
    "DHA City Karachi", "DHA City Karachi Phase 1", "DHA City Karachi Phase 2",
    "Bin Qasim", "Gadap Town", "Hub River Road",
    "Superhighway", "Nooriabad",
    # Cantonment Areas
    "Clifton Cantt", "Karachi Cantt", "Fighter Cantt",
    # Other Areas
    "Qayumabad", "Hyderi", "Water Pump", "Soldier Bazar",
    "Memon Goth", "Madina Colony", " Sultanabad",
]

# Karachi-specific facilities and amenities
FACILITY_OPTIONS = [
    # Electricity/Utilities
    "Light 24/7",
    "Light With Loadshedding",
    "Generator",
    "Solar",
    "Inverter",
    # Gas
    "Sui Gas",
    "LPG Gas",
    "No Gas",
    # Water
    "Sweet Water",
    "Bore Water",
    "Tank Water",
    "Water Tank",
    "No Water Issue",
    # Security
    "Watchman",
    "CCTV Camera",
    "Security Fence",
    "Gated Community",
    "Boundary Wall",
    # Parking
    "Car Parking",
    "Bike Parking",
    "Covered Parking",
    "No Parking",
    # Building Features
    "Lift",
    "Service Lift",
    "Fire Exit",
    "Stairs",
    # Furnishing
    "Furnished",
    "Semi-Furnished",
    "Unfurnished",
    # AC/Climate
    "Central AC",
    "Split AC",
    "AC Installed",
    # Location/Position
    "Main Road",
    "Side Road",
    "Corner Plot",
    "Back To Back",
    # Proximity
    "Near Market",
    "Near Mosque",
    "Near School",
    "Near Hospital",
    "Near Main Road",
]

FACILITY_ALIASES = {
    # Parking
    "parking": "Car Parking",
    "car park": "Car Parking",
    "covered parking": "Covered Parking",
    "bike": "Bike Parking",
    "bike parking": "Bike Parking",
    # CCTV/Security
    "cctv": "CCTV Camera",
    "camera": "CCTV Camera",
    "security": "Watchman",
    # Electricity
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
    "generator": "Generator",
    "ups": "Inverter",
    "solar": "Solar",
    # Water
    "sweet water": "Sweet Water",
    "clean water": "Sweet Water",
    "salty water": "Bore Water",
    "tank": "Water Tank",
    "water tank": "Water Tank",
    # Watchman/Security
    "watchman": "Watchman",
    "guard": "Watchman",
    "security guard": "Watchman",
    "gated": "Gated Community",
    "boundary wall": "Boundary Wall",
    # Lift/Building
    "lift": "Lift",
    "elevator": "Lift",
    "service lift": "Service Lift",
    # AC
    "ac": "Split AC",
    "air conditioning": "Split AC",
    "central ac": "Central AC",
    "split ac": "Split AC",
    # Furnishing
    "furnished": "Furnished",
    "fully furnished": "Furnished",
    "semi furnished": "Semi-Furnished",
    "unfurnished": "Unfurnished",
    # Gas
    "gas": "Sui Gas",
    "sui gas": "Sui Gas",
    "lng": "LPG Gas",
    # Location
    "corner": "Corner Plot",
    "corner plot": "Corner Plot",
    "main road": "Main Road",
    "side road": "Side Road",
}

FLOOR_OPTIONS = ["Basement", "Ground", "Mezzanine", "1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th", "11th", "12th", "Top"]
PROPERTY_TYPE_OPTIONS = [
    # Residential
    "Flat", "Apartment", "Penthouse", "Bungalow",
    "House", "Villa", "Townhouse", "Row House",
    # Commercial
    "Shop", "Showroom", "Office", "Plaza", "Commercial Plaza",
    # Industrial
    "Warehouse", "Factory", "Industrial Unit",
    # Land
    "Plot", "File", "Land",
    # Investment
    "Hotel Suite", "Service Apartment",
    # Building
    "Building", "Floor", "Portion",
]
MEASUREMENT_UNIT_OPTIONS = ["Sq Ft", "Sq Yard", "Marla", "Kanal", "Acre"]
OWNER_BROKER_OPTIONS = ["Client", "Broker", "Owner"]
FAMILY_OPTIONS = ["Family", "Bachelor", "Students", "Working Women", "Corporate", "Any"]

# =============================================================================
# KARACHI MARKET PRICE BRACKETS (2026)
# =============================================================================

# Sale price brackets in PKR
KARACHI_PRICE_BRACKETS = {
    "Budget": (0, 5000000, "Under 50 Lakh"),
    "Mid-Range": (5000000, 25000000, "50 Lakh - 2.5 Crore"),
    "Premium": (25000000, 100000000, "2.5 - 10 Crore"),
    "Luxury": (100000000, 500000000, "10 - 50 Crore"),
    "Ultra-Luxury": (500000000, None, "Above 50 Crore"),
}

# Rent price brackets in PKR/month
KARACHI_RENT_BRACKETS = {
    "Economy": (0, 75000, "Under 75K"),
    "Standard": (75000, 200000, "75K - 2 Lakh"),
    "Premium": (200000, 500000, "2 - 5 Lakh"),
    "Luxury": (500000, 2000000, "5 Lakh - 20 Lakh"),
    "Ultra-Luxury": (2000000, None, "Above 20 Lakh"),
}

# Area-wise estimated price per square yard (PKR)
KARACHI_AREA_PRICES = {
    # Premium Areas
    "DHA Phase 1": 135000,
    "DHA Phase 2": 130000,
    "DHA Phase 4": 95000,
    "DHA Phase 5": 90000,
    "DHA Phase 6": 110000,
    "DHA Phase 7": 85000,
    "DHA Phase 8": 100000,
    "Clifton": 160000,
    "Clifton Block 1-9": 140000,
    "Zamzama": 120000,
    "Boat Basin": 110000,
    "Sea View": 95000,
    "Marina": 130000,
    "Askari 1-5": 120000,
    "Cantt": 100000,
    # Upper-Mid Areas
    "PECHS": 70000,
    "Tariq Road": 65000,
    "Gulshan-e-Iqbal": 60000,
    "Bahadurabad": 55000,
    "North Nazimabad": 45000,
    "FB Area": 40000,
    # Mid-Range Areas
    "Gulistan-e-Johar": 35000,
    "Scheme 33": 30000,
    "Korangi": 25000,
    "Malir": 20000,
    # Bahria Town
    "Bahria Town Karachi": 18000,
    "Bahria Sports City": 15000,
    # Emerging Areas
    "DHA City Karachi": 12000,
    "Bin Qasim": 8000,
    "Superhighway": 6000,
}

# =============================================================================
# KARACHI LOCATION ALIASES FOR MATCHING
# =============================================================================

KARACHI_LOCATION_ALIASES = {
    # DHA variants
    "dha": "DHA",
    "defence": "DHA",
    "defence housing": "DHA",
    "defence housing authority": "DHA",
    "phase 1": "DHA Phase 1",
    "phase-1": "DHA Phase 1",
    "phase1": "DHA Phase 1",
    "phase 2": "DHA Phase 2",
    "phase-2": "DHA Phase 2",
    "phase2": "DHA Phase 2",
    "phase 4": "DHA Phase 4",
    "phase-4": "DHA Phase 4",
    "phase4": "DHA Phase 4",
    "phase 5": "DHA Phase 5",
    "phase-5": "DHA Phase 5",
    "phase5": "DHA Phase 5",
    "phase 6": "DHA Phase 6",
    "phase-6": "DHA Phase 6",
    "phase6": "DHA Phase 6",
    "phase 7": "DHA Phase 7",
    "phase-7": "DHA Phase 7",
    "phase7": "DHA Phase 7",
    "phase 8": "DHA Phase 8",
    "phase-8": "DHA Phase 8",
    "phase8": "DHA Phase 8",
    # Clifton variants
    "clifton": "Clifton",
    "cb": "Clifton Block",
    "clifton block": "Clifton",
    "block": "Clifton Block",
    # Bahria variants
    "bahria": "Bahria Town Karachi",
    "bth": "Bahria Town Karachi",
    "btk": "Bahria Town Karachi",
    "bahria town": "Bahria Town Karachi",
    "bahria sports": "Bahria Sports City",
    # Gulshan variants
    "gulshan": "Gulshan-e-Iqbal",
    "gulshan iqbal": "Gulshan-e-Iqbal",
    "gulshan-e-iqbal": "Gulshan-e-Iqbal",
    "gulshan jauhar": "Gulshan-e-Jauhar",
    "gulshan-e-jauhar": "Gulshan-e-Jauhar",
    # Other common aliases
    "nazimabad": "North Nazimabad",
    "f.b area": "FB Area",
    "fb area": "FB Area",
    "gulistan johar": "Gulistan-e-Johar",
    "gulistan-e-johar": "Gulistan-e-Johar",
    "scheme 33": "Scheme 33",
    "north nazimabad": "North Nazimabad",
}

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
