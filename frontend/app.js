const API = '';
let token = localStorage.getItem('token');
let currentUser = null;
let currentTab = 'phase1';
let currentSub = 'rent_requirements';
let phase1CurrentTable = '';
let phase1Settings = { areas: [], facilities: [], floors: [], propertyTypes: [], measurementUnits: [], expenseCategories: [], theme: 'Light', company_name: 'MBM Enterprises' };
let refreshBusy = false;
let companyName = 'MBM Enterprises';
let lastMatchReport = null;
const tableState = {};
const TABLE_PAGE_SIZE = 100;
const PHASE1_TABLE_PAGE_SIZE = 1000;
let tableSearchTimer = null;
const printableRowsPerPage = 18;

const PIPELINE_TABLES = ['rent_requirements','rent_availability','sale_requirements','sale_availability'];
const TABLE_DEFAULT_SORT = {
  broker_contacts: { sort: 'area', direction: 'asc' },
};
const ROLE_TABS = {
  'Super Admin': ['phase1','approvals','dashboard','rent','sale','find','followups','financial','employees','clients','broker_contacts','properties','successfactors','workflow','reports','audit'],
  'Admin': ['phase1','approvals','dashboard','rent','sale','find','followups','financial','employees','clients','broker_contacts','properties','successfactors','workflow','reports','audit'],
  'Manager': ['phase1','dashboard','rent','sale','find','followups','financial','employees','clients','broker_contacts','properties','successfactors','workflow','reports'],
  'Staff': ['phase1','dashboard','rent','sale','find','followups','workflow','reports'],
  'Viewer': ['phase1','dashboard','rent','sale','find','reports']
};


// === INLINE MENU HANDLERS (defined at top for reliability) ===
function toggleMenu(event, menuName) {
  event.stopPropagation();
  // Find all menu items and close their dropdowns
  document.querySelectorAll('.menu-dropdown').forEach(d => d.classList.remove('active'));
  document.querySelectorAll('.menu-item.open').forEach(i => {
    i.classList.remove('open');
    i.setAttribute('aria-expanded', 'false');
  });
  
  // Open the clicked menu
  const menuItem = event.currentTarget;
  const dropdown = menuItem.querySelector('.menu-dropdown');
  if (dropdown) {
    dropdown.classList.add('active');
    menuItem.classList.add('open');
    menuItem.setAttribute('aria-expanded', 'true');
  }
}

function menuAction(event, action) {
  event.stopPropagation();
  // Close all menus and reset aria-expanded
  document.querySelectorAll('.menu-dropdown').forEach(d => d.classList.remove('active'));
  document.querySelectorAll('.menu-item.open').forEach(i => {
    i.classList.remove('open');
    i.setAttribute('aria-expanded', 'false');
  });
  // Execute the action
  if (typeof handleMenuAction === 'function') {
    handleMenuAction(action);
  }
}

function normalizeRole(role) {
  const text = String(role || '').trim().replace(/\s+/g, ' ');
  const key = text.toLowerCase();
  const aliases = {
    'superadmin': 'Super Admin',
    'super admin': 'Super Admin',
    'administrator': 'Admin',
    'admin': 'Admin',
    'manager': 'Manager',
    'staff': 'Staff',
    'staf': 'Staff',
    'viewer': 'Viewer',
    'view': 'Viewer'
  };
  return aliases[key] || text || 'Staff';
}

const SEARCH_TABLE_LABELS = {
  rent_requirements: 'Rent Requirement',
  rent_availability: 'Rent Availability',
  rented_properties: 'Rented Property',
  sale_requirements: 'Sale Requirement',
  sale_availability: 'Sale Availability',
  sold_properties: 'Sold Property',
  clients: 'Client',
  broker_contacts: 'Broker Contact',
  properties: 'Property',
  employees: 'Employee',
  income_transactions: 'Income',
  expense_transactions: 'Expense',
  attendance: 'Attendance',
  salary_payments: 'Salary Payment',
  sf_employees: 'SF Employee',
  sf_positions: 'SF Position',
  sf_performance_goals: 'SF Performance Goal',
  sf_must_win_battles: 'SF Must Win Battle',
  sf_kpis: 'SF KPI',
  sf_learning: 'SF Learning',
  sf_recruiting: 'SF Recruiting',
  sf_compensation: 'SF Compensation',
  sf_onboarding: 'SF Onboarding',
  wf_workflows: 'Workflow Definition',
  wf_workflow_steps: 'Workflow Step',
  wf_instances: 'Workflow Instance',
  wf_tasks: 'Workflow Task',
  wf_approvals: 'Workflow Approval',
  wf_notifications: 'Workflow Notification',
  wf_sla_log: 'Workflow SLA Log',
  wf_audit_log: 'Workflow Audit Log'
};

const SEARCH_COLUMNS = ['type','id','date','name','status','contact','property','amount','floor','location','facilities','remarks'];

const PHASE1_TABLES = ['rent_requirements','rent_availability','sale_requirements','sale_availability'];
const PHASE1_LABELS = {
  rent_requirements: 'Rent Requirement',
  rent_availability: 'Rent Availability',
  rented_properties: 'Rented Property',
  sale_requirements: 'Sale Requirement',
  sale_availability: 'Sale Availability',
  sold_properties: 'Sold Property'
};
const DEAL_STAGES = ['Lead','Contacted','Visit Scheduled','Negotiation','Title Verified','Pending','Closed','Deal Done'];
const AVAILABILITY_STATUSES = ['Available','Pending','Reserved','Rented','Sold','Withdrawn','Inactive'];
const GENERIC_STATUSES = ['Active','Pending','Inactive','Closed'];
const VERIFICATION_STATUSES = ['Unverified','Documents Pending','Title Clear','NOC Obtained','Registry Done','Transfer Complete'];

// Karachi Real Estate Market Data (synced with Qt Desktop)
const DEFAULT_PHASE1 = {
  // 101 Karachi areas organized by price tier
  areas: [
    // DHA Phases (Premium)
    'DHA Phase 1','DHA Phase 2','DHA Phase 4','DHA Phase 5','DHA Phase 6','DHA Phase 7','DHA Phase 8',
    'DHA Phase 1 Commercial','DHA Phase 2 Commercial','DHA Phase 5 Commercial','DHA Phase 6 Commercial','DHA Phase 8 Commercial',
    // Clifton & Surrounding (Premium)
    'Clifton','Clifton Block 1','Clifton Block 2','Clifton Block 3','Clifton Block 4','Clifton Block 5','Clifton Block 6','Clifton Block 7','Clifton Block 8','Clifton Block 9',
    'Zamzama','Boat Basin','Sea View','Marina','Gizri','Cantt','Civil Lines',
    // DHA Khayabans (Premium)
    'Khayaban-e-Ittehad','Khayaban-e-Bukhari','Khayaban-e-Shahbaz','Khayaban-e-Hafiz','Khayaban-e-Rahat','Khayaban-e-Sehar','Khayaban-e-Tariq','Khayaban-e-Muslim','Khayaban-e-Jami','Khayaban-e-Ameer Khusro','Khayaban-e-Roomi',
    // Askari (Premium)
    'Askari 1','Askari 2','Askari 3','Askari 4','Askari 5',
    // Commercial Areas
    'Badar Commercial','Bukhari Commercial','Tauheed Commercial','Zamzama Commercial','Shaheen Complex',
    // Upper-Mid (PKR 40k-80k/sq yard)
    'PECHS','Tariq Road','Bahadurabad','KDA Scheme','Gulshan-e-Iqbal','Gulshan-e-Jauhar','Gulshan 13','Gulshan 14','FB Area','North Nazimabad','Nazimabad',
    // Mid-Range (PKR 15k-40k/sq yard)
    'Gulistan-e-Johar','Gulistan-e-Maymar','Scheme 33','Korangi','Korangi Road','Landhi','Malir','Malir Cantt','Airport','Lyari','Saddar','M A Jinnah Road',
    // Bahria Town (Mid-Range)
    'Bahria Town Karachi','Bahria Sports City','Bahria Precinct 1','Bahria Precinct 2','Bahria Precinct 5','Bahria Precinct 8','Bahria Precinct 10','Bahria Precinct 15','Bahria Jinnah Commercial','Bahria Midway Commercial',
    // Emerging Areas (PKR 8k-20k/sq yard)
    'DHA City Karachi','DHA City Karachi Phase 1','DHA City Karachi Phase 2','Bin Qasim','Gadap Town','Hub River Road','Superhighway','Nooriabad',
    // Cantonment Areas
    'Clifton Cantt','Karachi Cantt','Fighter Cantt',
    // Other Areas
    'Qayumabad','Hyderi','Water Pump','Soldier Bazar','Memon Goth','Madina Colony','Sultanabad'
  ],
  // 41 facilities including Karachi-specific amenities
  facilities: [
    // Electricity/Utilities
    'Light 24/7','Light With Loadshedding','Generator','Solar','Inverter',
    // Gas
    'Sui Gas','LPG Gas','No Gas',
    // Water
    'Sweet Water','Bore Water','Tank Water','Water Tank','No Water Issue',
    // Security
    'Watchman','CCTV Camera','Security Fence','Gated Community','Boundary Wall',
    // Parking
    'Car Parking','Bike Parking','Covered Parking','No Parking',
    // Building Features
    'Lift','Service Lift','Fire Exit','Stairs',
    // Furnishing
    'Furnished','Semi-Furnished','Unfurnished',
    // AC/Climate
    'Central AC','Split AC','AC Installed',
    // Location/Position
    'Main Road','Side Road','Corner Plot','Back To Back',
    // Proximity
    'Near Market','Near Mosque','Near School','Near Hospital','Near Main Road'
  ],
  floors: ['Basement','Ground','Mezzanine','1st','2nd','3rd','4th','5th','6th','7th','8th','9th','10th','11th','12th','Top'],
  // 22 property types (expanded for Karachi market)
  propertyTypes: ['Flat','Apartment','Penthouse','Bungalow','House','Villa','Townhouse','Row House','Shop','Showroom','Office','Plaza','Commercial Plaza','Warehouse','Factory','Industrial Unit','Plot','File','Land','Hotel Suite','Service Apartment','Building','Floor','Portion'],
  // Standard Pakistani measurement units
  measurementUnits: ['Sq Ft','Sq Yard','Marla','Kanal','Acre']
};

// Karachi Market Price Brackets (PKR)
const KARACHI_PRICE_BRACKETS = {
  'Budget': { min: 0, max: 5000000, label: 'Under 50 Lakh' },
  'Mid-Range': { min: 5000000, max: 25000000, label: '50 Lakh - 2.5 Crore' },
  'Premium': { min: 25000000, max: 100000000, label: '2.5 - 10 Crore' },
  'Luxury': { min: 100000000, max: 500000000, label: '10 - 50 Crore' },
  'Ultra-Luxury': { min: 500000000, max: null, label: 'Above 50 Crore' }
};

// Karachi Area Price Estimates (per sq yard)
const KARACHI_AREA_PRICES = {
  'DHA Phase 1': 135000,'DHA Phase 2': 130000,'DHA Phase 4': 95000,'DHA Phase 5': 90000,
  'DHA Phase 6': 110000,'DHA Phase 7': 85000,'DHA Phase 8': 100000,'Clifton': 160000,
  'Zamzama': 120000,'Boat Basin': 110000,'Sea View': 95000,'Marina': 130000,
  'Askari 1': 120000,'Askari 2': 120000,'Askari 3': 120000,'Askari 4': 120000,'Askari 5': 120000,
  'Cantt': 100000,'PECHS': 70000,'Tariq Road': 65000,'Gulshan-e-Iqbal': 60000,
  'Bahadurabad': 55000,'North Nazimabad': 45000,'FB Area': 40000,'Gulistan-e-Johar': 35000,
  'Scheme 33': 30000,'Korangi': 25000,'Malir': 20000,'Bahria Town Karachi': 18000,
  'Bahria Sports City': 15000,'DHA City Karachi': 12000,'Bin Qasim': 8000,'Superhighway': 6000
};

// Loading State Management
function showLoading(element, type = 'overlay') {
  if (!element) return;
  
  if (type === 'overlay') {
    element.classList.add('table-loading');
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.innerHTML = '<div class="loading-spinner"></div>';
    overlay.id = 'loading-overlay-' + Date.now();
    element.appendChild(overlay);
    return overlay.id;
  } else if (type === 'skeleton') {
    element.innerHTML = generateSkeletonRows(5);
  } else if (type === 'button') {
    element.classList.add('btn-loading');
    element.disabled = true;
  } else if (type === 'search') {
    element.classList.add('search-loading');
  }
}

function hideLoading(element, type = 'overlay', overlayId = null) {
  if (!element) return;
  
  if (type === 'overlay') {
    element.classList.remove('table-loading');
    if (overlayId) {
      const overlay = document.getElementById(overlayId);
      if (overlay) overlay.remove();
    } else {
      const overlays = element.querySelectorAll('.loading-overlay');
      overlays.forEach(o => o.remove());
    }
  } else if (type === 'button') {
    element.classList.remove('btn-loading');
    element.disabled = false;
  } else if (type === 'search') {
    element.classList.remove('search-loading');
  }
}

function generateSkeletonRows(count) {
  let html = '';
  for (let i = 0; i < count; i++) {
    html += `
      <div class="skeleton-row">
        <div class="skeleton skeleton-cell"></div>
        <div class="skeleton skeleton-cell"></div>
        <div class="skeleton skeleton-cell"></div>
        <div class="skeleton skeleton-cell"></div>
        <div class="skeleton skeleton-cell"></div>
      </div>
    `;
  }
  return html;
}

const EXPENSE_CATEGORIES = [
  'Petty Cash',
  'Office Rent',
  'PTCL BILL',
  'Electric Bill',
  'Jazz Bill',
  'Salaries',
  'Food & Hygine',
  'Labour',
  'Advance',
  'Fuel',
  'Staff Residence Rent',
  'Staff Water bill',
  'Office expenses',
  'Maintenance',
  'Utilities',
  'Repair',
  'Salary',
  'Commission',
  'Tax',
  'Legal',
  'Marketing',
  'Other'
];

function normalizeOptionList(value, fallback = []) {
  let values = Array.isArray(value)
    ? value
    : String(value || '').split(/\r?\n|,/);
  values = values.map(item => String(item || '').trim()).filter(Boolean);
  if (values.length === 1 && fallback.length) {
    const packed = values[0].toLowerCase().replace(/\s+/g, ' ');
    const unpacked = fallback.filter(option => packed.includes(String(option).toLowerCase().replace(/\s+/g, ' ')));
    if (unpacked.length > 1) return unpacked;
  }
  return values.length ? values : [...fallback];
}

function defaultMultiOptions(key) {
  if (key === 'facilities') return DEFAULT_PHASE1.facilities;
  if (key === 'floor') return DEFAULT_PHASE1.floors;
  return [];
}

function splitMultiValue(value) {
  return String(value || '').split(/[,;|\n]+/).map(v => v.trim()).filter(Boolean);
}

function multiOptionsForField(field, value = '') {
  const options = normalizeOptionList(field.options, defaultMultiOptions(field.key));
  const keys = new Set(options.map(option => String(option).trim().toLowerCase()));
  splitMultiValue(value).forEach(option => {
    const clean = String(option || '').trim();
    const key = clean.toLowerCase();
    if (clean && !keys.has(key)) {
      options.push(clean);
      keys.add(key);
    }
  });
  return options;
}

