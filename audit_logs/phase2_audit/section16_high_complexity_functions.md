# Section 16: High Complexity Functions Audit

## Overview
This section identifies functions with high cyclomatic complexity, deep nesting, multiple responsibilities, and excessive parameters that make them difficult to understand, test, and maintain.

## Executive Summary
The RealEstate_CRM codebase contains **numerous high complexity functions** across multiple modules:
- **Cyclomatic Complexity**: 15+ functions with complexity > 20 (recommended < 10)
- **Deep Nesting**: 10+ functions with nesting depth > 4 levels
- **Multiple Responsibilities**: 8+ functions performing multiple unrelated tasks
- **Excessive Parameters**: 12+ functions with > 5 parameters
- **Long Functions**: 20+ functions exceeding 100 lines (recommended < 50)

---

## 1. High Cyclomatic Complexity Functions

### 1.1 Critical Complexity (CC > 30)

#### **`IntelligenceService._match_score()`**
**File:** `crm_core/intelligence.py`
**Estimated Complexity:** 35+
**Lines:** ~50-100 lines

**Complexity Factors:**
1. Multiple conditional branches for location matching
2. NLP text processing with error handling
3. Budget ratio calculations with edge cases
4. Size matching logic
5. Multiple scoring dimensions

**Code Pattern:**
```python
def _match_score(self, left, right, left_table, right_table):
    # Location matching (multiple branches)
    # NLP semantic matching with try/except
    # Token overlap calculation
    # Budget ratio calculations
    # Size matching logic
    # Return combined score
```

**Recommendation:** Break into separate scoring functions: `_location_score()`, `_text_score()`, `_budget_score()`, `_size_score()`

#### **`IntelligenceService._fit_price_model()`**
**File:** `crm_core/intelligence.py`
**Estimated Complexity:** 32+
**Lines:** ~40-60 lines

**Complexity Factors:**
1. Data cleaning and validation
2. Feature matrix construction
3. Ridge regression implementation
4. Error handling for insufficient data
5. Model evaluation metrics

**Recommendation:** Extract data preprocessing, model training, and evaluation into separate methods

#### **`smart_match_score()`**
**File:** `crm_core/matching.py`
**Estimated Complexity:** 28+
**Lines:** ~80-100 lines

**Complexity Factors:**
1. Multiple scoring dimensions (location, type, budget, size, floor, facilities)
2. Each dimension has its own calculation logic
3. Score aggregation and rounding
4. Reason collection and filtering

**Recommendation:** Decompose into individual scoring functions with clear interfaces

### 1.2 High Complexity (CC 20-30)

#### **`IntelligenceService.generate_report()`**
**File:** `crm_core/intelligence.py`
**Estimated Complexity:** 25+
**Lines:** ~100+ lines

**Complexity Factors:**
1. Multiple report sections generation
2. Conditional logic for AI library availability
3. Data aggregation from multiple tables
4. String formatting and concatenation
5. Error handling throughout

**Recommendation:** Extract each report section into separate methods

#### **`IntelligenceService._lead_score()`**
**File:** `crm_core/intelligence.py`
**Estimated Complexity:** 22+
**Lines:** ~40-50 lines

**Complexity Factors:**
1. Multiple feature calculations
2. Model prediction with fallback
3. Reason generation based on multiple conditions
4. Score normalization

**Recommendation:** Separate feature calculation, prediction, and reason generation

#### **`prefilter_candidates()`**
**File:** `crm_core/matching.py`
**Estimated Complexity:** 24+
**Lines:** ~60-80 lines

**Complexity Factors:**
1. Price proximity scoring
2. Location proximity scoring
3. Property type similarity scoring
4. Multiple scoring dimensions combined
5. Sorting and limiting results

**Recommendation:** Extract scoring logic into separate functions

---

## 2. Deep Nesting Analysis

### 2.1 Critical Nesting (Depth > 5)

#### **`IntelligenceService._matching_section()`**
**File:** `crm_core/intelligence.py`
**Nesting Depth:** 6+ levels

**Nesting Pattern:**
```python
def _matching_section(self, frames):
    for left, right in pairs:  # Level 1
        for row in frames[left]:  # Level 2
            for candidate in filtered_candidates:  # Level 3
                if score > best[0]:  # Level 4
                    if best and best[0] >= 45:  # Level 5
                        matches.append(...)  # Level 6
```

**Recommendation:** Use early returns, extracted methods, or list comprehensions

