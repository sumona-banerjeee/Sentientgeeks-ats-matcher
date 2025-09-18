from typing import Dict, List, Optional, Tuple
import re
from datetime import datetime

class JDProcessor:
    def __init__(self):
        self.required_fields = ['job_title', 'experience_required', 'primary_skills']
        self.skill_synonyms = {
            'react': ['react', 'reactjs', 'react.js', 'react js'],
            'javascript': ['javascript', 'js', 'ecmascript', 'es6', 'es2015'],
            'python': ['python', 'python3', 'py', 'cpython'],
            'java': ['java', 'core java', 'java se', 'java ee', 'openjdk'],
            'nodejs': ['node.js', 'nodejs', 'node', 'node js'],
            'angular': ['angular', 'angularjs', 'angular.js', 'angular2+'],
            'spring': ['spring', 'spring boot', 'springframework', 'spring framework'],
            'dotnet': ['.net', 'dotnet', 'dot net', '.net framework', '.net core'],
            'csharp': ['c#', 'csharp', 'c sharp'],
            'mysql': ['mysql', 'my sql', 'Database'],
            'postgresql': ['postgresql', 'postgres', 'psql', 'Database'],
            'mongodb': ['mongodb', 'mongo', 'mongo db'],
            'aws': ['aws', 'amazon web services'],
            'azure': ['azure', 'microsoft azure'],
            'docker': ['docker', 'containerization'],
            'kubernetes': ['kubernetes', 'k8s'],
            'html': ['html', 'html5'],
            'css': ['css', 'css3'],
            'django': ['django', 'django framework'],
            'flask': ['flask', 'flask framework'],
            'fastapi': ['fastapi', 'fast api'],
            'express': ['express', 'expressjs', 'express.js'],
            'vue': ['vue', 'vuejs', 'vue.js'],
            'jquery': ['jquery', 'jquery library'],
            'bootstrap': ['bootstrap', 'bootstrap css'],
            'git': ['git', 'github', 'gitlab', 'version control'],
            'redis': ['redis', 'redis cache'],
            'elasticsearch': ['elasticsearch', 'elastic search'],
            'typescript': ['typescript', 'ts'],
            'php': ['php', 'php7', 'php8'],
            'laravel': ['laravel', 'laravel framework'],
            'ruby': ['ruby', 'ruby language'],
            'rails': ['rails', 'ruby on rails', 'ror'],
            'go': ['go', 'golang', 'go lang'],
            'rust': ['rust', 'rust lang'],
            'swift': ['swift', 'swift language'],
            'kotlin': ['kotlin', 'kotlin language'],
            'flutter': ['flutter', 'flutter framework'],
            'react native': ['react native', 'react-native', 'reactnative']
        }
        
        self.experience_patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'(\d+)\+?\s*years?\s*(?:of\s*)?exp(?:erience)?',
            r'minimum\s*(\d+)\+?\s*years?',
            r'at\s*least\s*(\d+)\+?\s*years?',
            r'(\d+)\+?\s*yrs?\s*experience',
            r'experience\s*(?:of\s*)?(\d+)\+?\s*years?',
            r'(\d+)\s*to\s*(\d+)\s*years?\s*experience',
            r'(\d+)-(\d+)\s*years?\s*experience',
            r'(\d+)\+\s*years?',
            r'(\d+)\s*years?\s*minimum'
        ]
    
    def validate_jd_structure(self, jd_data: dict) -> Tuple[bool, List[str]]:
        """
        Validate JD has required fields for proper matching
        
        Args:
            jd_data: Dictionary containing JD data
            
        Returns:
            Tuple of (is_valid, list_of_missing_fields)
        """
        missing_fields = []
        warnings = []
        
        # Check essential fields
        for field in self.required_fields:
            if not jd_data.get(field):
                missing_fields.append(field)
        
        # Check if skills lists are empty
        primary_skills = jd_data.get('primary_skills', [])
        secondary_skills = jd_data.get('secondary_skills', [])
        
        if not primary_skills and not secondary_skills:
            missing_fields.append('skills (primary or secondary)')
        
        # Check experience requirement format
        exp_req = jd_data.get('experience_required')
        if exp_req and not self._is_valid_experience_format(exp_req):
            warnings.append('experience_required format might be unclear')
        
        is_valid = len(missing_fields) == 0
        
        if warnings:
            print(f"⚠️ JD Validation Warnings: {warnings}")
        
        return is_valid, missing_fields
    
    def standardize_skills(self, skills: List[str]) -> List[str]:
        """
        Standardize skill names for consistent matching
        
        Args:
            skills: List of skill names (possibly with variations)
            
        Returns:
            List of standardized skill names
        """
        if not skills:
            return []
        
        standardized = []
        processed_canonicals = set()  # Track canonical forms we've added
        
        for skill in skills:
            if not skill or not isinstance(skill, str):
                continue
                
            clean_skill = self._clean_skill_name(skill)
            if not clean_skill:
                continue
            
            # Find canonical form
            canonical = self._find_canonical_skill(clean_skill)
            
            # Add if we haven't seen this canonical form yet
            if canonical and canonical not in processed_canonicals:
                standardized.append(canonical)
                processed_canonicals.add(canonical)
        
        return standardized
    
    def extract_experience_requirement(self, jd_text: str) -> float:
        """
        Extract numeric experience requirement from JD text
        
        Args:
            jd_text: Raw job description text
            
        Returns:
            Years of experience required (0.0 if not found)
        """
        if not jd_text or not isinstance(jd_text, str):
            return 0.0
        
        jd_lower = jd_text.lower()
        
        for pattern in self.experience_patterns:
            matches = re.findall(pattern, jd_lower)
            if matches:
                if isinstance(matches[0], tuple):
                    # Range like "2-5 years" - take minimum
                    try:
                        return float(matches[0][0])
                    except (ValueError, IndexError):
                        continue
                else:
                    # Single number like "3+ years"
                    try:
                        return float(matches[0])
                    except (ValueError, IndexError):
                        continue
        
        return 0.0
    
    def enhance_jd_data(self, raw_jd_data: dict) -> dict:
        """
        Post-process and enhance JD data from LLM
        
        Args:
            raw_jd_data: Raw JD data from LLM processing
            
        Returns:
            Enhanced and validated JD data
        """
        enhanced_data = raw_jd_data.copy()
        
        # Standardize skills
        if 'primary_skills' in enhanced_data:
            enhanced_data['primary_skills'] = self.standardize_skills(
                enhanced_data['primary_skills']
            )
        
        if 'secondary_skills' in enhanced_data:
            enhanced_data['secondary_skills'] = self.standardize_skills(
                enhanced_data['secondary_skills']
            )
        
        # Ensure experience requirement is numeric
        if 'experience_required' in enhanced_data:
            exp_req = enhanced_data['experience_required']
            if isinstance(exp_req, str):
                numeric_exp = self.extract_experience_requirement(exp_req)
                enhanced_data['experience_required'] = numeric_exp
        
        # Validate final structure
        is_valid, missing = self.validate_jd_structure(enhanced_data)
        if not is_valid:
            print(f"⚠️ JD missing required fields: {missing}")
        
        return enhanced_data
    
    def categorize_skills_by_priority(self, jd_data: dict) -> dict:
        """
        Categorize skills into different priority levels
        
        Args:
            jd_data: Job description data
            
        Returns:
            Dictionary with priority-categorized skills
        """
        primary_skills = jd_data.get('primary_skills', [])
        secondary_skills = jd_data.get('secondary_skills', [])
        job_title = jd_data.get('job_title', '').lower()
        
        # Determine core technology based on job title
        core_tech = self._identify_core_technology(job_title)
        
        categorized = {
            'must_have': [],      # Priority 1 - Essential skills
            'nice_to_have': [],   # Priority 2 - Good to have
            'bonus': []           # Priority 3 - Bonus skills
        }
        
        # Categorize primary skills
        for skill in primary_skills:
            skill_lower = skill.lower()
            if core_tech and core_tech in skill_lower:
                categorized['must_have'].append(skill)
            else:
                categorized['must_have'].append(skill)  # All primary are must-have
        
        # Categorize secondary skills
        for skill in secondary_skills:
            categorized['nice_to_have'].append(skill)
        
        return categorized
    
    def _clean_skill_name(self, skill: str) -> str:
        """Clean and normalize skill name"""
        if not skill:
            return ""
        
        # Convert to lowercase and strip
        clean = skill.lower().strip()
        
        # Remove special characters except +, #, .
        clean = re.sub(r'[^\w\s+#.-]', '', clean)
        
        # Remove common suffixes
        suffixes = ['framework', 'js', 'developer', 'development', 'language', 'library']
        for suffix in suffixes:
            if clean.endswith(f' {suffix}'):
                clean = clean[:-len(suffix)-1].strip()
        
        # Handle special cases
        if clean == 'c sharp':
            return 'c#'
        if clean == 'dot net':
            return '.net'
        
        return clean.strip()
    
    def _find_canonical_skill(self, skill: str) -> Optional[str]:
        """Find canonical form of skill"""
        skill_lower = skill.lower().strip()
        
        # Direct lookup in synonyms
        for canonical, variations in self.skill_synonyms.items():
            if skill_lower in variations:
                return canonical
        
        # If not found in synonyms, return original if valid
        if len(skill_lower) >= 2 and not skill_lower.isdigit():
            return skill_lower
        
        return None
    
    def _is_valid_experience_format(self, exp_req) -> bool:
        """Check if experience requirement is in valid format"""
        if isinstance(exp_req, (int, float)):
            return True
        
        if isinstance(exp_req, str):
            # Check if string contains numeric experience pattern
            return bool(re.search(r'\d+', exp_req))
        
        return False
    
    def _identify_core_technology(self, job_title: str) -> Optional[str]:
        """Identify core technology from job title"""
        title_lower = job_title.lower()
        
        tech_indicators = {
            'python': ['python', 'django', 'flask'],
            'java': ['java', 'spring', 'j2ee'],
            'javascript': ['javascript', 'js', 'react', 'angular', 'node'],
            'dotnet': ['.net', 'c#', 'asp.net'],
            'php': ['php', 'laravel'],
            'ruby': ['ruby', 'rails'],
            'go': ['golang', 'go '],
            'mobile': ['android', 'ios', 'mobile']
        }
        
        for tech, indicators in tech_indicators.items():
            if any(indicator in title_lower for indicator in indicators):
                return tech
        
        return None

# Utility function for easy import
def create_jd_processor() -> JDProcessor:
    """Create and return a JDProcessor instance"""
    return JDProcessor()