const FIELDS = {
  rent_requirements: [
    {key:'client_name',label:'Name',required:true},{key:'client_status',label:'Status',type:'select',options:['Client','Broker','Owner']},
    {key:'contact',label:'Contact',required:true},{key:'date',label:'Date',type:'date',required:true},
    {key:'property_requires',label:'Property Required / Needed',type:'select',options:DEFAULT_PHASE1.propertyTypes,required:true},
    {key:'size',label:'Rooms',required:true},
    {key:'measurement',label:'Measurement',type:'number'},
    {key:'measurement_unit',label:'Size',type:'select',options:DEFAULT_PHASE1.measurementUnits},
    {key:'floor',label:'Floor',type:'multiselect',options:DEFAULT_PHASE1.floors,required:true},
    {key:'location',label:'Location',type:'combo',options:DEFAULT_PHASE1.areas,required:true},
    {key:'bachelor_family',label:'Family / Bachelor / Other',type:'select',options:['Family','Bachelor','Other']},
    {key:'persons',label:'Persons'},
    {key:'facilities',label:'Facilities',type:'multiselect',options:DEFAULT_PHASE1.facilities},
    {key:'budget',label:'Budget',type:'number'},
    {key:'workflow_stage',label:'Workflow',readonly:true},
    {key:'created_by',label:'Created By',readonly:true},{key:'created_at',label:'Created At',readonly:true},
    {key:'last_edited_by',label:'Last Edited By',readonly:true},{key:'last_edited_at',label:'Last Edited At',readonly:true}
  ],
  rent_availability: [
    {key:'owner_name',label:'Name',required:true},{key:'client_broker',label:'Status',type:'select',options:['Client','Broker','Owner']},
    {key:'contact',label:'Contact',required:true},{key:'date',label:'Date',type:'date',required:true},
    {key:'property_availability',label:'Property Available',type:'select',options:DEFAULT_PHASE1.propertyTypes,required:true},
    {key:'size',label:'Rooms',required:true},
    {key:'measurement',label:'Measurement',type:'number'},
    {key:'measurement_unit',label:'Size',type:'select',options:DEFAULT_PHASE1.measurementUnits},
    {key:'floor',label:'Floor',type:'multiselect',options:DEFAULT_PHASE1.floors,required:true},
    {key:'monthly_rent',label:'Rent',type:'number',required:true},{key:'deposit',label:'Advance',type:'number'},
    {key:'maintenance_charge',label:'Maintenance',type:'number'},{key:'location',label:'Location',type:'combo',options:DEFAULT_PHASE1.areas,required:true},
    {key:'building_name',label:'Building Name'},{key:'bachelor_family',label:'Family / Bachelor / Other',type:'select',options:['Family','Bachelor','Other']},
    {key:'persons',label:'Persons'},{key:'facilities',label:'Facilities',type:'multiselect',options:DEFAULT_PHASE1.facilities},
    {key:'status',label:'Availability Status',readonly:true},{key:'workflow_stage',label:'Workflow',readonly:true},
    {key:'created_by',label:'Created By',readonly:true},{key:'created_at',label:'Created At',readonly:true},
    {key:'last_edited_by',label:'Last Edited By',readonly:true},{key:'last_edited_at',label:'Last Edited At',readonly:true}
  ],
  rented_properties: [
    {key:'closed_at',label:'Rented Date',readonly:true},{key:'owner_name',label:'Name',readonly:true},
    {key:'client_broker',label:'Status',readonly:true},{key:'contact',label:'Contact',readonly:true},
    {key:'property_availability',label:'Property Rented',readonly:true},{key:'size',label:'Rooms',readonly:true},
    {key:'measurement',label:'Measurement',readonly:true},{key:'measurement_unit',label:'Size',readonly:true},
    {key:'floor',label:'Floor',readonly:true},{key:'monthly_rent',label:'Rent',readonly:true},
    {key:'deposit',label:'Advance',readonly:true},{key:'maintenance_charge',label:'Maintenance',readonly:true},
    {key:'location',label:'Location',readonly:true},{key:'building_name',label:'Building Name',readonly:true},
    {key:'closed_status',label:'Status',readonly:true},{key:'archived_by',label:'Archived By',readonly:true},
    {key:'source_id',label:'Source ID',readonly:true},{key:'remarks',label:'Remarks',readonly:true}
  ],
  sale_requirements: [
    {key:'client_name',label:'Name',required:true},{key:'client_status',label:'Status',type:'select',options:['Client','Broker','Owner']},
    {key:'contact',label:'Contact',required:true},{key:'date',label:'Date',type:'date',required:true},
    {key:'property_requires',label:'Property Required / Needed',type:'select',options:DEFAULT_PHASE1.propertyTypes,required:true},
    {key:'size',label:'Rooms',required:true},
    {key:'measurement',label:'Measurement',type:'number'},
    {key:'measurement_unit',label:'Size',type:'select',options:DEFAULT_PHASE1.measurementUnits},
    {key:'floor',label:'Floor',type:'multiselect',options:DEFAULT_PHASE1.floors,required:true},
    {key:'budget',label:'Budget',type:'number',required:true},{key:'maintenance_charge',label:'Maintenance',type:'number'},
    {key:'location',label:'Location',type:'combo',options:DEFAULT_PHASE1.areas,required:true},
    {key:'bachelor_family',label:'Family / Bachelor / Other',type:'select',options:['Family','Bachelor','Other']},
    {key:'facilities',label:'Facilities',type:'multiselect',options:DEFAULT_PHASE1.facilities},
    {key:'workflow_stage',label:'Workflow',readonly:true},
    {key:'created_by',label:'Created By',readonly:true},{key:'created_at',label:'Created At',readonly:true},
    {key:'last_edited_by',label:'Last Edited By',readonly:true},{key:'last_edited_at',label:'Last Edited At',readonly:true}
  ],
  sale_availability: [
    {key:'owner_name',label:'Name',required:true},{key:'client_broker',label:'Status',type:'select',options:['Client','Broker','Owner']},
    {key:'contact',label:'Contact',required:true},{key:'date',label:'Date',type:'date',required:true},
    {key:'property_availability',label:'Property Available',type:'select',options:DEFAULT_PHASE1.propertyTypes,required:true},
    {key:'size',label:'Rooms',required:true},
    {key:'measurement',label:'Measurement',type:'number'},
    {key:'measurement_unit',label:'Size',type:'select',options:DEFAULT_PHASE1.measurementUnits},
    {key:'floor',label:'Floor',type:'multiselect',options:DEFAULT_PHASE1.floors,required:true},
    {key:'demand',label:'Demand',type:'number',required:true},{key:'maintenance_charge',label:'Maintenance',type:'number'},
    {key:'location',label:'Location',type:'combo',options:DEFAULT_PHASE1.areas,required:true},
    {key:'building_name',label:'Building Name'},
    {key:'facilities',label:'Facilities',type:'multiselect',options:DEFAULT_PHASE1.facilities},
    {key:'status',label:'Availability Status',readonly:true},{key:'workflow_stage',label:'Workflow',readonly:true},
    {key:'created_by',label:'Created By',readonly:true},{key:'created_at',label:'Created At',readonly:true},
    {key:'last_edited_by',label:'Last Edited By',readonly:true},{key:'last_edited_at',label:'Last Edited At',readonly:true}
  ],
  sold_properties: [
    {key:'closed_at',label:'Sold Date',readonly:true},{key:'owner_name',label:'Name',readonly:true},
    {key:'client_broker',label:'Status',readonly:true},{key:'contact',label:'Contact',readonly:true},
    {key:'property_availability',label:'Property Sold',readonly:true},{key:'size',label:'Rooms',readonly:true},
    {key:'measurement',label:'Measurement',readonly:true},{key:'measurement_unit',label:'Size',readonly:true},
    {key:'floor',label:'Floor',readonly:true},{key:'demand',label:'Demand',readonly:true},
    {key:'maintenance_charge',label:'Maintenance',readonly:true},{key:'location',label:'Location',readonly:true},
    {key:'building_name',label:'Building Name',readonly:true},{key:'closed_status',label:'Status',readonly:true},
    {key:'archived_by',label:'Archived By',readonly:true},{key:'source_id',label:'Source ID',readonly:true},
    {key:'remarks',label:'Remarks',readonly:true}
  ],
  income_transactions: [
    {key:'transaction_date',label:'Date',type:'date'},{key:'income_type',label:'Income Type'},{key:'amount',label:'Amount',type:'number'},
    {key:'tenant_name',label:'Tenant Name'},{key:'description',label:'Description'},{key:'receipt_no',label:'Receipt No'},
    {key:'payment_method',label:'Payment Method'}
  ],
  expense_transactions: [
    {key:'transaction_date',label:'Date',type:'date'},{key:'expense_category',label:'Category',type:'select',options:EXPENSE_CATEGORIES},{key:'amount',label:'Amount',type:'number'},
    {key:'vendor_name',label:'Vendor'},{key:'description',label:'Description'},{key:'invoice_no',label:'Invoice No'},
    {key:'payment_method',label:'Payment Method'}
  ],
  employees: [
    {key:'employee_id',label:'Employee ID'},{key:'full_name',label:'Full Name'},{key:'cnic',label:'CNIC'},{key:'phone',label:'Phone'},
    {key:'email',label:'Email'},{key:'position',label:'Position'},{key:'department',label:'Department'},{key:'hire_date',label:'Hire Date',type:'date'},
    {key:'base_salary',label:'Base Salary',type:'number'},{key:'commission_rate',label:'Commission %',type:'number'},
    {key:'status',label:'Status'},{key:'address',label:'Address'},{key:'notes',label:'Notes'}
  ],
  attendance: [
    {key:'employee_id',label:'Employee ID',type:'number',required:true},
    {key:'date',label:'Date',type:'date',required:true},
    {key:'check_in',label:'Check In'},
    {key:'check_out',label:'Check Out'},
    {key:'shift_name',label:'Shift'},
    {key:'scheduled_start',label:'Shift Start'},
    {key:'scheduled_end',label:'Shift End'},
    {key:'status',label:'Status',type:'select',options:['Present','Late','Absent','Leave','Half Day','Remote','Field Visit']},
    {key:'leave_type',label:'Leave Type',type:'select',options:['','Sick','Casual','Annual','Emergency','Unpaid']},
    {key:'worked_minutes',label:'Worked Minutes',type:'number',readonly:true},
    {key:'late_minutes',label:'Late Minutes',type:'number',readonly:true},
    {key:'early_leave_minutes',label:'Early Leave Minutes',type:'number',readonly:true},
    {key:'overtime_minutes',label:'Overtime Minutes',type:'number',readonly:true},
    {key:'notes',label:'Notes'}
  ],
  salary_payments: [
    {key:'employee_id',label:'Employee ID',type:'number'},{key:'payment_date',label:'Payment Date',type:'date'},{key:'month',label:'Month'},
    {key:'year',label:'Year'},{key:'base_salary',label:'Base Salary',type:'number'},{key:'bonus',label:'Bonus',type:'number'},
    {key:'deductions',label:'Deductions',type:'number'},{key:'net_salary',label:'Net Salary',type:'number'},
    {key:'payment_method',label:'Payment Method'},{key:'notes',label:'Notes'}
  ],
  clients: [
    {key:'client_name',label:'Client Name'},{key:'cnic',label:'CNIC'},{key:'phone',label:'Phone'},{key:'email',label:'Email'},
    {key:'address',label:'Address'},{key:'client_type',label:'Type'},{key:'notes',label:'Notes'},{key:'status',label:'Status'}
  ],
  broker_contacts: [
    {key:'name',label:'Name',required:true},
    {key:'contact',label:'Contact',required:true},
    {key:'area',label:'Area'},
    {key:'office_address',label:'Office Address'},
    {key:'home_address',label:'Home Address'},
    {key:'remarks',label:'Remarks'}
  ],
  properties: [
    {key:'property_code',label:'Code'},{key:'title',label:'Title'},{key:'property_type',label:'Type'},{key:'status',label:'Status'},
    {key:'owner_name',label:'Owner'},{key:'owner_contact',label:'Owner Contact'},{key:'location',label:'Location'},{key:'area',label:'Area'},
    {key:'floor',label:'Floor',type:'multiselect',options:DEFAULT_PHASE1.floors},{key:'bedrooms',label:'Beds'},{key:'bathrooms',label:'Baths'},
    {key:'furnishing',label:'Furnishing',type:'select',options:['','Unfurnished','Semi Furnished','Furnished']},{key:'parking',label:'Parking',type:'select',options:['','No','Bike','Car','Bike + Car']},
    {key:'nearby_landmarks',label:'Nearby Landmarks'},{key:'area_notes',label:'Area Notes'},
    {key:'verification_status',label:'Verification',type:'select',options:['Unverified','Phone Verified','Visited','Documents Checked']},{key:'photo_paths',label:'Photo Paths'},
    {key:'monthly_rent',label:'Monthly Rent',type:'number'},{key:'sale_price',label:'Sale Price',type:'number'},
    {key:'maintenance_charge',label:'Maintenance',type:'number'},{key:'facilities',label:'Facilities'},{key:'description',label:'Description'}
  ],
  sf_employees: [
    {key:'sf_employee_id',label:'SF Employee ID'},{key:'full_name',label:'Full Name',required:true},{key:'email',label:'Email'},
    {key:'department',label:'Department',type:'select',options:['Sales','Operations','HR','Finance','IT','Admin'],required:true},
    {key:'job_title',label:'Job Title',required:true},{key:'manager_name',label:'Manager'},{key:'hire_date',label:'Hire Date',type:'date'},
    {key:'location',label:'Location'},{key:'cost_center',label:'Cost Center'},
    {key:'employment_status',label:'Status',type:'select',options:['Active','On Leave','Terminated','Suspended']},{key:'notes',label:'Notes'}
  ],
  sf_positions: [
    {key:'position_code',label:'Position Code'},{key:'position_title',label:'Position Title',required:true},
    {key:'department',label:'Department',type:'select',options:['Sales','Operations','HR','Finance','IT','Admin']},{key:'location',label:'Location'},
    {key:'headcount_max',label:'Max Headcount',type:'number'},{key:'headcount_current',label:'Current Headcount',type:'number'},
    {key:'reports_to',label:'Reports To'},{key:'status',label:'Status',type:'select',options:['Open','Filled','Frozen','Closed']}
  ],
  sf_performance_goals: [
    {key:'employee_name',label:'Employee Name',required:true},{key:'goal_title',label:'Goal Title',required:true},{key:'goal_description',label:'Description'},
    {key:'review_period',label:'Review Period',type:'select',options:['Q1','Q2','Q3','Q4','H1','H2','Annual']},{key:'due_date',label:'Due Date',type:'date'},
    {key:'progress_pct',label:'Progress %',type:'number'},{key:'status',label:'Status',type:'select',options:['In Progress','Completed','On Hold','Cancelled']},
    {key:'rating',label:'Rating',type:'select',options:['','Exceeds','Meets','Below','N/A']},{key:'notes',label:'Notes'}
  ],
  sf_must_win_battles: [
    {key:'battle_code',label:'Battle Code'},{key:'battle_title',label:'Battle Title',required:true},{key:'owner_name',label:'Owner Name',required:true},
    {key:'department',label:'Department',type:'select',options:['Sales','Operations','HR','Finance','IT','Admin']},{key:'objective',label:'Objective'},
    {key:'start_date',label:'Start Date',type:'date'},{key:'end_date',label:'End Date',type:'date'},
    {key:'priority',label:'Priority',type:'select',options:['Low','Medium','High','Critical']},{key:'status',label:'Status',type:'select',options:['Active','At Risk','Won','Lost','On Hold']},
    {key:'target_value',label:'Target Value',type:'number'},{key:'current_value',label:'Current Value',type:'number'},{key:'progress_pct',label:'Progress %',type:'number'},
    {key:'business_impact',label:'Business Impact'},{key:'risks',label:'Risks / Blockers'},{key:'notes',label:'Notes'}
  ],
  sf_kpis: [
    {key:'kpi_code',label:'KPI Code'},{key:'kpi_name',label:'KPI Name',required:true},{key:'employee_name',label:'Employee Name'},{key:'owner_name',label:'Owner Name'},
    {key:'department',label:'Department',type:'select',options:['Sales','Operations','HR','Finance','IT','Admin']},
    {key:'category',label:'Category',type:'select',options:['Revenue','Sales','Operations','Customer','People','Compliance','Quality']},
    {key:'period',label:'Period',type:'select',options:['Q1','Q2','Q3','Q4','H1','H2','Annual','Monthly']},
    {key:'start_date',label:'Start Date',type:'date'},{key:'end_date',label:'End Date',type:'date'},
    {key:'target_value',label:'Target Value',type:'number'},{key:'actual_value',label:'Actual Value',type:'number'},{key:'unit',label:'Unit'},
    {key:'weight_pct',label:'Weight %',type:'number'},{key:'achievement_pct',label:'Achievement %',type:'number'},
    {key:'status',label:'Status',type:'select',options:['Not Started','On Track','At Risk','Off Track','Completed']},{key:'review_date',label:'Review Date',type:'date'},{key:'notes',label:'Notes'}
  ],
  sf_learning: [
    {key:'employee_name',label:'Employee Name',required:true},{key:'course_title',label:'Course Title',required:true},{key:'course_code',label:'Course Code'},
    {key:'category',label:'Category'},{key:'instructor',label:'Instructor'},{key:'assigned_date',label:'Assigned Date',type:'date'},
    {key:'due_date',label:'Due Date',type:'date'},{key:'completion_date',label:'Completion Date',type:'date'},
    {key:'status',label:'Status',type:'select',options:['Assigned','In Progress','Completed','Overdue','Waived']},{key:'score',label:'Score',type:'number'},{key:'notes',label:'Notes'}
  ],
  sf_recruiting: [
    {key:'job_requisition_id',label:'Requisition ID'},{key:'job_title',label:'Job Title',required:true},
    {key:'department',label:'Department',type:'select',options:['Sales','Operations','HR','Finance','IT','Admin']},{key:'location',label:'Location'},
    {key:'hiring_manager',label:'Hiring Manager'},{key:'recruiter',label:'Recruiter'},{key:'open_date',label:'Open Date',type:'date'},
    {key:'close_date',label:'Close Date',type:'date'},{key:'status',label:'Status',type:'select',options:['Open','On Hold','Filled','Cancelled']},
    {key:'applications_count',label:'Applications',type:'number'},{key:'shortlisted_count',label:'Shortlisted',type:'number'},{key:'notes',label:'Notes'}
  ],
  sf_compensation: [
    {key:'employee_name',label:'Employee Name',required:true},{key:'base_salary',label:'Base Salary',type:'number',required:true},
    {key:'bonus',label:'Bonus',type:'number'},{key:'allowances',label:'Allowances',type:'number'},{key:'total_compensation',label:'Total Compensation',type:'number'},
    {key:'currency',label:'Currency',type:'select',options:['PKR','USD','AED','GBP']},{key:'effective_date',label:'Effective Date',type:'date'},
    {key:'review_cycle',label:'Review Cycle'},{key:'approved_by',label:'Approved By'},
    {key:'status',label:'Status',type:'select',options:['Active','Pending','Expired']},{key:'notes',label:'Notes'}
  ],
  sf_onboarding: [
    {key:'employee_name',label:'Employee Name',required:true},{key:'task_title',label:'Task Title',required:true},{key:'task_category',label:'Category'},
    {key:'assigned_to',label:'Assigned To'},{key:'due_date',label:'Due Date',type:'date'},{key:'completion_date',label:'Completion Date',type:'date'},
    {key:'status',label:'Status',type:'select',options:['Pending','In Progress','Completed','Waived']},
    {key:'priority',label:'Priority',type:'select',options:['Low','Medium','High','Critical']},{key:'notes',label:'Notes'}
  ],
  wf_workflows: [
    {key:'workflow_name',label:'Workflow Name',required:true},{key:'workflow_type',label:'Type'},{key:'trigger_event',label:'Trigger Event'},
    {key:'status',label:'Status',type:'select',options:['Active','Draft','Paused','Archived']},{key:'version',label:'Version',type:'number'},{key:'description',label:'Description'}
  ],
  wf_workflow_steps: [
    {key:'workflow_id',label:'Workflow ID',type:'number'},{key:'step_name',label:'Step Name',required:true},{key:'step_order',label:'Step Order',type:'number'},
    {key:'step_type',label:'Step Type'},{key:'assignee_role',label:'Assignee Role'},{key:'assignee_name',label:'Assignee Name'},
    {key:'sla_hours',label:'SLA Hours',type:'number'},{key:'action_on_approve',label:'On Approve'},{key:'action_on_reject',label:'On Reject'},
    {key:'is_conditional',label:'Conditional',type:'number'},{key:'condition_field',label:'Condition Field'},{key:'condition_value',label:'Condition Value'}
  ],
  wf_instances: [
    {key:'workflow_name',label:'Workflow',readonly:true},{key:'reference_table',label:'Source Table',readonly:true},{key:'reference_id',label:'Record ID',type:'number',readonly:true},
    {key:'initiated_by',label:'Started By',readonly:true},{key:'initiated_at',label:'Started At',readonly:true},{key:'current_step',label:'Step',type:'number',readonly:true},
    {key:'current_assignee',label:'Assignee',readonly:true},{key:'status',label:'Status',readonly:true},{key:'due_at',label:'Due',readonly:true},{key:'priority',label:'Priority',readonly:true},{key:'notes',label:'Notes',readonly:true}
  ],
  wf_tasks: [
    {key:'workflow_name',label:'Workflow'},{key:'step_name',label:'Step Name'},{key:'assigned_to',label:'Assigned To',required:true},
    {key:'assigned_at',label:'Assigned At',type:'date'},{key:'due_at',label:'Due Date',type:'date'},
    {key:'status',label:'Status',type:'select',options:['Pending','Completed','Rejected','Cancelled']},
    {key:'priority',label:'Priority',type:'select',options:['Low','Normal','High','Critical']},{key:'reference_table',label:'Reference Table'},
    {key:'reference_id',label:'Reference ID',type:'number'},{key:'comments',label:'Comments'}
  ],
  wf_approvals: [
    {key:'workflow_name',label:'Workflow',readonly:true},{key:'approval_type',label:'Type',readonly:true},{key:'requested_by',label:'Requested By',readonly:true},
    {key:'requested_at',label:'Requested At',readonly:true},{key:'reviewed_by',label:'Reviewed By',readonly:true},{key:'reviewed_at',label:'Reviewed At',readonly:true},
    {key:'decision',label:'Decision',readonly:true},{key:'status',label:'Status',readonly:true},{key:'comments',label:'Comments',readonly:true}
  ],
  wf_notifications: [
    {key:'recipient',label:'Recipient',required:true},{key:'subject',label:'Subject',required:true},{key:'body',label:'Body'},
    {key:'channel',label:'Channel',type:'select',options:['In-App','Email','SMS','WhatsApp']},
    {key:'status',label:'Status',type:'select',options:['Unread','Read','Sent','Failed']}
  ],
  wf_sla_log: [
    {key:'instance_id',label:'Instance ID',type:'number',readonly:true},{key:'task_id',label:'Task ID',type:'number',readonly:true},
    {key:'sla_target_hours',label:'SLA Target Hours',type:'number',readonly:true},{key:'actual_hours',label:'Actual Hours',type:'number',readonly:true},
    {key:'breached',label:'Breached',type:'number',readonly:true},{key:'logged_at',label:'Logged At',readonly:true}
  ],
  wf_audit_log: [
    {key:'action',label:'Action',readonly:true},{key:'performed_by',label:'By',readonly:true},{key:'performed_at',label:'At',readonly:true},
    {key:'reference_table',label:'Table',readonly:true},{key:'reference_id',label:'Record ID',type:'number',readonly:true},
    {key:'old_value',label:'Old Value',readonly:true},{key:'new_value',label:'New Value',readonly:true}
  ]
};

const SUB_TABLES = {
  rent: { rent_requirements: 'rent_requirements', rent_availability: 'rent_availability', rented_properties: 'rented_properties' },
  sale: { sale_requirements: 'sale_requirements', sale_availability: 'sale_availability', sold_properties: 'sold_properties' },
  financial: { income_transactions: 'income_transactions', expense_transactions: 'expense_transactions' },
  employees: { employees: 'employees', attendance: 'attendance', salary_payments: 'salary_payments' },
  successfactors: {
    sf_employees: 'Employee Central',
    sf_recruiting: 'Recruiting',
    sf_performance_goals: 'Performance & Goals',
    sf_must_win_battles: 'Must Win Battles',
    sf_kpis: 'KPIs',
    sf_learning: 'Learning',
    sf_compensation: 'Compensation',
    sf_onboarding: 'Onboarding',
    sf_positions: 'Positions'
  },
  workflow: {
    wf_workflows: 'Workflow Definitions',
    wf_workflow_steps: 'Workflow Steps',
    wf_instances: 'Running Instances',
    wf_tasks: 'Tasks',
    wf_approvals: 'Approvals',
    wf_notifications: 'Notifications',
    wf_sla_log: 'SLA Log',
    wf_audit_log: 'Audit Trail'
  }
};

function $(id) { return document.getElementById(id); }

function formatClock(date = new Date()) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function setSyncStatus(message, kind = '') {
  const el = $('sync-status');
  if (!el) return;
  el.textContent = message;
  el.classList.toggle('busy', kind === 'busy');
  el.classList.toggle('error', kind === 'error');
}

function setRefreshBusy(busy) {
  refreshBusy = busy;
  const btn = $('btn-refresh');
  if (btn) {
    btn.disabled = busy;
    btn.textContent = busy ? 'Refreshing...' : 'Refresh';
  }
}

function setPageSubtitle(tab) {
  const el = $('page-subtitle');
  if (el) el.textContent = companyName || 'Real Estate CRM';
}

function setCompanyName(value) {
  companyName = String(value || companyName || 'Real Estate CRM').trim();
  setPageSubtitle(currentTab);
}

function setNetworkLabels() {
  const host = window.location.hostname || '127.0.0.1';
  const port = window.location.port || '6090';
  const browserUrl = `${window.location.protocol}//${host}${port ? `:${port}` : ''}`;
  const apiPort = port === '6190' ? '6091' : '6091';
  const browserEl = $('browser-url');
  const apiEl = $('desktop-api-url');
  if (browserEl) browserEl.textContent = browserUrl;
  if (apiEl) apiEl.textContent = `${window.location.protocol}//${host}:${apiPort}`;
}

async function refreshCurrentView() {
  if (refreshBusy) return;
  setRefreshBusy(true);
  setSyncStatus('Refreshing current view...', 'busy');
  try {
    await loadTab(currentTab);
    setSyncStatus(`Updated ${formatClock()}`);
  } catch (err) {
    console.error(err);
    setSyncStatus(err.message || 'Refresh failed', 'error');
  } finally {
    setRefreshBusy(false);
  }
}

function renderTableLoading(tableEl, columnCount) {
  let thead = tableEl.querySelector('thead');
  if (!thead) { thead = document.createElement('thead'); tableEl.prepend(thead); }
  let tbody = tableEl.querySelector('tbody');
  if (!tbody) { tbody = document.createElement('tbody'); tableEl.appendChild(tbody); }
  tbody.innerHTML = Array.from({ length: 6 }).map(() =>
    `<tr>${Array.from({ length: columnCount }).map(() => '<td><span class="skeleton-row"></span></td>').join('')}</tr>`
  ).join('');
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function isDateKey(key) {
  return key === 'date' || key === 'transaction_date' || key === 'hire_date' || key.endsWith('_date') || key.endsWith('_at');
}

function todayISODate() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function formatDate(value) {
  if (!value) return '';
  const text = String(value).slice(0, 10);
  const match = text.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  return match ? `${match[3]}/${match[2]}/${match[1]}` : String(value);
}

function formatCell(value, key = '') {
  if (value === null || value === undefined) return '';
  if (isDateKey(key)) return formatDate(value);
  if (['worked_minutes','late_minutes','early_leave_minutes','overtime_minutes'].includes(key)) {
    const total = Number(value || 0);
    if (!Number.isFinite(total)) return '00:00';
    const hours = Math.floor(Math.max(total, 0) / 60);
    const minutes = Math.max(total, 0) % 60;
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
  }
  if (typeof value === 'number') {
    const moneyKeys = ['budget','monthly_rent','demand','sale_price','amount','base_salary','bonus','deductions','net_salary','maintenance_charge','deposit','allowances','total_compensation','target_value','current_value','actual_value'];
    return moneyKeys.includes(key) ? `Rs. ${value.toLocaleString()}` : value.toLocaleString();
  }
  return String(value);
}

function formatMoney(value) {
  const number = Number(value || 0);
  return `Rs. ${number.toLocaleString()}`;
}

function parseMoney(value) {
  if (value === null || value === undefined || value === '') return 0;
  const cleaned = String(value).replace(/rs\.?/ig, '').replace(/,/g, '').trim();
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : 0;
}

function validatePhone(value, required = false) {
  let digits = String(value || '').replace(/\D/g, '');
  if (digits.startsWith('92') && digits.length === 12) digits = `0${digits.slice(2)}`;
  if (!digits) {
    if (required) throw new Error('Contact is required.');
    return '';
  }
  if (digits.length !== 11 || !digits.startsWith('03')) {
    throw new Error('Contact must be 03001234567 or +923001234567.');
  }
  return digits;
}

function normalizeContactRole(value, fallback = 'Client') {
  const text = String(value || '').trim().toLowerCase();
  const aliases = { c: 'Client', client: 'Client', b: 'Broker', broker: 'Broker', agent: 'Broker', o: 'Owner', owner: 'Owner', seller: 'Owner' };
  return aliases[text] || fallback;
}

function phoneKeyForTable(table) {
  return {
    rent_requirements: 'contact',
    rent_availability: 'contact',
    sale_requirements: 'contact',
    sale_availability: 'contact',
    clients: 'phone',
    properties: 'owner_contact',
    employees: 'phone'
  }[table] || 'contact';
}

function formatBytes(value) {
  const size = Number(value || 0);
  if (size >= 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(2)} MB`;
  if (size >= 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${size} bytes`;
}

function listingQuality(table, row = {}) {
  const fieldSets = {
    rent_availability: ['owner_name','contact','property_availability','monthly_rent','location','size','measurement','measurement_unit','floor','bedrooms','bathrooms','facilities','nearby_landmarks','verification_status','photo_paths'],
    sale_availability: ['owner_name','contact','property_availability','demand','location','size','measurement','measurement_unit','floor','bedrooms','bathrooms','facilities','nearby_landmarks','verification_status','photo_paths'],
    properties: ['title','property_type','status','owner_name','owner_contact','location','area','floor','bedrooms','bathrooms','facilities','nearby_landmarks','verification_status','photo_paths'],
  };
  const fields = fieldSets[table] || [];
  if (!fields.length) return null;
  const missing = fields.filter(key => String(row[key] ?? '').trim() === '');
  const score = Math.round(((fields.length - missing.length) / fields.length) * 100);
  return { score, missing };
}

function listingQualityHtml(table, row = {}) {
  const quality = listingQuality(table, row);
  if (!quality) return '';
  const tone = quality.score >= 80 ? 'good' : quality.score >= 55 ? 'warn' : 'bad';
  const missing = quality.missing.length
    ? quality.missing.slice(0, 8).map(key => fieldLabel(table, key)).join(', ')
    : 'Ready for client presentation';
  return `
    <div class="quality-panel ${tone}">
      <div>
        <strong>${quality.score}% Listing Complete</strong>
        <span>${escapeHtml(missing)}</span>
      </div>
      <div class="quality-meter"><i style="width:${quality.score}%"></i></div>
    </div>
  `;
}

async function api(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${API}${path}`, { ...opts, headers });
  let data = {};
  try {
    data = await res.json();
  } catch (_err) {
    data = {};
  }
  if (!res.ok) {
    const detail = data.detail;
    let message = 'Request failed';
    if (typeof detail === 'string') {
      message = detail;
    } else if (detail?.message) {
      const lines = Array.isArray(detail.errors) ? detail.errors : [];
      message = [detail.message, ...lines.map(item => `- ${item}`)].join('\n');
    }
    if (res.status === 401 && path !== '/api/auth/login') logout();
    throw new Error(message);
  }
  return data;
}

async function apiBlob(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API}${path}`, { ...opts, headers });
  if (res.status === 401) { logout(); throw new Error('Unauthorized'); }
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (typeof data.detail === 'string') message = data.detail;
      else if (data.detail?.message) message = data.detail.message;
    } catch (_) {}
    throw new Error(message);
  }
  return res.blob();
}

function logout() { token = null; localStorage.removeItem('token'); currentUser = null; showLogin(); }
function showLogin() { $('login-screen').classList.remove('hidden'); $('main-screen').classList.add('hidden'); }
function showMain() { $('login-screen').classList.add('hidden'); $('main-screen').classList.remove('hidden'); }

function isAdmin() {
  const role = normalizeRole(currentUser?.role);
  return role === 'Super Admin' || role === 'Admin';
}
function canViewEcosystem() {
  const role = normalizeRole(currentUser?.role);
  return role === 'Super Admin' || role === 'Admin' || role === 'Manager';
}
function allowedTabs() { return ROLE_TABS[normalizeRole(currentUser?.role)] || ['rent','sale','find']; }
function canAccessTab(tab) { return allowedTabs().includes(tab); }
function firstAllowedTab() { return allowedTabs()[0] || 'rent'; }
function canWriteTable(table) {
  const role = normalizeRole(currentUser?.role);
  if (['rented_properties','sold_properties','wf_instances','wf_approvals','wf_sla_log','wf_audit_log'].includes(table)) return false;
  if (role === 'Viewer') return false;
  if (role === 'Staff') return PHASE1_TABLES.includes(table);
  return true;
}

function setupNavigationForRole() {
  const allowed = new Set(allowedTabs());
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('hidden', !allowed.has(el.dataset.tab));
  });
  document.querySelectorAll('.nav-section').forEach(section => {
    let visible = false;
    let node = section.nextElementSibling;
    while (node && !node.classList.contains('nav-section')) {
      if (node.classList?.contains('nav-item') && !node.classList.contains('hidden')) visible = true;
      node = node.nextElementSibling;
    }
    section.classList.toggle('hidden', !visible);
  });
  $('btn-settings').classList.toggle('hidden', !isAdmin());
}