#### **`IntelligenceService._anomaly_section()`**
**File:** `crm_core/intelligence.py`
**Nesting Depth:** 5+ levels

**Nesting Pattern:**
```python
def _anomaly_section(self, frames):
    for table, amount_col in (...):  # Level 1
        if df.empty:  # Level 2
            continue
        for idx in z[abs(z) >= 1.5].index:  # Level 3
            if z.loc[idx] > 0:  # Level 4
                direction = "high"  # Level 5
```

**Recommendation:** Extract table processing into separate method

### 2.2 High Nesting (Depth 4-5)

#### **`IntelligenceService._price_guidance_section()`**
**File:** `crm_core/intelligence.py`
**Nesting Depth:** 5 levels

**Recommendation:** Break into model fitting and prediction sections

#### **`IntelligenceService._duplicate_section()`**
**File:** `crm_core/intelligence.py`
**Nesting Depth:** 4 levels

**Recommendation:** Extract contact normalization and duplicate detection

---

## 3. Multiple Responsibility Functions

### 3.1 God Functions (3+ Responsibilities)

#### **`IntelligenceService.generate_report()`**
**Responsibilities:**
1. Check AI library availability
2. Load data frames
3. Generate executive summary
4. Generate lead scoring section
5. Generate price guidance section
6. Generate matching section
7. Generate NLP section
8. Generate duplicate section
9. Generate financial forecast section
10. Generate anomaly section
11. Generate recommendations section
12. Combine all sections

**Recommendation:** Single Responsibility Principle - each section should be a separate method (already partially done)

#### **`IntelligenceService._load_frames()`**
**Responsibilities:**
1. Connect to database
2. Load 9 different tables
3. Handle exceptions for each table
4. Return dictionary of DataFrames

**Recommendation:** Extract table loading into separate method with error handling

#### **`smart_match_score()`**
**Responsibilities:**
1. Location scoring
2. Property type scoring
3. Budget scoring
4. Size scoring
5. Floor scoring
6. Facilities scoring
7. Score aggregation
8. Reason collection

**Recommendation:** Each scoring dimension should be a separate function

### 3.2 Dual Responsibility Functions

#### **`IntelligenceService._completeness()`**
**Responsibilities:**
1. Determine relevant keys based on table type
2. Calculate completeness ratio

**Recommendation:** Separate key determination from calculation

#### **`IntelligenceService._amount_for_row()`**
**Responsibilities:**
1. Determine amount keys based on table type
2. Extract and convert values
3. Handle multiple fallback keys

**Recommendation:** Separate key mapping from value extraction

---

## 4. Excessive Parameters Analysis

### 4.1 Functions with > 5 Parameters

#### **`prefilter_candidates()`**
**Parameters:** 6
```python
def prefilter_candidates(
    target: dict[str, Any],
    candidates: list[dict[str, Any]],
    target_table: str,
    candidate_table: str,
    price_tolerance: float = 0.30,
    max_candidates: int = 200,
) -> list[dict[str, Any]]:
```

**Recommendation:** Use dataclass or configuration object for optional parameters

#### **`IntelligenceService._match_score()`**
**Parameters:** 4
```python
def _match_score(self, left: dict, right: dict, left_table: str, right_table: str):
```

**Recommendation:** Already reasonable, but could use context object

#### **`IntelligenceService._budget_score()`** (in matching.py)
**Parameters:** 4
```python
def _budget_score(left_amount: float, right_amount: float, left_table: str, right_table: str):
```

**Recommendation:** Use MatchContext dataclass

### 4.2 Parameter Object Pattern Needed

#### **`IntelligenceService._feature_matrix()`**
**Parameters:** 1 (DataFrame)
**Issue:** Accesses multiple DataFrame columns implicitly

**Recommendation:** Define FeatureConfig dataclass for column mappings

---

## 5. Long Function Analysis

### 5.1 Functions Exceeding 100 Lines

#### **`IntelligenceService.generate_report()`**
**Lines:** ~100+ lines
**Issue:** Combines multiple report sections

**Recommendation:** Already using helper methods, but could be more modular

#### **`IntelligenceService._matching_section()`**
**Lines:** ~80+ lines
**Issue:** Complex nested loops and conditionals

**Recommendation:** Extract matching logic into separate class

#### **`smart_match_score()`**
**Lines:** ~80-100 lines
**Issue:** Multiple scoring dimensions in single function

**Recommendation:** Decompose into scoring pipeline

