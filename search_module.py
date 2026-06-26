"""
Real Estate CRM - Intelligent Search Module
Features: NLP, Fuzzy Matching, Multi-filter Search, Ranking
"""

import sqlite3
import numpy as np
import pandas as pd
from difflib import SequenceMatcher
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import NLP libraries
try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False
    logger.warning("TextBlob not installed. Basic NLP only.")

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning("spaCy not installed. Will use basic NLP.")

try:
    from fuzzywuzzy import fuzz
    from fuzzywuzzy import process
    FUZZYWUZZY_AVAILABLE = True
except ImportError:
    FUZZYWUZZY_AVAILABLE = False
    logger.warning("FuzzyWuzzy not installed. Basic string matching only.")


class TextProcessing:
    """NLP text processing and extraction"""
    
    @staticmethod
    def extract_keywords(text):
        """Extract key terms from property description"""
        if not text:
            return []
        
        text = text.lower()
        keywords = {
            'luxury': ['luxury', 'premium', 'high-end', 'upscale'],
            'modern': ['modern', 'new', 'recently built', 'renovated'],
            'spacious': ['spacious', 'large', 'big', 'huge'],
            'compact': ['compact', 'cozy', 'small', 'intimate'],
            'furnished': ['furnished', 'furnished', 'ready to move'],
            'unfurnished': ['unfurnished', 'bare', 'empty'],
            'balcony': ['balcony', 'terrace', 'patio'],
            'garden': ['garden', 'garden', 'yard'],
            'parking': ['parking', 'garage', 'carport'],
            'security': ['security', 'gated', 'secure', 'safe'],
            'pool': ['pool', 'swimming', 'aqua'],
            'gym': ['gym', 'fitness', 'exercise'],
            'view': ['view', 'scenic', 'vista', 'outlook'],
        }
        
        found_keywords = []
        for category, terms in keywords.items():
            for term in terms:
                if term in text:
                    found_keywords.append(category)
                    break
        return found_keywords
    
    @staticmethod
    def normalize_location(location):
        """Normalize location strings for better matching"""
        if not location:
            return ""
        return location.lower().strip()
    
    @staticmethod
    def extract_price_range(description):
        """Extract numerical values from text"""
        import re
        numbers = re.findall(r'\d+(?:,\d+)*(?:\.\d+)?', str(description))
        return [float(n.replace(',', '')) for n in numbers]