function switchTab(tab) {
  if (!canAccessTab(tab)) tab = firstAllowedTab();
  if (tab === 'rent' && !(currentSub in SUB_TABLES.rent)) currentSub = 'rent_requirements';
  if (tab === 'sale' && !(currentSub in SUB_TABLES.sale)) currentSub = 'sale_requirements';
  if (tab === 'successfactors' && !(currentSub in SUB_TABLES.successfactors)) currentSub = 'sf_employees';
  if (tab === 'workflow' && !(currentSub in SUB_TABLES.workflow)) currentSub = 'wf_workflows';
  currentTab = tab;
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  const el = $(`tab-${tab}`);
  if (el) el.classList.add('active');
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  document.querySelector(`.nav-item[data-tab="${tab}"]`)?.classList.add('active');
  const names = {phase1:'QT_CRM Desk',dashboard:'Dashboard',rent:'Rent Dealings',sale:'Sale Dealings',find:'Find',followups:'Follow-ups',financial:'Financial',employees:'Employees',clients:'Clients',properties:'Properties',successfactors:'SuccessFactors',workflow:'Workflow Engine',reports:'Reports',approvals:'Approvals',audit:'Audit History'};
  $('page-title').textContent = names[tab] || tab;
  setPageSubtitle(tab);
  loadTab(tab);
}

function switchSub(sub) {
  currentSub = sub;
  const parent = document.querySelector(`#tab-${currentTab} .sub-nav`);
  if (parent) {
    parent.querySelectorAll('.sub-tab').forEach(el => el.classList.remove('active'));
    parent.querySelector(`.sub-tab[data-sub="${sub}"]`)?.classList.add('active');
  }
  loadTable(sub);
  const btn = document.querySelector(`#tab-${currentTab} .add-btn`);
  if (btn) btn.dataset.table = sub;
}

$('login-form').addEventListener('submit', async e => {
  e.preventDefault();
  const username = $('login-username').value.trim();
  const password = $('login-password').value;
  $('login-error').textContent = '';
  try {
    const data = await api('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) });
    token = data.access_token;
    localStorage.setItem('token', token);
    currentUser = data.user;
    currentUser.role = normalizeRole(currentUser.role);
    $('user-badge').textContent = currentUser.role;
    setupNavigationForRole();
    showMain();
    switchTab(firstAllowedTab());
  } catch (err) {
    $('login-error').textContent = err.message;
  }
});

$('btn-logout').addEventListener('click', logout);
$('btn-settings').addEventListener('click', openSettings);
$('btn-refresh')?.addEventListener('click', refreshCurrentView);
$('btn-find-shortcut')?.addEventListener('click', () => switchTab('find'));
$('btn-run-backup')?.addEventListener('click', runBackupNow);
$('find-button')?.addEventListener('click', runFind);
$('find-query')?.addEventListener('keydown', e => {
  if (e.key === 'Enter') runFind();
});
$('find-source')?.addEventListener('change', () => {
  if (($('find-query')?.value || '').trim()) runFind();
});
$('phase-search-button')?.addEventListener('click', runPhaseSearch);
$('phase-search-query')?.addEventListener('keydown', e => {
  if (e.key === 'Enter') runPhaseSearch();
});
$('btn-load-approvals')?.addEventListener('click', loadApprovals);

document.querySelectorAll('.nav-item').forEach(el => {
  el.addEventListener('click', () => switchTab(el.dataset.tab));
});

document.querySelectorAll('.phase-card').forEach(el => {
  el.addEventListener('click', () => openPhaseSection(el.dataset.phaseTable));
});

setNetworkLabels();

document.addEventListener('click', e => {
  if (e.target.classList.contains('sub-tab')) switchSub(e.target.dataset.sub);
});

$('modal-close').addEventListener('click', closeModal);
$('modal-cancel').addEventListener('click', closeModal);
$('modal-overlay').addEventListener('click', e => { if (e.target === $('modal-overlay')) closeModal(); });
$('modal-save').onclick = saveForm;

// Keyboard navigation: Escape closes modal and menus
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    // Close modal if open
    if (!$('modal-overlay').classList.contains('hidden')) {
      closeModal();
      e.preventDefault();
      return;
    }
    // Close any open menu dropdowns
    document.querySelectorAll('.menu-dropdown.active').forEach(d => d.classList.remove('active'));
    document.querySelectorAll('.menu-item.open').forEach(i => i.classList.remove('open'));
    // Close mobile sidebar if open
    const sidebar = document.getElementById('sidebar');
    if (sidebar && sidebar.classList.contains('open')) {
      sidebar.classList.remove('open');
      const overlay = document.getElementById('sidebar-overlay');
      if (overlay) overlay.classList.remove('visible');
    }
  }
});

// Keyboard navigation for menu bar
document.querySelectorAll('.menu-item').forEach(item => {
  item.setAttribute('tabindex', '0');
  item.setAttribute('role', 'menuitem');
  item.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      item.click();
    }
    if (e.key === 'ArrowRight') {
      const next = item.nextElementSibling;
      if (next && next.classList.contains('menu-item')) next.focus();
    }
    if (e.key === 'ArrowLeft') {
      const prev = item.previousElementSibling;
      if (prev && prev.classList.contains('menu-item')) prev.focus();
    }
  });
});

// Make menu dropdown containers role=menu, and items keyboard accessible
document.querySelectorAll('.menu-dropdown').forEach(d => d.setAttribute('role', 'menu'));
document.querySelectorAll('.menu-dropdown-item').forEach(item => {
  item.setAttribute('tabindex', '0');
  item.setAttribute('role', 'menuitem');
  item.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      item.click();
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      const next = item.nextElementSibling;
      if (next) next.focus();
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      const prev = item.previousElementSibling;
      if (prev) prev.focus();
    }
  });
});

// Make nav items keyboard accessible
document.querySelectorAll('.nav-item').forEach(item => {
  item.setAttribute('tabindex', '0');
  item.setAttribute('role', 'link');
  item.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      item.click();
    }
  });
});

// Add ARIA roles to sub-tabs and table tabs
document.querySelectorAll('.sub-tab, .table-tab').forEach(tab => {
  tab.setAttribute('tabindex', '0');
  tab.setAttribute('role', 'tab');
  tab.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      tab.click();
    }
  });
});

function sidebarIsManuallyCollapsed() {
  return document.getElementById('sidebar-toggle')?.classList.contains('sidebar-collapsed') || false;
}

function hideSidebarForFocus() {
  const sidebar = document.getElementById('sidebar');
  if (sidebar && !sidebarIsManuallyCollapsed()) {
    sidebar.classList.add('sidebar-hidden');
  }
}

function restoreSidebarAfterFocus() {
  const sidebar = document.getElementById('sidebar');
  if (sidebar && !sidebarIsManuallyCollapsed()) {
    sidebar.classList.remove('sidebar-hidden');
  }
}

function closeModal() {
  $('modal-overlay').classList.add('hidden');
  $('modal-body').innerHTML = '';
  $('modal').classList.remove('report-modal');
  closeReadonlyMode();
  $('modal-save').textContent = 'Save';
  $('modal-save').onclick = saveForm;
  restoreSidebarAfterFocus();
}
function openModal(title, options = {}) {
  $('modal-title').textContent = title;
  $('modal').classList.toggle('report-modal', Boolean(options.wide));
  $('modal-overlay').classList.remove('hidden');
}

document.addEventListener('click', e => {
  if (e.target.classList.contains('add-btn')) {
    const table = e.target.dataset.table;
    showAddForm(table);
  }
  if (e.target.classList.contains('module-report-btn')) {
    printDealingsReport(e.target.dataset.reportKind || 'all');
  }
  const actionButton = e.target.closest?.('.row-action');
  if (actionButton) {
    const table = actionButton.dataset.table;
    const id = Number(actionButton.dataset.id);
    const action = actionButton.dataset.rowAction;
    const row = stateForTable(table).rowMap.get(id) || {};
    if (action === 'edit') showEditForm(table, id);
    if (action === 'delete') deleteRecord(table, id);
    if (action === 'approve') approveRecord(table, id);
    if (action === 'reject') rejectRecord(table, id);
    if (action === 'match') findMatch(table, id);
    if (action === 'deal') convertToDeal(table, id, row.client_name || row.owner_name || '');
    if (action === 'rented') markAvailability(table, id, 'Rented');
    if (action === 'sold') markAvailability(table, id, 'Sold');
  }
});

document.addEventListener('change', e => {
  if (e.target.classList.contains('row-select')) {
    const table = e.target.dataset.table;
    const id = Number(e.target.dataset.id);
    const state = stateForTable(table);
    if (e.target.checked) state.selected.add(id); else state.selected.delete(id);
    updateSelectionToolbar(table);
  }
  if (e.target.classList.contains('page-select')) {
    const table = e.target.dataset.table;
    if (e.target.checked) selectVisibleRows(table); else clearSelectedRows(table);
  }
});

async function loadTab(tab) {
  if (tab === 'phase1') return loadPhase1Home();
  if (tab === 'approvals') return loadApprovals();
  if (tab === 'dashboard') return loadDashboard();
  if (tab === 'reports') return loadReports();
  if (tab === 'find') return loadFind();
  if (tab === 'followups') return loadFollowups();
  if (tab === 'audit') return loadAudit();
  if (tab === 'rent') return loadTable(currentSub);
  if (tab === 'sale') { currentSub = currentSub in SUB_TABLES.sale ? currentSub : 'sale_requirements'; return loadTable(currentSub); }
  if (tab === 'financial') { currentSub = currentSub in SUB_TABLES.financial ? currentSub : 'income_transactions'; return loadTable(currentSub); }
  if (tab === 'employees') { currentSub = currentSub in SUB_TABLES.employees ? currentSub : 'employees'; return loadTable(currentSub); }
  if (tab === 'successfactors') { currentSub = currentSub in SUB_TABLES.successfactors ? currentSub : 'sf_employees'; return loadTable(currentSub); }
  if (tab === 'workflow') { currentSub = currentSub in SUB_TABLES.workflow ? currentSub : 'wf_workflows'; return loadTable(currentSub); }
  if (tab === 'clients') return loadTable('clients');
  if (tab === 'broker_contacts') return loadTable('broker_contacts');
  if (tab === 'properties') return loadTable('properties');
}

async function loadPhase1Settings() {
  try {
    const data = await api('/api/records/phase1/settings');
    phase1Settings = {
      areas: normalizeOptionList(data.areas, DEFAULT_PHASE1.areas),
      facilities: normalizeOptionList(data.facilities, DEFAULT_PHASE1.facilities),
      floors: normalizeOptionList(data.floors, DEFAULT_PHASE1.floors),
      propertyTypes: normalizeOptionList(data.property_types, DEFAULT_PHASE1.propertyTypes),
      measurementUnits: normalizeOptionList(data.measurement_units, DEFAULT_PHASE1.measurementUnits),
      expenseCategories: normalizeOptionList(data.expense_categories, EXPENSE_CATEGORIES),
      theme: data.theme || 'Light',
      company_name: data.company_name || companyName,
      company_address: data.company_address || '',
      company_phone: data.company_phone || '',
      company_email: data.company_email || '',
      company_logo: data.company_logo || '',
      currency_symbol: data.currency_symbol || 'Rs.',
      default_commission: data.default_commission || '',
      tax_rate: data.tax_rate || '',
      bank_account: data.bank_account || ''
    };
    setCompanyName(phase1Settings.company_name || companyName);
    document.body.classList.toggle('dark-theme', phase1Settings.theme === 'Dark');
    ['rent_requirements','rent_availability','sale_requirements','sale_availability','properties'].forEach(table => {
      (FIELDS[table] || []).forEach(field => {
        if (field.key === 'location') field.options = phase1Settings.areas;
        if (field.key === 'facilities') field.options = phase1Settings.facilities;
        if (field.key === 'floor') field.options = phase1Settings.floors;
        if (field.key === 'property_requires' || field.key === 'property_availability') field.options = phase1Settings.propertyTypes;
        if (field.key === 'measurement_unit') field.options = phase1Settings.measurementUnits;
      });
    });
    const expenseCategory = (FIELDS.expense_transactions || []).find(field => field.key === 'expense_category');
    if (expenseCategory) expenseCategory.options = phase1Settings.expenseCategories;
  } catch (err) {
    console.warn('Phase 1 settings unavailable', err);
  }
}

async function loadPhase1Home() {
  await loadPhase1Settings();
  $('phase1-home')?.classList.remove('hidden');
  $('phase1-section')?.classList.add('hidden');
  $('phase1-form')?.classList.add('hidden');
  phase1CurrentTable = '';
  // Load desktop grid with default table
  setTimeout(() => {
    if (document.getElementById('data-grid-body')) {
      loadDesktopGrid('rent_requirements');
    }
  }, 100);
}

function openPhaseSection(table) {
  phase1CurrentTable = table;
  stateForTable(table).deletedOnly = false;
  $('phase1-home')?.classList.add('hidden');
  $('phase1-form')?.classList.add('hidden');
  $('phase1-section')?.classList.remove('hidden');
  currentTab = 'phase1';
  loadTable(table);
}

async function runPhaseSearch() {
  const q = ($('phase-search-query')?.value || '').trim();
  const container = $('phase-search-results');
  if (!container) return;
  container.innerHTML = '';
  if (!q) return;
  setSyncStatus('Searching...', 'busy');
  try {
    for (const table of PHASE1_TABLES) {
      const data = await api(`/api/records/${table}?limit=25&q=${encodeURIComponent(q)}`);
      const rows = data.rows || [];
      const fields = tableDisplayFields(table).slice(0, 7);
      const block = document.createElement('div');
      block.className = 'phase-result-group glass-card';
      block.innerHTML = `
        <div class="phase-result-head">
          <h3>${escapeHtml(PHASE1_LABELS[table])} (${rows.length})</h3>
          <button class="btn btn-sm" type="button">Open Section</button>
        </div>
        <div class="table-container mini-results">
          <table><thead><tr>${fields.map(f => `<th>${escapeHtml(f.label)}</th>`).join('')}</tr></thead>
          <tbody>${rows.length ? rows.map(row => `<tr>${fields.map(f => `<td>${escapeHtml(formatCell(row[f.key], f.key))}</td>`).join('')}</tr>`).join('') : `<tr><td colspan="${fields.length}" class="empty-cell">No matches.</td></tr>`}</tbody></table>
        </div>
      `;
      block.querySelector('button')?.addEventListener('click', () => openPhaseSection(table));
      container.appendChild(block);
    }
    setSyncStatus(`Search complete ${formatClock()}`);
  } catch (err) {
    alert(err.message);
    setSyncStatus('Search failed', 'error');
  }
}

async function loadApprovals() {
  if (!isAdmin()) return;
  const table = $('approvals-table');
  if (!table) return;
  renderTableLoading(table, 8);
  try {
    const data = await api('/api/records/approvals/pending');
    const rows = data.rows || [];
    table.querySelector('thead').innerHTML = '<tr>' + ['ID','Action','Section','Record','Requested By','Requested At','Payload','Review'].map(h => `<th>${h}</th>`).join('') + '</tr>';
    const body = table.querySelector('tbody');
    if (!rows.length) {
      body.innerHTML = '<tr><td colspan="8" class="empty-cell">No pending approvals.</td></tr>';
      return;
    }
    body.innerHTML = rows.map(row => `
      <tr>
        <td>${row.id}</td>
        <td>${escapeHtml(row.action)}</td>
        <td>${escapeHtml(row.table_label)}</td>
        <td>${escapeHtml(row.record_id || '')}</td>
        <td>${escapeHtml(row.requested_by || '')}</td>
        <td>${escapeHtml(row.requested_at || '')}</td>
        <td><pre class="payload-preview">${escapeHtml(JSON.stringify(row.payload || {}, null, 2))}</pre></td>
        <td>
          <button class="btn btn-sm btn-primary approval-review" data-id="${row.id}" data-approved="1">Approve</button>
          <button class="btn btn-sm btn-danger approval-review" data-id="${row.id}" data-approved="0">Reject</button>
        </td>
      </tr>
    `).join('');
    body.querySelectorAll('.approval-review').forEach(btn => {
      btn.addEventListener('click', () => reviewApproval(btn.dataset.id, btn.dataset.approved === '1'));
    });
  } catch (err) {
    alert(err.message);
  }
}

async function reviewApproval(id, approved) {
  const comment = approved ? '' : (prompt('Reason for rejection:') || 'Rejected');
  try {
    await api(`/api/records/approvals/${id}/review`, { method: 'POST', body: JSON.stringify({ approved, comment }) });
    await loadApprovals();
    if (phase1CurrentTable) await loadTable(phase1CurrentTable);
  } catch (err) {
    alert(err.message);
  }
}

function loadFind() {
  const input = $('find-query');
  const tbody = $('find-table')?.querySelector('tbody');
  if (input) input.focus();
  if (tbody && !input?.value.trim()) {
    renderFindRows([]);
    $('find-status').textContent = 'Search rent and sale records visible to your user role.';
  }
}

function findField(fields, keys) {
  for (const key of keys) {
    const value = fields?.[key];
    if (value !== undefined && value !== null && String(value).trim() !== '') return value;
  }
  return '';
}

function normalizeFindRow(row) {
  const fields = row.fields || {};
  const table = row.table || '';
  const requirement = table.includes('requirements');
  const name = findField(fields, ['client_name','owner_name','name','full_name','employee_id','title','tenant_name','vendor_name','income_type','expense_category']) || row.label || '';
  const property = requirement
    ? findField(fields, ['property_requires','property_type'])
    : findField(fields, ['property_availability','property_type']);
  const amount = findField(fields, ['budget','monthly_rent','demand','asking_price','sale_price','amount','base_salary','net_salary']);
  const status = findField(fields, ['client_status','client_broker','broker','posted_by','status','verification_status','workflow_stage','payment_method']);
  const matched = Array.isArray(row.matched_columns) && row.matched_columns.length
    ? `Matched: ${row.matched_columns.slice(0, 5).map(col => col.replace(/_/g, ' ')).join(', ')}`
    : '';
  return {
    table,
    type: row.source || SEARCH_TABLE_LABELS[table] || table.replace(/_/g, ' '),
    id: row.id,
    date: findField(fields, ['date','transaction_date','payment_date','hire_date','date_created','date_posted','created_at']),
    name,
    status,
    contact: findField(fields, ['contact_phone','owner_phone','contact','phone','owner_contact','email']) || row.detail || '',
    property,
    amount,
    floor: findField(fields, ['floor','floor_no']),
    location: findField(fields, ['location','area','address','department']),
    facilities: findField(fields, ['facilities']),
    remarks: findField(fields, ['remarks','description','notes','receipt_no','invoice_no']) || matched
  };
}

function renderFindRows(rows) {
  const table = $('find-table');
  if (!table) return;
  table.querySelector('thead').innerHTML = `<tr>${[
    'Type','Sr No.','Date','Name','Status','Contact No.','Property','Budget/Rent/Demand','Floor','Location','Facilities','Remarks','Actions'
  ].map(h => `<th>${h}</th>`).join('')}</tr>`;
  const body = table.querySelector('tbody');
  if (!rows.length) {
    body.innerHTML = `<tr><td colspan="13" class="empty-cell">No find results yet.</td></tr>`;
    return;
  }
  body.innerHTML = rows.map(row => {
    const normalized = normalizeFindRow(row);
    const cells = SEARCH_COLUMNS.map(key => `<td>${escapeHtml(formatCell(normalized[key], key))}</td>`).join('');
    const action = `<button class="btn btn-sm" onclick="showEditForm('${normalized.table}', ${Number(normalized.id) || 0})">Open</button>`;
    return `<tr>${cells}<td class="actions">${action}</td></tr>`;
  }).join('');
}

async function runFind() {
  const query = ($('find-query')?.value || '').trim();
  const source = $('find-source')?.value || '';
  if (!query) {
    renderFindRows([]);
    $('find-status').textContent = 'Type at least one character to find records.';
    return;
  }
  $('find-status').textContent = `Finding "${query}"...`;
  try {
    const tableParam = source ? `&table=${encodeURIComponent(source)}` : '';
    const data = await api(`/api/records/search/global?q=${encodeURIComponent(query)}&limit=100${tableParam}`);
    let rows = data.results || [];
    if (source) rows = rows.filter(row => row.table === source);
    renderFindRows(rows);
    const label = source ? (SEARCH_TABLE_LABELS[source] || source.replace(/_/g, ' ')) : 'All';
    $('find-status').textContent = rows.length
      ? `Found ${rows.length} result${rows.length === 1 ? '' : 's'} for "${query}" in ${label}.`
      : `No records found for "${query}" in ${label}.`;
  } catch (err) {
    $('find-status').textContent = err.message;
  }
}

async function loadDashboard() {
  try {
    setSyncStatus('Loading dashboard...', 'busy');
    const dashboard = $('dashboard-cards');
    dashboard.className = 'report-dashboard loading';
    dashboard.innerHTML = `
      <div class="report-title-block">
        <span class="skeleton-row"></span>
        <span class="skeleton-row" style="width:42%"></span>
      </div>
      <div class="summary-kpis">
        ${Array.from({ length: 7 }).map(() => '<div class="summary-tile"><span class="skeleton-row"></span><span class="skeleton-row" style="width:60%"></span></div>').join('')}
      </div>
      <div class="summary-insight-grid">
        <div class="approval-hero skeleton-panel"></div>
        <div class="summary-panel skeleton-panel"></div>
        <div class="summary-panel skeleton-panel"></div>
        <div class="summary-panel skeleton-panel"></div>
      </div>
    `;
    const data = await api('/api/reports/dashboard');
    setCompanyName(data.company);
    dashboard.className = 'report-dashboard';
    dashboard.innerHTML = renderDashboardReport(data);
    await loadEcosystemHealth();
    setSyncStatus(`Dashboard updated ${formatClock()}`);
  } catch (err) {
    console.error(err);
    setSyncStatus(err.message || 'Dashboard failed', 'error');
  }
}

function dashboardNum(value) {
  const number = Number(value || 0);
  return Number.isFinite(number) ? number.toLocaleString() : '0';
}

function clampPercent(value) {
  const number = Number(value || 0);
  if (!Number.isFinite(number)) return 0;
  return Math.max(0, Math.min(100, number));
}

function renderDashboardReport(data) {
  const kpis = [
    { label: 'Rent Requirements', value: data.rent_requirements, tone: 'blue' },
    { label: 'Rent Availability', value: data.rent_available, tone: 'cyan' },
    { label: 'Sale Requirements', value: data.sale_requirements, tone: 'silver' },
    { label: 'Sale Availability', value: data.sale_available, tone: 'green' },
    { label: 'Properties', value: data.properties, tone: 'royal' },
    { label: 'Clients', value: data.clients, tone: 'sky' },
    { label: 'Employee', value: data.employees, tone: 'slate' }
  ];
  const generatedBy = data.generated_by || 'CRM User';
  const generatedRole = data.generated_role || 'Staff';
  return `
    <div class="report-surface">
      <div class="report-title-block">
        <h1>${escapeHtml(data.company || 'MBM Enterprises')} Report Summary</h1>
        <p>${escapeHtml(generatedBy)}, ${escapeHtml(generatedRole)}</p>
      </div>
      <div class="summary-kpis">
        ${kpis.map(card => `
          <div class="summary-tile ${card.tone}">
            <strong>${dashboardNum(card.value)}</strong>
            <span>${escapeHtml(card.label)}</span>
          </div>
        `).join('')}
      </div>
      <div class="summary-insight-grid">
        <section class="approval-hero">
          <strong>${dashboardNum(data.pending_approvals)}</strong>
          <span>Pending Approvals</span>
          <small>Needs Admin Review</small>
        </section>
        ${renderDemandSupplyPanel(data.demand_supply || [])}
        ${renderClientSegmentsPanel(data.client_segments || [], data.clients || 0, data.operations || [])}
        ${renderRoadmapPanel(data.roadmap || [])}
      </div>
    </div>
  `;
}

function renderDemandSupplyPanel(rows) {
  const safeRows = rows.length ? rows.slice(0, 6) : [{ location: 'No Data', rent_requirements: 0, rent_availability: 0 }];
  const maxValue = Math.max(1, ...safeRows.flatMap(row => [Number(row.rent_requirements || 0), Number(row.rent_availability || 0)]));
  return `
    <section class="summary-panel demand-panel">
      <h2>Rent Demand vs. Supply</h2>
      <div class="demand-chart" aria-label="Rent demand and supply by location">
        ${safeRows.map(row => {
          const req = Number(row.rent_requirements || 0);
          const av = Number(row.rent_availability || 0);
          return `
            <div class="demand-group">
              <div class="bar-stage">
                <span class="demand-bar req" style="height:${Math.max(4, Math.round((req / maxValue) * 100))}%"></span>
                <span class="demand-bar av" style="height:${Math.max(4, Math.round((av / maxValue) * 100))}%"></span>
              </div>
              <span class="bar-location">${escapeHtml(row.location || 'Area')}</span>
            </div>
          `;
        }).join('')}
      </div>
      <div class="chart-legend">
        <span><i class="legend-blue"></i>Rent Requirements</span>
        <span><i class="legend-green"></i>Rent Availability</span>
      </div>
    </section>
  `;
}

