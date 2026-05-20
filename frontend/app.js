const API = '';
let token = localStorage.getItem('token');
let currentUser = null;
let currentTab = 'dashboard';
let currentSub = 'rent_requirements';
let refreshBusy = false;
let companyName = 'MBM Enterprises';
const tableState = {};
const TABLE_PAGE_SIZE = 100;
let tableSearchTimer = null;
const printableRowsPerPage = 18;

const PIPELINE_TABLES = ['rent_requirements','rent_availability','sale_requirements','sale_availability'];
const ROLE_TABS = {
  'Super Admin': ['dashboard','rent','sale','find','followups','financial','employees','clients','properties','reports','audit'],
  'Admin': ['dashboard','rent','sale','find','followups','financial','employees','clients','properties','reports','audit'],
  'Manager': ['dashboard','rent','sale','find','followups','financial','employees','clients','properties','reports'],
  'Staff': ['rent','sale','find','followups'],
  'Viewer': ['dashboard','rent','sale','find','reports']
};

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
  sale_requirements: 'Sale Requirement',
  sale_availability: 'Sale Availability'
};

const SEARCH_COLUMNS = ['type','id','date','name','contact','property','amount','floor','location','facilities','remarks'];

const FIELDS = {
  rent_requirements: [
    {key:'date',label:'Date',type:'date'},{key:'client_name',label:'Name'},
    {key:'client_status',label:'Client Status',type:'select',options:['Client','Broker','Investor','Owner','Other']},
    {key:'broker',label:'Broker',type:'select',options:['Direct','Broker','Agent','Other']},{key:'contact',label:'Contact No.'},
    {key:'property_requires',label:'Property Requirement'},{key:'size',label:'Size'},{key:'measurement',label:'Measurement'},
    {key:'budget',label:'Budget',type:'number'},{key:'floor',label:'Floor'},{key:'location',label:'Location'},
    {key:'facilities',label:'Facilities'},
    {key:'client_broker',label:'Client/Broker'},{key:'bachelor_family',label:'Bachelor/Family'},{key:'remarks',label:'Remarks'},
    {key:'approval_status',label:'Status'},{key:'approval_comment',label:'Comment'}
  ],
  rent_availability: [
    {key:'date',label:'Date',type:'date'},{key:'owner_name',label:'Owner Name'},{key:'contact',label:'Contact'},
    {key:'property_availability',label:'Property Available'},{key:'size',label:'Size'},{key:'measurement',label:'Measurement'},
    {key:'monthly_rent',label:'Monthly Rent',type:'number'},{key:'floor',label:'Floor'},{key:'location',label:'Location'},
    {key:'bedrooms',label:'Beds'},{key:'bathrooms',label:'Baths'},{key:'furnishing',label:'Furnishing',type:'select',options:['','Unfurnished','Semi Furnished','Furnished']},
    {key:'parking',label:'Parking',type:'select',options:['','No','Bike','Car','Bike + Car']},{key:'nearby_landmarks',label:'Nearby Landmarks'},
    {key:'area_notes',label:'Area Notes'},{key:'verification_status',label:'Verification',type:'select',options:['Unverified','Phone Verified','Visited','Documents Checked']},
    {key:'photo_paths',label:'Photo Paths'},
    {key:'deposit',label:'Deposit',type:'number'},{key:'maintenance_charge',label:'Maintenance',type:'number'},
    {key:'facilities',label:'Facilities'},{key:'client_broker',label:'Client/Broker'},{key:'bachelor_family',label:'Bachelor/Family'},
    {key:'remarks',label:'Remarks'},{key:'status',label:'Availability Status',options:['Available','Rented','Sold','Reserved']},
    {key:'approval_status',label:'Status'},{key:'approval_comment',label:'Comment'}
  ],
  sale_requirements: [
    {key:'date',label:'Date',type:'date'},{key:'client_name',label:'Name'},
    {key:'client_status',label:'Client Status',type:'select',options:['Client','Broker','Investor','Owner','Other']},
    {key:'broker',label:'Broker',type:'select',options:['Direct','Broker','Agent','Other']},{key:'contact',label:'Contact No.'},
    {key:'property_requires',label:'Property Requirement'},{key:'size',label:'Size'},{key:'measurement',label:'Measurement'},
    {key:'budget',label:'Budget',type:'number'},{key:'floor',label:'Floor'},{key:'location',label:'Location'},
    {key:'facilities',label:'Facilities'},
    {key:'client_broker',label:'Client/Broker'},{key:'bachelor_family',label:'Bachelor/Family'},{key:'remarks',label:'Remarks'},
    {key:'approval_status',label:'Status'},{key:'approval_comment',label:'Comment'}
  ],
  sale_availability: [
    {key:'date',label:'Date',type:'date'},{key:'owner_name',label:'Owner Name'},{key:'contact',label:'Contact'},
    {key:'property_availability',label:'Property Available'},{key:'size',label:'Size'},{key:'measurement',label:'Measurement'},
    {key:'demand',label:'Demand (Price)',type:'number'},{key:'floor',label:'Floor'},{key:'location',label:'Location'},
    {key:'bedrooms',label:'Beds'},{key:'bathrooms',label:'Baths'},{key:'furnishing',label:'Furnishing',type:'select',options:['','Unfurnished','Semi Furnished','Furnished']},
    {key:'parking',label:'Parking',type:'select',options:['','No','Bike','Car','Bike + Car']},{key:'nearby_landmarks',label:'Nearby Landmarks'},
    {key:'area_notes',label:'Area Notes'},{key:'verification_status',label:'Verification',type:'select',options:['Unverified','Phone Verified','Visited','Documents Checked']},
    {key:'photo_paths',label:'Photo Paths'},
    {key:'facilities',label:'Facilities'},
    {key:'client_broker',label:'Client/Broker'},{key:'bachelor_family',label:'Bachelor/Family'},{key:'remarks',label:'Remarks'},
    {key:'status',label:'Availability Status',options:['Available','Rented','Sold','Reserved']},
    {key:'approval_status',label:'Status'},{key:'approval_comment',label:'Comment'}
  ],
  income_transactions: [
    {key:'transaction_date',label:'Date',type:'date'},{key:'income_type',label:'Income Type'},{key:'amount',label:'Amount',type:'number'},
    {key:'tenant_name',label:'Tenant Name'},{key:'description',label:'Description'},{key:'receipt_no',label:'Receipt No'},
    {key:'payment_method',label:'Payment Method'}
  ],
  expense_transactions: [
    {key:'transaction_date',label:'Date',type:'date'},{key:'expense_category',label:'Category'},{key:'amount',label:'Amount',type:'number'},
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
    {key:'employee_id',label:'Employee ID',type:'number'},{key:'date',label:'Date',type:'date'},{key:'check_in',label:'Check In'},
    {key:'check_out',label:'Check Out'},{key:'status',label:'Status'},{key:'notes',label:'Notes'}
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
  properties: [
    {key:'property_code',label:'Code'},{key:'title',label:'Title'},{key:'property_type',label:'Type'},{key:'status',label:'Status'},
    {key:'owner_name',label:'Owner'},{key:'owner_contact',label:'Owner Contact'},{key:'location',label:'Location'},{key:'area',label:'Area'},
    {key:'floor',label:'Floor'},{key:'bedrooms',label:'Beds'},{key:'bathrooms',label:'Baths'},
    {key:'furnishing',label:'Furnishing',type:'select',options:['','Unfurnished','Semi Furnished','Furnished']},{key:'parking',label:'Parking',type:'select',options:['','No','Bike','Car','Bike + Car']},
    {key:'nearby_landmarks',label:'Nearby Landmarks'},{key:'area_notes',label:'Area Notes'},
    {key:'verification_status',label:'Verification',type:'select',options:['Unverified','Phone Verified','Visited','Documents Checked']},{key:'photo_paths',label:'Photo Paths'},
    {key:'monthly_rent',label:'Monthly Rent',type:'number'},{key:'sale_price',label:'Sale Price',type:'number'},
    {key:'maintenance_charge',label:'Maintenance',type:'number'},{key:'facilities',label:'Facilities'},{key:'description',label:'Description'}
  ]
};

const SUB_TABLES = {
  rent: { rent_requirements: 'rent_requirements', rent_availability: 'rent_availability' },
  sale: { sale_requirements: 'sale_requirements', sale_availability: 'sale_availability' },
  financial: { income_transactions: 'income_transactions', expense_transactions: 'expense_transactions' },
  employees: { employees: 'employees', attendance: 'attendance', salary_payments: 'salary_payments' }
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
  return key === 'date' || key === 'transaction_date' || key === 'hire_date' || key.endsWith('_date');
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
  if (typeof value === 'number') {
    const moneyKeys = ['budget','monthly_rent','demand','sale_price','amount','base_salary','bonus','deductions','net_salary','maintenance_charge','deposit'];
    return moneyKeys.includes(key) ? `Rs. ${value.toLocaleString()}` : value.toLocaleString();
  }
  return String(value);
}

function formatMoney(value) {
  const number = Number(value || 0);
  return `Rs. ${number.toLocaleString()}`;
}

function listingQuality(table, row = {}) {
  const fieldSets = {
    rent_availability: ['owner_name','contact','property_availability','monthly_rent','location','size','floor','bedrooms','bathrooms','facilities','nearby_landmarks','verification_status','photo_paths'],
    sale_availability: ['owner_name','contact','property_availability','demand','location','size','floor','bedrooms','bathrooms','facilities','nearby_landmarks','verification_status','photo_paths'],
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
  if (res.status === 401) { logout(); throw new Error('Unauthorized'); }
  const data = await res.json();
  if (!res.ok) {
    const detail = data.detail;
    let message = 'Request failed';
    if (typeof detail === 'string') {
      message = detail;
    } else if (detail?.message) {
      const lines = Array.isArray(detail.errors) ? detail.errors : [];
      message = [detail.message, ...lines.map(item => `- ${item}`)].join('\n');
    }
    throw new Error(message);
  }
  return data;
}

function logout() { token = null; localStorage.removeItem('token'); currentUser = null; showLogin(); }
function showLogin() { $('login-screen').classList.remove('hidden'); $('main-screen').classList.add('hidden'); }
function showMain() { $('login-screen').classList.add('hidden'); $('main-screen').classList.remove('hidden'); }

function isAdmin() {
  const role = normalizeRole(currentUser?.role);
  return role === 'Super Admin' || role === 'Admin';
}
function allowedTabs() { return ROLE_TABS[normalizeRole(currentUser?.role)] || ['rent','sale','find']; }
function canAccessTab(tab) { return allowedTabs().includes(tab); }
function firstAllowedTab() { return allowedTabs()[0] || 'rent'; }

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
  currentTab = tab;
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  const el = $(`tab-${tab}`);
  if (el) el.classList.add('active');
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  document.querySelector(`.nav-item[data-tab="${tab}"]`)?.classList.add('active');
  const names = {dashboard:'Dashboard',rent:'Rent Dealings',sale:'Sale Dealings',find:'Find',followups:'Follow-ups',financial:'Financial',employees:'Employees',clients:'Clients',properties:'Properties',reports:'Reports',audit:'Audit History'};
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
  const username = $('login-username').value;
  const password = $('login-password').value;
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

document.querySelectorAll('.nav-item').forEach(el => {
  el.addEventListener('click', () => switchTab(el.dataset.tab));
});

setNetworkLabels();

document.addEventListener('click', e => {
  if (e.target.classList.contains('sub-tab')) switchSub(e.target.dataset.sub);
});

$('modal-close').addEventListener('click', closeModal);
$('modal-cancel').addEventListener('click', closeModal);
$('modal-overlay').addEventListener('click', e => { if (e.target === $('modal-overlay')) closeModal(); });
$('modal-save').onclick = saveForm;

function closeModal() {
  $('modal-overlay').classList.add('hidden');
  $('modal-body').innerHTML = '';
  $('modal').classList.remove('report-modal');
  closeReadonlyMode();
  $('modal-save').onclick = saveForm;
}
function openModal(title) { $('modal-title').textContent = title; $('modal-overlay').classList.remove('hidden'); }

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
  if (tab === 'dashboard') return loadDashboard();
  if (tab === 'reports') return loadReports();
  if (tab === 'find') return loadFind();
  if (tab === 'followups') return loadFollowups();
  if (tab === 'audit') return loadAudit();
  if (tab === 'rent') return loadTable(currentSub);
  if (tab === 'sale') { currentSub = currentSub in SUB_TABLES.sale ? currentSub : 'sale_requirements'; return loadTable(currentSub); }
  if (tab === 'financial') { currentSub = currentSub in SUB_TABLES.financial ? currentSub : 'income_transactions'; return loadTable(currentSub); }
  if (tab === 'employees') { currentSub = currentSub in SUB_TABLES.employees ? currentSub : 'employees'; return loadTable(currentSub); }
  if (tab === 'clients') return loadTable('clients');
  if (tab === 'properties') return loadTable('properties');
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
  const name = findField(fields, ['client_name','owner_name','full_name','title']) || row.label || '';
  const property = requirement
    ? findField(fields, ['property_requires','property_type'])
    : findField(fields, ['property_availability','property_type']);
  const amount = findField(fields, ['budget','monthly_rent','demand','asking_price','sale_price']);
  return {
    table,
    type: row.source || SEARCH_TABLE_LABELS[table] || table.replace(/_/g, ' '),
    id: row.id,
    date: findField(fields, ['date','date_created','date_posted','created_at']),
    name,
    contact: findField(fields, ['contact','contact_phone','phone','owner_contact']) || row.detail || '',
    property,
    amount,
    floor: findField(fields, ['floor','floor_no']),
    location: findField(fields, ['location']),
    facilities: findField(fields, ['facilities']),
    remarks: findField(fields, ['remarks','description','notes'])
  };
}

function renderFindRows(rows) {
  const table = $('find-table');
  if (!table) return;
  table.querySelector('thead').innerHTML = `<tr>${[
    'Type','Sr No.','Date','Name','Contact No.','Property','Budget/Rent/Demand','Floor','Location','Facilities','Remarks','Actions'
  ].map(h => `<th>${h}</th>`).join('')}</tr>`;
  const body = table.querySelector('tbody');
  if (!rows.length) {
    body.innerHTML = `<tr><td colspan="12" class="empty-cell">No find results yet.</td></tr>`;
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
    const data = await api(`/api/records/search/global?q=${encodeURIComponent(query)}&limit=100`);
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
    $('dashboard-cards').innerHTML = Array.from({ length: 8 }).map(() => `
      <div class="glass-card stat-card">
        <span class="skeleton-row"></span>
        <span class="skeleton-row" style="width:52%"></span>
      </div>
    `).join('');
    const data = await api('/api/reports/dashboard');
    setCompanyName(data.company);
    const cards = [
      { label: 'Rent Requirements', value: data.rent_requirements, note: 'Client demand' },
      { label: 'Rent Availability', value: data.rent_available, note: 'Listed rentals' },
      { label: 'Sale Requirements', value: data.sale_requirements, note: 'Buyer demand' },
      { label: 'Sale Availability', value: data.sale_available, note: 'Listed sales' },
      { label: 'Properties', value: data.properties, note: 'Portfolio records' },
      { label: 'Clients', value: data.clients, note: 'Saved contacts' },
      { label: 'Employees', value: data.employees, note: 'Active staff data' },
      { label: 'Pending Approvals', value: data.pending_approvals, note: 'Needs admin review' }
    ];
    $('dashboard-cards').innerHTML = cards.map(c => `
      <div class="glass-card stat-card">
        <div class="stat-value">${c.value}</div>
        <div class="stat-label">${c.label}</div>
        <div class="stat-note">${c.note}</div>
      </div>
    `).join('');
    setSyncStatus(`Dashboard updated ${formatClock()}`);
  } catch (err) {
    console.error(err);
    setSyncStatus(err.message || 'Dashboard failed', 'error');
  }
}

function statusBadge(status) {
  const colors = {Pending:'var(--warning)',Approved:'var(--success)',Resend:'var(--danger)',Rejected:'var(--danger)'};
  const c = colors[status] || 'var(--text-muted)';
  return `<span style="display:inline-block;padding:2px 10px;border-radius:10px;font-size:0.75rem;background:${c}22;color:${c};border:1px solid ${c}44">${status||'Draft'}</span>`;
}

function rowActionButton(label, action, table, id, className = '', style = '') {
  return `<button class="btn btn-sm row-action ${className}" type="button" data-row-action="${action}" data-table="${table}" data-id="${Number(id) || 0}"${style ? ` style="${style}"` : ''}>${escapeHtml(label)}</button>`;
}

function stateForTable(table) {
  if (!tableState[table]) {
    tableState[table] = {
      offset: 0,
      limit: TABLE_PAGE_SIZE,
      q: '',
      stage: '',
      status: '',
      date_from: '',
      date_to: '',
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
  titleRow.innerHTML = `<div class="table-section-title">${escapeHtml(tableTitle(table))}</div><div class="primary-tools"></div>`;
  const primary = titleRow.querySelector('.primary-tools');
  const markAction = table === 'rent_availability'
    ? '<button class="btn btn-primary" type="button" data-table-action="rented">Mark Rented</button>'
    : table === 'sale_availability'
      ? '<button class="btn btn-primary" type="button" data-table-action="sold">Mark Sold</button>'
      : '';
  const addLabel = table.includes('requirements') ? 'Add' : 'Add';
  primary.innerHTML = `
    <button class="btn btn-primary add-btn" type="button" data-table="${table}">${addLabel}</button>
    <button class="btn" type="button" data-table-action="edit">Edit</button>
    <button class="btn btn-danger" type="button" data-table-action="delete">Delete</button>
    ${markAction}
    <button class="btn" type="button" data-table-action="ai">AI Match</button>
    <button class="btn" type="button" data-table-action="report">Report</button>
  `;
  let actions = bar.querySelector('.selection-tools');
  if (!actions) {
    actions = document.createElement('div');
    actions.className = 'selection-tools';
    titleRow.after(actions);
  }
  actions.innerHTML = `
    <span class="selected-count">0 selected</span>
    <button class="btn" type="button" data-table-action="select-all">Select All</button>
    <button class="btn" type="button" data-table-action="clear">Clear Selection</button>
    <button class="btn" type="button" data-table-action="details">Details</button>
    <button class="btn" type="button" data-table-action="copy">Copy Selected</button>
    <button class="btn" type="button" data-table-action="refresh">Refresh</button>
    <button class="btn" type="button" data-table-action="export">Export</button>
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
        ${['Lead','Contacted','Visit Scheduled','Negotiation','Closed','Deal Done'].map(stage => `<option value="${stage}">${stage}</option>`).join('')}
      </select>`
    : '';
  const statusSelect = tableHasField(table, 'status')
    ? `<select class="toolbar-input table-status" title="Status">
        <option value="">All status</option>
        ${['Active','Available','Reserved','Rented','Sold','Inactive'].map(status => `<option value="${status}">${status}</option>`).join('')}
      </select>`
    : '';
  tools.innerHTML = `
    <input class="toolbar-input table-query" type="search" placeholder="Search this table" value="${escapeHtml(state.q)}">
    ${stageSelect}
    ${statusSelect}
    <input class="toolbar-input mini-date table-from" type="date" value="${escapeHtml(state.date_from)}" title="From date">
    <input class="toolbar-input mini-date table-to" type="date" value="${escapeHtml(state.date_to)}" title="To date">
    <button class="btn btn-sm pager-prev" type="button">Prev</button>
    <span class="pager-count">Page</span>
    <button class="btn btn-sm pager-next" type="button">Next</button>
  `;
  const setAndReload = (key, value, immediate = false) => {
    state[key] = value;
    state.offset = 0;
    if (immediate) loadTable(table); else scheduleTableReload(table);
  };
  const queryInput = tools.querySelector('.table-query');
  queryInput?.addEventListener('input', e => setAndReload('q', e.target.value));
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
  primary.querySelector('[data-table-action="rented"]')?.addEventListener('click', () => markSelectedAvailability(table, 'Rented'));
  primary.querySelector('[data-table-action="sold"]')?.addEventListener('click', () => markSelectedAvailability(table, 'Sold'));
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
  const hasActiveFilter = ['q','stage','status','date_from','date_to'].some(key => state[key]);
  tools.classList.toggle('hidden', total <= count && !hasActiveFilter);
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
  ['q','stage','status','date_from','date_to'].forEach(key => {
    if (state[key]) params.set(key, state[key]);
  });
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
  const oneOnly = ['edit', 'details'];
  const needsAny = ['delete', 'copy'];
  const isPipeline = PIPELINE_TABLES.includes(table);
  bar?.querySelectorAll('[data-table-action]').forEach(btn => {
    const action = btn.dataset.tableAction;
    if (oneOnly.includes(action)) btn.disabled = count !== 1;
    if (needsAny.includes(action)) btn.disabled = count === 0;
    if (action === 'ai') btn.disabled = count !== 1 || !isPipeline;
    if (action === 'rented' || action === 'sold') btn.disabled = count !== 1;
  });
  document.querySelectorAll(`input.row-select[data-table="${table}"]`).forEach(input => {
    input.checked = state.selected.has(Number(input.dataset.id));
  });
  const pageSelect = document.querySelector(`input.page-select[data-table="${table}"]`);
  if (pageSelect) {
    pageSelect.checked = state.rows.length > 0 && state.rows.every(row => state.selected.has(Number(row.id)));
  }
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

async function deleteSelectedRows(table) {
  if (!isAdmin()) {
    alert('Only Admin and Super Admin users can delete records.');
    return;
  }
  const ids = selectedIds(table);
  if (!ids.length) {
    alert('Select at least one record first.');
    return;
  }
  if (!confirm(`Delete ${ids.length} selected record${ids.length === 1 ? '' : 's'}?`)) return;
  try {
    for (const id of ids) {
      await api(`/api/records/${table}/${id}`, { method: 'DELETE' });
    }
    clearSelectedRows(table);
    await loadTable(table);
    setSyncStatus(`Deleted ${ids.length} record${ids.length === 1 ? '' : 's'}`);
  } catch (err) {
    alert(err.message);
  }
}

function matchSelectedRow(table) {
  const id = requireSingleSelected(table);
  if (!id) return;
  if (!PIPELINE_TABLES.includes(table)) {
    alert('AI Match is available for rent and sale deal records.');
    return;
  }
  findMatch(table, id);
}

function markSelectedAvailability(table, status) {
  const id = requireSingleSelected(table);
  if (!id) return;
  markAvailability(table, id, status);
}

function showReadonlyModal(title, html) {
  $('modal-body').innerHTML = html;
  $('modal-save').classList.add('hidden');
  openModal(title);
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
    downloadText(`${table}_${new Date().toISOString().slice(0,10)}.csv`, csv, 'text/csv');
    setSyncStatus(`Exported ${rows.length} row${rows.length === 1 ? '' : 's'}`);
  } catch (err) {
    alert(err.message);
  }
}

function tableTitle(table) {
  return {
    rent_requirements: 'Rent Requirements',
    rent_availability: 'Rent Availability',
    sale_requirements: 'Sale Requirements',
    sale_availability: 'Sale Availability',
    clients: 'Clients',
    properties: 'Properties',
    employees: 'Employees',
    income_transactions: 'Income Transactions',
    expense_transactions: 'Expense Transactions',
    attendance: 'Attendance',
    salary_payments: 'Salary Payments',
  }[table] || table.replace(/_/g, ' ').replace(/\b\w/g, ch => ch.toUpperCase());
}

function fieldLabel(table, key) {
  if (key === 'id') return 'Sr No.';
  return (FIELDS[table] || []).find(field => field.key === key)?.label || key.replace(/_/g, ' ');
}

function tableDisplayFields(table) {
  const preferred = {
    rent_requirements: [
      ['id', 'ID'], ['date', 'Date'], ['client_name', 'Name'], ['client_status', 'Owner/Broker'],
      ['contact', 'Contact No.'], ['property_requires', 'Property Requirement'], ['size', 'Size'], ['budget', 'Budget'],
    ],
    rent_availability: [
      ['id', 'ID'], ['date', 'Date'], ['owner_name', 'Name'], ['client_broker', 'Owner/Broker'],
      ['contact', 'Contact'], ['property_availability', 'Property Availability'], ['size', 'Size'], ['monthly_rent', 'Rent'],
    ],
    sale_requirements: [
      ['id', 'ID'], ['date', 'Date'], ['client_name', 'Name'], ['client_status', 'Owner/Broker'],
      ['contact', 'Contact No.'], ['property_requires', 'Property Requirement'], ['size', 'Size'], ['budget', 'Budget'],
    ],
    sale_availability: [
      ['id', 'ID'], ['date', 'Date'], ['owner_name', 'Name'], ['client_broker', 'Owner/Broker'],
      ['contact', 'Contact'], ['property_availability', 'Property Availability'], ['size', 'Size'], ['demand', 'Demand'],
    ],
  }[table];
  if (preferred) return preferred.map(([key, label]) => ({ key, label }));
  return [{ key: 'id', label: 'ID' }, ...(FIELDS[table] || []).slice(0, 9)];
}

function reportFieldsForTable(table) {
  const preferred = {
    rent_requirements: ['id','date','client_name','contact','property_requires','size','budget','location','workflow_stage','remarks'],
    rent_availability: ['id','date','owner_name','contact','property_availability','size','monthly_rent','location','status','remarks'],
    sale_requirements: ['id','date','client_name','contact','property_requires','size','budget','location','workflow_stage','remarks'],
    sale_availability: ['id','date','owner_name','contact','property_availability','size','demand','location','status','remarks'],
    clients: ['id','client_name','phone','email','client_type','status','notes'],
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

function openPrintableReport({ title, subtitle = '', company = 'Real Estate CRM', sections, summaryHtml = '', meta = [] }, targetWindow = null) {
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
          <div class="brand">${escapeHtml(company)}</div>
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
    `);
    $('modal').classList.add('report-modal');
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
    sale_requirements: summary?.sale?.requirements || 0,
    sale_availability: summary?.sale?.available_properties || 0,
  };
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
      const table = section.toLowerCase().includes('availability')
        ? (section.toLowerCase().startsWith('rent') ? 'rent_availability' : 'sale_availability')
        : (section.toLowerCase().startsWith('rent') ? 'rent_requirements' : 'sale_requirements');
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
  const container = document.querySelector(`#tab-${currentTab} .table-container`);
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
      const vals = fields.map(f => {
        if (f.key === 'approval_status') return `<td>${statusBadge(r[f.key])}</td>`;
        let v = r[f.key] !== undefined && r[f.key] !== null ? r[f.key] : '';
        return `<td>${escapeHtml(formatCell(v, f.key))}</td>`;
      }).join('');

      const checked = state.selected.has(Number(r.id)) ? ' checked' : '';
      return `<tr>
        <td class="select-col"><input class="row-select" type="checkbox" data-table="${table}" data-id="${Number(r.id) || 0}"${checked}></td>
        ${vals}
      </tr>`;
    }).join('');
    updateTablePager(table, data.total ?? rows.length, rows.length);
    updateSelectionToolbar(table);
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
  if (!confirm(`Mark this property as ${status}?`)) return;
  try {
    await api(`/api/records/${table}/${id}/workflow`, {
      method: 'PUT',
      body: JSON.stringify({ stage: 'Deal Done', priority: 'Medium', deal_probability: 100 })
    });
    await loadTable(table);
    setSyncStatus(`${status} saved`);
  } catch (err) { alert(err.message); }
}

async function findMatch(table, id) {
  try {
    const data = await api('/api/records/ai-match', { method: 'POST', body: JSON.stringify({ record_id: id, table }) });
    const matches = data.matches || [];
    const matchTable = table.replace('requirements','availability');
    const label = matchTable === 'rent_availability' ? 'Available Rentals' : 'Available Properties';
    if (matches.length === 0) {
      alert('No matches found for this requirement.');
      return;
    }
    let html = `<h4 style="margin-bottom:12px">${matches.length} ${label} Found</h4><div style="max-height:300px;overflow-y:auto">`;
    html += matches.map(m => `
      <div class="glass-card" style="padding:12px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center">
        <div>
          <strong>${escapeHtml(m.name)}</strong>
          <br><span style="font-size:0.8rem;color:var(--text-muted)">${escapeHtml(m.location)} - ${formatMoney(m.price)} - ${Number(m.score || 0).toFixed(0)}%</span>
          <br><span style="font-size:0.76rem;color:var(--text-muted)">${escapeHtml((m.reasons || []).join(', '))}</span>
        </div>
        <a href="#" onclick="showEditForm('${matchTable}',${m.id});closeModal();return false" style="color:var(--primary);font-size:0.85rem">View</a>
      </div>
    `).join('');
    html += '</div>';
    $('modal-body').innerHTML = html;
    openModal(`AI Matches for #${id}`);
  } catch (err) { alert(err.message); }
}

async function confirmDuplicateSave(table, data, id) {
  const phoneKey = { clients: 'phone', properties: 'owner_contact', employees: 'phone' }[table] || 'contact';
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
    <div class="field"><label>Transaction Date</label><input id="deal-date" type="date" value="${new Date().toISOString().slice(0,10)}"></div>
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

function showAddForm(table) {
  const fields = FIELDS[table] || [];
  const html = `<div class="form-grid">${fields.map(f => {
    if (f.key === 'approval_status' || f.key === 'approval_comment' || f.key === 'created_by' || f.key === 'created_at') return '';
    const isText = ['remarks','description','address','notes','facilities','nearby_landmarks','area_notes','photo_paths'].includes(f.key);
    const tag = isText ? 'textarea' : (f.type === 'select' || f.key === 'status' || f.key === 'payment_method' || f.key === 'client_type' || f.key === 'bachelor_family' ? 'select' : 'input');
    let extra = '';
    if (tag === 'input') extra = `type="${f.type || 'text'}" step="${f.type === 'number' ? '0.01' : ''}"`;
    let options = '';
    if (f.options) options = f.options.map(o => `<option>${escapeHtml(o)}</option>`).join('');
    if (f.key === 'status' && !f.options) options = '<option>Active</option><option>Inactive</option><option>Available</option><option>Rented</option><option>Sold</option>';
    if (f.key === 'payment_method') options = '<option>Cash</option><option>Bank Transfer</option><option>Cheque</option>';
    if (f.key === 'client_type') options = '<option>Tenant</option><option>Buyer</option><option>Owner</option><option>Seller</option>';
    if (f.key === 'bachelor_family') options = '<option>Bachelor</option><option>Family</option><option>Both</option>';
    return `<div class="field${isText ? ' field-full' : ''}">
      <label>${f.label}</label>
      ${tag === 'select' ? `<select id="f-${f.key}">${options}</select>` :
        `<${tag} id="f-${f.key}" ${extra} placeholder="${f.label}"></${tag}>`}
    </div>`;
  }).filter(Boolean).join('')}</div>`;
  $('modal-body').innerHTML = html;
  openModal(`Add ${table.replace('_',' ')}`);
  $('modal-save').dataset.table = table;
  $('modal-save').dataset.id = '';
}

async function showEditForm(table, id) {
  try {
    const data = await api(`/api/records/${table}/${id}`);
    const r = data.record;
    const fields = FIELDS[table] || [];
    const html = `<div class="form-grid">${fields.map(f => {
      if (f.key === 'created_by' || f.key === 'created_at') return '';
      const val = r[f.key] !== undefined && r[f.key] !== null ? r[f.key] : '';
      const isText = ['remarks','description','address','notes','facilities','nearby_landmarks','area_notes','photo_paths','approval_comment'].includes(f.key);
      const tag = isText ? 'textarea' : (f.type === 'select' || f.key === 'approval_status' || f.key === 'status' || f.key === 'payment_method' || f.key === 'client_type' || f.key === 'bachelor_family' ? 'select' : 'input');
      let extra = '';
      if (tag === 'input') extra = `type="${f.type || 'text'}" step="${f.type === 'number' ? '0.01' : ''}"`;
      let options = '';
      if (f.options) options = f.options.map(o => `<option>${escapeHtml(o)}</option>`).join('');
      if (f.key === 'approval_status') options = '<option>Pending</option><option>Approved</option><option>Resend</option>';
      if (f.key === 'status' && !f.options) options = '<option>Active</option><option>Inactive</option><option>Available</option><option>Rented</option><option>Sold</option>';
      if (f.key === 'payment_method') options = '<option>Cash</option><option>Bank Transfer</option><option>Cheque</option>';
      if (f.key === 'client_type') options = '<option>Tenant</option><option>Buyer</option><option>Owner</option><option>Seller</option>';
      if (f.key === 'bachelor_family') options = '<option>Bachelor</option><option>Family</option><option>Both</option>';
      const escVal = String(val).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
      return `<div class="field${isText ? ' field-full' : ''}">
        <label>${f.label}</label>
        ${tag === 'select' ? `<select id="f-${f.key}">${options}</select>` :
          tag === 'input' ? `<input id="f-${f.key}" ${extra} placeholder="${f.label}" value="${escVal}">` :
          `<textarea id="f-${f.key}" ${extra} placeholder="${f.label}">${escVal}</textarea>`}
      </div>`;
    }).filter(Boolean).join('')}</div>`;
    $('modal-body').innerHTML = html;
    // Set values for select elements
    fields.forEach(f => {
      const el = $(`f-${f.key}`);
      if (el && el.tagName === 'SELECT') {
        const opts = el.options;
        for (let i = 0; i < opts.length; i++) {
          if (opts[i].value === String(r[f.key])) { opts[i].selected = true; break; }
        }
      }
    });
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
  fields.forEach(f => {
    const el = $(`f-${f.key}`);
    if (el) {
      let val = el.value;
      if (f.type === 'number') val = parseFloat(val) || 0;
      data[f.key] = val;
    }
  });
  try {
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
  if (!confirm('Delete this record?')) return;
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

async function loadReports() {
  try {
    setSyncStatus('Loading reports...', 'busy');
    $('reports-content').innerHTML = '<div class="report-grid">' + Array.from({ length: 4 }).map(() => '<div class="glass-card report-item"><span class="skeleton-row"></span><span class="skeleton-row" style="width:55%;margin-top:10px"></span></div>').join('') + '</div>';
    const fin = await api('/api/reports/financial');
    const prop = await api('/api/reports/properties');
    const emp = await api('/api/reports/employees');
    $('reports-content').innerHTML = `
      <div class="glass-card report-command">
        <div class="field">
          <label>From</label>
          <input id="report-start" type="date">
        </div>
        <div class="field">
          <label>To</label>
          <input id="report-end" type="date">
        </div>
        <button class="btn btn-primary" type="button" data-report-kind="rent">Print Rent Report</button>
        <button class="btn btn-primary" type="button" data-report-kind="sale">Print Sale Report</button>
        <button class="btn" type="button" data-report-kind="all">Print Full Report</button>
      </div>
      <div class="report-section">
        <h3>Financial Summary</h3>
        <div class="report-grid">
          <div class="glass-card report-item"><div class="value" style="color:var(--success)">${formatMoney(fin.total_income)}</div><div class="label">Total Income</div></div>
          <div class="glass-card report-item"><div class="value" style="color:var(--danger)">${formatMoney(fin.total_expense)}</div><div class="label">Total Expense</div></div>
          <div class="glass-card report-item"><div class="value">${formatMoney(fin.net_profit)}</div><div class="label">Net Profit</div></div>
          <div class="glass-card report-item"><div class="value">${fin.profit_margin}%</div><div class="label">Profit Margin</div></div>
        </div>
      </div>
      <div class="report-section">
        <h3>Income by Type</h3>
        <div class="report-grid">${Object.entries(fin.income_by_type||{}).map(([k,v]) =>
          `<div class="glass-card report-item"><div class="value">${formatMoney(v)}</div><div class="label">${k}</div></div>`
        ).join('')}</div>
      </div>
      <div class="report-section">
        <h3>Expenses by Category</h3>
        <div class="report-grid">${Object.entries(fin.expense_by_category||{}).map(([k,v]) =>
          `<div class="glass-card report-item"><div class="value" style="color:var(--danger)">${formatMoney(v)}</div><div class="label">${k}</div></div>`
        ).join('')}</div>
      </div>
      <div class="report-section">
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
      <div class="report-section">
        <h3>Employees (${emp.total})</h3>
        <div class="report-grid">
          <div class="glass-card report-item"><div class="value">${emp.total}</div><div class="label">Total Employees</div></div>
          <div class="glass-card report-item"><div class="value">${formatMoney(emp.total_payroll)}</div><div class="label">Monthly Payroll</div></div>
        </div>
      </div>
    `;
    document.querySelectorAll('[data-report-kind]').forEach(button => {
      button.addEventListener('click', () => printDealingsReport(button.dataset.reportKind || 'all'));
    });
    setSyncStatus(`Reports updated ${formatClock()}`);
  } catch (err) {
    console.error(err);
    setSyncStatus(err.message || 'Reports failed', 'error');
  }
}

function openSettings() {
  if (!isAdmin()) {
    alert('Only Admin and Super Admin users can manage users.');
    return;
  }
  const html = `
    <div style="margin-bottom:16px"><button class="btn btn-primary" onclick="showUserForm()">+ Add User</button></div>
    <div id="users-list"></div>
  `;
  $('modal-body').innerHTML = html;
  openModal('Settings - User Management');
  loadUsers();
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