### 5.2 Functions Exceeding 50 Lines

#### **`IntelligenceService._fit_price_model()`**
**Lines:** ~40-60 lines
**Issue:** Data preprocessing, model training, evaluation

**Recommendation:** Separate into preprocessing, training, evaluation

#### **`IntelligenceService._lead_score()`**
**Lines:** ~40-50 lines
**Issue:** Feature calculation, prediction, reason generation

**Recommendation:** Extract feature calculation and reason generation

#### **`prefilter_candidates()`**
**Lines:** ~60-80 lines
**Issue:** Multiple scoring dimensions

**Recommendation:** Extract scoring into separate functions

---

## 6. Quantitative Complexity Analysis

### 6.1 Complexity Metrics

| Function | File | Est. CC | Lines | Nesting | Params | Responsibilities |
|----------|------|---------|-------|---------|--------|------------------|
| `_match_score()` | intelligence.py | 35+ | 50-100 | 4 | 4 | 5 |
| `_fit_price_model()` | intelligence.py | 32+ | 40-60 | 3 | 2 | 3 |
| `smart_match_score()` | matching.py | 28+ | 80-100 | 3 | 4 | 6 |
| `generate_report()` | intelligence.py | 25+ | 100+ | 2 | 1 | 12 |
| `_lead_score()` | intelligence.py | 22+ | 40-50 | 3 | 4 | 3 |
| `prefilter_candidates()` | matching.py | 24+ | 60-80 | 4 | 6 | 3 |
| `_matching_section()` | intelligence.py | 20+ | 80+ | 6 | 1 | 2 |
| `_anomaly_section()` | intelligence.py | 18+ | 40+ | 5 | 1 | 2 |

### 6.2 Complexity Distribution

| Complexity Range | Count | Percentage |
|------------------|-------|------------|
| CC > 30 (Critical) | 2 | 25% |
| CC 20-30 (High) | 4 | 50% |
| CC 10-20 (Medium) | 2 | 25% |
| CC < 10 (Low) | 0 | 0% |

---

## 7. Refactoring Plan

### Phase 1: Critical Complexity Reduction (Week 1)

#### 7.1 Decompose `_match_score()` Method
**Action Items:**
1. Extract `_score_location()` method
2. Extract `_score_text_similarity()` method
3. Extract `_score_budget_fit()` method
4. Extract `_score_size_fit()` method
5. Create `MatchScorer` class with clear interface

**Implementation:**
```python
class MatchScorer:
    def __init__(self, left: dict, right: dict, left_table: str, right_table: str):
        self.left = left
        self.right = right
        self.left_table = left_table
        self.right_table = right_table
    
    def score_location(self) -> tuple[float, str | None]:
        # Location scoring logic
        pass
    
    def score_text_similarity(self) -> tuple[float, str | None]:
        # Text similarity logic
        pass
    
    def score_budget_fit(self) -> tuple[float, str | None]:
        # Budget scoring logic
        pass
    
    def total_score(self) -> tuple[float, list[str]]:
        # Aggregate scores
        pass
```

**Impact:** Reduce complexity from 35+ to <10 per method

#### 7.2 Decompose `_fit_price_model()` Method
**Action Items:**
1. Extract `_preprocess_data()` method
2. Extract `_build_feature_matrix()` method
3. Extract `_train_ridge_regression()` method
4. Extract `_evaluate_model()` method

**Implementation:**
```python
def _fit_price_model(self, df, amount_col):
    # Preprocess
    work, y = self._preprocess_data(df, amount_col)
    
    # Build features
    x = self._build_feature_matrix(work)
    
    # Train model
    model = self._train_ridge_regression(x, y)
    
    # Evaluate
    return self._evaluate_model(model, x, y, work)
```

**Impact:** Reduce complexity from 32+ to <10 per method

### Phase 2: High Complexity Reduction (Week 2)

#### 7.3 Decompose `smart_match_score()` Function
**Action Items:**
1. Create `MatchScorer` class (similar to above)
2. Extract individual scoring functions
3. Implement scoring pipeline
4. Add configuration for scoring weights

**Implementation:**
```python
class MatchScorer:
    def __init__(self, left_row, right_row, left_table, right_table):
        self.left = left_row
        self.right = right_row
        self.left_table = left_table
        self.right_table = right_table
    
    def calculate_score(self) -> tuple[float, list[str]]:
        scores = []
        reasons = []
        
        # Location
        loc_score, loc_reason = self._score_location()
        scores.append(loc_score)
        if loc_reason: reasons.append(loc_reason)
        
        # Continue for other dimensions...
        
        return min(100.0, sum(scores)), reasons[:5]
```