function renderClientSegmentsPanel(segments, clientTotal, operations) {
  const palette = ['#1976d2', '#43a047', '#007c91'];
  const safeSegments = (segments.length ? segments : [
    { label: 'Active Searchers', percent: 0, value: 0, color: palette[0] },
    { label: 'Long-Term Leads', percent: 0, value: 0, color: palette[1] },
    { label: 'Past Clients', percent: 0, value: 0, color: palette[2] }
  ]).slice(0, 3).map((segment, index) => ({
    ...segment,
    percent: clampPercent(segment.percent),
    color: segment.color || palette[index] || palette[0]
  }));
  let cursor = 0;
  const gradientStops = safeSegments.map(segment => {
    const start = cursor;
    cursor += segment.percent;
    return `${segment.color} ${start}% ${Math.max(start, cursor)}%`;
  });
  const donutGradient = cursor > 0 ? gradientStops.join(', ') : '#cbd5e1 0% 100%';
  const rows = (operations.length ? operations : [
    { label: 'First Response', value: '< 15 Min', tone: 'blue' },
    { label: 'Pending Approvals', value: 'Review Queue', tone: 'orange' },
    { label: 'Conversion Rate', value: '0%', tone: 'green' }
  ]).slice(0, 3);
  return `
    <section class="summary-panel client-panel">
      <div class="donut-wrap">
        <div class="client-donut" style="background: conic-gradient(${donutGradient});">
          <span>${dashboardNum(clientTotal)}</span>
        </div>
        <div class="segment-list">
          <h2>Client Segments</h2>
          ${safeSegments.map(segment => `
            <div class="segment-row">
              <span><i style="background:${escapeHtml(segment.color)}"></i>${escapeHtml(segment.label || '')}</span>
              <strong>${dashboardNum(segment.percent)}%</strong>
            </div>
          `).join('')}
        </div>
      </div>
      <div class="operation-table">
        ${rows.map(row => `
          <div class="operation-row">
            <i class="${escapeHtml(row.tone || 'blue')}"></i>
            <span>${escapeHtml(row.label || '')}</span>
            <strong>${escapeHtml(row.value || '')}</strong>
          </div>
        `).join('')}
      </div>
    </section>
  `;
}

function renderRoadmapPanel(roadmap) {
  const rows = roadmap.length ? roadmap.slice(0, 3) : [
    { period: '30 Days', response_time: 35, approvals_cleared: 20, conversion: 12 },
    { period: '90 Days', response_time: 65, approvals_cleared: 60, conversion: 35 },
    { period: '180 Days', response_time: 72, approvals_cleared: 82, conversion: 50 }
  ];
  const series = [
    { key: 'response_time', className: 'line-blue' },
    { key: 'approvals_cleared', className: 'line-orange' },
    { key: 'conversion', className: 'line-green' }
  ];
  const xPoints = [54, 202, 350];
  const yFor = value => 156 - (clampPercent(value) * 1.16);
  const polylines = series.map(item => {
    const points = rows.map((row, index) => `${xPoints[index] || xPoints[xPoints.length - 1]},${yFor(row[item.key])}`).join(' ');
    const circles = rows.map((row, index) => `<circle class="${item.className}" cx="${xPoints[index] || xPoints[xPoints.length - 1]}" cy="${yFor(row[item.key])}" r="6"></circle>`).join('');
    return `<polyline class="${item.className}" points="${points}"></polyline>${circles}`;
  }).join('');
  return `
    <section class="summary-panel roadmap-panel">
      <h2>30 / 90 / 180 Day Roadmap</h2>
      <svg class="roadmap-chart" viewBox="0 0 410 190" role="img" aria-label="Operational roadmap">
        <line x1="32" y1="38" x2="378" y2="38"></line>
        <line x1="32" y1="78" x2="378" y2="78"></line>
        <line x1="32" y1="118" x2="378" y2="118"></line>
        <line x1="32" y1="156" x2="378" y2="156"></line>
        ${polylines}
        ${rows.map((row, index) => `<text x="${xPoints[index] || 350}" y="180" text-anchor="middle">${escapeHtml(row.period || '')}</text>`).join('')}
      </svg>
      <div class="chart-legend roadmap-legend">
        <span><i class="legend-blue"></i>Response Time</span>
        <span><i class="legend-orange"></i>Approvals Cleared</span>
        <span><i class="legend-green"></i>Conversion</span>
      </div>
    </section>
  `;
}

async function loadEcosystemHealth() {
  const panel = $('ecosystem-panel');
  if (!panel) return;
  if (!canViewEcosystem()) {
    panel.innerHTML = '';
    return;
  }
  panel.innerHTML = `
    <div class="glass-card ecosystem-card">
      <div class="ecosystem-header">
        <div>
          <h2>QT_CRM Ecosystem</h2>
          <p>Checking Desktop/Web database alignment, backups, settings, approvals, and Phase 1 tables.</p>
        </div>
        <span class="status-pill busy">Checking...</span>
      </div>
      <div class="ecosystem-grid">
        <span class="skeleton-row"></span>
        <span class="skeleton-row"></span>
        <span class="skeleton-row"></span>
      </div>
    </div>
  `;
  try {
    const health = await api('/api/records/ecosystem/health');
    const phaseRows = Object.values(health.phase1 || {});
    const active = health.phase1_total_active ?? phaseRows.reduce((sum, row) => sum + Number(row.active || 0), 0);
    const recycled = health.phase1_total_recycled ?? phaseRows.reduce((sum, row) => sum + Number(row.recycled || 0), 0);
    const issues = health.issues || [];
    const issueHtml = issues.length
      ? issues.slice(0, 5).map(item => `<li class="${escapeHtml(item.severity || 'warning')}">${escapeHtml(item.message || '')}</li>`).join('')
      : '<li class="ok">No ecosystem issues found.</li>';
    const backup = health.backups || {};
    const settings = health.settings || {};
    panel.innerHTML = `
      <div class="glass-card ecosystem-card">
        <div class="ecosystem-header">
          <div>
            <h2>QT_CRM Ecosystem</h2>
            <p>Last checked ${escapeHtml(formatCell(health.generated_at || '', 'created_at'))}</p>
          </div>
          <span class="health-badge ${health.ok ? 'ok' : 'warn'}">${escapeHtml(health.status || 'Unknown')}</span>
        </div>
        <div class="ecosystem-grid">
          <div class="ecosystem-metric"><span>${active}</span><label>Phase 1 active entries</label></div>
          <div class="ecosystem-metric"><span>${recycled}</span><label>Recycled entries</label></div>
          <div class="ecosystem-metric"><span>${health.approvals?.pending || 0}</span><label>Pending approvals</label></div>
          <div class="ecosystem-metric"><span>${backup.count || 0}</span><label>Backups found</label></div>
          <div class="ecosystem-metric"><span>${formatBytes(health.database?.size_bytes || 0)}</span><label>Database size</label></div>
          <div class="ecosystem-metric"><span>${escapeHtml(settings.theme || '-')}</span><label>Theme setting</label></div>
        </div>
        <div class="ecosystem-detail">
          <div>
            <h3>Phase 1 Table Counts</h3>
            <div class="ecosystem-table-list">
              ${phaseRows.map(row => `<div><strong>${escapeHtml(row.label || '')}</strong><span>${Number(row.active || 0)} active, ${Number(row.recycled || 0)} recycled</span></div>`).join('')}
            </div>
          </div>
          <div>
            <h3>Issues</h3>
            <ul class="ecosystem-issues">${issueHtml}</ul>
          </div>
        </div>
        <div class="muted-line">Latest backup: ${escapeHtml(backup.latest_path || 'No backup file found')}</div>
      </div>
    `;
  } catch (err) {
    panel.innerHTML = `
      <div class="glass-card ecosystem-card">
        <div class="ecosystem-header">
          <div>
            <h2>QT_CRM Ecosystem</h2>
            <p>Health check could not be loaded.</p>
          </div>
          <span class="health-badge warn">Unavailable</span>
        </div>
        <div class="error-msg">${escapeHtml(err.message || 'Ecosystem health failed')}</div>
      </div>
    `;
  }
}

function statusBadge(status) {
  return dataBadge(status || 'Draft', 'approval');
}

function badgeTone(value, family) {
  const text = String(value || '').trim().toLowerCase();
  if (family === 'property') {
    if (text.includes('plot')) return 'property-plot';
    if (text.includes('shop') || text.includes('commercial')) return 'property-shop';
    if (text.includes('flat') || text.includes('apartment')) return 'property-flat';
    return 'property-default';
  }
  if (['client', 'owner', 'broker'].includes(text)) return `status-${text}`;
  if (text.includes('pending')) return 'status-pending';
  if (text.includes('rented') || text.includes('sold') || text.includes('available') || text.includes('approved')) return 'status-success';
  if (text.includes('reject') || text.includes('withdraw') || text.includes('deleted')) return 'status-danger';
  return 'status-default';
}

function dataBadge(value, family = 'status') {
  const text = value === undefined || value === null || value === '' ? '-' : String(value);
  const tone = badgeTone(text, family);
  return `<span class="data-badge ${tone}">${escapeHtml(text)}</span>`;
}

function isStatusColumn(key) {
  return ['client_status', 'client_broker', 'status', 'workflow_stage', 'approval_status', 'verification_status'].includes(key);
}

function isPropertyColumn(key) {
  return ['property_requires', 'property_availability', 'property_type', 'property_requirement'].includes(key);
}

function tableCellHtml(table, row, field) {
  const value = row[field.key] !== undefined && row[field.key] !== null ? row[field.key] : '';
  const display = formatCell(value, field.key);
  if (isPropertyColumn(field.key)) return `<td>${dataBadge(display, 'property')}</td>`;
  if (isStatusColumn(field.key)) return `<td>${dataBadge(display, 'status')}</td>`;
  return `<td>${escapeHtml(display)}</td>`;
}

function rowActionButton(label, action, table, id, className = '', style = '') {
  return `<button class="btn btn-sm row-action ${className}" type="button" data-row-action="${action}" data-table="${table}" data-id="${Number(id) || 0}"${style ? ` style="${style}"` : ''}>${escapeHtml(label)}</button>`;
}

function stateForTable(table) {
  if (!tableState[table]) {
    const defaultSort = TABLE_DEFAULT_SORT[table] || { sort: 'id', direction: 'desc' };
    tableState[table] = {
      offset: 0,
      limit: PHASE1_TABLES.includes(table) ? PHASE1_TABLE_PAGE_SIZE : TABLE_PAGE_SIZE,
      q: '',
      stage: '',
      status: '',
      date_from: '',
      date_to: '',
      area: '',
      office_address: '',
      home_address: '',
      sort: defaultSort.sort,
      direction: defaultSort.direction,
      deletedOnly: false,
      selected: new Set(),
      rows: [],
      rowMap: new Map(),
      controller: null,
    };
  }
  if (!(tableState[table].selected instanceof Set)) tableState[table].selected = new Set();
  if (!(tableState[table].rowMap instanceof Map)) tableState[table].rowMap = new Map();
  return tableState[table];
}

function tableHasField(table, key) {
  return (FIELDS[table] || []).some(field => field.key === key);
}

function sortFieldsForTable(table) {
  const seen = new Set();
  const options = [{ key: 'id', label: 'Serial No.' }, ...tableDisplayFields(table), ...(FIELDS[table] || [])];
  return options.filter(field => {
    if (!field?.key || seen.has(field.key)) return false;
    seen.add(field.key);
    return true;
  });
}

function statusOptionsForTable(table) {
  return table === 'rent_availability' || table === 'sale_availability'
    ? AVAILABILITY_STATUSES
    : GENERIC_STATUSES;
}

function scheduleTableReload(table) {
  clearTimeout(tableSearchTimer);
  tableSearchTimer = setTimeout(() => loadTable(table), 280);
}

function ensureTableControls(table) {
  const bar = document.querySelector(`#tab-${currentTab} .table-actions`);
  if (!bar) return stateForTable(table);
  const state = stateForTable(table);
  const staticAdd = bar.querySelector(':scope > .add-btn');
  if (staticAdd) staticAdd.classList.add('hidden');
  let titleRow = bar.querySelector('.table-title-row');
  if (!titleRow) {
    titleRow = document.createElement('div');
    titleRow.className = 'table-title-row';
    bar.prepend(titleRow);
  }
  const phaseAdmin = PHASE1_TABLES.includes(table) && isAdmin();
  const modeTitle = state.deletedOnly ? `${tableTitle(table)} - Recycle Bin` : tableTitle(table);
  titleRow.innerHTML = `
    <div>
      <div class="table-breadcrumb">QT CRM &rsaquo; QT_CRM Desk</div>
      <div class="table-section-title">${escapeHtml(modeTitle)}</div>
    </div>
    <div class="table-record-pill">Showing 0 of 0</div>
  `;
  let primary = bar.querySelector('.primary-tools');
  if (!primary) {
    primary = document.createElement('div');
    primary.className = 'primary-tools';
    titleRow.after(primary);
  }
  const pendingAction = PHASE1_TABLES.includes(table)
    ? '<button class="btn btn-warning" type="button" data-table-action="pending">Mark Pending</button>'
    : '';
  const canEditTable = canWriteTable(table) && (FIELDS[table] || []).some(field => !field.readonly);
  const markAction = table === 'rent_availability'
    ? '<button class="btn btn-primary" type="button" data-table-action="rented">Mark Rented</button>'
    : table === 'sale_availability'
      ? '<button class="btn btn-primary" type="button" data-table-action="sold">Mark Sold</button>'
      : '';
  const recycleAction = phaseAdmin
    ? state.deletedOnly
      ? '<button class="btn" type="button" data-table-action="active-list">Active List</button><button class="btn btn-primary" type="button" data-table-action="restore">Restore</button>'
      : '<button class="btn" type="button" data-table-action="recycle-bin">Recycle Bin</button>'
    : '';
  const addLabel = table.includes('requirements') ? '+ Add' : '+ Add';
  primary.innerHTML = `
    <div class="action-group">
      <button class="btn btn-primary add-btn" type="button" data-table="${table}">${addLabel}</button>
      <button class="btn" type="button" data-table-action="edit"${canEditTable ? '' : ' disabled'}>Edit</button>
      <button class="btn btn-danger" type="button" data-table-action="delete"${canEditTable ? '' : ' disabled'}>Delete</button>
    </div>
    <span class="action-divider" aria-hidden="true"></span>
    <div class="action-group">
      ${pendingAction}
      ${markAction}
      <button class="btn" type="button" data-table-action="ai">Search Match</button>
      <button class="btn" type="button" data-table-action="report">Report</button>
      ${recycleAction}
    </div>
    <span class="action-divider" aria-hidden="true"></span>
    <div class="action-group">
      <button class="btn" type="button" data-table-action="refresh">Refresh</button>
      ${PHASE1_TABLES.includes(table) ? '<button class="btn" type="button" data-table-action="import">Import Excel/CSV</button><button class="btn" type="button" data-table-action="export-excel">Export Excel</button><button class="btn" type="button" data-table-action="template">Template</button>' : ''}
      <button class="btn" type="button" data-table-action="export">Export CSV</button>
    </div>
  `;
  primary.querySelector('.add-btn')?.toggleAttribute('disabled', state.deletedOnly || !canEditTable);
  let actions = bar.querySelector('.selection-tools');
  if (!actions) {
    actions = document.createElement('div');
    actions.className = 'selection-tools';
  }
  primary.after(actions);
  actions.innerHTML = `
    <label class="selection-check"><input class="selection-select-all" type="checkbox" data-table="${table}"> Select All</label>
    <span class="selected-count">0 of 0 selected</span>
    <span class="selection-divider" aria-hidden="true"></span>
    <button class="btn" type="button" data-table-action="details">Details</button>
    <button class="btn" type="button" data-table-action="copy">Copy Selected</button>
    <button class="btn" type="button" data-table-action="clear">Clear Selection</button>
  `;
  let tools = bar.querySelector('.list-tools');
  if (!tools) {
    tools = document.createElement('div');
    tools.className = 'list-tools';
    actions.after(tools);
  }
  const stageSelect = PIPELINE_TABLES.includes(table)
    ? `<select class="toolbar-input table-stage" title="Pipeline stage">
        <option value="">All stages</option>
        ${DEAL_STAGES.map(stage => `<option value="${stage}">${stage}</option>`).join('')}
      </select>`
    : '';
  const statusSelect = tableHasField(table, 'status')
    ? `<select class="toolbar-input table-status" title="Status">
        <option value="">All status</option>
        ${statusOptionsForTable(table).map(status => `<option value="${status}">${status}</option>`).join('')}
      </select>`
    : '';
  const brokerAddressFilters = table === 'broker_contacts'
    ? `<input class="toolbar-input table-area-filter" type="search" placeholder="Area filter" value="${escapeHtml(state.area)}">
       <input class="toolbar-input table-office-filter" type="search" placeholder="Office address" value="${escapeHtml(state.office_address)}">
       <input class="toolbar-input table-home-filter" type="search" placeholder="Home address" value="${escapeHtml(state.home_address)}">`
    : '';
  const sortSelect = `<select class="toolbar-input table-sort" title="Sort by">
      ${sortFieldsForTable(table).map(field => `<option value="${field.key}"${state.sort === field.key ? ' selected' : ''}>Sort by ${escapeHtml(field.label || field.key)}</option>`).join('')}
    </select>`;
  tools.innerHTML = `
    <input class="toolbar-input table-query" type="search" placeholder="Keyword search" value="${escapeHtml(state.q)}">
    ${brokerAddressFilters}
    ${stageSelect}
    ${statusSelect}
    ${sortSelect}
    <select class="toolbar-input table-direction" title="Sort direction">
      <option value="desc"${state.direction === 'desc' ? ' selected' : ''}>Descending</option>
      <option value="asc"${state.direction === 'asc' ? ' selected' : ''}>Ascending</option>
    </select>
    <input class="toolbar-input mini-date table-from" type="date" value="${escapeHtml(state.date_from)}" title="Start date">
    <input class="toolbar-input mini-date table-to" type="date" value="${escapeHtml(state.date_to)}" title="End date">
    <button class="btn btn-sm pager-prev" type="button">Prev</button>
    <span class="pager-count">Page</span>
    <button class="btn btn-sm pager-next" type="button">Next</button>
  `;
  let attendanceSummary = bar.querySelector('.attendance-summary-strip');
  if (table === 'attendance') {
    if (!attendanceSummary) {
      attendanceSummary = document.createElement('div');
      attendanceSummary.className = 'attendance-summary-strip';
      tools.after(attendanceSummary);
    }
    attendanceSummary.textContent = 'Attendance summary loading...';
  } else if (attendanceSummary) {
    attendanceSummary.remove();
  }
  const setAndReload = (key, value, immediate = false) => {
    state[key] = value;
    state.offset = 0;
    if (immediate) loadTable(table); else scheduleTableReload(table);
  };
  const queryInput = tools.querySelector('.table-query');
  queryInput?.addEventListener('input', e => setAndReload('q', e.target.value));
  tools.querySelector('.table-area-filter')?.addEventListener('input', e => setAndReload('area', e.target.value));
  tools.querySelector('.table-office-filter')?.addEventListener('input', e => setAndReload('office_address', e.target.value));
  tools.querySelector('.table-home-filter')?.addEventListener('input', e => setAndReload('home_address', e.target.value));
  const stageInput = tools.querySelector('.table-stage');
  if (stageInput) {
    stageInput.value = state.stage;
    stageInput.addEventListener('change', e => setAndReload('stage', e.target.value, true));
  }
  const statusInput = tools.querySelector('.table-status');
  if (statusInput) {
    statusInput.value = state.status;
    statusInput.addEventListener('change', e => setAndReload('status', e.target.value, true));
  }
  const sortInput = tools.querySelector('.table-sort');
  if (sortInput) {
    sortInput.value = state.sort || 'id';
    sortInput.addEventListener('change', e => setAndReload('sort', e.target.value || 'id', true));
  }
  const directionInput = tools.querySelector('.table-direction');
  if (directionInput) {
    directionInput.value = state.direction || 'desc';
    directionInput.addEventListener('change', e => setAndReload('direction', e.target.value || 'desc', true));
  }
  tools.querySelector('.table-from')?.addEventListener('change', e => setAndReload('date_from', e.target.value, true));
  tools.querySelector('.table-to')?.addEventListener('change', e => setAndReload('date_to', e.target.value, true));
  tools.querySelector('.pager-prev')?.addEventListener('click', () => {
    state.offset = Math.max(0, state.offset - state.limit);
    loadTable(table);
  });
  tools.querySelector('.pager-next')?.addEventListener('click', () => {
    state.offset += state.limit;
    loadTable(table);
  });
  primary.querySelector('[data-table-action="edit"]')?.addEventListener('click', () => editSelectedRow(table));
  primary.querySelector('[data-table-action="delete"]')?.addEventListener('click', () => deleteSelectedRows(table));
  primary.querySelector('[data-table-action="ai"]')?.addEventListener('click', () => matchSelectedRow(table));
  primary.querySelector('[data-table-action="report"]')?.addEventListener('click', () => printTableReport(table));
  primary.querySelector('[data-table-action="pending"]')?.addEventListener('click', () => markSelectedAvailability(table, 'Pending'));
  primary.querySelector('[data-table-action="rented"]')?.addEventListener('click', () => markSelectedAvailability(table, 'Rented'));
  primary.querySelector('[data-table-action="sold"]')?.addEventListener('click', () => markSelectedAvailability(table, 'Sold'));
  primary.querySelector('[data-table-action="recycle-bin"]')?.addEventListener('click', () => showRecycleBin(table));
  primary.querySelector('[data-table-action="active-list"]')?.addEventListener('click', () => showActiveList(table));
  primary.querySelector('[data-table-action="restore"]')?.addEventListener('click', () => restoreSelectedRows(table));
  primary.querySelector('[data-table-action="refresh"]')?.addEventListener('click', () => loadTable(table));
  primary.querySelector('[data-table-action="import"]')?.addEventListener('click', () => importTableCsv(table));
  primary.querySelector('[data-table-action="template"]')?.addEventListener('click', () => downloadTemplate(table));
  primary.querySelector('[data-table-action="export-excel"]')?.addEventListener('click', () => exportTableExcel(table));
  primary.querySelector('[data-table-action="export"]')?.addEventListener('click', () => exportTableCsv(table));
  actions.querySelector('.selection-select-all')?.addEventListener('change', e => {
    if (e.target.checked) selectVisibleRows(table); else clearSelectedRows(table);
  });
  actions.querySelector('[data-table-action="edit"]')?.addEventListener('click', () => editSelectedRow(table));
  actions.querySelector('[data-table-action="delete"]')?.addEventListener('click', () => deleteSelectedRows(table));
  actions.querySelector('[data-table-action="ai"]')?.addEventListener('click', () => matchSelectedRow(table));
  actions.querySelector('[data-table-action="report"]')?.addEventListener('click', () => printTableReport(table));
  actions.querySelector('[data-table-action="module-report"]')?.addEventListener('click', () => printDealingsReport(currentTab === 'rent' ? 'rent' : 'sale'));
  actions.querySelector('[data-table-action="select-all"]')?.addEventListener('click', () => selectVisibleRows(table));
  actions.querySelector('[data-table-action="clear"]')?.addEventListener('click', () => clearSelectedRows(table));
  actions.querySelector('[data-table-action="details"]')?.addEventListener('click', () => showSelectedDetails(table));
  actions.querySelector('[data-table-action="copy"]')?.addEventListener('click', () => copySelectedRows(table));
  actions.querySelector('[data-table-action="refresh"]')?.addEventListener('click', () => loadTable(table));
  actions.querySelector('[data-table-action="import"]')?.addEventListener('click', () => importTableCsv(table));
  actions.querySelector('[data-table-action="template"]')?.addEventListener('click', () => downloadTemplate(table));
  actions.querySelector('[data-table-action="export-excel"]')?.addEventListener('click', () => exportTableExcel(table));
  actions.querySelector('[data-table-action="export"]')?.addEventListener('click', () => exportTableCsv(table));
  updateSelectionToolbar(table);
  return state;
}

function updateTablePager(table, total, count) {
  const bar = document.querySelector(`#tab-${currentTab} .table-actions`);
  const tools = bar?.querySelector('.list-tools');
  if (!tools) return;
  const state = stateForTable(table);
  state.total = total;
  tools.classList.remove('hidden');
  const start = total ? state.offset + 1 : 0;
  const end = Math.min(state.offset + count, total);
  const countEl = tools.querySelector('.pager-count');
  if (countEl) countEl.textContent = `${start}-${end} / ${total}`;
  const prev = tools.querySelector('.pager-prev');
  const next = tools.querySelector('.pager-next');
  if (prev) prev.disabled = state.offset <= 0;
  if (next) next.disabled = state.offset + count >= total;
}

