# CRM Improvements Implementation Tasks

## Task 1: Consolidate Shared Constants
- [ ] 1.1 Audit existing constants across all files
  - Find all DEAL_STAGES definitions
  - Find all PHASE1_TABLES definitions
  - Find all PRIORITY/SCORE constants
  - Document locations in analysis file

- [ ] 1.2 Update crm_core/constants.py with unified constants
  - Add DEAL_STAGES list
  - Add DEAL_PRIORITIES list
  - Add STAGE_PROBABILITY dict
  - Add PHASE1_TABLES tuple
  - Add PIPELINE_TABLES constant
  - Add PRIORITY_SCORE dict
  - Add all other shared constants

- [ ] 1.3 Update imports in crm_core/intelligence.py
  - Import DEAL_STAGES from constants
  - Import PRIORITY_SCORE from constants
  - Import STAGE_PROBABILITY from constants
  - Remove duplicate constant definitions

- [ ] 1.4 Update imports in backend/routers/records_router.py
  - Import DEAL_STAGES from constants
  - Import DEAL_PRIORITIES from constants
  - Import STAGE_PROBABILITY from constants
  - Import PHASE1_TABLES from constants
  - Remove duplicate constant definitions

- [ ] 1.5 Update imports in qt_crm_app.py
  - Import DEAL_STAGES from constants
  - Import DEAL_PRIORITIES from constants
  - Import STAGE_PROBABILITY from constants
  - Import PHASE1_TABLES from constants
  - Remove duplicate constant definitions

## Task 2: Optimize Matching Algorithm
- [ ] 2.1 Add prefilter_candidates function to crm_core/matching.py
  - Filter by price range (target ±30%)
  - Filter by location keywords overlap
  - Return filtered candidate list

- [ ] 2.2 Update best_matches function in crm_core/matching.py
  - Call prefilter_candidates before scoring
  - Maintain existing scoring logic
  - Ensure output format unchanged

- [ ] 2.3 Optimize _matching_section in crm_core/intelligence.py
  - Apply pre-filtering to candidate pairs
  - Maintain top 12 results limit
  - Verify performance improvement

## Task 3: Add Loading States to Web UI
- [ ] 3.1 Add skeleton screen CSS to frontend/styles.css
  - Create .skeleton class with shimmer animation
  - Create .table-skeleton for table rows
  - Add transition animations

- [ ] 3.2 Add spinner/overlay CSS to frontend/styles.css
  - Create .loading-overlay class
  - Add spinner animation keyframes
  - Style for center positioning

- [ ] 3.3 Add loading state management to frontend/app.js
  - Create showLoading() function
  - Create hideLoading() function
  - Add loading state to table render functions

- [ ] 3.4 Integrate loading states in table operations
  - Show skeleton on initial table load
  - Show spinner on search operations
  - Hide loading when data ready

## Task 4: Improve Mobile Responsiveness
- [ ] 4.1 Add mobile breakpoint CSS to frontend/styles.css
  - Add @media (max-width: 768px) breakpoint
  - Style collapsed sidebar
  - Adjust main content padding

- [ ] 4.2 Add mobile menu toggle to frontend/index.html
  - Add hamburger menu button
  - Add mobile header structure
  - Ensure semantic HTML

- [ ] 4.3 Add mobile menu handlers to frontend/app.js
  - Toggle sidebar visibility on mobile
  - Close menu on outside click
  - Handle window resize events

- [ ] 4.4 Adjust table layouts for mobile
  - Enable horizontal scroll on tables
  - Reduce padding on small screens
  - Stack action buttons vertically

## Task 5: Add Keyboard Shortcuts
- [ ] 5.1 Add keyboard event handler to frontend/app.js
  - Create handleKeyboardShortcuts function
  - Check for Ctrl/Cmd modifier keys
  - Prevent default on handled shortcuts

- [ ] 5.2 Implement Ctrl+K for global search
  - Focus find query input
  - Open find tab if not active

- [ ] 5.3 Implement Ctrl+N for new record
  - Trigger add button click on current table
  - Works from any tab

- [ ] 5.4 Implement Escape to close modal
  - Close modal overlay on Escape key
  - Return focus to trigger element

- [ ] 5.5 Add visual shortcut hints
  - Add title attributes with shortcuts
  - Optional: Show shortcut overlay on ? key

## Task 6: Make Qt Area Lists Configurable
- [ ] 6.1 Update settings handling in qt_crm_app.py
  - Load areas from settings with fallback
  - Load facilities from settings with fallback
  - Load property types from settings with fallback

- [ ] 6.2 Update SettingsModule in qt_crm_app.py
  - Add UI for editing area list
  - Add UI for editing facilities list
  - Save to app_settings table

- [ ] 6.3 Update all area/facility dropdowns
  - Use dynamic lists from settings
  - Maintain defaults when settings empty