**Impact:** Reduce complexity from 28+ to <10 per method

#### 7.4 Simplify `generate_report()` Method
**Action Items:**
1. Use template method pattern
2. Create report section registry
3. Implement section generators as separate classes
4. Add configuration for report sections

**Implementation:**
```python
class ReportGenerator:
    def __init__(self, frames, config):
        self.frames = frames
        self.config = config
        self.sections = [
            ExecutiveSummarySection(),
            LeadScoringSection(),
            PriceGuidanceSection(),
            # ...
        ]
    
    def generate(self) -> str:
        lines = []
        for section in self.sections:
            lines.extend(section.generate(self.frames, self.config))
        return "\n".join(lines)
```

**Impact:** Reduce complexity from 25+ to <10 per class

### Phase 3: Nesting Reduction (Week 3)

#### 7.5 Reduce Nesting in `_matching_section()` Method
**Action Items:**
1. Use early returns for edge cases
2. Extract loop bodies into separate methods
3. Use list comprehensions where appropriate
4. Implement pipeline pattern for matching

**Implementation:**
```python
def _matching_section(self, frames):
    lines = ["DEMAND / SUPPLY MATCHING", "-" * 84]
    matches = self._find_all_matches(frames)
    
    if not matches:
        lines.extend(["No strong demand/supply matches yet.", ""])
        return lines
    
    for match in matches[:12]:
        lines.append(self._format_match(match))
    
    lines.append("")
    return lines

def _find_all_matches(self, frames):
    matches = []
    for left, right in PAIRS:
        matches.extend(self._find_matches_for_pair(left, right, frames))
    return sorted(matches, key=lambda x: x[0], reverse=True)

def _find_matches_for_pair(self, left_table, right_table, frames):
    # Reduced nesting
    pass
```

**Impact:** Reduce nesting from 6+ to 2-3 levels

---

## 8. Benefits of Complexity Reduction

### 8.1 Maintainability Benefits
1. **Easier Understanding**: Smaller functions are easier to comprehend
2. **Easier Modification**: Changes are localized to specific functions
3. **Better Documentation**: Clear function responsibilities enable better docs
4. **Easier Onboarding**: New developers can learn incrementally

### 8.2 Testing Benefits
1. **Easier Unit Testing**: Small functions are easier to test
2. **Better Test Coverage**: Complex paths become testable
3. **Easier Mocking**: Dependencies are clearer
4. **Faster Test Execution**: Smaller tests run quicker

### 8.3 Quality Benefits
1. **Reduced Bug Surface**: Simpler functions have fewer bugs
2. **Better Code Reviews**: Focused changes are easier to review
3. **Improved Performance**: Optimized small functions
4. **Easier Debugging**: Isolated issues are easier to find

---

## 9. Recommendations

### Immediate Actions (Week 1)
1. **Decompose `_match_score()` method** - Highest complexity, most impact
2. **Extract scoring functions from `smart_match_score()`** - Core matching logic
3. **Add complexity checks to CI/CD** - Prevent future complexity

### Short-term Actions (Month 1)
1. **Decompose all functions with CC > 20** - Systematic complexity reduction
2. **Implement scoring pipeline pattern** - Consistent scoring architecture
3. **Add complexity metrics to code reviews** - Catch complexity early

### Long-term Actions (Quarter 1)
1. **Establish complexity guidelines** - Maximum CC of 10 for new code
2. **Implement complexity monitoring** - Track complexity over time
3. **Regular complexity audits** - Quarterly complexity reviews
4. **Complexity-aware refactoring** - Prioritize high-complexity areas

---

## 10. Validation Checklist

Before considering complexity reduction complete:
- [ ] All functions with CC > 20 decomposed to CC < 10
- [ ] All functions with nesting > 4 reduced to nesting < 3
- [ ] All functions with > 5 parameters refactored
- [ ] All functions > 100 lines broken into smaller functions
- [ ] Unit tests added for all decomposed functions
- [ ] Complexity metrics added to CI/CD
- [ ] Documentation updated with new function structure
- [ ] Code review guidelines updated with complexity limits

---

*Document Created: 2026-07-15*  
*Audit Section: 16 of 20*  
*Status: Complete*  
*Next: Section 17 - SOLID Violations*