function buildRecordQuery(table) {
  const state = stateForTable(table);
  const params = new URLSearchParams({
    limit: String(state.limit),
    offset: String(state.offset),
  });
  if (state.sort) params.set('sort', state.sort);
  if (state.sort) params.set('sort_by', state.sort);
  if (state.direction) params.set('direction', state.direction);
  if (state.q) params.set('keyword', state.q);
  if (state.date_from) params.set('start_date', state.date_from);
  if (state.date_to) params.set('end_date', state.date_to);
  if (table === 'broker_contacts') {
    ['area','office_address','home_address'].forEach(key => {
      if (state[key]) params.set(key, state[key]);
    });
  }
  ['stage','status'].forEach(key => {
    if (state[key]) params.set(key, state[key]);
  });
  if (state.deletedOnly) params.set('deleted_only', 'true');
  return params.toString();
}

function selectedIds(table) {
  return [...stateForTable(table).selected].map(Number).filter(Boolean);
}

function updateSelectionToolbar(table) {
  const state = stateForTable(table);
  const count = state.selected.size;
  const bar = document.querySelector(`#tab-${currentTab} .table-actions`);
  const selectedCount = bar?.querySelector('.selected-count');
  const total = state.total ?? state.rows.length ?? 0;
  if (selectedCount) selectedCount.textContent = `${count} of ${total} selected`;
  const recordPill = bar?.querySelector('.table-record-pill');
  if (recordPill) recordPill.textContent = `Showing ${state.rows.length || 0} of ${total}`;
  const oneOnly = ['edit', 'details'];
  const needsAny = ['delete', 'copy'];
  const canEditTable = canWriteTable(table) && (FIELDS[table] || []).some(field => !field.readonly);
  const canMatchTable = table === 'rent_requirements' || table === 'sale_requirements' || (!PHASE1_TABLES.includes(table) && PIPELINE_TABLES.includes(table));
  bar?.querySelectorAll('[data-table-action]').forEach(btn => {
    const action = btn.dataset.tableAction;
    if (oneOnly.includes(action)) btn.disabled = count !== 1;
    if (needsAny.includes(action)) btn.disabled = count === 0;
    if (['edit','delete'].includes(action) && !canEditTable) btn.disabled = true;
    if (action === 'ai') btn.disabled = count !== 1 || !canMatchTable;
    if (['pending','rented','sold'].includes(action)) btn.disabled = count !== 1;
    if (action === 'restore') btn.disabled = count === 0 || !state.deletedOnly;
    if (state.deletedOnly && ['add','edit','delete','ai','report','pending','rented','sold','import','template','export','export-excel'].includes(action)) {
      btn.disabled = ['report','export','export-excel'].includes(action) ? false : true;
    }
  });
  document.querySelectorAll(`input.row-select[data-table="${table}"]`).forEach(input => {
    const checked = state.selected.has(Number(input.dataset.id));
    input.checked = checked;
    input.closest('tr')?.classList.toggle('is-selected', checked);
  });
  const pageSelect = document.querySelector(`input.page-select[data-table="${table}"]`);
  const selectAll = bar?.querySelector(`.selection-select-all[data-table="${table}"]`);
  const allVisibleSelected = state.rows.length > 0 && state.rows.every(row => state.selected.has(Number(row.id)));
  if (pageSelect) {
    pageSelect.checked = allVisibleSelected;
  }
  if (selectAll) selectAll.checked = allVisibleSelected;
}

function selectVisibleRows(table) {
  const state = stateForTable(table);
  state.rows.forEach(row => state.selected.add(Number(row.id)));
  updateSelectionToolbar(table);
}

function clearSelectedRows(table) {
  stateForTable(table).selected.clear();
  updateSelectionToolbar(table);
}

function selectedRowsFromState(table) {
  const state = stateForTable(table);
  const rows = selectedIds(table).map(id => state.rowMap.get(Number(id))).filter(Boolean);
  return rows;
}

function requireSingleSelected(table) {
  const ids = selectedIds(table);
  if (ids.length !== 1) {
    alert('Select exactly one record first.');
    return null;
  }
  return ids[0];
}

function editSelectedRow(table) {
  const id = requireSingleSelected(table);
  if (id) showEditForm(table, id);
}

function phaseFieldHtml(field, value = '') {
  if (field.readonly) return '';
  const required = field.required ? ' required' : '';
  const safe = escapeHtml(value ?? '');
  const label = `${escapeHtml(field.label)}${field.required ? ' *' : ''}`;
  if (field.type === 'multiselect') {
    const selected = new Set(splitMultiValue(value).map(option => option.toLowerCase()));
    const options = multiOptionsForField(field, value);
    return `<div class="field field-full phase-multi-field phase-multi-${field.key}"><label>${label}</label><div class="multi-options desktop-options" data-key="${field.key}">
      ${options.map(option => `<label><input type="checkbox" value="${escapeHtml(option)}"${selected.has(String(option).toLowerCase()) ? ' checked' : ''}> <span>${escapeHtml(option)}</span></label>`).join('')}
    </div></div>`;
  }
  if (field.type === 'select') {
    const options = [...(field.options || [])];
    if (value && !options.some(option => String(option) === String(value))) options.push(value);
    return `<div class="field"><label>${label}</label><select id="pf-${field.key}"${required}>
      <option value="">Select</option>
      ${options.map(option => `<option value="${escapeHtml(option)}"${String(option) === String(value) ? ' selected' : ''}>${escapeHtml(option)}</option>`).join('')}
    </select></div>`;
  }
  if (field.type === 'combo') {
    return `<div class="field"><label>${label}</label><input id="pf-${field.key}" list="dl-${field.key}" value="${safe}"${required}>
      <datalist id="dl-${field.key}">${(field.options || []).map(option => `<option value="${escapeHtml(option)}"></option>`).join('')}</datalist></div>`;
  }
  const type = field.type === 'date' ? 'date' : field.type === 'number' ? 'number' : 'text';
  const step = type === 'number' ? ' step="0.01"' : '';
  const defaultValue = field.type === 'date' && !value ? todayISODate() : safe;
  return `<div class="field"><label>${label}</label><input id="pf-${field.key}" type="${type}"${step} value="${defaultValue}"${required}></div>`;
}

function phaseFormGroupTitle(key) {
  if (['client_name','owner_name','client_status','client_broker','contact','contact_phone','owner_phone','date'].includes(key)) {
    return 'Contact';
  }
  if (['budget','monthly_rent','deposit','demand','maintenance_charge','maintenance'].includes(key)) {
    return 'Price';
  }
  if (['facilities','remarks','notes'].includes(key)) {
    return 'Facilities';
  }
  return 'Property';
}

function phaseFormSectionsHtml(table, fields, row) {
  const groups = [];
  for (const field of fields) {
    const html = phaseFieldHtml(field, row[field.key]);
    if (!html) continue;
    const title = phaseFormGroupTitle(field.key);
    let group = groups[groups.length - 1];
    if (!group || group.title !== title) {
      group = { title, fields: [] };
      groups.push(group);
    }
    group.fields.push(html);
  }
  return groups.map(group => `
    <section class="phase-form-section">
      <h2>${escapeHtml(group.title)}</h2>
      <div class="form-grid">${group.fields.join('')}</div>
    </section>
  `).join('');
}

function showPhaseForm(table, id = '') {
  const state = stateForTable(table);
  const row = id ? (state.rowMap.get(Number(id)) || {}) : {};
  $('phase1-home')?.classList.add('hidden');
  $('phase1-section')?.classList.add('hidden');
  const form = $('phase1-form');
  const fields = FIELDS[table] || [];
  form.classList.remove('hidden');
  form.innerHTML = `
    <div class="phase-form-head">
      <div>
        <h1>${id ? 'Edit' : 'Add New'} ${escapeHtml(PHASE1_LABELS[table] || tableTitle(table))}</h1>
        <p>${id ? 'Edits from non-admin users are sent for admin approval.' : 'After save, this form clears for fast next entry.'}</p>
      </div>
      <button class="btn" id="phase-form-exit" type="button">Exit</button>
    </div>
    <div class="glass-card phase-form-card">
      <div class="phase-form-sections">${phaseFormSectionsHtml(table, fields, row)}</div>
      <div class="phase-form-actions">
        <button class="btn btn-primary" id="phase-form-save" type="button">Save</button>
      </div>
    </div>
  `;
  $('phase-form-exit').onclick = () => {
    if (phaseFormHasInput() && !confirm('Exit this form? Unsaved entries will be cleared.')) return;
    form.classList.add('hidden');
    $('phase1-section')?.classList.remove('hidden');
    restoreSidebarAfterFocus();
    loadTable(table);
  };
  $('phase-form-save').onclick = () => savePhaseForm(table, id);
}

function phaseFormHasInput() {
  const today = todayISODate();
  const controls = [...document.querySelectorAll('#phase1-form input, #phase1-form select, #phase1-form textarea')];
  return controls.some(control => {
    if (control.type === 'checkbox') return control.checked;
    const value = String(control.value || '').trim();
    if (!value) return false;
    if (control.type === 'date' && value === today) return false;
    return true;
  });
}

function phaseFormData(table) {
  const data = {};
  for (const field of FIELDS[table] || []) {
    if (field.readonly) continue;
    if (field.type === 'multiselect') {
      data[field.key] = [...document.querySelectorAll(`.multi-options[data-key="${field.key}"] input:checked`)].map(input => input.value).join(', ');
      if (field.required && !data[field.key]) {
        throw new Error(`${field.label} is required.`);
      }
      continue;
    }
    const el = $(`pf-${field.key}`);
    if (!el) continue;
    data[field.key] = field.type === 'number' ? parseMoney(el.value) : el.value;
    if (field.required && !String(data[field.key] || '').trim()) {
      throw new Error(`${field.label} is required.`);
    }
    if (['contact_phone','owner_phone','contact','owner_contact','phone'].includes(field.key)) {
      data[field.key] = validatePhone(data[field.key], field.required);
    }
    if (field.key === 'client_status') data[field.key] = normalizeContactRole(data[field.key], 'Client');
    if (field.key === 'client_broker') data[field.key] = normalizeContactRole(data[field.key], 'Owner');
  }
  if (PHASE1_TABLES.includes(table)) {
    const phoneKey = phoneKeyForTable(table);
    if (data[phoneKey]) data.contact = data[phoneKey];
  }
  return data;
}

async function savePhaseForm(table, id = '') {
  let data;
  try {
    data = phaseFormData(table);
  } catch (err) {
    alert(err.message);
    return;
  }
  try {
    const okToSave = await confirmDuplicateSave(table, data, id);
    if (!okToSave) return;
    if (id) {
      const result = await api(`/api/records/${table}/${id}`, { method: 'PUT', body: JSON.stringify({ data }) });
      alert(result.pending ? 'Edit sent for admin approval.' : 'Record updated.');
      $('phase-form-exit').click();
      return;
    }
    await api(`/api/records/${table}`, { method: 'POST', body: JSON.stringify({ data }) });
    document.querySelectorAll('#phase1-form input').forEach(input => {
      if (input.type === 'date') input.value = todayISODate();
      else if (input.type !== 'checkbox') input.value = '';
      else input.checked = false;
    });
    document.querySelectorAll('#phase1-form select').forEach(select => { select.selectedIndex = 0; });
    setSyncStatus(`${PHASE1_LABELS[table]} saved`);
  } catch (err) {
    alert(err.message);
  }
}

async function deleteSelectedRows(table) {
  const ids = selectedIds(table);
  if (!ids.length) {
    alert('Select at least one record first.');
    return;
  }
  if (!confirm(`Recycle ${ids.length} selected record${ids.length === 1 ? '' : 's'}? Staff changes may need admin approval.`)) return;
  try {
    for (const id of ids) {
      await api(`/api/records/${table}/${id}`, { method: 'DELETE' });
    }
    clearSelectedRows(table);
    await loadTable(table);
    setSyncStatus(`Recycle request saved for ${ids.length} record${ids.length === 1 ? '' : 's'}`);
  } catch (err) {
    alert(err.message);
  }
}

async function showRecycleBin(table) {
  const state = stateForTable(table);
  state.deletedOnly = true;
  state.offset = 0;
  state.selected.clear();
  await loadTable(table);
}

async function showActiveList(table) {
  const state = stateForTable(table);
  state.deletedOnly = false;
  state.offset = 0;
  state.selected.clear();
  await loadTable(table);
}

async function restoreSelectedRows(table) {
  const ids = selectedIds(table);
  if (!ids.length) {
    alert('Select recycled records to restore first.');
    return;
  }
  if (!confirm(`Restore ${ids.length} recycled record${ids.length === 1 ? '' : 's'}?`)) return;
  try {
    for (const id of ids) {
      await api(`/api/records/${table}/${id}/restore`, { method: 'POST', body: JSON.stringify({}) });
    }
    clearSelectedRows(table);
    await loadTable(table);
    setSyncStatus(`Restored ${ids.length} record${ids.length === 1 ? '' : 's'}`);
  } catch (err) {
    alert(err.message);
  }
}

function matchSelectedRow(table) {
  const id = requireSingleSelected(table);
  if (!id) return;
  if (table !== 'rent_requirements' && table !== 'sale_requirements') {
    alert('Match search starts from a rent or sale requirement.');
    return;
  }
  findMatch(table, id);
}

function markSelectedAvailability(table, status) {
  const id = requireSingleSelected(table);
  if (!id) return;
  markAvailability(table, id, status);
}

function showReadonlyModal(title, html, options = {}) {
  $('modal-body').innerHTML = html;
  $('modal-save').classList.add('hidden');
  openModal(title, options);
}

async function showSelectedDetails(table) {
  const id = requireSingleSelected(table);
  if (!id) return;
  try {
    const result = await api(`/api/records/${table}/${id}`);
    const record = result.record || {};
    const fields = FIELDS[table] || [];
    const rows = fields.map(field => `
      <tr>
        <th>${escapeHtml(field.label)}</th>
        <td>${escapeHtml(formatCell(record[field.key], field.key))}</td>
      </tr>
    `).join('');
    showReadonlyModal(
      `Details - ${table.replace(/_/g, ' ')} #${id}`,
      `${listingQualityHtml(table, record)}<table class="details-table"><tbody>${rows}</tbody></table>`
    );
  } catch (err) {
    alert(err.message);
  }
}

function closeReadonlyMode() {
  $('modal-save').classList.remove('hidden');
}

function rowsToDelimited(rows, fields, delimiter = '\t') {
  const headers = fields.map(field => field.label);
  const lines = [headers.join(delimiter)];
  rows.forEach(row => {
    lines.push(fields.map(field => {
      const text = formatCell(row[field.key], field.key).replace(/\s+/g, ' ').trim();
      return delimiter === ',' ? `"${text.replace(/"/g, '""')}"` : text;
    }).join(delimiter));
  });
  return lines.join('\n');
}

async function copySelectedRows(table) {
  const rows = selectedRowsFromState(table);
  if (!rows.length) {
    alert('Select records to copy first.');
    return;
  }
  const text = rowsToDelimited(rows, FIELDS[table] || []);
  try {
    await navigator.clipboard.writeText(text);
  } catch (_err) {
    const temp = document.createElement('textarea');
    temp.value = text;
    document.body.appendChild(temp);
    temp.select();
    document.execCommand('copy');
    temp.remove();
  }
  setSyncStatus(`Copied ${rows.length} record${rows.length === 1 ? '' : 's'}`);
}

function downloadText(filename, content, type = 'text/plain') {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function fetchCurrentReportRows(table, selectedOnly = false) {
  if (selectedOnly) {
    const rows = selectedRowsFromState(table);
    if (rows.length) return rows;
  }
  const params = new URLSearchParams(buildRecordQuery(table));
  params.set('limit', '1000');
  params.set('offset', '0');
  const data = await api(`/api/records/${table}?${params.toString()}`);
  return data.rows || [];
}

async function exportTableCsv(table) {
  try {
    const selected = selectedIds(table).length > 0;
    const rows = selected ? selectedRowsFromState(table) : await fetchCurrentReportRows(table);
    if (!rows.length) {
      alert('No rows available to export.');
      return;
    }
    const csv = rowsToDelimited(rows, FIELDS[table] || [], ',');
    downloadText(`${table}_${todayISODate()}.csv`, csv, 'text/csv');
    setSyncStatus(`Exported ${rows.length} row${rows.length === 1 ? '' : 's'}`);
  } catch (err) {
    alert(err.message);
  }
}

async function exportTableExcel(table) {
  try {
    const selected = selectedIds(table).length > 0;
    const rows = selected ? selectedRowsFromState(table) : await fetchCurrentReportRows(table);
    if (!rows.length) {
      alert('No rows available to export.');
      return;
    }
    const fields = FIELDS[table] || [];
    const html = `<!doctype html><html><head><meta charset="utf-8"></head><body>
      <table>
        <thead><tr>${fields.map(field => `<th>${escapeHtml(field.label)}</th>`).join('')}</tr></thead>
        <tbody>${rows.map(row => `<tr>${fields.map(field => `<td>${escapeHtml(formatCell(row[field.key], field.key))}</td>`).join('')}</tr>`).join('')}</tbody>
      </table>
    </body></html>`;
    downloadText(`${table}_${todayISODate()}.xls`, html, 'application/vnd.ms-excel');
    setSyncStatus(`Exported Excel file with ${rows.length} row${rows.length === 1 ? '' : 's'}`);
  } catch (err) {
    alert(err.message);
  }
}

function downloadTemplate(table) {
  const fields = (FIELDS[table] || []).filter(field => !field.readonly);
  const csv = fields.map(field => `"${field.label.replace(/"/g, '""')}"`).join(',') + '\n';
  downloadText(`${table}_template.csv`, csv, 'text/csv');
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = '';
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    const next = text[i + 1];
    if (quoted) {
      if (ch === '"' && next === '"') { cell += '"'; i++; }
      else if (ch === '"') quoted = false;
      else cell += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ',') { row.push(cell); cell = ''; }
    else if (ch === '\n') { row.push(cell); rows.push(row); row = []; cell = ''; }
    else if (ch !== '\r') cell += ch;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  return rows;
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(reader.error || new Error('Could not read file'));
    reader.readAsDataURL(file);
  });
}

function importTableCsv(table) {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
  input.onchange = async () => {
    const file = input.files?.[0];
    if (!file) return;
    const fields = (FIELDS[table] || []).filter(field => !field.readonly);
    let records = [];
    try {
      const contentBase64 = await readFileAsDataUrl(file);
      const result = await api(`/api/records/${table}/import/preview`, {
        method: 'POST',
        body: JSON.stringify({ filename: file.name, content_base64: contentBase64 })
      });
      records = result.records || [];
    } catch (err) {
      alert(err.message);
      return;
    }
    if (!records.length) {
      alert('No import rows found. Please use the template headings.');
      return;
    }
    const preview = records.slice(0, 25).map(record => `<tr>${fields.slice(0, 8).map(field => `<td>${escapeHtml(record[field.key] || '')}</td>`).join('')}</tr>`).join('');
    $('modal-body').innerHTML = `
      <p>Previewing ${records.length} row(s) from ${escapeHtml(file.name)}. Showing first 25.</p>
      <div class="table-container"><table><thead><tr>${fields.slice(0, 8).map(field => `<th>${escapeHtml(field.label)}</th>`).join('')}</tr></thead><tbody>${preview}</tbody></table></div>
    `;
    openModal(`Import ${PHASE1_LABELS[table] || tableTitle(table)}`);
    $('modal-save').onclick = async () => {
      let imported = 0;
      const failed = [];
      for (let index = 0; index < records.length; index++) {
        const record = records[index];
        try {
          const ok = await confirmDuplicateSave(table, record, null);
          if (!ok) continue;
          await api(`/api/records/${table}`, { method: 'POST', body: JSON.stringify({ data: record }) });
          imported++;
        } catch (err) {
          failed.push(`Row ${index + 2}: ${err.message}`);
        }
      }
      closeModal();
      $('modal-save').onclick = saveForm;
      await loadTable(table);
      alert(`Imported ${imported} row(s).${failed.length ? `\n\nCould not import:\n${failed.slice(0, 8).join('\n')}` : ''}`);
    };
  };
  input.click();
}

function tableTitle(table) {
  return {
    rent_requirements: 'Rent Requirements',
    rent_availability: 'Rent Availability',
    rented_properties: 'Rented Properties',
    sale_requirements: 'Sale Requirements',
    sale_availability: 'Sale Availability',
    sold_properties: 'Sold Properties',
    clients: 'Clients',
    broker_contacts: 'Broker Contact List',
    properties: 'Properties',
    employees: 'Employees',
    income_transactions: 'Income Transactions',
    expense_transactions: 'Expense Transactions',
    attendance: 'Attendance',
    salary_payments: 'Salary Payments',
    sf_employees: 'SF Employee Central',
    sf_positions: 'SF Positions',
    sf_performance_goals: 'SF Performance & Goals',
    sf_must_win_battles: 'SF Must Win Battles',
    sf_kpis: 'SF KPIs',
    sf_learning: 'SF Learning',
    sf_recruiting: 'SF Recruiting',
    sf_compensation: 'SF Compensation',
    sf_onboarding: 'SF Onboarding',
    wf_workflows: 'Workflow Definitions',
    wf_workflow_steps: 'Workflow Steps',
    wf_instances: 'Running Instances',
    wf_tasks: 'Workflow Tasks',
    wf_approvals: 'Workflow Approvals',
    wf_notifications: 'Workflow Notifications',
    wf_sla_log: 'SLA Log',
    wf_audit_log: 'Workflow Audit Trail',
  }[table] || table.replace(/_/g, ' ').replace(/\b\w/g, ch => ch.toUpperCase());
}

function fieldLabel(table, key) {
  if (key === 'id') return 'Sr No.';
  return (FIELDS[table] || []).find(field => field.key === key)?.label || key.replace(/_/g, ' ');
}

function tableDisplayFields(table) {
  const preferred = {
    rent_requirements: [
      ['id', 'Serial No.'], ['date', 'Date'], ['client_name', 'Name'], ['client_status', 'Status'], ['contact', 'Contact'],
      ['property_requires', 'Property Required / Needed'], ['size', 'Rooms'], ['floor', 'Floor'], ['location', 'Location'], ['budget', 'Budget'],
    ],
    rent_availability: [
      ['id', 'Serial No.'], ['date', 'Date'], ['owner_name', 'Name'], ['client_broker', 'Status'], ['contact', 'Contact'],
      ['property_availability', 'Property Available'], ['size', 'Rooms'], ['floor', 'Floor'], ['monthly_rent', 'Rent'], ['status', 'Availability'],
    ],
    rented_properties: [
      ['id', 'Serial No.'], ['closed_at', 'Rented Date'], ['owner_name', 'Name'], ['client_broker', 'Status'], ['contact', 'Contact'],
      ['property_availability', 'Property Rented'], ['size', 'Rooms'], ['floor', 'Floor'], ['monthly_rent', 'Rent'], ['closed_status', 'Status'],
    ],
    sale_requirements: [
      ['id', 'Serial No.'], ['date', 'Date'], ['client_name', 'Name'], ['client_status', 'Status'], ['contact', 'Contact'],
      ['property_requires', 'Property Required / Needed'], ['size', 'Rooms'], ['floor', 'Floor'], ['location', 'Location'], ['budget', 'Budget'],
    ],
    sale_availability: [
      ['id', 'Serial No.'], ['date', 'Date'], ['owner_name', 'Name'], ['client_broker', 'Status'], ['contact', 'Contact'],
      ['property_availability', 'Property Available'], ['size', 'Rooms'], ['floor', 'Floor'], ['demand', 'Demand'], ['status', 'Availability'],
    ],
    sold_properties: [
      ['id', 'Serial No.'], ['closed_at', 'Sold Date'], ['owner_name', 'Name'], ['client_broker', 'Status'], ['contact', 'Contact'],
      ['property_availability', 'Property Sold'], ['size', 'Rooms'], ['floor', 'Floor'], ['demand', 'Demand'], ['closed_status', 'Status'],
    ],
    broker_contacts: [
      ['id', 'Sr. No'], ['name', 'Name'], ['contact', 'Contact'], ['area', 'Area'],
      ['office_address', 'Office Address'], ['home_address', 'Home Address'], ['remarks', 'Remarks'],
    ],
    attendance: [
      ['id', 'ID'], ['date', 'Date'], ['employee_id', 'Employee ID'], ['check_in', 'In'], ['check_out', 'Out'],
      ['status', 'Status'], ['worked_minutes', 'Worked'], ['late_minutes', 'Late'], ['overtime_minutes', 'OT'], ['leave_type', 'Leave Type'],
    ],
  }[table];
  if (preferred) return preferred.map(([key, label]) => ({ key, label }));
  return [{ key: 'id', label: 'ID' }, ...(FIELDS[table] || []).slice(0, 9)];
}

