import PyPDF2
import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import io
import traceback


class ResumeProcessor:
    def __init__(self):
        self.experience_indicators = [
            'experience', 'work history', 'employment', 'professional experience',
            'career history', 'work experience', 'employment history'
        ]
        
        self.skill_categories = {
            'programming': [
                'python', 'java', 'javascript', 'c++', 'c#', 'go', 'rust', 'php',
                'ruby', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'perl'
            ],
            'web_frameworks': [
                'react', 'angular', 'vue', 'django', 'flask', 'fastapi', 'spring',
                'express', 'laravel', 'rails', 'asp.net', 'node.js', 'next.js'
            ],
            'databases': [
                'mysql', 'postgresql', 'mongodb', 'redis', 'sqlite', 'oracle',
                'cassandra', 'elasticsearch', 'dynamodb', 'mariadb'
            ],
            'cloud': [
                'aws', 'azure', 'gcp', 'google cloud', 'heroku', 'digitalocean',
                'linode', 'cloudflare', 'firebase'
            ],
            'devops': [
                'docker', 'kubernetes', 'jenkins', 'git', 'github', 'gitlab',
                'terraform', 'ansible', 'puppet', 'chef', 'vagrant'
            ],
            'tools': [
                'jira', 'postman', 'swagger', 'figma', 'photoshop', 'vs code',
                'intellij', 'eclipse', 'xcode', 'android studio'
            ],
            'web_tech': [
                'html', 'css', 'bootstrap', 'tailwind', 'sass', 'less',
                'webpack', 'babel', 'typescript', 'jquery'
            ],
            'mobile': [
                'android', 'ios', 'react native', 'flutter', 'xamarin', 'cordova'
            ],
            'data': [
                'pandas', 'numpy', 'tensorflow', 'pytorch', 'scikit-learn',
                'matplotlib', 'seaborn', 'jupyter', 'tableau', 'power bi'
            ]
        }
        
        self.company_indicators = [
            r'[A-Z][a-zA-Z\s&.,]+(?:Pvt\.?\s*Ltd\.?|Private\s+Limited)',
            r'[A-Z][a-zA-Z\s&.,]+(?:Inc\.?|Corporation|Corp\.?)',
            r'[A-Z][a-zA-Z\s&.,]+(?:LLC|LLP)',
            r'[A-Z][a-zA-Z\s&.,]+(?:Technologies|Systems|Solutions|Software)',
            r'[A-Z][a-zA-Z\s&.,]+(?:Company|Group|Enterprises)'
        ]
        
        self.role_indicators = [
            'engineer', 'developer', 'programmer', 'analyst', 'manager',
            'lead', 'senior', 'junior', 'intern', 'consultant', 'architect',
            'specialist', 'coordinator', 'administrator'
        ]
        
        self.duration_patterns = [
            r'(\w+\s+\d{4})\s*[-–]\s*(\w+\s+\d{4})',  # "Jan 2020 - Dec 2022"
            r'(\d{1,2}/\d{4})\s*[-–]\s*(\d{1,2}/\d{4})',  # "01/2020 - 12/2022"
            r'(\d{4})\s*[-–]\s*(\d{4})',  # "2020 - 2022"
            r'(\w+\s+\d{4})\s*[-–]\s*present',  # "Jan 2020 - Present"
            r'(\d{1,2}/\d{4})\s*[-–]\s*present',  # "01/2020 - Present"
            r'(\d{4})\s*[-–]\s*present',  # "2020 - Present"
        ]
    
    def extract_text_from_pdf(self, file_content: bytes) -> str:
        """
        Extract text from PDF file content
        
        Args:
            file_content: PDF file as bytes
            
        Returns:
            Extracted text string
        """
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            text = ""
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                except Exception as e:
                    print(f"Error extracting page {page_num}: {e}")
                    continue
            
            # Clean up the text
            text = re.sub(r'\n+', '\n', text)  # Remove multiple newlines
            text = re.sub(r'\s+', ' ', text)   # Remove multiple spaces
            
            return text.strip()
            
        except Exception as e:
            print(f"Error extracting PDF text: {e}")
            traceback.print_exc()
            return ""
    
    def extract_education_details(self, text: str) -> List[str]:
        """
        Extract education information with enhanced parsing
        
        Args:
            text: Resume text
            
        Returns:
            List of education entries
        """
        education = []
        text_lower = text.lower()
        
        # Degree patterns with field of study
        degree_patterns = [
            r'(bachelor(?:\'s)?|b\.?tech|b\.?e\.?|b\.?sc|ba|bs)\s+(?:of|in|degree)?\s*([a-z\s]+)',
            r'(master(?:\'s)?|m\.?tech|m\.?e\.?|m\.?sc|ma|ms|mba)\s+(?:of|in|degree)?\s*([a-z\s]+)',
            r'(phd|ph\.d\.|doctorate|doctor)\s+(?:of|in)?\s*([a-z\s]+)',
            r'(diploma|associate)\s+(?:in)?\s*([a-z\s]+)'
        ]
        
        # Extract degree + field combinations
        for pattern in degree_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 2:
                    degree = match[0].strip().title()
                    field = match[1].strip().title()
                    # Clean up field (remove extra words)
                    field_words = field.split()[:5]  # Take first 5 words max
                    field_clean = ' '.join(field_words)
                    
                    if field_clean and len(field_clean) > 2:
                        edu_entry = f"{degree} in {field_clean}"
                        if edu_entry not in education:
                            education.append(edu_entry)
        
        # Extract from education section if no patterns matched
        if not education:
            edu_section_pattern = r'education.*?(?:experience|skills|certifications|projects|achievements|$)'
            edu_match = re.search(edu_section_pattern, text_lower, re.DOTALL)
            
            if edu_match:
                edu_text = edu_match.group()
                lines = [line.strip() for line in edu_text.split('\n') if line.strip()]
                
                # Filter out section headers and extract meaningful lines
                for line in lines[:8]:  # Check first 8 lines of education section
                    line_clean = line.strip()
                    # Skip section headers and very short lines
                    if len(line_clean) > 10 and len(line_clean) < 150:
                        # Skip if it's just a year or location
                        if not re.match(r'^\d{4}(-\d{4})?$', line_clean):
                            if not any(skip in line_clean.lower() for skip in ['education', 'degree', 'university', 'college', 'institute']):
                                if any(c.isalpha() for c in line_clean):
                                    education.append(line_clean.title())
        
        # If still no education found, look for university/college names
        if not education:
            university_patterns = [
                r'([A-Z][a-zA-Z\s]+(?:University|College|Institute)[a-zA-Z\s]*)',
            ]
            
            for pattern in university_patterns:
                matches = re.findall(pattern, text)
                for match in matches[:3]:  # Limit to 3 universities
                    if isinstance(match, str) and len(match) > 10:
                        education.append(match.strip())
        
        return education if education else ["No education information available"]
    
    def extract_certifications_details(self, text: str) -> List[str]:
        """
        Extract certifications with enhanced parsing
        
        Args:
            text: Resume text
            
        Returns:
            List of certification entries
        """
        certifications = []
        text_lower = text.lower()
        
        # Common certification keywords
        cert_keywords = [
            'certified', 'certification', 'certificate',
            'aws certified', 'azure certified', 'google cloud',
            'pmp', 'prince2', 'itil', 'cissp', 'ceh',
            'scrum master', 'comptia', 'cisco', 'oracle certified',
            'ccna', 'mcsa', 'mcse', 'rhce', 'cka', 'ckad'
        ]
        
        # Look for certification section
        cert_section_pattern = r'certifications?.*?(?:education|experience|skills|projects|achievements|languages|$)'
        cert_match = re.search(cert_section_pattern, text_lower, re.DOTALL)
        
        if cert_match:
            cert_text = cert_match.group()
            lines = [line.strip() for line in cert_text.split('\n') if line.strip()]
            
            for line in lines:
                line_clean = line.strip()
                # Check if line contains certification keywords
                if any(keyword in line_clean.lower() for keyword in cert_keywords):
                    if 5 < len(line_clean) < 150:
                        # Skip section headers
                        if not re.match(r'^certifications?:?$', line_clean.lower()):
                            if line_clean not in certifications:
                                certifications.append(line_clean.title())
        
        # Also check for specific certification patterns anywhere in full text
        specific_patterns = [
            r'(aws\s+certified\s+[a-z\s\-]+(?:associate|professional|specialty)?)',
            r'(microsoft\s+certified\s+[a-z\s\-]+)',
            r'(google\s+cloud\s+[a-z\s\-]+(?:engineer|architect)?)',
            r'(oracle\s+certified\s+[a-z\s\-]+)',
            r'(cisco\s+certified\s+[a-z\s\-]+)',
            r'(comptia\s+[a-z+]+)',
            r'(certified\s+kubernetes\s+[a-z\s]+)',
            r'(pmp|prince2|itil|cissp|ceh|ccna|ccnp|mcsa|mcse|rhce|cka|ckad)\s*(?:certified)?',
        ]
        
        for pattern in specific_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                cert = match if isinstance(match, str) else match[0]
                cert_clean = cert.strip().title()
                
                # Avoid duplicates
                if cert_clean and cert_clean not in certifications and len(cert_clean) > 3:
                    certifications.append(cert_clean)
        
        # Limit to top 10 certifications to avoid noise
        certifications = certifications[:10]
        
        return certifications if certifications else ["No certifications available"]
    
    def parse_experience_timeline(self, text: str) -> List[Dict]:
        """
        Parse work experience into structured timeline
        
        Args:
            text: Resume text
            
        Returns:
            List of experience dictionaries
        """
        if not text:
            return []
        
        experiences = []
        lines = text.split('\n')
        current_experience = {}
        in_experience_section = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Check if we're entering experience section
            if self._is_experience_section_header(line):
                in_experience_section = True
                continue
            
            # Check if we're leaving experience section
            if in_experience_section and self._is_new_section_header(line):
                if current_experience:
                    experiences.append(self._finalize_experience(current_experience))
                    current_experience = {}
                in_experience_section = False
                continue
            
            if not in_experience_section:
                continue
            
            # Look for company and role patterns
            company_role = self._extract_company_role(line)
            if company_role:
                # Save previous experience if exists
                if current_experience:
                    experiences.append(self._finalize_experience(current_experience))
                
                current_experience = {
                    'company': company_role['company'],
                    'role': company_role['role'],
                    'duration': '',
                    'technologies_used': [],
                    'responsibilities': []
                }
                
                # Look for duration in nearby lines
                duration = self._find_duration_nearby(lines, i)
                if duration:
                    current_experience['duration'] = duration
                
                continue
            
            # Look for duration patterns in current line
            if current_experience and not current_experience.get('duration'):
                duration = self._extract_duration_from_line(line)
                if duration:
                    current_experience['duration'] = duration
                    continue
            
            # Extract technologies and responsibilities from current line
            if current_experience:
                # Extract technologies
                techs = self._extract_technologies_from_line(line)
                if techs:
                    current_experience['technologies_used'].extend(techs)
                
                # Add as responsibility if it looks like one
                if self._is_responsibility_line(line):
                    current_experience['responsibilities'].append(line)
        
        # Don't forget the last experience
        if current_experience:
            experiences.append(self._finalize_experience(current_experience))
        
        return experiences
    
    def calculate_total_experience(self, experiences: List[Dict]) -> float:
        """
        Calculate total years of experience from timeline
        
        Args:
            experiences: List of experience dictionaries
            
        Returns:
            Total years as float
        """
        if not experiences:
            return 0.0
        
        total_months = 0
        
        for exp in experiences:
            duration = exp.get('duration', '')
            months = self._parse_duration_to_months(duration)
            total_months += months
        
        return round(total_months / 12, 1)
    
    def extract_skills_from_text(self, text: str) -> List[str]:
        """
        Extract technical skills from resume text
        
        Args:
            text: Resume text
            
        Returns:
            List of identified skills
        """
        if not text:
            return []
        
        skills = set()
        text_lower = text.lower()
        
        # Extract from all skill categories
        for category, skill_list in self.skill_categories.items():
            for skill in skill_list:
                # Use word boundaries to avoid partial matches
                pattern = rf'\b{re.escape(skill.lower())}\b'
                if re.search(pattern, text_lower):
                    skills.add(skill)
        
        # Extract from dedicated skills section
        skills_section_text = self._extract_skills_section(text)
        if skills_section_text:
            section_skills = self._parse_skills_section(skills_section_text)
            skills.update(section_skills)
        
        # Extract from tech stack mentions
        tech_stack_skills = self._extract_tech_stack_mentions(text)
        skills.update(tech_stack_skills)
        
        return list(skills)
    
    def extract_personal_info(self, text: str) -> Dict:
        """
        Extract personal information from resume
        
        Args:
            text: Resume text
            
        Returns:
            Dictionary with personal info
        """
        info = {
            'name': '',
            'email': '',
            'phone': '',
            'linkedin': '',
            'github': '',
            'location': ''
        }
        
        lines = text.split('\n')[:10]  # Check first 10 lines
        
        for line in lines:
            line = line.strip()
            
            # Extract name (usually first non-empty line)
            if not info['name'] and line and not any(x in line.lower() for x in ['@', 'http', '+91', '+1']):
                if len(line.split()) <= 4 and all(word.replace('.', '').replace(',', '').isalpha() for word in line.split()):
                    info['name'] = line
            
            # Extract email
            email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', line)
            if email_match and not info['email']:
                info['email'] = email_match.group()
            
            # Extract phone
            phone_match = re.search(r'[\+]?[1-9]?[\s\-]?[\(]?[0-9]{3}[\)]?[\s\-]?[0-9]{3}[\s\-]?[0-9]{4,6}', line)
            if phone_match and not info['phone']:
                info['phone'] = phone_match.group()
            
            # Extract LinkedIn
            if 'linkedin' in line.lower() and not info['linkedin']:
                linkedin_match = re.search(r'linkedin\.com/in/[\w\-]+', line.lower())
                if linkedin_match:
                    info['linkedin'] = linkedin_match.group()
            
            # Extract GitHub
            if 'github' in line.lower() and not info['github']:
                github_match = re.search(r'github\.com/[\w\-]+', line.lower())
                if github_match:
                    info['github'] = github_match.group()
        
        return info
    
    def enhance_resume_data(self, raw_resume_data: dict) -> dict:
        """
        Post-process and enhance resume data
    
        Args:
            raw_resume_data: Raw resume data from processing
        
        Returns:
            Enhanced resume data with guaranteed skills array
        """
        enhanced_data = raw_resume_data.copy()
    
        # Ensure experience timeline exists and is properly formatted
        if 'experience_timeline' not in enhanced_data:
            enhanced_data['experience_timeline'] = []
    
        # Calculate total experience if not provided
        if 'total_experience' not in enhanced_data or not enhanced_data['total_experience']:
            enhanced_data['total_experience'] = self.calculate_total_experience(
                enhanced_data['experience_timeline']
            )
    
        # ✅ ENSURE SKILLS IS ALWAYS AN ARRAY - NORMALIZE FIRST
        if 'skills' in enhanced_data:
            # Normalize skills to array format (handles string, dict, list, etc.)
            enhanced_data['skills'] = self.normalize_skills_to_array(enhanced_data['skills'])
            enhanced_skills = set(enhanced_data['skills'])
        
            # Extract additional skills from experience descriptions
            for exp in enhanced_data.get('experience_timeline', []):
                exp_text = ' '.join([
                    exp.get('role', ''),
                    ' '.join(exp.get('responsibilities', [])),
                    ' '.join(exp.get('technologies_used', []))
                ])
                additional_skills = self.extract_skills_from_text(exp_text)
                enhanced_skills.update(additional_skills)
        
            # Convert back to list and ensure it's an array
            enhanced_data['skills'] = list(enhanced_skills)
        else:
            # If no skills key exists, ensure empty array
            enhanced_data['skills'] = []
    
        # ✅ FINAL VALIDATION: Ensure skills is a list
        if not isinstance(enhanced_data['skills'], list):
            enhanced_data['skills'] = self.normalize_skills_to_array(enhanced_data['skills'])
        
        # ✅ ENSURE EDUCATION IS PRESENT
        if 'education' not in enhanced_data or not enhanced_data['education']:
            # Extract education from original text if available
            original_text = raw_resume_data.get('original_text', '')
            if original_text:
                enhanced_data['education'] = self.extract_education_details(original_text)
            else:
                enhanced_data['education'] = ["No education information available"]
        
        # ✅ ENSURE CERTIFICATIONS IS PRESENT
        if 'certifications' not in enhanced_data or not enhanced_data['certifications']:
            # Extract certifications from original text if available
            original_text = raw_resume_data.get('original_text', '')
            if original_text:
                enhanced_data['certifications'] = self.extract_certifications_details(original_text)
            else:
                enhanced_data['certifications'] = ["No certifications available"]
    
        return enhanced_data
    
    def normalize_skills_to_array(self, skills) -> List[str]:
        """
        Ensure skills is always returned as a list/array
        Handles all possible input types: string, list, dict, None, etc.
    
        Args:
            skills: Skills in any format
        
        Returns:
            List of skill strings
        """
        # Handle None/empty
        if not skills:
            return []
    
        # Already a list - just clean it
        if isinstance(skills, list):
            return [str(skill).strip() for skill in skills if skill and str(skill).strip()]
    
        # Handle dictionary format (e.g., {0: "Python", 1: "Java"})
        if isinstance(skills, dict):
            return [str(v).strip() for v in skills.values() if v and str(v).strip()]
    
        # Handle string format
        if isinstance(skills, str):
            # Try splitting by comma first
            skill_list = [s.strip() for s in skills.split(',') if s.strip()]
        
            # If no commas found, try other delimiters
            if len(skill_list) == 1:
                for delimiter in ['|', ';', '/', '\n', '•', '-']:
                    if delimiter in skills:
                        skill_list = [s.strip() for s in skills.split(delimiter) if s.strip()]
                        break
        
            return skill_list
    
        # For any other type, try to convert to string and return as single-item list
        try:
            skill_str = str(skills).strip()
            return [skill_str] if skill_str else []
        except:
            return []
    
    # Helper methods
    def _is_experience_section_header(self, line: str) -> bool:
        """Check if line is an experience section header"""
        line_lower = line.lower().strip()
        return any(indicator in line_lower for indicator in self.experience_indicators)
    
    def _is_new_section_header(self, line: str) -> bool:
        """Check if line starts a new section (not experience)"""
        section_headers = [
            'education', 'skills', 'projects', 'certifications', 'achievements',
            'awards', 'publications', 'languages', 'interests', 'references'
        ]
        line_lower = line.lower().strip()
        return any(header in line_lower for header in section_headers)
    
    def _extract_company_role(self, line: str) -> Optional[Dict]:
        """Extract company and role from a line"""
        # Pattern 1: "Software Engineer at Google Inc."
        at_pattern = r'(.+?)\s+at\s+(.+?)(?:\s*,|\s*$)'
        match = re.search(at_pattern, line, re.IGNORECASE)
        if match:
            return {'role': match.group(1).strip(), 'company': match.group(2).strip()}
        
        # Pattern 2: "Google Inc. - Software Engineer"
        dash_pattern = r'(.+?)\s*[-–]\s*(.+?)(?:\s*,|\s*$)'
        match = re.search(dash_pattern, line)
        if match:
            part1, part2 = match.group(1).strip(), match.group(2).strip()
            # Determine which is company vs role based on common patterns
            if any(indicator in part1.lower() for indicator in ['inc', 'ltd', 'corp', 'llc', 'technologies', 'systems']):
                return {'company': part1, 'role': part2}
            elif any(indicator in part2.lower() for indicator in self.role_indicators):
                return {'company': part1, 'role': part2}
            else:
                return {'role': part1, 'company': part2}
        
        # Pattern 3: Just role or company (need more context)
        if any(indicator in line.lower() for indicator in self.role_indicators):
            return {'role': line.strip(), 'company': ''}
        
        return None
    
    def _find_duration_nearby(self, lines: List[str], current_index: int) -> str:
        """Find duration in nearby lines"""
        # Check next few lines for duration
        for i in range(current_index + 1, min(current_index + 4, len(lines))):
            duration = self._extract_duration_from_line(lines[i])
            if duration:
                return duration
        
        # Check previous few lines
        for i in range(max(0, current_index - 3), current_index):
            duration = self._extract_duration_from_line(lines[i])
            if duration:
                return duration
        
        return ''
    
    def _extract_duration_from_line(self, line: str) -> str:
        """Extract duration from a line"""
        for pattern in self.duration_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return line.strip()
        return ''
    
    def _parse_duration_to_months(self, duration: str) -> int:
        """Convert duration string to months"""
        if not duration:
            return 0
        
        duration = duration.lower().strip()
        
        # Handle "present" or "current"
        if 'present' in duration or 'current' in duration:
            # Extract start date and calculate to present
            year_matches = re.findall(r'\b(\d{4})\b', duration)
            if year_matches:
                start_year = int(year_matches[0])
                current_year = datetime.now().year
                return max(1, (current_year - start_year) * 12)
        
        # Handle explicit years/months
        years_match = re.search(r'(\d+(?:\.\d+)?)\s*years?', duration)
        if years_match:
            return int(float(years_match.group(1)) * 12)
        
        months_match = re.search(r'(\d+)\s*months?', duration)
        if months_match:
            return int(months_match.group(1))
        
        # Handle year ranges
        year_matches = re.findall(r'\b(\d{4})\b', duration)
        if len(year_matches) >= 2:
            start_year = int(year_matches[0])
            end_year = int(year_matches[-1])
            return max(1, (end_year - start_year) * 12)
        
        # Handle month-year patterns
        month_year_matches = re.findall(r'(\d{1,2})/(\d{4})', duration)
        if len(month_year_matches) >= 2:
            start_month, start_year = month_year_matches[0]
            end_month, end_year = month_year_matches[-1]
            start_total = int(start_year) * 12 + int(start_month)
            end_total = int(end_year) * 12 + int(end_month)
            return max(1, end_total - start_total)
        
        return 6  # Default 6 months if unparseable
    
    def _extract_technologies_from_line(self, line: str) -> List[str]:
        """Extract technologies mentioned in a line"""
        technologies = []
        line_lower = line.lower()
        
        # Check all skill categories
        for category, skills in self.skill_categories.items():
            for skill in skills:
                if f' {skill} ' in f' {line_lower} ' or line_lower.startswith(skill) or line_lower.endswith(skill):
                    technologies.append(skill)
        
        return technologies
    
    def _is_responsibility_line(self, line: str) -> bool:
        """Check if line describes a responsibility"""
        line = line.strip()
        
        # Common responsibility indicators
        responsibility_indicators = [
            '•', '◦', '-', '*', '→',  # Bullet points
            'developed', 'built', 'created', 'designed', 'implemented',
            'managed', 'led', 'coordinated', 'maintained', 'optimized',
            'collaborated', 'worked', 'responsible', 'achieved'
        ]
        
        line_lower = line.lower()
        return any(indicator in line_lower for indicator in responsibility_indicators) and len(line) > 20
    
    def _extract_skills_section(self, text: str) -> str:
        """Extract the skills section from resume text"""
        skills_patterns = [
            r'(?:technical\s+skills|skills|technologies|tech\s+stack|core\s+competencies)[:\s]+(.*?)(?=\n\n|\n[A-Z][A-Z\s]+:|\Z)',
            r'(?:programming\s+languages|languages)[:\s]+(.*?)(?=\n\n|\n[A-Z][A-Z\s]+:|\Z)',
            r'(?:tools\s+and\s+technologies|tools)[:\s]+(.*?)(?=\n\n|\n[A-Z][A-Z\s]+:|\Z)'
        ]
        
        for pattern in skills_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        
        return ''
    
    def _parse_skills_section(self, skills_text: str) -> List[str]:
        """Parse skills from skills section text"""
        skills = []
        
        # Split by common delimiters
        delimiters = [',', '|', ';', '•', '-', '\n']
        text = skills_text
        
        for delimiter in delimiters:
            text = text.replace(delimiter, ',')
        
        # Extract individual skills
        potential_skills = [s.strip() for s in text.split(',') if s.strip()]
        
        for skill in potential_skills:
            # Clean up the skill
            skill = re.sub(r'[^\w\s+#.-]', '', skill)
            skill = skill.strip()
            
            # Filter out non-skills
            if len(skill) > 1 and not skill.isdigit():
                skills.append(skill.lower())
        
        return skills
    
    def _extract_tech_stack_mentions(self, text: str) -> List[str]:
        """Extract skills from tech stack mentions"""
        tech_stack_pattern = r'tech\s+stack[:\s]+(.*?)(?=\n\n|\n[A-Z]|\Z)'
        matches = re.findall(tech_stack_pattern, text, re.IGNORECASE | re.DOTALL)
        
        skills = []
        for match in matches:
            # Split by common delimiters and extract skills
            potential_skills = re.split(r'[,|;•\-\n]+', match)
            for skill in potential_skills:
                skill = skill.strip().lower()
                if len(skill) > 1 and not skill.isdigit():
                    skills.append(skill)
        
        return skills
    
    def _finalize_experience(self, experience: Dict) -> Dict:
        """Clean up and finalize an experience entry"""
        # Remove duplicates from technologies
        if 'technologies_used' in experience:
            experience['technologies_used'] = list(set(experience['technologies_used']))
        
        # Ensure all required fields exist
        required_fields = ['company', 'role', 'duration', 'technologies_used', 'responsibilities']
        for field in required_fields:
            if field not in experience:
                experience[field] = [] if field in ['technologies_used', 'responsibilities'] else ''
        
        return experience


def create_resume_processor() -> 'ResumeProcessor':
    """Create and return a ResumeProcessor instance"""
    return ResumeProcessor()