class PropertyMatcher:
    """Core matching engine with scoring"""
    
    def __init__(self, db_path="real_estate_crm.db"):
        self.db_path = db_path
        self.text_processor = TextProcessing()

    @staticmethod
    def _first(record, *keys, default=None):
        for key in keys:
            value = record.get(key)
            if value not in (None, ""):
                return value
        return default

    @staticmethod
    def _parse_beds(value):
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            import re
            match = re.search(r"\d+", str(value))
            return int(match.group(0)) if match else None

    def _normalize_requirement(self, requirement):
        req = dict(requirement)
        req['property_type'] = self._first(req, 'property_type', 'property_requires', default='')
        req['budget_max'] = self._first(req, 'budget_max', 'budget', default=0)
        req['budget_min'] = self._first(req, 'budget_min', default=0)
        req['size_beds'] = self._parse_beds(self._first(req, 'size_beds', 'size'))
        req['description'] = self._first(req, 'description', 'remarks', 'notes', default='')
        req['contact_phone'] = self._first(req, 'contact_phone', 'contact', default='')
        return req

    def _normalize_availability(self, availability):
        avail = dict(availability)
        avail['property_type'] = self._first(avail, 'property_type', 'property_availability', default='')
        avail['size_beds'] = self._parse_beds(self._first(avail, 'size_beds', 'size'))
        avail['description'] = self._first(avail, 'description', 'remarks', 'notes', default='')
        avail['contact_phone'] = self._first(avail, 'contact_phone', 'contact', default='')
        return avail
    
    def _get_exact_match_score(self, requirement, availability):
        """Calculate exact match score (0-100)"""
        score = 0
        weights = {
            'location': 30,
            'budget': 25,
            'property_type': 20,
            'size': 15,
            'facilities': 10
        }
        
        # Location match (highest priority)
        req_loc = self.text_processor.normalize_location(requirement.get('location', ''))
        avail_loc = self.text_processor.normalize_location(availability.get('location', ''))
        if req_loc and avail_loc:
            if req_loc == avail_loc:
                score += weights['location']
            elif req_loc in avail_loc or avail_loc in req_loc:
                score += weights['location'] * 0.7
        
        # Budget match
        if 'budget_max' in requirement and 'monthly_rent' in availability:
            req_budget_max = float(requirement.get('budget_max', float('inf')) or float('inf'))
            avail_rent = float(availability.get('monthly_rent', 0) or 0)
            if avail_rent <= req_budget_max:
                budget_diff = req_budget_max - avail_rent
                budget_ratio = 1 - min(budget_diff / req_budget_max, 1)
                score += weights['budget'] * max(budget_ratio, 0.5)
        
        # Property type match
        if requirement.get('property_type') and availability.get('property_type'):
            if requirement['property_type'].lower() == availability['property_type'].lower():
                score += weights['property_type']
        
        # Size match (beds, baths)
        if requirement.get('size_beds') and availability.get('size_beds'):
            if int(requirement['size_beds']) <= int(availability['size_beds']):
                score += weights['size'] * 0.8
        
        # Facilities keyword match
        req_keywords = set(self.text_processor.extract_keywords(
            f"{requirement.get('description', '')} {requirement.get('facilities', '')}"
        ))
        avail_keywords = set(self.text_processor.extract_keywords(
            f"{availability.get('description', '')} {availability.get('facilities', '')}"
        ))
        
        if req_keywords and avail_keywords:
            overlap = len(req_keywords & avail_keywords)
            match_ratio = overlap / len(req_keywords)
            score += weights['facilities'] * match_ratio
        
        return min(score, 100)
    
    def _get_fuzzy_match_score(self, requirement, availability):
        """Calculate fuzzy match score using string similarity"""
        if not FUZZYWUZZY_AVAILABLE:
            return self._simple_string_similarity(requirement, availability)
        
        scores = []
        
        # Location fuzzy match
        req_loc = str(requirement.get('location', ''))
        avail_loc = str(availability.get('location', ''))
        loc_score = fuzz.token_set_ratio(req_loc.lower(), avail_loc.lower())
        scores.append(loc_score * 0.3)
        
        # Description fuzzy match
        req_desc = str(requirement.get('description', ''))
        avail_desc = str(availability.get('description', ''))
        desc_score = fuzz.token_set_ratio(req_desc.lower(), avail_desc.lower())
        scores.append(desc_score * 0.2)
        
        # Facilities fuzzy match
        req_fac = str(requirement.get('facilities', ''))
        avail_fac = str(availability.get('facilities', ''))
        fac_score = fuzz.token_set_ratio(req_fac.lower(), avail_fac.lower())
        scores.append(fac_score * 0.2)
        
        return sum(scores)
    
    def _simple_string_similarity(self, requirement, availability):
        """Simple string similarity fallback"""
        req_str = f"{requirement.get('location', '')} {requirement.get('description', '')}"
        avail_str = f"{availability.get('location', '')} {availability.get('description', '')}"
        
        similarity = SequenceMatcher(None, req_str.lower(), avail_str.lower()).ratio()
        return similarity * 100
    
    def search_properties(self, requirement_id, match_threshold=60, fuzzy_fallback=True):
        """
        Search for matching properties
        
        Args:
            requirement_id: ID of rent requirement
            match_threshold: Minimum score to include result (0-100)
            fuzzy_fallback: If True, search with fuzzy matching after exact match
        
        Returns:
            List of matches sorted by score
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Get requirement
        c.execute("SELECT * FROM rent_requirements WHERE id=?", (requirement_id,))
        requirement = self._normalize_requirement(dict(c.fetchone() or {}))
        
        if not requirement:
            logger.warning(f"Requirement {requirement_id} not found")
            return []
        
        # Get all available properties
        c.execute("""
            SELECT * FROM rent_availability
            WHERE lower(COALESCE(status, 'available')) NOT IN ('closed', 'inactive', 'deleted')
        """)
        availabilities = [self._normalize_availability(dict(row)) for row in c.fetchall()]
        
        matches = []
        
        # STEP 1: Exact Matching
        logger.info(f"Searching for exact matches for requirement {requirement_id}")
        for avail in availabilities:
            exact_score = self._get_exact_match_score(requirement, avail)
            
            if exact_score >= match_threshold:
                matches.append({
                    'requirement_id': requirement_id,
                    'availability_id': avail['id'],
                    'match_score': exact_score,
                    'match_type': 'EXACT',
                    'match_reason': f"Exact match: Location, budget, and property type aligned",
                    'property': avail,
                    'details': {
                        'location': avail['location'],
                        'rent': avail['monthly_rent'],
                        'beds': avail['size_beds'],
                        'contact': avail['contact_phone']
                    }
                })
        
        matches.sort(key=lambda x: x['match_score'], reverse=True)
        
        # STEP 2: Fuzzy Matching (if enabled and no exact matches)
        if fuzzy_fallback and len(matches) == 0:
            logger.info(f"No exact matches. Searching with fuzzy matching...")
            for avail in availabilities:
                fuzzy_score = self._get_fuzzy_match_score(requirement, avail)
                
                if fuzzy_score >= (match_threshold * 0.7):  # Lower threshold for fuzzy
                    matches.append({
                        'requirement_id': requirement_id,
                        'availability_id': avail['id'],
                        'match_score': fuzzy_score,
                        'match_type': 'FUZZY',
                        'match_reason': f"Similar property: Some attributes match the requirement",
                        'property': avail,
                        'details': {
                            'location': avail['location'],
                            'rent': avail['monthly_rent'],
                            'beds': avail['size_beds'],
                            'contact': avail['contact_phone']
                        }
                    })
        
        matches.sort(key=lambda x: x['match_score'], reverse=True)
        conn.close()
        
        return matches
    
    def filter_by_criteria(self, requirement_id, filters=None):
        """
        Advanced filtering with multiple criteria
        
        Args:
            requirement_id: ID of requirement
            filters: Dict with optional keys:
                - price_range: (min, max)
                - location_radius: km (radius around location)
                - property_types: list of property types
                - min_beds, max_beds
                - min_baths, max_baths
                - min_sq_ft, max_sq_ft
        
        Returns:
            Filtered matches
        """
        if filters is None:
            filters = {}
        
        matches = self.search_properties(requirement_id)
        filtered_matches = []
        
        for match in matches:
            avail = match['property']
            include = True
            
            # Price filter
            if 'price_range' in filters:
                min_p, max_p = filters['price_range']
                rent = float(avail.get('monthly_rent', 0) or 0)
                if not (min_p <= rent <= max_p):
                    include = False
            
            # Property type filter
            if include and 'property_types' in filters:
                if avail.get('property_type') not in filters['property_types']:
                    include = False
            
            # Beds filter
            if include and 'min_beds' in filters:
                if int(avail.get('size_beds', 0) or 0) < filters['min_beds']:
                    include = False
            
            if include and 'max_beds' in filters:
                if int(avail.get('size_beds', 0) or 0) > filters['max_beds']:
                    include = False
            
            # Baths filter
            if include and 'min_baths' in filters:
                if int(avail.get('size_bath', 0) or 0) < filters['min_baths']:
                    include = False
            
            if include and 'max_baths' in filters:
                if int(avail.get('size_bath', 0) or 0) > filters['max_baths']:
                    include = False
            
            # Square footage filter
            if include and 'min_sq_ft' in filters:
                if float(avail.get('sq_ft', 0) or 0) < filters['min_sq_ft']:
                    include = False
            
            if include and 'max_sq_ft' in filters:
                if float(avail.get('sq_ft', 0) or 0) > filters['max_sq_ft']:
                    include = False
            
            if include:
                filtered_matches.append(match)
        
        return filtered_matches


if __name__ == "__main__":
    matcher = PropertyMatcher()
    print("✅ Property Matcher initialized!")