function reportFieldsForTable(table) {
  const preferred = {
    rent_requirements: ['id','date','client_name','client_status','contact','property_requires','size','measurement','measurement_unit','budget','location','floor','workflow_stage','facilities'],
    rent_availability: ['id','date','owner_name','client_broker','contact','property_availability','size','measurement','measurement_unit','monthly_rent','location','floor','status','workflow_stage','facilities'],
    rented_properties: ['id','closed_at','owner_name','client_broker','contact','property_availability','size','measurement','measurement_unit','monthly_rent','location','floor','closed_status','archived_by'],
    sale_requirements: ['id','date','client_name','client_status','contact','property_requires','size','measurement','measurement_unit','budget','location','workflow_stage','facilities'],
    sale_availability: ['id','date','owner_name','client_broker','contact','property_availability','size','measurement','measurement_unit','demand','location','floor','status','workflow_stage','facilities'],
    sold_properties: ['id','closed_at','owner_name','client_broker','contact','property_availability','size','measurement','measurement_unit','demand','location','floor','closed_status','archived_by'],
    clients: ['id','client_name','phone','email','client_type','status','notes'],
    broker_contacts: ['id','name','contact','area','office_address','home_address','remarks'],
    properties: ['id','property_code','title','property_type','status','owner_name','owner_contact','location','monthly_rent','sale_price'],
    employees: ['id','employee_id','full_name','phone','position','department','base_salary','status'],
    income_transactions: ['id','transaction_date','income_type','amount','tenant_name','receipt_no','payment_method'],
    expense_transactions: ['id','transaction_date','expense_category','amount','vendor_name','invoice_no','payment_method'],
  }[table] || ['id', ...(FIELDS[table] || []).slice(0, 8).map(field => field.key)];
  return preferred.map(key => ({ key, label: fieldLabel(table, key) }));
}

function reportSummaryCards(summary = {}) {
  return Object.entries(summary)
    .filter(([_key, value]) => typeof value !== 'object')
    .slice(0, 8)
    .map(([key, value]) => `
      <div class="report-summary-card">
        <strong>${escapeHtml(formatCell(value, key))}</strong>
        <span>${escapeHtml(key.replace(/_/g, ' '))}</span>
      </div>
    `).join('');
}

function splitRows(rows, perPage = printableRowsPerPage) {
  const pages = [];
  for (let i = 0; i < rows.length; i += perPage) pages.push(rows.slice(i, i + perPage));
  return pages.length ? pages : [[]];
}

function renderPrintableTable(section, rows) {
  const fields = section.fields || [];
  if (!fields.length) {
    return `
      <h2>${escapeHtml(section.title)}</h2>
      <div class="empty-print">No printable columns configured.</div>
    `;
  }
  const body = rows.length
    ? rows.map(row => `<tr>${fields.map(field => `<td>${escapeHtml(formatCell(row[field.key], field.key))}</td>`).join('')}</tr>`).join('')
    : `<tr><td colspan="${fields.length}" class="empty-print">No records found.</td></tr>`;
  return `
    <h2>${escapeHtml(section.title)}</h2>
    <table>
      <thead><tr>${fields.map(field => `<th>${escapeHtml(field.label)}</th>`).join('')}</tr></thead>
      <tbody>${body}</tbody>
    </table>
  `;
}

function createReportWindow(title) {
  const reportWindow = window.open('', '_blank');
  if (!reportWindow) return null;
  reportWindow.document.open();
  reportWindow.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${escapeHtml(title)}</title></head><body style="font-family:Segoe UI,Arial,sans-serif;padding:24px">Preparing report...</body></html>`);
  reportWindow.document.close();
  return reportWindow;
}

function openPrintableReport({ title, subtitle = '', company = companyName || 'Real Estate CRM', companyLogo = phase1Settings.company_logo || '', sections, summaryHtml = '', meta = [] }, targetWindow = null) {
  const pages = [];
  const safeSections = sections?.length ? sections : [{ title: 'Records', fields: [], rows: [] }];
  safeSections.forEach(section => {
    splitRows(section.rows || [], section.rowsPerPage || printableRowsPerPage).forEach((rows, pageIndex) => {
      pages.push({ section, rows, pageIndex });
    });
  });
  const totalPages = Math.max(pages.length, 1);
  const generated = new Date().toLocaleString();
  const metaItems = [
    subtitle || 'Generated report',
    `Generated: ${generated}`,
    currentUser?.full_name || currentUser?.username ? `Prepared by: ${currentUser.full_name || currentUser.username}` : '',
    ...meta,
  ].filter(Boolean);
  const pageHtml = pages.map((page, index) => `
    <section class="print-page">
      <header>
        <div>
          <div class="brand-row">${companyLogo ? `<img class="brand-logo" src="${escapeHtml(companyLogo)}" alt="">` : ''}<div class="brand">${escapeHtml(company)}</div></div>
          <h1>${escapeHtml(title)}</h1>
          <div class="report-meta">${metaItems.map(item => `<span>${escapeHtml(item)}</span>`).join('')}</div>
        </div>
        <div class="stamp">
          <span class="page-chip">Page ${index + 1} / ${totalPages}</span>
          <strong>${escapeHtml(page.section.title)}${page.pageIndex ? ' continued' : ''}</strong>
        </div>
      </header>
      ${index === 0 && summaryHtml ? `<div class="report-summary">${summaryHtml}</div>` : ''}
      ${renderPrintableTable(page.section, page.rows)}
      <footer>
        <span>${escapeHtml(company)}</span>
        <strong>Page ${index + 1} of ${totalPages}</strong>
      </footer>
    </section>
  `).join('');
  const html = `<!doctype html>
<html><head><meta charset="utf-8"><title>${escapeHtml(title)}</title>
<style>
  @page { size: A4 landscape; margin: 9mm; }
  * { box-sizing: border-box; }
  body { margin: 0; background: #e5e7eb; color: #111827; font-family: "Segoe UI", Arial, sans-serif; }
  .print-page { width: 297mm; min-height: 210mm; margin: 0 auto 10mm; padding: 9mm 10mm; background: white; page-break-after: always; display: flex; flex-direction: column; }
  header { display: flex; justify-content: space-between; align-items: flex-start; gap: 18px; border-bottom: 2px solid #111827; padding-bottom: 7px; margin-bottom: 8px; }
  .brand-row { display: flex; align-items: center; gap: 7px; }
  .brand-logo { width: 30px; height: 30px; object-fit: contain; border: 1px solid #cbd5e1; }
  .brand { font-size: 11px; font-weight: 800; color: #0f766e; text-transform: uppercase; letter-spacing: 0; }
  h1 { margin: 2px 0 4px; font-size: 21px; line-height: 1.1; color: #0f172a; }
  h2 { margin: 8px 0 7px; font-size: 14px; color: #0f172a; }
  .report-meta { display: flex; flex-wrap: wrap; gap: 4px; }
  .report-meta span { border: 1px solid #cbd5e1; color: #475569; font-size: 9px; padding: 2px 5px; }
  .stamp { text-align: right; color: #475569; font-size: 10px; display: grid; gap: 4px; min-width: 138px; }
  .page-chip { display: inline-block; border: 1px solid #0f766e; color: #0f766e; font-weight: 800; padding: 4px 7px; justify-self: end; }
  .report-summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin: 6px 0 8px; }
  .report-summary-card { border: 1px solid #cbd5e1; padding: 6px 8px; min-height: 38px; }
  .report-summary-card strong { display: block; font-size: 14px; color: #0f172a; }
  .report-summary-card span { display: block; color: #64748b; font-size: 9px; text-transform: uppercase; }
  table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 8.8px; }
  th, td { border: 1px solid #cbd5e1; padding: 3.8px 4.5px; vertical-align: top; overflow-wrap: anywhere; word-break: break-word; }
  th { background: #edf7f5; color: #0f172a; font-weight: 800; }
  tr:nth-child(even) td { background: #f8fafc; }
  .empty-print { text-align: center; padding: 18px; color: #64748b; }
  footer { margin-top: auto; border-top: 1px solid #cbd5e1; padding-top: 6px; display: flex; justify-content: space-between; color: #475569; font-size: 10px; }
  @media screen { .print-page { box-shadow: 0 20px 40px rgba(15,23,42,.18); } .print-actions { position: sticky; top: 0; padding: 10px; background: #0f172a; text-align: right; } .print-actions button { padding: 8px 14px; border: 0; background: #2563eb; color: white; border-radius: 6px; font-weight: 700; } }
  @media print { body { background: white; } .print-page { margin: 0; box-shadow: none; } .print-actions { display: none; } }
</style></head><body>
<div class="print-actions"><button onclick="window.print()">Print / Save PDF</button></div>
${pageHtml}
<script>window.addEventListener('load',()=>setTimeout(()=>window.print(),350));</script>
</body></html>`;
  const reportWindow = targetWindow || window.open('', '_blank');
  if (!reportWindow) {
    const frameId = `report-frame-${Date.now()}`;
    showReadonlyModal(title, `
      <div class="report-preview-actions">
        <button class="btn btn-primary" type="button" id="print-report-preview">Print / Save PDF</button>
        <button class="btn" type="button" id="download-report-preview">Download HTML</button>
      </div>
      <iframe id="${frameId}" class="report-preview-frame" title="${escapeHtml(title)}"></iframe>
    `, { wide: true });
    const frame = $(frameId);
    frame.srcdoc = html.replace(/<script>[\s\S]*?<\/script>/g, '');
    $('print-report-preview').onclick = () => frame.contentWindow?.print();
    $('download-report-preview').onclick = () => downloadText(`${title.toLowerCase().replace(/[^a-z0-9]+/g, '_')}.html`, html, 'text/html');
    return;
  }
  reportWindow.document.open();
  reportWindow.document.write(html);
  reportWindow.document.close();
}

async function printTableReport(table) {
  const reportWindow = createReportWindow(`${tableTitle(table)} Report`);
  try {
    const selected = selectedIds(table).length > 0;
    const rows = selected ? selectedRowsFromState(table) : await fetchCurrentReportRows(table);
    const summaryHtml = reportSummaryCards({
      records: rows.length,
      selected_records: selected ? rows.length : 0,
      generated: new Date().toLocaleDateString(),
      filter: stateForTable(table).q || 'All',
    });
    openPrintableReport({
      title: `${tableTitle(table)} Report`,
      subtitle: selected ? 'Selected records only' : 'Current filtered records',
      sections: [{ title: tableTitle(table), fields: reportFieldsForTable(table), rows }],
      summaryHtml,
      meta: [
        `Filter: ${stateForTable(table).q || 'All'}`,
        `Rows: ${rows.length}`,
      ],
    }, reportWindow);
  } catch (err) {
    if (reportWindow) reportWindow.close();
    alert(err.message);
  }
}

function summaryFromDealings(summary, kind) {
  if (kind === 'rent') return summary;
  if (kind === 'sale') return summary;
  return {
    rent_requirements: summary?.rent?.requirements || 0,
    rent_availability: summary?.rent?.available_properties || 0,
    rent_done: summary?.rent?.completed_rent_deals || 0,
    sale_requirements: summary?.sale?.requirements || 0,
    sale_availability: summary?.sale?.available_properties || 0,
    sale_done: summary?.sale?.completed_sale_deals || 0,
  };
}

function dealingsSectionTable(section) {
  const normalized = String(section || '').toLowerCase();
  if (normalized.includes('rented')) return 'rented_properties';
  if (normalized.includes('sold')) return 'sold_properties';
  if (normalized.includes('availability')) {
    return normalized.startsWith('rent') ? 'rent_availability' : 'sale_availability';
  }
  return normalized.startsWith('rent') ? 'rent_requirements' : 'sale_requirements';
}

async function printDealingsReport(kind = 'all') {
  const reportWindow = createReportWindow(`${kind === 'rent' ? 'Rent' : kind === 'sale' ? 'Sale' : 'Property Dealings'} Report`);
  try {
    const start = $('report-start')?.value || '';
    const end = $('report-end')?.value || '';
    const params = new URLSearchParams({ kind });
    if (start) params.set('start_date', start);
    if (end) params.set('end_date', end);
    const result = await api(`/api/reports/dealings?${params.toString()}`);
    const grouped = {};
    (result.rows || []).forEach(row => {
      const section = row.section || 'Records';
      if (!grouped[section]) grouped[section] = [];
      grouped[section].push(row);
    });
    const sections = Object.entries(grouped).map(([section, rows]) => {
      const table = dealingsSectionTable(section);
      return { title: section, fields: reportFieldsForTable(table), rows };
    });
    const period = start || end ? `Period: ${start || 'start'} to ${end || 'today'}` : 'All available records';
    openPrintableReport({
      title: result.title || 'Property Dealings Report',
      subtitle: period,
      company: result.company || 'Real Estate CRM',
      sections,
      summaryHtml: reportSummaryCards(summaryFromDealings(result.summary, kind)),
      meta: [
        `Report type: ${kind === 'all' ? 'Rent + Sale' : kind}`,
        `Rows: ${(result.rows || []).length}`,
      ],
    }, reportWindow);
  } catch (err) {
    if (reportWindow) reportWindow.close();
    alert(err.message);
  }
}

async function loadTable(table) {
  const container = currentTab === 'phase1'
    ? document.querySelector('#phase1-section > .table-container')
    : document.querySelector(`#tab-${currentTab} .table-container`);
  if (!container) return;
  const state = ensureTableControls(table);
  if (state.controller) state.controller.abort();
  const controller = new AbortController();
  state.controller = controller;
  const tableEl = container.querySelector('table') || container;
  const fields = tableDisplayFields(table);
  const headers = [''].concat(fields.map(f => f.label));
  renderTableLoading(tableEl, headers.length);
  setSyncStatus(`Loading ${table.replace(/_/g, ' ')}...`, 'busy');
  try {
    const data = await api(`/api/records/${table}?${buildRecordQuery(table)}`, { signal: controller.signal });
    if (state.controller !== controller) return;
    const rows = data.rows || [];
    if (!rows.length && state.offset > 0) {
      state.offset = 0;
      return loadTable(table);
    }
    state.rows = rows;
    state.rowMap = new Map(rows.map(row => [Number(row.id), row]));

    let thead = tableEl.querySelector('thead');
    if (!thead) { thead = document.createElement('thead'); tableEl.prepend(thead); }
    thead.innerHTML = '<tr>' + headers.map((h, index) => index === 0
      ? `<th class="select-col"><input class="page-select" type="checkbox" title="Select visible rows" data-table="${table}"></th>`
      : `<th>${h}</th>`
    ).join('') + '</tr>';

    let tbody = tableEl.querySelector('tbody');
    if (!tbody) { tbody = document.createElement('tbody'); tableEl.appendChild(tbody); }

    if (!rows.length) {
      state.rows = [];
      state.rowMap = new Map();
      tbody.innerHTML = `<tr><td colspan="${headers.length}" class="empty-cell">No records found for ${escapeHtml(table.replace(/_/g, ' '))}.</td></tr>`;
      updateTablePager(table, data.total ?? 0, 0);
      updateSelectionToolbar(table);
      setSyncStatus(`No records - ${formatClock()}`);
      return;
    }

    tbody.innerHTML = rows.map(r => {
      const vals = fields.map(f => tableCellHtml(table, r, f)).join('');
      const rowId = Number(r.id) || 0;
      const checked = state.selected.has(rowId) ? ' checked' : '';
      const selectedClass = state.selected.has(rowId) ? ' class="is-selected"' : '';
      return `<tr data-table="${table}" data-id="${rowId}"${selectedClass}>
        <td class="select-col"><input class="row-select" type="checkbox" data-table="${table}" data-id="${Number(r.id) || 0}"${checked}></td>
        ${vals}
      </tr>`;
    }).join('');
    tbody.querySelectorAll('tr[data-id]').forEach(rowEl => {
      rowEl.addEventListener('click', event => {
        if (event.target.closest('input,button,a,select,textarea')) return;
        const input = rowEl.querySelector('input.row-select');
        if (!input) return;
        input.checked = !input.checked;
        const rowId = Number(input.dataset.id);
        if (input.checked) state.selected.add(rowId); else state.selected.delete(rowId);
        updateSelectionToolbar(table);
      });
    });
    if (PHASE1_TABLES.includes(table)) {
      state.offset = 0;
      container.scrollTop = 0;
    }
    updateTablePager(table, data.total ?? rows.length, rows.length);
    updateSelectionToolbar(table);
    if (table === 'attendance') await loadAttendanceSummary();
    setSyncStatus(`Showing ${rows.length} of ${data.total ?? rows.length} - ${formatClock()}`);
  } catch (err) {
    if (err.name === 'AbortError') return;
    console.error(err);
    let thead = tableEl.querySelector('thead');
    if (!thead) { thead = document.createElement('thead'); tableEl.prepend(thead); }
    thead.innerHTML = '<tr>' + headers.map(h => `<th>${h}</th>`).join('') + '</tr>';
    let tbody = tableEl.querySelector('tbody');
    if (!tbody) { tbody = document.createElement('tbody'); tableEl.appendChild(tbody); }
    tbody.innerHTML = `<tr><td colspan="${headers.length}" class="empty-cell">${escapeHtml(err.message || 'Could not load records.')}</td></tr>`;
    setSyncStatus(err.message || 'Load failed', 'error');
  } finally {
    if (state.controller === controller) state.controller = null;
  }
}

async function loadAttendanceSummary() {
  const strip = document.querySelector('.attendance-summary-strip');
  if (!strip) return;
  const state = tableState.attendance || {};
  const params = new URLSearchParams();
  if (state.date_from) params.set('start_date', state.date_from);
  if (state.date_to) params.set('end_date', state.date_to);
  try {
    const summary = await api(`/api/reports/attendance?${params.toString()}`);
    strip.innerHTML = [
      ['Present', summary.present_days],
      ['Absent', summary.absent_days],
      ['Leave', summary.leave_days],
      ['Late', summary.late_days],
      ['Field', summary.field_visit_days],
      ['Worked', formatCell(summary.worked_minutes, 'worked_minutes')],
      ['OT', formatCell(summary.overtime_minutes, 'overtime_minutes')],
      ['Rate', `${summary.attendance_rate || 0}%`],
    ].map(([label, value]) => `<span><strong>${escapeHtml(value)}</strong>${escapeHtml(label)}</span>`).join('');
  } catch (err) {
    strip.textContent = err.message || 'Attendance summary unavailable';
  }
}

async function approveRecord(table, id) {
  const comment = prompt('Approval comment (optional):') || '';
  try {
    await api(`/api/records/${table}/${id}/approve`, { method: 'PUT', body: JSON.stringify({ status: 'Approved', comment }) });
    await loadTable(table);
    setSyncStatus(`Approved #${id}`);
  } catch (err) { alert(err.message); }
}

async function rejectRecord(table, id) {
  const comment = prompt('Reason for rejection:') || 'Rejected';
  try {
    await api(`/api/records/${table}/${id}/approve`, { method: 'PUT', body: JSON.stringify({ status: 'Resend', comment }) });
    await loadTable(table);
    setSyncStatus(`Sent back #${id}`);
  } catch (err) { alert(err.message); }
}

async function markAvailability(table, id, status) {
  if (!confirm(`Mark this record as ${status}?`)) return;
  const finalStatus = status === 'Rented' || status === 'Sold';
  const payload = {
    stage: status === 'Pending' ? 'Pending' : (finalStatus ? 'Deal Done' : 'Contacted'),
    priority: status === 'Pending' ? 'High' : 'Medium',
    status,
    deal_probability: status === 'Pending' ? 60 : (finalStatus ? 100 : 25)
  };
  try {
    await api(`/api/records/${table}/${id}/workflow`, {
      method: 'PUT',
      body: JSON.stringify(payload)
    });
    await loadTable(table);
    setSyncStatus(`${status} saved`);
  } catch (err) { alert(err.message); }
}

function printMatchSheet(report) {
  if (!report) return;
  const requirement = report.requirement || {};
  const sourceLabel = PHASE1_LABELS[report.table] || tableTitle(report.table);
  const targetLabel = PHASE1_LABELS[report.targetTable] || tableTitle(report.targetTable);
  const reqName = requirement.client_name || requirement.owner_name || '';
  const reqContact = requirement.contact_phone || requirement.owner_phone || requirement.contact || '';
  const summaryHtml = [
    ['Name', reqName],
    ['Contact', reqContact],
    ['Property', requirement.property_requires || requirement.property_availability || ''],
    ['Location', requirement.location || ''],
    ['Budget', formatMoney(requirement.budget || 0)],
    ['Rooms', requirement.size || ''],
    ['Measurement', [requirement.measurement, requirement.measurement_unit].filter(Boolean).join(' ')],
    ['Floor', requirement.floor || ''],
    ['Facilities', requirement.facilities || ''],
    ['Matches', String(report.matches.length)],
  ].map(([label, value]) => `
    <div class="report-summary-card">
      <strong>${escapeHtml(value || '-')}</strong>
      <span>${escapeHtml(label)}</span>
    </div>
  `).join('');
  const rows = report.matches.map(item => ({
    id: item.id,
    name: item.name || item.record?.owner_name || '',
    contact: item.contact || item.record?.owner_phone || item.record?.contact_phone || item.record?.contact || '',
    location: item.location || '',
    property: item.record?.property_availability || item.record?.property_requires || '',
    rooms: item.rooms || item.record?.size || '',
    measurement: [item.record?.measurement, item.record?.measurement_unit].filter(Boolean).join(' '),
    floor: item.floor || item.record?.floor || '',
    amount: item.amount || 0,
    facilities: item.record?.facilities || '',
    score: `${Number(item.score || 0).toFixed(0)}%`,
    reasons: (item.reasons || []).join(', '),
  }));
  openPrintableReport({
    title: `${sourceLabel} Match Sheet`,
    subtitle: `Requirement #${requirement.id || ''} matched with ${targetLabel}`,
    company: companyName,
    companyLogo: phase1Settings.company_logo || '',
    summaryHtml,
    sections: [{
      title: targetLabel,
      rows,
      rowsPerPage: 12,
      fields: [
        { key: 'id', label: 'Serial No.' },
        { key: 'name', label: 'Name' },
        { key: 'contact', label: 'Contact' },
        { key: 'location', label: 'Location' },
        { key: 'property', label: 'Property' },
        { key: 'rooms', label: 'Rooms' },
        { key: 'measurement', label: 'Measurement' },
        { key: 'floor', label: 'Floor' },
        { key: 'amount', label: report.targetTable === 'rent_availability' ? 'Rent' : 'Demand' },
        { key: 'facilities', label: 'Facilities' },
        { key: 'score', label: 'Score' },
        { key: 'reasons', label: 'Reasons' },
      ],
    }],
    meta: [
      `Client requirement: ${reqName || 'Requirement'} #${requirement.id || ''}`,
      `Date/time: ${new Date().toLocaleString()}`,
      `Staff: ${currentUser?.full_name || currentUser?.username || ''}`,
    ],
  });
}

async function findMatch(table, id) {
  try {
    const phaseMode = table === 'rent_requirements' || table === 'sale_requirements';
    const data = phaseMode
      ? await api('/api/records/match', { method: 'POST', body: JSON.stringify({ record_id: id, table }) })
      : await api('/api/records/ai-match', { method: 'POST', body: JSON.stringify({ record_id: id, table }) });
    const matches = data.matches || [];
    const matchTable = data.target_table || table.replace('requirements','availability');
    const label = matchTable === 'rent_availability' ? 'Available Rentals' : 'Available Properties';
    if (matches.length === 0) {
      alert('No matches found for this requirement.');
      return;
    }
    lastMatchReport = phaseMode ? { table, targetTable: matchTable, requirement: data.requirement || {}, matches } : null;
    let html = `<div class="match-print-head">
      <h4>${matches.length} ${label} Found</h4>
      ${phaseMode ? '<button class="btn btn-primary" type="button" id="print-match-sheet">Print Match Sheet</button>' : '<button class="btn btn-primary" type="button" onclick="window.print()">Print</button>'}
    </div><div style="max-height:360px;overflow-y:auto">`;
    html += matches.map(m => `
      <div class="glass-card" style="padding:12px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center">
        <div>
          <strong>${escapeHtml(m.name || m.record?.owner_name || '')}</strong>
          <br><span style="font-size:0.8rem;color:var(--text-muted)">${escapeHtml(m.location || '')} - ${formatMoney(m.amount || m.price || 0)} - ${Number(m.score || 0).toFixed(0)}%</span>
          <br><span style="font-size:0.76rem;color:var(--text-muted)">${escapeHtml((m.reasons || []).join(', '))}</span>
        </div>
        <a href="#" onclick="showEditForm('${matchTable}',${m.id});closeModal();return false" style="color:var(--primary);font-size:0.85rem">View</a>
      </div>
    `).join('');
    html += '</div>';
    $('modal-body').innerHTML = html;
    openModal(`AI Matches for #${id}`);
    $('print-match-sheet')?.addEventListener('click', () => printMatchSheet(lastMatchReport));
  } catch (err) { alert(err.message); }
}

async function confirmDuplicateSave(table, data, id) {
  const phoneKey = phoneKeyForTable(table);
  if (!data[phoneKey]) return true;
  const payload = { table, data, record_id: id || null };
  const result = await api('/api/records/duplicates/check', { method: 'POST', body: JSON.stringify(payload) });
  const duplicates = result.duplicates || [];
  if (!duplicates.length) return true;
  const lines = duplicates.slice(0, 6).map(item =>
    `${item.table_label} #${item.id}: ${item.name}${item.location ? ` (${item.location})` : ''}`
  );
  const extra = duplicates.length > lines.length ? `\n...and ${duplicates.length - lines.length} more.` : '';
  return confirm(`This contact number already exists:\n\n${lines.join('\n')}${extra}\n\nSave anyway?`);
}

async function convertToDeal(table, id, clientName) {
  const matchTable = table.replace('requirements','availability');
  const type = table.startsWith('rent') ? 'Rent' : 'Sale';
  const name = clientName || `Client #${id}`;
  const safeName = escapeHtml(name);

  const html = `<div class="form-grid">
    <div class="field"><label>Transaction Date</label><input id="deal-date" type="date" value="${todayISODate()}"></div>
    <div class="field"><label>Income Type</label><input id="deal-type" value="${type} Commission"></div>
    <div class="field"><label>Amount (Rs.)</label><input id="deal-amount" type="number" step="0.01"></div>
    <div class="field"><label>Tenant/Buyer Name</label><input id="deal-name" value="${safeName}"></div>
    <div class="field field-full"><label>Description</label><textarea id="deal-desc">Deal from ${escapeHtml(table.replace('_',' '))} #${Number(id) || 0}</textarea></div>
    <div class="field"><label>Receipt No</label><input id="deal-receipt"></div>
    <div class="field"><label>Payment Method</label>
      <select id="deal-payment"><option>Cash</option><option>Bank Transfer</option><option>Cheque</option></select>
    </div>
  </div>`;
  $('modal-body').innerHTML = html;
  openModal(`Convert to Deal - ${type} #${id}`);
  $('modal-save').onclick = async () => {
    const data = {
      transaction_date: $('deal-date').value,
      income_type: $('deal-type').value,
      amount: parseFloat($('deal-amount').value) || 0,
      tenant_name: $('deal-name').value,
      description: $('deal-desc').value,
      receipt_no: $('deal-receipt').value,
      payment_method: $('deal-payment').value,
    };
    if (!data.amount) { alert('Please enter an amount'); return; }
    try {
      await api('/api/records/income_transactions', { method: 'POST', body: JSON.stringify({ data }) });
      closeModal();
      $('modal-save').onclick = saveForm;
      switchTab('financial');
    } catch (err) { alert(err.message); }
  };
}

function modalFieldHtml(f, value = '') {
  if (f.key === 'approval_status' || f.key === 'approval_comment' || f.key === 'created_by' || f.key === 'created_at' || f.readonly) return '';
  const label = `${escapeHtml(f.label)}${f.required ? ' *' : ''}`;
  const safe = escapeHtml(value ?? '');
  if (f.type === 'multiselect') {
    const selected = new Set(splitMultiValue(value).map(option => option.toLowerCase()));
    const options = multiOptionsForField(f, value);
    return `<div class="field field-full">
      <label>${label}</label>
      <div class="multi-options modal-multi-options desktop-options" data-key="${f.key}">
        ${options.map(option => `<label><input type="checkbox" value="${escapeHtml(option)}"${selected.has(String(option).toLowerCase()) ? ' checked' : ''}> <span>${escapeHtml(option)}</span></label>`).join('')}
      </div>
    </div>`;
  }
  if (f.type === 'combo') {
    return `<div class="field">
      <label>${label}</label>
      <input id="f-${f.key}" list="f-dl-${f.key}" value="${safe}"${f.required ? ' required' : ''} placeholder="${escapeHtml(f.label)}">
      <datalist id="f-dl-${f.key}">${(f.options || []).map(option => `<option value="${escapeHtml(option)}"></option>`).join('')}</datalist>
    </div>`;
  }
  const isText = ['remarks','description','address','office_address','home_address','notes','nearby_landmarks','area_notes','photo_paths'].includes(f.key);
  const isSelect = f.type === 'select' || f.key === 'status' || f.key === 'payment_method' || f.key === 'client_type' || f.key === 'bachelor_family';
  if (isSelect) {
    let options = f.options ? [...f.options] : [];
    if (f.key === 'status' && !options.length) options = ['Active','Inactive','Available','Rented','Sold'];
    if (f.key === 'payment_method') options = ['Cash','Bank Transfer','Cheque'];
    if (f.key === 'client_type') options = ['Tenant','Buyer','Owner','Seller'];
    if (f.key === 'bachelor_family' && !options.length) options = ['Family','Bachelor','Other'];
    if (value && !options.some(option => String(option) === String(value))) options.push(value);
    return `<div class="field">
      <label>${label}</label>
      <select id="f-${f.key}"${f.required ? ' required' : ''}>
        <option value="">Select</option>
        ${options.map(option => `<option value="${escapeHtml(option)}"${String(option) === String(value) ? ' selected' : ''}>${escapeHtml(option)}</option>`).join('')}
      </select>
    </div>`;
  }
  const type = f.type === 'date' ? 'date' : f.type === 'number' ? 'number' : 'text';
  const step = type === 'number' ? ' step="0.01"' : '';
  const defaultValue = f.type === 'date' && !value ? todayISODate() : safe;
  if (isText) {
    return `<div class="field field-full"><label>${label}</label><textarea id="f-${f.key}" placeholder="${escapeHtml(f.label)}">${safe}</textarea></div>`;
  }
  return `<div class="field"><label>${label}</label><input id="f-${f.key}" type="${type}"${step} placeholder="${escapeHtml(f.label)}" value="${defaultValue}"${f.required ? ' required' : ''}></div>`;
}

function readModalField(f) {
  if (f.type === 'multiselect') {
    const value = [...document.querySelectorAll(`.modal-multi-options[data-key="${f.key}"] input:checked`)].map(input => input.value).join(', ');
    if (f.required && !value) {
      throw new Error(`${f.label} is required.`);
    }
    return value;
  }
  const el = $(`f-${f.key}`);
  if (!el) return undefined;
  let value = f.type === 'number' ? parseMoney(el.value) : el.value;
  if (['contact_phone','owner_phone','contact','owner_contact','phone'].includes(f.key)) {
    value = validatePhone(value, f.required);
  }
  if (f.key === 'client_status') value = normalizeContactRole(value, 'Client');
  if (f.key === 'client_broker') value = normalizeContactRole(value, 'Owner');
  return value;
}

function showAddForm(table) {
  if (currentTab === 'phase1' && PHASE1_TABLES.includes(table)) {
    showPhaseForm(table);
    return;
  }
  const fields = FIELDS[table] || [];
  const html = `<div class="form-grid">${fields.map(f => modalFieldHtml(f)).filter(Boolean).join('')}</div>`;
  $('modal-body').innerHTML = html;
  openModal(`Add ${table.replace('_',' ')}`);
  $('modal-save').dataset.table = table;
  $('modal-save').dataset.id = '';
}

async function showEditForm(table, id) {
  if (currentTab === 'phase1' && PHASE1_TABLES.includes(table)) {
    showPhaseForm(table, id);
    return;
  }
  try {
    const data = await api(`/api/records/${table}/${id}`);
    const r = data.record;
    const fields = FIELDS[table] || [];
    const html = `<div class="form-grid">${fields.map(f => modalFieldHtml(f, r[f.key] ?? '')).filter(Boolean).join('')}</div>`;
    $('modal-body').innerHTML = html;
    $('modal-save').dataset.table = table;
    $('modal-save').dataset.id = id;
    openModal(`Edit ${table.replace('_',' ')} #${id}`);
  } catch (err) { alert(err.message); }
}

async function saveForm() {
  const table = $('modal-save').dataset.table;
  const id = $('modal-save').dataset.id;
  const fields = FIELDS[table] || [];
  const data = {};
  try {
    fields.forEach(f => {
      if (f.readonly) return;
      const val = readModalField(f);
      if (val !== undefined) data[f.key] = val;
    });
    if (PHASE1_TABLES.includes(table)) {
      const phoneKey = phoneKeyForTable(table);
      if (data[phoneKey]) data.contact = data[phoneKey];
    }
    const okToSave = await confirmDuplicateSave(table, data, id);
    if (!okToSave) return;
    if (id) {
      await api(`/api/records/${table}/${id}`, { method: 'PUT', body: JSON.stringify({ data }) });
    } else {
      await api(`/api/records/${table}`, { method: 'POST', body: JSON.stringify({ data }) });
    }
    closeModal();
    await loadTable(table);
    setSyncStatus(id ? `Updated #${id}` : 'Record saved');
  } catch (err) { alert(err.message); }
}

async function deleteRecord(table, id) {
  if (!confirm('Recycle this record? Staff changes may need admin approval.')) return;
  try {
    await api(`/api/records/${table}/${id}`, { method: 'DELETE' });
    await loadTable(table);
    setSyncStatus(`Deleted #${id}`);
  } catch (err) { alert(err.message); }
}

async function loadFollowups() {
  const table = $('followups-table');
  if (!table) return;
  renderTableLoading(table, 9);
  setSyncStatus('Loading follow-ups...', 'busy');
  try {
    const data = await api('/api/records/followups/today?limit=200');
    const rows = data.rows || [];
    const urgent = rows.filter(row => row.priority === 'Urgent').length;
    const high = rows.filter(row => row.priority === 'High').length;
    const overdue = rows.filter(row => row.due_status === 'Overdue').length;
    $('followup-summary').innerHTML = [
      { label: 'Due Items', value: rows.length, note: data.date },
      { label: 'Overdue', value: overdue, note: 'Needs first attention' },
      { label: 'Urgent', value: urgent, note: 'Highest priority' },
      { label: 'High Priority', value: high, note: 'Watch closely' }
    ].map(c => `
      <div class="glass-card stat-card">
        <div class="stat-value">${c.value}</div>
        <div class="stat-label">${c.label}</div>
        <div class="stat-note">${c.note}</div>
      </div>
    `).join('');
    table.querySelector('thead').innerHTML = '<tr>' + ['Due','Type','ID','Name','Contact','Property','Location','Priority','Action'].map(h => `<th>${h}</th>`).join('') + '</tr>';
    const body = table.querySelector('tbody');
    if (!rows.length) {
      body.innerHTML = '<tr><td colspan="9" class="empty-cell">No due follow-ups today.</td></tr>';
      setSyncStatus(`Follow-ups clear ${formatClock()}`);
      return;
    }
    body.innerHTML = rows.map(row => `
      <tr>
        <td>${escapeHtml(row.due_status || '')}</td>
        <td>${escapeHtml(row.label || '')}</td>
        <td>${escapeHtml(row.id)}</td>
        <td>${escapeHtml(row.name || '')}</td>
        <td>${escapeHtml(row.contact || '')}</td>
        <td>${escapeHtml(row.property_type || '')}</td>
        <td>${escapeHtml(row.location || '')}</td>
        <td>${escapeHtml(row.priority || '')}</td>
        <td class="actions"><button class="btn btn-sm" onclick="showEditForm('${row.table}', ${Number(row.id) || 0})">Open</button></td>
      </tr>
    `).join('');
    setSyncStatus(`Follow-ups updated ${formatClock()}`);
  } catch (err) {
    table.querySelector('thead').innerHTML = '<tr><th>Follow-ups</th></tr>';
    table.querySelector('tbody').innerHTML = `<tr><td class="empty-cell">${escapeHtml(err.message)}</td></tr>`;
    setSyncStatus(err.message || 'Follow-ups failed', 'error');
  }
}

async function loadAudit() {
  const table = $('audit-table');
  if (!table) return;
  renderTableLoading(table, 7);
  setSyncStatus('Loading audit history...', 'busy');
  try {
    const [logs, backup] = await Promise.all([
      api('/api/records/audit/logs?limit=100'),
      api('/api/records/backup/status')
    ]);
    const backupText = backup.last_auto_backup_date
      ? `Last backup: ${backup.last_auto_backup_date}`
      : 'No automatic backup yet';
    $('backup-status').textContent = backupText;
    const rows = logs.rows || [];
    table.querySelector('thead').innerHTML = '<tr>' + ['Time','User','Action','Table','Record','Summary','Open'].map(h => `<th>${h}</th>`).join('') + '</tr>';
    const body = table.querySelector('tbody');
    if (!rows.length) {
      body.innerHTML = '<tr><td colspan="7" class="empty-cell">No audit entries yet.</td></tr>';
      setSyncStatus(`Audit updated ${formatClock()}`);
      return;
    }
    body.innerHTML = rows.map(row => `
      <tr>
        <td>${escapeHtml(formatDate(row.created_at))}</td>
        <td>${escapeHtml(row.username || '')}</td>
        <td>${escapeHtml(row.action || '')}</td>
        <td>${escapeHtml(row.table_label || row.table || '')}</td>
        <td>${escapeHtml(row.record_id || '')}</td>
        <td>${escapeHtml(row.summary || '')}</td>
        <td class="actions"><button class="btn btn-sm" onclick="showEditForm('${row.table}', ${Number(row.record_id) || 0})">Open</button></td>
      </tr>
    `).join('');
    setSyncStatus(`Audit updated ${formatClock()}`);
  } catch (err) {
    table.querySelector('thead').innerHTML = '<tr><th>Audit</th></tr>';
    table.querySelector('tbody').innerHTML = `<tr><td class="empty-cell">${escapeHtml(err.message)}</td></tr>`;
    setSyncStatus(err.message || 'Audit failed', 'error');
  }
}

async function runBackupNow() {
  const status = $('backup-status');
  if (status) status.textContent = 'Creating backup...';
  try {
    const result = await api('/api/records/backup/run', { method: 'POST', body: JSON.stringify({}) });
    if (status) status.textContent = result.path || 'Backup created';
    setSyncStatus('Backup created');
  } catch (err) {
    if (status) status.textContent = err.message;
    alert(err.message);
  }
}

function reportCommandHtml() {
  return `
    <div class="report-workspace">
      <div class="report-title-block">
        <div>
          <h1>Dealings Reports</h1>
          <p>Rent, sale, and combined PDF reports</p>
        </div>
        <span id="report-status" class="status-pill">PDF ready</span>
      </div>
      <div class="report-command">
        <div class="field">
          <label>From</label>
          <input id="report-start" type="date">
        </div>
        <div class="field">
          <label>To</label>
          <input id="report-end" type="date">
        </div>
        <div class="report-action-group">
          <button class="btn btn-primary" type="button" data-report-kind="rent">Rent PDF</button>
          <button class="btn btn-primary" type="button" data-report-kind="sale">Sale PDF</button>
          <button class="btn" type="button" data-report-kind="all">Rent + Sale PDF</button>
        </div>
      </div>
    </div>
  `;
}

function bindReportButtons() {
  document.querySelectorAll('[data-report-kind]').forEach(button => {
    button.addEventListener('click', () => openDealingsPdf(button.dataset.reportKind || 'all', button));
  });
}

function reportPdfName(kind) {
  const prefix = kind === 'rent' ? 'rent_report' : kind === 'sale' ? 'sale_report' : 'property_dealings_report';
  const stamp = new Date().toISOString().slice(0, 10).replace(/-/g, '');
  return `${prefix}_${stamp}.pdf`;
}

async function openDealingsPdf(kind = 'all', button = null) {
  const start = $('report-start')?.value || '';
  const end = $('report-end')?.value || '';
  const params = new URLSearchParams({ kind });
  if (start) params.set('start_date', start);
  if (end) params.set('end_date', end);
  const status = $('report-status');
  const originalText = button?.textContent || '';
  try {
    if (button) {
      button.disabled = true;
      button.textContent = 'Creating...';
    }
    if (status) {
      status.textContent = 'Creating PDF...';
      status.classList.add('busy');
      status.classList.remove('error');
    }
    const blob = await apiBlob(`/api/reports/dealings/pdf?${params.toString()}`);
    const url = URL.createObjectURL(blob);
    const opened = window.open(url, '_blank', 'noopener');
    if (!opened) {
      const link = document.createElement('a');
      link.href = url;
      link.download = reportPdfName(kind);
      document.body.appendChild(link);
      link.click();
      link.remove();
    }
    setTimeout(() => URL.revokeObjectURL(url), 60000);
    if (status) {
      status.textContent = 'PDF opened';
      status.classList.remove('busy');
    }
    setSyncStatus('PDF report created');
  } catch (err) {
    if (status) {
      status.textContent = err.message || 'PDF failed';
      status.classList.remove('busy');
      status.classList.add('error');
    }
    alert(err.message);
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = originalText;
    }
  }
}

async function loadReports() {
  try {
    setSyncStatus('Loading reports...', 'busy');
    $('reports-content').innerHTML = '<div class="report-grid">' + Array.from({ length: 4 }).map(() => '<div class="glass-card report-item"><span class="skeleton-row"></span><span class="skeleton-row" style="width:55%;margin-top:10px"></span></div>').join('') + '</div>';
    const role = normalizeRole(currentUser?.role);
    if (role === 'Staff' || role === 'Viewer') {
      $('reports-content').innerHTML = reportCommandHtml();
      bindReportButtons();
      setSyncStatus(`Reports updated ${formatClock()}`);
      return;
    }
    const [fin, prop, emp] = await Promise.all([
      api('/api/reports/financial'),
      api('/api/reports/properties'),
      api('/api/reports/employees'),
    ]);
    $('reports-content').innerHTML = `
      ${reportCommandHtml()}
      <div class="report-section report-section-panel">
        <h3>Financial Summary</h3>
        <div class="report-grid">
          <div class="glass-card report-item"><div class="value" style="color:var(--success)">${formatMoney(fin.total_income)}</div><div class="label">Total Income</div></div>
          <div class="glass-card report-item"><div class="value" style="color:var(--danger)">${formatMoney(fin.total_expense)}</div><div class="label">Total Expense</div></div>
          <div class="glass-card report-item"><div class="value">${formatMoney(fin.net_profit)}</div><div class="label">Net Profit</div></div>
          <div class="glass-card report-item"><div class="value">${fin.profit_margin}%</div><div class="label">Profit Margin</div></div>
        </div>
      </div>
      <div class="report-section report-section-panel">
        <h3>Income by Type</h3>
        <div class="report-grid">${Object.entries(fin.income_by_type||{}).map(([k,v]) =>
          `<div class="glass-card report-item"><div class="value">${formatMoney(v)}</div><div class="label">${escapeHtml(k)}</div></div>`
        ).join('')}</div>
      </div>
      <div class="report-section report-section-panel">
        <h3>Expenses by Category</h3>
        <div class="report-grid">${Object.entries(fin.expense_by_category||{}).map(([k,v]) =>
          `<div class="glass-card report-item"><div class="value" style="color:var(--danger)">${formatMoney(v)}</div><div class="label">${escapeHtml(k)}</div></div>`
        ).join('')}</div>
      </div>
      <div class="report-section report-section-panel">
        <h3>Properties (${prop.total})</h3>
        <div class="report-grid">
          <div class="glass-card report-item"><div class="value">${prop.presentation_ready || 0}</div><div class="label">Presentation Ready</div></div>
          ${Object.entries(prop.by_status || {}).map(([k,v]) =>
            `<div class="glass-card report-item"><div class="value">${v}</div><div class="label">${escapeHtml(k)}</div></div>`
          ).join('')}
          ${Object.entries(prop.by_verification || {}).map(([k,v]) =>
            `<div class="glass-card report-item"><div class="value">${v}</div><div class="label">${escapeHtml(k)}</div></div>`
          ).join('')}
        </div>
      </div>
      <div class="report-section report-section-panel">
        <h3>Employees (${emp.total})</h3>
        <div class="report-grid">
          <div class="glass-card report-item"><div class="value">${emp.total}</div><div class="label">Total Employees</div></div>
          <div class="glass-card report-item"><div class="value">${formatMoney(emp.total_payroll)}</div><div class="label">Monthly Payroll</div></div>
          <div class="glass-card report-item"><div class="value">${emp.attendance?.attendance_rate || 0}%</div><div class="label">Attendance Rate</div></div>
          <div class="glass-card report-item"><div class="value">${formatCell(emp.attendance?.worked_minutes || 0, 'worked_minutes')}</div><div class="label">Worked Hours</div></div>
          <div class="glass-card report-item"><div class="value">${formatCell(emp.attendance?.overtime_minutes || 0, 'overtime_minutes')}</div><div class="label">Overtime</div></div>
          <div class="glass-card report-item"><div class="value">${emp.attendance?.late_days || 0}</div><div class="label">Late Days</div></div>
        </div>
      </div>
    `;
    bindReportButtons();
    setSyncStatus(`Reports updated ${formatClock()}`);
  } catch (err) {
    console.error(err);
    setSyncStatus(err.message || 'Reports failed', 'error');
  }
}

function openSettings() {
  if (!isAdmin()) {
    alert('Only Admin and Super Admin users can manage settings.');
    return;
  }
  const html = `
    <div class="settings-tabs">
      <button class="btn btn-primary" type="button" id="settings-users-tab">Users</button>
      <button class="btn" type="button" id="settings-crm-tab">CRM Settings</button>
    </div>
    <div id="settings-panel"></div>
  `;
  $('modal-body').innerHTML = html;
  openModal('Settings', { wide: true });
  $('settings-users-tab').onclick = showSettingsUsers;
  $('settings-crm-tab').onclick = showPhaseSettings;
  showSettingsUsers();
}

function setSettingsTab(active) {
  $('settings-users-tab')?.classList.toggle('btn-primary', active === 'users');
  $('settings-crm-tab')?.classList.toggle('btn-primary', active === 'crm');
}

function showSettingsUsers() {
  setSettingsTab('users');
  $('modal-save').classList.add('hidden');
  $('settings-panel').innerHTML = `
    <div style="margin-bottom:16px"><button class="btn btn-primary" onclick="showUserForm()">+ Add User</button></div>
    <div id="users-list"></div>
  `;
  loadUsers();
}

function settingsField(label, id, value, attrs = '') {
  return `<div class="field"><label>${label}</label><input id="${id}" value="${escapeHtml(value || '')}" ${attrs}></div>`;
}

function settingsListEditor(label, id, values, rows = 6) {
  const items = normalizeOptionList(values, []);
  return `
    <div class="settings-list-editor">
      <div class="settings-list-head">
        <label for="${id}">${label}</label>
        <span>${items.length} items</span>
      </div>
      <textarea id="${id}" rows="${rows}">${escapeHtml(items.join('\n'))}</textarea>
    </div>
  `;
}

async function showPhaseSettings() {
  setSettingsTab('crm');
  await loadPhase1Settings();
  $('modal-save').classList.remove('hidden');
  $('modal-save').textContent = 'Save Settings';
  $('settings-panel').innerHTML = `
    <div class="settings-layout">
      <section class="settings-section">
        <div class="settings-section-head"><h4>Company</h4></div>
        <div class="form-grid settings-form">
          ${settingsField('Agency Name', 'set-company-name', phase1Settings.company_name || companyName)}
          ${settingsField('Logo URL', 'set-company-logo', phase1Settings.company_logo || '')}
          ${settingsField('Company Phone', 'set-company-phone', phase1Settings.company_phone || '')}
          ${settingsField('Company Email', 'set-company-email', phase1Settings.company_email || '', 'type="email"')}
          <div class="field field-full"><label>Company Address</label><input id="set-company-address" value="${escapeHtml(phase1Settings.company_address || '')}"></div>
          <div class="field"><label>Theme</label><select id="set-theme"><option>Light</option><option>Dark</option></select></div>
        </div>
      </section>
      <section class="settings-section">
        <div class="settings-section-head"><h4>Financial</h4></div>
        <div class="form-grid settings-form">
          ${settingsField('Currency Symbol', 'set-currency-symbol', phase1Settings.currency_symbol || 'Rs.')}
          ${settingsField('Default Commission %', 'set-default-commission', phase1Settings.default_commission || '', 'type="number" step="0.01"')}
          ${settingsField('Tax Rate %', 'set-tax-rate', phase1Settings.tax_rate || '', 'type="number" step="0.01"')}
          <div class="field field-full"><label>Bank Account</label><input id="set-bank-account" value="${escapeHtml(phase1Settings.bank_account || '')}"></div>
          <div class="field field-full">${settingsListEditor('Expense Categories', 'set-expense-categories', phase1Settings.expenseCategories || EXPENSE_CATEGORIES, 7)}</div>
        </div>
      </section>
      <section class="settings-section settings-section-wide">
        <div class="settings-section-head"><h4>CRM Lists</h4></div>
        <div class="settings-list-grid">
          ${settingsListEditor('Locations', 'set-areas', phase1Settings.areas || DEFAULT_PHASE1.areas, 7)}
          ${settingsListEditor('Facilities', 'set-facilities', phase1Settings.facilities || DEFAULT_PHASE1.facilities, 6)}
          ${settingsListEditor('Floors', 'set-floors', phase1Settings.floors || DEFAULT_PHASE1.floors, 5)}
          ${settingsListEditor('Property Types', 'set-property-types', phase1Settings.propertyTypes || DEFAULT_PHASE1.propertyTypes, 5)}
          ${settingsListEditor('Measurement Units', 'set-measurement-units', phase1Settings.measurementUnits || DEFAULT_PHASE1.measurementUnits, 3)}
        </div>
      </section>
    </div>
  `;
  $('set-theme').value = phase1Settings.theme || 'Light';
  $('modal-save').onclick = savePhaseSettings;
}

function settingsLines(id, fallback = []) {
  return normalizeOptionList($(id)?.value || '', fallback);
}

async function savePhaseSettings() {
  try {
    await api('/api/records/phase1/settings', {
      method: 'PUT',
      body: JSON.stringify({
        company_name: $('set-company-name').value,
        company_address: $('set-company-address').value,
        company_phone: $('set-company-phone').value,
        company_email: $('set-company-email').value,
        company_logo: $('set-company-logo').value,
        currency_symbol: $('set-currency-symbol').value,
        default_commission: $('set-default-commission').value,
        tax_rate: $('set-tax-rate').value,
        bank_account: $('set-bank-account').value,
        theme: $('set-theme').value,
        areas: settingsLines('set-areas', DEFAULT_PHASE1.areas),
        facilities: settingsLines('set-facilities', DEFAULT_PHASE1.facilities),
        floors: settingsLines('set-floors', DEFAULT_PHASE1.floors),
        property_types: settingsLines('set-property-types', DEFAULT_PHASE1.propertyTypes),
        measurement_units: settingsLines('set-measurement-units', DEFAULT_PHASE1.measurementUnits),
        expense_categories: settingsLines('set-expense-categories', EXPENSE_CATEGORIES),
      })
    });
    await loadPhase1Settings();
    setSyncStatus('Settings saved');
    closeModal();
  } catch (err) {
    alert(err.message);
  }
}

async function loadUsers() {
  try {
    const users = await api('/api/auth/users');
    $('users-list').innerHTML = `<table>
      <thead><tr><th>ID</th><th>Username</th><th>Full Name</th><th>Email</th><th>Role</th><th>Active</th><th>Actions</th></tr></thead>
      <tbody>${users.map(u => `<tr>
        <td>${u.id}</td><td>${escapeHtml(u.username)}</td><td>${escapeHtml(u.full_name||'')}</td><td>${escapeHtml(u.email||'')}</td>
        <td>${escapeHtml(u.role)}</td><td>${u.is_active ? 'Yes' : 'No'}</td>
        <td class="actions">
          <button class="btn btn-sm" onclick="editUser(${u.id})">Edit</button>
          <button class="btn btn-sm btn-danger" onclick="removeUser(${u.id})">Remove</button>
        </td>
      </tr>`).join('')}</tbody>
    </table>`;
  } catch (err) { alert(err.message); }
}

function showUserForm() {
  const html = `<div class="form-grid">
    <div class="field"><label>Username</label><input id="uf-username"></div>
    <div class="field"><label>Password</label><input id="uf-password" type="password"></div>
    <div class="field"><label>Full Name</label><input id="uf-full_name"></div>
    <div class="field"><label>Email</label><input id="uf-email" type="email"></div>
    <div class="field"><label>Role</label><select id="uf-role"><option>Staff</option><option>Manager</option><option>Admin</option><option>Viewer</option><option>Super Admin</option></select></div>
  </div>`;
  $('modal-body').innerHTML = html;
  openModal('Add User');
  $('modal-save').classList.remove('hidden');
  $('modal-save').textContent = 'Save';
  $('modal-save').onclick = async () => {
    try {
      await api('/api/auth/users', { method: 'POST', body: JSON.stringify({
        username: $('uf-username').value,
        password: $('uf-password').value,
        full_name: $('uf-full_name').value,
        email: $('uf-email').value,
        role: $('uf-role').value
      })});
      closeModal(); openSettings();
    } catch (err) { alert(err.message); }
    $('modal-save').onclick = saveForm;
  };
}

async function editUser(id) {
  let user;
  try {
    user = await api(`/api/auth/users/${id}`);
  } catch (err) {
    alert(err.message);
    return;
  }
  const html = `<div class="form-grid">
    <div class="field"><label>Username</label><input id="uf-username" value="${escapeHtml(user.username)}"></div>
    <div class="field"><label>New Password</label><input id="uf-password" type="password"></div>
    <div class="field"><label>Full Name</label><input id="uf-full_name" value="${escapeHtml(user.full_name || '')}"></div>
    <div class="field"><label>Email</label><input id="uf-email" type="email" value="${escapeHtml(user.email || '')}"></div>
    <div class="field"><label>Role</label><select id="uf-role"><option>Staff</option><option>Manager</option><option>Admin</option><option>Viewer</option><option>Super Admin</option></select></div>
    <div class="field"><label>Active</label><select id="uf-is_active"><option value="true">Yes</option><option value="false">No</option></select></div>
  </div>`;
  $('modal-body').innerHTML = html;
  $('uf-role').value = user.role || 'Staff';
  $('uf-is_active').value = user.is_active ? 'true' : 'false';
  openModal('Edit User');
  $('modal-save').classList.remove('hidden');
  $('modal-save').textContent = 'Save';
  $('modal-save').onclick = async () => {
    const data = {};
    const g = k => { const e = $(`uf-${k}`); return e ? e.value : undefined; };
    if (g('username')) data.username = g('username');
    if (g('password')) data.password = g('password');
    if (g('full_name')) data.full_name = g('full_name');
    if (g('email')) data.email = g('email');
    data.role = g('role');
    data.is_active = g('is_active') === 'true';
    try {
      await api(`/api/auth/users/${id}`, { method: 'PUT', body: JSON.stringify(data) });
      closeModal(); openSettings();
    } catch (err) { alert(err.message); }
    $('modal-save').onclick = saveForm;
  };
}

async function removeUser(id) {
  if (!confirm('Remove this user? Their login will be disabled.')) return;
  try {
    await api(`/api/auth/users/${id}`, { method: 'DELETE' });
    loadUsers();
  } catch (err) {
    alert(err.message);
  }
}

if (token) {
  api('/api/auth/me').then(u => {
    currentUser = u;
    currentUser.role = normalizeRole(currentUser.role);
    $('user-badge').textContent = u.role;
    setupNavigationForRole();
    showMain();
    switchTab(firstAllowedTab());
  }).catch(() => logout());
} else {
  showLogin();
}

// Mobile menu handlers
const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
const sidebar = document.getElementById('sidebar');
const sidebarOverlay = document.getElementById('sidebar-overlay');

function openMobileMenu() {
  sidebar.classList.add('open');
  sidebarOverlay.classList.add('visible');
}

function closeMobileMenu() {
  sidebar.classList.remove('open');
  sidebarOverlay.classList.remove('visible');
}

if (mobileMenuToggle) {
  mobileMenuToggle.addEventListener('click', openMobileMenu);
}

if (sidebarOverlay) {
  sidebarOverlay.addEventListener('click', closeMobileMenu);
}

// Close mobile menu when clicking nav items
const navItems = document.querySelectorAll('.nav-item');
navItems.forEach(item => {
  item.addEventListener('click', closeMobileMenu);
});

// Desktop UI Data Grid Functions
let desktopCurrentTable = 'rent_requirements';
let desktopSelectedRows = new Set();
let desktopAllRows = [];

const TABLE_COLUMNS = {
  rent_requirements: ['id', 'date', 'client_name', 'client_status', 'contact_phone', 'property_requires', 'size', 'floor', 'budget'],
  rent_availability: ['id', 'date', 'owner_name', 'client_broker', 'owner_phone', 'property_availability', 'size', 'floor', 'monthly_rent', 'status'],
  sale_requirements: ['id', 'date', 'client_name', 'client_status', 'contact_phone', 'property_requires', 'size', 'floor', 'budget'],
  sale_availability: ['id', 'date', 'owner_name', 'client_broker', 'owner_phone', 'property_availability', 'size', 'floor', 'demand', 'status']
};

const COLUMN_LABELS = {
  id: 'SERIAL NO.',
  date: 'DATE',
  client_name: 'NAME',
  owner_name: 'NAME',
  client_status: 'STATUS',
  client_broker: 'STATUS',
  contact_phone: 'CONTACT',
  owner_phone: 'CONTACT',
  property_requires: 'PROPERTY REQUIRED/NEEDED',
  property_availability: 'PROPERTY AVAILABLE',
  size: 'ROOMS',
  measurement: 'MEASUREMENT',
  measurement_unit: 'SIZE',
  floor: 'FLOOR',
  budget: 'BUDGET',
  monthly_rent: 'RENT',
  demand: 'DEMAND',
  status: 'AVAILABILITY'
};

function desktopColumns(table = desktopCurrentTable) {
  return TABLE_COLUMNS[table] || TABLE_COLUMNS.rent_requirements;
}

function renderDesktopGridHeader(table = desktopCurrentTable) {
  const grid = document.getElementById('data-grid');
  const head = grid?.querySelector('thead tr');
  if (!head) return;
  const columns = desktopColumns(table);
  head.innerHTML = `<th class="select-col"><input type="checkbox" id="select-all-header"></th>` +
    columns.map(col => `<th>${escapeHtml(COLUMN_LABELS[col] || col.replace(/_/g, ' ').toUpperCase())}</th>`).join('');
  bindDesktopHeaderCheckbox();
}

function bindDesktopHeaderCheckbox() {
  const headerCb = document.getElementById('select-all-header');
  if (!headerCb || headerCb.dataset.bound === '1') return;
  headerCb.dataset.bound = '1';
  headerCb.addEventListener('change', (e) => {
    if (e.target.checked) {
      desktopAllRows.forEach(row => desktopSelectedRows.add(Number(row.id) || 0));
    } else {
      desktopSelectedRows.clear();
    }
    renderDesktopGrid();
    updateDesktopSelection();
  });
}

async function loadDesktopGrid(table) {
  desktopCurrentTable = table;
  desktopSelectedRows.clear();
  updateDesktopSelection();
  
  const tbody = document.getElementById('data-grid-body');
  if (!tbody) return;
  const columns = desktopColumns(table);
  renderDesktopGridHeader(table);
  
  tbody.innerHTML = `<tr><td colspan="${columns.length + 1}" class="empty-cell">Loading...</td></tr>`;
  
  try {
    const data = await api(`/api/records/${table}?limit=50`);
    desktopAllRows = data.rows || [];
    renderDesktopGrid();
    document.getElementById('table-title').textContent = PHASE1_LABELS[table] || table.replace(/_/g, ' ');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="${columns.length + 1}" class="empty-cell">Error: ${escapeHtml(err.message)}</td></tr>`;
  }
}

function renderDesktopGrid() {
  const tbody = document.getElementById('data-grid-body');
  if (!tbody) return;
  
  if (!desktopAllRows.length) {
    tbody.innerHTML = `<tr><td colspan="${desktopColumns().length + 1}" class="empty-cell">No records found.</td></tr>`;
    return;
  }
  
  const columns = desktopColumns();
  
  tbody.innerHTML = desktopAllRows.map(row => {
    const rowId = Number(row.id) || 0;
    const checked = desktopSelectedRows.has(rowId) ? ' checked' : '';
    
    let cells = `<td class="select-col"><input type="checkbox" class="row-checkbox" data-id="${rowId}"${checked}></td>`;
    
    columns.forEach(col => {
      let value = row[col] || '';
      if ((col === 'contact_phone' || col === 'owner_phone') && !value) value = row.contact || '';
      if (col === 'date' && value) {
        const d = new Date(value);
        value = d.toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' }).replace(/\//g, '/');
      }
      if (col === 'measurement' && value) {
        value = parseFloat(value).toFixed(1);
      }
      cells += `<td>${escapeHtml(formatCell(value, col))}</td>`;
    });
    
    return `<tr data-id="${rowId}">${cells}</tr>`;
  }).join('');
  
  // Add event listeners
  tbody.querySelectorAll('.row-checkbox').forEach(cb => {
    cb.addEventListener('change', (e) => {
      const rowId = Number(e.target.dataset.id);
      if (e.target.checked) {
        desktopSelectedRows.add(rowId);
      } else {
        desktopSelectedRows.delete(rowId);
      }
      updateDesktopSelection();
    });
  });
  
  // Row click to toggle selection
  tbody.querySelectorAll('tr[data-id]').forEach(tr => {
    tr.addEventListener('click', (e) => {
      if (e.target.tagName === 'INPUT') return;
      const cb = tr.querySelector('.row-checkbox');
      if (cb) cb.click();
    });
  });
}

function updateDesktopSelection() {
  const countEl = document.getElementById('selection-count');
  if (countEl) {
    countEl.textContent = `${desktopSelectedRows.size} of ${desktopAllRows.length} selected`;
  }
  
  // Update header checkbox
  const headerCb = document.getElementById('select-all-header');
  if (headerCb) {
    if (desktopSelectedRows.size === 0) {
      headerCb.checked = false;
      headerCb.indeterminate = false;
    } else if (desktopSelectedRows.size === desktopAllRows.length) {
      headerCb.checked = true;
      headerCb.indeterminate = false;
    } else {
      headerCb.checked = false;
      headerCb.indeterminate = true;
    }
  }
}

function desktopSelectedIdsArray() {
  return Array.from(desktopSelectedRows).map(Number).filter(Boolean);
}

function requireSingleDesktopSelected() {
  const selected = desktopSelectedIdsArray();
  if (selected.length !== 1) {
    alert(selected.length ? 'Please select only one record.' : 'Please select one record first.');
    return null;
  }
  return selected[0];
}

function desktopSelectedRecords() {
  const ids = new Set(desktopSelectedIdsArray());
  return desktopAllRows.filter(row => ids.has(Number(row.id) || 0));
}

function showDesktopSelectedDetails() {
  const id = requireSingleDesktopSelected();
  if (!id) return;
  const record = desktopAllRows.find(row => Number(row.id) === Number(id)) || {};
  const fields = FIELDS[desktopCurrentTable] || [];
  const rows = fields.map(field => `
    <tr>
      <th>${escapeHtml(field.label)}</th>
      <td>${escapeHtml(formatCell(record[field.key], field.key))}</td>
    </tr>
  `).join('');
  showReadonlyModal(
    `Details - ${tableTitle(desktopCurrentTable)} #${id}`,
    `<table class="details-table"><tbody>${rows}</tbody></table>`
  );
}

async function copyDesktopSelectedRows() {
  const rows = desktopSelectedRecords();
  if (!rows.length) {
    alert('Select records to copy first.');
    return;
  }
  const text = rowsToDelimited(rows, FIELDS[desktopCurrentTable] || []);
  try {
    await navigator.clipboard.writeText(text);
  } catch (_err) {
    const temp = document.createElement('textarea');
    temp.value = text;
    document.body.appendChild(temp);
    temp.select();
    document.execCommand('copy');
    temp.remove();
  }
  setSyncStatus(`Copied ${rows.length} record${rows.length === 1 ? '' : 's'}`);
}

async function markDesktopPending() {
  const id = requireSingleDesktopSelected();
  if (!id) return;
  await markAvailability(desktopCurrentTable, id, 'Pending');
  await loadDesktopGrid(desktopCurrentTable);
}

function matchDesktopSelected() {
  const id = requireSingleDesktopSelected();
  if (!id) return;
  if (desktopCurrentTable !== 'rent_requirements' && desktopCurrentTable !== 'sale_requirements') {
    alert('Match search starts from a rent or sale requirement.');
    return;
  }
  findMatch(desktopCurrentTable, id);
}

function showDesktopRecycleBin() {
  openPhaseSection(desktopCurrentTable);
  showRecycleBin(desktopCurrentTable);
}

// Initialize Desktop UI
document.addEventListener('DOMContentLoaded', () => {
  // Table tab switching
  document.querySelectorAll('.table-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.table-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const table = tab.dataset.table;
      if (table) loadDesktopGrid(table);
    });
  });
  
  // Select all header checkbox
  bindDesktopHeaderCheckbox();
  
  // Toolbar buttons
  document.getElementById('btn-select-all')?.addEventListener('click', () => {
    desktopAllRows.forEach(row => desktopSelectedRows.add(Number(row.id) || 0));
    renderDesktopGrid();
    updateDesktopSelection();
  });
  
  document.getElementById('btn-clear-selection')?.addEventListener('click', () => {
    desktopSelectedRows.clear();
    renderDesktopGrid();
    updateDesktopSelection();
  });
  
  document.getElementById('btn-refresh-table')?.addEventListener('click', () => {
    loadDesktopGrid(desktopCurrentTable);
  });
  
  document.getElementById('btn-add-new')?.addEventListener('click', () => {
    showPhaseForm(desktopCurrentTable);
  });
  
  document.getElementById('btn-edit')?.addEventListener('click', () => {
    const selected = Array.from(desktopSelectedRows);
    if (selected.length === 0) {
      alert('Please select a record to edit.');
      return;
    }
    if (selected.length > 1) {
      alert('Please select only one record to edit.');
      return;
    }
    showPhaseForm(desktopCurrentTable, selected[0]);
  });
  
  document.getElementById('btn-delete')?.addEventListener('click', async () => {
    const selected = Array.from(desktopSelectedRows);
    if (selected.length === 0) {
      alert('Please select at least one record to delete.');
      return;
    }
    if (!confirm(`Delete ${selected.length} selected record(s)?`)) return;
    
    for (const id of selected) {
      try {
        await api(`/api/records/${desktopCurrentTable}/${id}`, { method: 'DELETE' });
      } catch (err) {
        alert(`Error deleting #${id}: ${err.message}`);
      }
    }
    loadDesktopGrid(desktopCurrentTable);
  });

  document.getElementById('btn-mark-pending')?.addEventListener('click', markDesktopPending);
  document.getElementById('btn-match')?.addEventListener('click', matchDesktopSelected);
  document.getElementById('btn-import')?.addEventListener('click', () => importTableCsv(desktopCurrentTable));
  document.getElementById('btn-export')?.addEventListener('click', () => exportTableCsv(desktopCurrentTable));
  document.getElementById('btn-template')?.addEventListener('click', () => downloadTemplate(desktopCurrentTable));
  document.getElementById('btn-recycle')?.addEventListener('click', showDesktopRecycleBin);
  document.getElementById('btn-details')?.addEventListener('click', showDesktopSelectedDetails);
  document.getElementById('btn-copy')?.addEventListener('click', copyDesktopSelectedRows);
  
  document.getElementById('btn-home-tab')?.addEventListener('click', () => {
    switchTab('phase1');
  });
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
  // Ctrl/Cmd + K: Open global search
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    document.getElementById('find-query')?.focus();
    switchTab('find');
  }
  
  // Ctrl/Cmd + N: Create new record
  if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
    e.preventDefault();
    const addBtn = document.querySelector('.tab-content.active .add-btn');
    if (addBtn) addBtn.click();
  }
  
  // Escape: Close modal
  if (e.key === 'Escape') {
    const modalOverlay = document.getElementById('modal-overlay');
    if (modalOverlay && !modalOverlay.classList.contains('hidden')) {
      closeModal();
    }
    closeMobileMenu();
    closeAllMenuDropdowns();
  }
});

// Menu Dropdowns
function closeAllMenuDropdowns() {
  document.querySelectorAll('.menu-dropdown').forEach(d => d.classList.remove('active'));
  document.querySelectorAll('.menu-item.open').forEach(item => item.classList.remove('open'));
}

// Event delegation on the menu bar for toggle + actions (no stopPropagation conflicts)
document.getElementById('top-menu-bar')?.addEventListener('click', (e) => {
  // Click on a menu-dropdown-item: execute action
  const dropdownItem = e.target.closest('.menu-dropdown-item');
  if (dropdownItem) {
    const action = dropdownItem.dataset.action;
    closeAllMenuDropdowns();
    handleMenuAction(action);
    return;
  }

  // Click on a menu-item: toggle dropdown
  const menuItem = e.target.closest('.menu-item');
  if (menuItem) {
    const dropdown = menuItem.querySelector('.menu-dropdown');
    if (dropdown) {
      const isActive = dropdown.classList.contains('active');
      closeAllMenuDropdowns();
      if (!isActive) {
        dropdown.classList.add('active');
        menuItem.classList.add('open');
      }
    }
  }
});

// Close menus when clicking outside the menu bar
document.addEventListener('click', (e) => {
  if (!e.target.closest('#top-menu-bar')) {
    closeAllMenuDropdowns();
  }
});

function showDocumentationModal() {
  showReadonlyModal('Documentation', `
    <div class="details-table-wrap">
      <table class="details-table"><tbody>
        <tr><th>New / Edit / Delete</th><td>Use the selected QT CRM table and current row selection.</td></tr>
        <tr><th>Import</th><td>Choose a CSV or Excel file that matches the table template.</td></tr>
        <tr><th>Export</th><td>Downloads the current table report as CSV or opens report output.</td></tr>
        <tr><th>Match</th><td>Select one rent or sale requirement first.</td></tr>
        <tr><th>Settings</th><td>Admins can manage floors, locations, facilities, users, and company details.</td></tr>
      </tbody></table>
    </div>
  `);
}

function showAboutModal() {
  showReadonlyModal('About', `
    <table class="details-table"><tbody>
      <tr><th>Application</th><td>Real Estate CRM</td></tr>
      <tr><th>Company</th><td>${escapeHtml(companyName || 'MBM Enterprises')}</td></tr>
      <tr><th>User</th><td>${escapeHtml(currentUser?.username || currentUser?.full_name || '')}</td></tr>
      <tr><th>Role</th><td>${escapeHtml(currentUser?.role || '')}</td></tr>
    </tbody></table>
  `);
}

function handleMenuAction(action) {
  switch (action) {
    case 'new':
      showPhaseForm(desktopCurrentTable);
      break;
    case 'edit':
      const selected = Array.from(desktopSelectedRows);
      if (selected.length === 1) {
        showPhaseForm(desktopCurrentTable, selected[0]);
      } else {
        alert('Please select one record to edit.');
      }
      break;
    case 'delete':
      document.getElementById('btn-delete')?.click();
      break;
    case 'import':
      importTableCsv(desktopCurrentTable);
      break;
    case 'export':
      exportTableCsv(desktopCurrentTable);
      break;
    case 'print':
      window.print();
      break;
    case 'exit':
      logout();
      break;
    case 'toggle-sidebar':
      toggleSidebar();
      break;
    case 'dashboard':
      switchTab('dashboard');
      break;
    case 'refresh':
      refreshCurrentView();
      break;
    case 'rent-requirements':
      switchTableTab('rent_requirements');
      break;
    case 'rent-availability':
      switchTableTab('rent_availability');
      break;
    case 'sale-requirements':
      switchTableTab('sale_requirements');
      break;
    case 'sale-availability':
      switchTableTab('sale_availability');
      break;
    case 'rent-dealings':
      switchTab('rent');
      break;
    case 'sale-dealings':
      switchTab('sale');
      break;
    case 'properties':
      switchTab('properties');
      break;
    case 'clients':
      switchTab('clients');
      break;
    case 'brokers':
      switchTab('broker_contacts');
      break;
    case 'employees':
      switchTab('employees');
      break;
    case 'financial':
      switchTab('financial');
      break;
    case 'all-reports':
      switchTab('reports');
      break;
    case 'summary':
      switchTab('dashboard');
      break;
    case 'employees-sf':
    case 'recruiting':
    case 'performance':
    case 'compensation':
      switchTab('successfactors');
      break;
    case 'approvals':
      switchTab('approvals');
      break;
    case 'tasks':
      switchTab('workflow');
      break;
    case 'audit':
      switchTab('audit');
      break;
    case 'find':
      switchTab('find');
      break;
    case 'match':
      matchDesktopSelected();
      break;
    case 'backup':
      runBackupNow();
      break;
    case 'settings':
      openSettings();
      break;
    case 'documentation':
      showDocumentationModal();
      break;
    case 'about':
      showAboutModal();
      break;
    case 'export-reports':
      switchTab('reports');
      setTimeout(() => openDealingsPdf('all'), 450);
      break;
  }
}

function switchTableTab(table) {
  document.querySelectorAll('.table-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.table === table);
  });
  loadDesktopGrid(table);
}

// Sidebar Toggle
let sidebarCollapsed = false;

function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const toggle = document.getElementById('sidebar-toggle');
  if (!sidebar) return;
  
  sidebarCollapsed = !sidebarCollapsed;
  sidebar.classList.toggle('sidebar-hidden', sidebarCollapsed);
  toggle?.classList.toggle('sidebar-collapsed', sidebarCollapsed);
}

// Auto-hide sidebar when modal opens
const originalOpenModal = openModal;
openModal = function(title, options = {}) {
  hideSidebarForFocus();
  originalOpenModal(title, options);
};

const originalCloseModal = closeModal;
closeModal = function() {
  originalCloseModal();
  restoreSidebarAfterFocus();
};

// Sidebar toggle button
document.getElementById('sidebar-toggle')?.addEventListener('click', toggleSidebar);

// Phase form handling - auto hide sidebar
const originalShowPhaseForm = showPhaseForm;
showPhaseForm = function(table, id) {
  hideSidebarForFocus();
  originalShowPhaseForm(table, id);
};
