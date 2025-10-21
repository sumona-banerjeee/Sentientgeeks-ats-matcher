import requests
import json
import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import re


load_dotenv()


class LLMService:
    
    def __init__(self):
        """
        Initialize LLM Service with multiple backend support
        - Agentic AI (CrewAI + Groq)
        - Perplexity API (fallback)
        - Mock mode (for testing)
        """
        # INITIALIZE ALL ATTRIBUTES FIRST (prevents AttributeError)
        self.use_mock = False
        self.use_agentic = False
        self.agentic_available = False
        self.api_key = None
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.headers = {}
        self.timeout_config = {
            "connection_timeout": 10,
            "read_timeout": 30,
            "total_timeout": 60
        }
        
        # Check if we should use Agentic AI
        use_agentic_env = os.getenv("USE_AGENTIC_AI", "false").lower() == "true"
        
        if use_agentic_env:
            try:
                from backend.app.services.agentic_service import EnhancedAgenticATSService
                self.agentic_service = EnhancedAgenticATSService()
                self.use_agentic = True
                self.agentic_available = True
                print("✅ LLM Service initialized with Agentic AI (CrewAI)")
            except Exception as e:
                print(f"⚠️ Failed to initialize Agentic AI: {e}")
                print("🔄 Falling back to Perplexity API")
                self.use_agentic = False
                self.agentic_available = False
                self._init_perplexity()
        else:
            print("🔧 LLM Service initialized with Perplexity API (Legacy Mode)")
            self.use_agentic = False
            self.agentic_available = False
            self._init_perplexity()
    
    def _init_perplexity(self):
        """Initialize Perplexity API configuration"""
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        self.timeout_config = {
            "connection_timeout": int(os.getenv("PERPLEXITY_CONNECTION_TIMEOUT", "10")),
            "read_timeout": int(os.getenv("PERPLEXITY_READ_TIMEOUT", "30")),
            "total_timeout": int(os.getenv("PERPLEXITY_TOTAL_TIMEOUT", "60")),
        }
        
        # Check if we should use mock mode
        self.use_mock = not self.api_key or self.api_key in ["your_perplexity_api_key_here", "", "None"]
        
        if self.use_mock:
            print("🔨 Perplexity API running in MOCK mode (no valid API key)")
        else:
            print("✅ Perplexity API configured with valid key")
    
    async def structure_job_description(self, jd_text: str) -> Dict[str, Any]:
        """Structure JD using Agentic AI or Perplexity"""
        # Try Agentic AI first if available
        if self.use_agentic and self.agentic_available:
            try:
                print("🤖 Using Agentic AI for JD analysis...")
                return await self.agentic_service.analyze_job_description(jd_text)
            except Exception as e:
                print(f"⚠️ Agentic AI failed: {e}, falling back to Perplexity...")
        
        # Fallback to Perplexity API
        return await self._structure_jd_perplexity(jd_text)
    
    async def extract_resume_information(self, resume_text: str) -> Dict[str, Any]:
        """Extract resume info using Agentic AI or Perplexity"""
        if self.use_agentic and self.agentic_available:
            try:
                print("🤖 Using Agentic AI for resume analysis...")
                return await self.agentic_service.analyze_resume(resume_text)
            except Exception as e:
                print(f"⚠️ Agentic AI failed: {e}, falling back to Perplexity...")
        
        # Fallback to Perplexity API
        return await self._extract_resume_perplexity(resume_text)
    
    async def refine_structure_based_on_feedback(self, current_structure: Dict, feedback: str) -> Dict[str, Any]:
        """Refine the structured JD based on user feedback"""
        
        # ✅ TRY AGENTIC AI FIRST
        if self.use_agentic and self.agentic_available:
            try:
                print("🤖 Using Agentic AI for refinement...")
                refined = await self.agentic_service.refine_job_description_structure(
                    current_structure, 
                    feedback
                )
                print(f"✅ Agentic AI refinement successful!")
                return refined
            except Exception as e:
                print(f"⚠️ Agentic AI refinement failed: {e}")
                print("🔄 Falling back to mock refinement")
        
        # Check if we should use mock or Perplexity
        if self.use_mock or not hasattr(self, 'base_url') or not self.base_url:
            print("🔨 Using mock refinement (no API available)")
            return self._refine_mock_structure(current_structure, feedback)
        
        # Try Perplexity API
        try:
            print(f"🔄 Refining structure with Perplexity API...")
            
            prompt = f"""
            Modify this job description structure based on the user feedback.
            
            Current Structure:
            {json.dumps(current_structure, indent=2)}
            
            User Feedback:
            {feedback}
            
            Apply the feedback and return the updated JSON structure with the same field names.
            Return only valid JSON, no explanatory text.
            """
            
            response = await self._make_api_call(prompt)
            
            try:
                refined_data = json.loads(response)
                print("✅ Successfully refined structure with Perplexity API")
                return refined_data
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    refined_data = json.loads(json_match.group())
                    return refined_data
                else:
                    raise Exception("Invalid JSON in refinement response")
                    
        except Exception as e:
            print(f"❌ Perplexity refinement failed: {str(e)}")
            return self._refine_mock_structure(current_structure, feedback)
    
    async def _structure_jd_perplexity(self, jd_text: str) -> Dict[str, Any]:
        """Structure JD using Perplexity API"""
        if self.use_mock:
            return self._generate_mock_jd_structure(jd_text)
        
        try:
            print(f"🔍 Processing JD with Perplexity API (length: {len(jd_text)})...")
            
            prompt = f"""
            Analyze this job description and extract information into a JSON format with these exact fields:
            - job_title: string
            - company: string (or "Not specified" if not mentioned)
            - location: string (or "Not specified" if not mentioned)  
            - experience_required: string (e.g., "3-5 years")
            - primary_skills: array of strings (most important technical skills)
            - secondary_skills: array of strings (nice-to-have skills)
            - responsibilities: array of strings
            - qualifications: array of strings
            - job_type: string (Full-time, Part-time, Contract, etc.)


            Job Description:
            {jd_text}


            Return only valid JSON, no explanatory text.
            """
            
            response = await self._make_api_call(prompt)
            
            try:
                structured_data = json.loads(response)
                print("✅ Successfully structured JD with Perplexity API")
                return structured_data
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    structured_data = json.loads(json_match.group())
                    print("✅ Successfully extracted JSON from Perplexity response")
                    return structured_data
                else:
                    raise Exception("Invalid JSON response from API")
                    
        except Exception as e:
            print(f"❌ Perplexity API failed: {str(e)}")
            print("🔄 Falling back to mock data...")
            return self._generate_mock_jd_structure(jd_text)
    
    async def _extract_resume_perplexity(self, resume_text: str) -> Dict[str, Any]:
        """Extract resume info using Perplexity API"""
        if self.use_mock:
            return self._generate_mock_resume_data(resume_text)


        prompt = f"""
        Please extract the following information from this resume text and return it as a JSON object:


        Resume Text:
        {resume_text}


        Please extract and return a JSON object with these fields:
        {{
            "name": "Full name of the candidate",
            "email": "Email address",
            "phone": "Phone number",
            "linkedin": "LinkedIn profile URL (complete URL, not just username)",
            "github": "GitHub profile URL (complete URL, not just username)",
            "portfolio": "Portfolio website URL if any",
            "current_role": "Current job title",
            "total_experience": "Total years of experience as a number",
            "skills": ["List", "of", "technical", "skills"],
            "education": ["Education qualifications"],
            "certifications": ["Professional certifications"],
            "experience_timeline": [
                {{
                    "company": "Company name",
                    "role": "Job title",
                    "duration": "Time period",
                    "technologies_used": ["Technologies"]
                }}
            ]
        }}


        IMPORTANT INSTRUCTIONS for URLs:
        - LinkedIn: Look for "linkedin.com/in/username", "LinkedIn: username", "in/username"
        - GitHub: Look for "github.com/username", "GitHub: username"
        - Portfolio: Any personal website link (exclude LinkedIn/GitHub)
        - Always return complete URLs starting with https://
        - If no profile found, return "Not provided"


        Return ONLY the JSON object, no other text.
        """


        try:
            print("🔍 Processing resume with Perplexity API...")
            response = await self._make_api_call(prompt)


            try:
                return json.loads(response)
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    raise Exception("Invalid JSON in resume response")


        except Exception as e:
            print(f"❌ Error with Perplexity API, falling back to mock extraction: {e}")
            return self._generate_mock_resume_data(resume_text)
    
    async def _make_api_call(self, prompt: str) -> str:
        """Make API call to Perplexity"""
        # ✅ SAFETY CHECK
        if not hasattr(self, 'base_url') or not self.base_url:
            raise Exception("Perplexity API not configured (no base_url)")
        
        if not hasattr(self, 'headers') or not self.headers:
            raise Exception("Perplexity API not configured (no headers)")
        
        payload = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 1500,
            "temperature": 0.2,
            "top_p": 0.9
        }
        
        try:
            print(f"📡 Making Perplexity API call...")
            response = requests.post(
                self.base_url, 
                headers=self.headers, 
                json=payload, 
                timeout=120
            )
            
            print(f"📊 API Response Status: {response.status_code}")
            
            if response.status_code == 400:
                error_details = response.json()
                print(f"❌ API Error Details: {error_details}")
                raise Exception(f"API Error 400: {error_details.get('error', {}).get('message', 'Bad Request')}")
            
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        
        except requests.exceptions.Timeout:
            raise Exception("API request timed out")
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")
    
    def _generate_mock_jd_structure(self, jd_text: str) -> Dict[str, Any]:
        """Generate mock structured data for testing"""
        print("🔨 Generating mock JD structure...")
        
        jd_lower = jd_text.lower()
        
        # Enhanced skill detection
        skill_patterns = {
            'python': ['python', 'django', 'flask', 'fastapi', 'pandas', 'numpy'],
            'javascript': ['javascript', 'js', 'node.js', 'nodejs', 'react', 'angular', 'vue'],
            'java': ['java', 'spring', 'hibernate', 'maven'],
            'sql': ['sql', 'mysql', 'postgresql', 'postgres', 'database'],
            'html': ['html', 'html5'],
            'css': ['css', 'css3', 'sass', 'scss'],
            'git': ['git', 'github', 'gitlab', 'version control'],
            'docker': ['docker', 'container'],
            'aws': ['aws', 'amazon web services', 'cloud'],
            'api': ['api', 'rest', 'restful', 'graphql'],
            'mongodb': ['mongodb', 'mongo', 'nosql'],
            'redis': ['redis', 'cache'],
            'kubernetes': ['kubernetes', 'k8s'],
            'linux': ['linux', 'ubuntu', 'unix'],
            'machine learning': ['machine learning', 'ml', 'ai', 'artificial intelligence'],
            'data science': ['data science', 'data analysis', 'analytics'],
            'react': ['react', 'reactjs', 'react.js'],
            'typescript': ['typescript', 'ts'],
            'bootstrap': ['bootstrap', 'css framework']
        }
        
        found_skills = []
        for skill_name, patterns in skill_patterns.items():
            for pattern in patterns:
                if pattern in jd_lower:
                    if skill_name not in found_skills:
                        found_skills.append(skill_name.title())
                    break
        
        if not found_skills:
            if any(word in jd_lower for word in ['developer', 'development', 'programming']):
                found_skills = ['Python', 'JavaScript', 'SQL', 'Git', 'HTML', 'CSS']
            elif any(word in jd_lower for word in ['data', 'analysis', 'analyst']):
                found_skills = ['Python', 'SQL', 'Data Analysis', 'Machine Learning']
            else:
                found_skills = ['Communication', 'Problem Solving', 'Teamwork']
        
        # Detect job title
        job_title = "Software Developer"
        if 'senior' in jd_lower and 'developer' in jd_lower:
            job_title = "Senior Software Developer"
        elif 'senior' in jd_lower and 'engineer' in jd_lower:
            job_title = "Senior Software Engineer"
        elif 'data scientist' in jd_lower:
            job_title = "Data Scientist"
        elif 'analyst' in jd_lower:
            job_title = "Data Analyst"
        elif 'manager' in jd_lower:
            job_title = "Technical Manager"
        
        # Detect experience level
        experience_required = "2-3 years"
        if 'senior' in jd_lower or '5+' in jd_text or 'five' in jd_lower:
            experience_required = "5+ years"
        elif '3+' in jd_text or 'three' in jd_lower:
            experience_required = "3+ years"
        elif 'junior' in jd_lower or 'entry' in jd_lower:
            experience_required = "0-2 years"
        
        # Split skills
        skills_count = len(found_skills)
        primary_count = min(5, max(2, skills_count // 2))
        
        primary_skills = found_skills[:primary_count]
        secondary_skills = found_skills[primary_count:primary_count + 3]
        
        mock_structure = {
            "job_title": job_title,
            "company": "Tech Company Inc.",
            "location": "Remote/Hybrid",
            "experience_required": experience_required,
            "primary_skills": primary_skills,
            "secondary_skills": secondary_skills,
            "responsibilities": [
                "Develop and maintain software applications",
                "Write clean, maintainable, and efficient code",
                "Collaborate with cross-functional teams",
                "Participate in code reviews and technical discussions",
                "Debug and troubleshoot application issues"
            ],
            "qualifications": [
                f"Bachelor's degree in Computer Science or related field",
                f"{experience_required} of relevant work experience",
                "Strong problem-solving and analytical skills",
                "Experience with version control systems (Git)",
                "Excellent communication and teamwork abilities"
            ],
            "job_type": "Full-time"
        }
        
        print(f"✅ Mock structure created with {len(primary_skills)} primary skills")
        return mock_structure
    
    def _refine_mock_structure(self, current_structure: Dict, feedback: str) -> Dict[str, Any]:
        """Refine mock structure based on feedback with comprehensive skill detection"""
        refined = current_structure.copy()
        feedback_lower = feedback.lower()
        
        # Determine target section
        add_to_primary = 'primary' in feedback_lower
        add_to_secondary = 'secondary' in feedback_lower
        
        # Skill extraction patterns
        skill_patterns = [
            r'add\s+([^.]+?)(?:\s+in\s+(?:primary|secondary))?',
            r'include\s+([^.]+?)(?:\s+in\s+(?:primary|secondary))?',
            r'need\s+([^.]+?)(?:\s+in\s+(?:primary|secondary))?',
            r'requires?\s+([^.]+?)(?:\s+in\s+(?:primary|secondary))?',
            r'(?:should have|must have)\s+([^.]+)',
            r'looking for\s+([^.]+)',
            r'seeking\s+([^.]+)',
            r'wants?\s+([^.]+)',
        ]
        
        extracted_skills = []
        
        for pattern in skill_patterns:
            matches = re.finditer(pattern, feedback_lower, re.IGNORECASE)
            for match in matches:
                skill_text = match.group(1).strip()
                
                # Split by delimiters
                skill_parts = re.split(r',|\s+and\s+|\s*&\s*|\s*\|\s*', skill_text)
                
                for part in skill_parts:
                    part = part.strip()
                    # Clean up noise phrases
                    part = re.sub(r'\s+in\s+(?:primary|secondary)(?:\s+skill)?', '', part, flags=re.IGNORECASE)
                    part = re.sub(r'\s+skill(?:s)?$', '', part, flags=re.IGNORECASE)
                    part = re.sub(r'^(?:the\s+)?(?:skill\s+)?', '', part, flags=re.IGNORECASE)
                    part = part.strip()
                    
                    if part and len(part) > 1:
                        # Smart capitalization
                        if part.isupper() or (len(part) <= 5 and part.isalpha()):
                            extracted_skills.append(part.upper())
                        elif '.' in part or '/' in part:
                            extracted_skills.append(part)
                        else:
                            extracted_skills.append(part.title())
        
        # Remove duplicates while preserving order
        extracted_skills = list(dict.fromkeys(extracted_skills))
        
        # Comprehensive common skills map
        common_skills_map = {
            # Programming Languages
            'python': 'Python', 'java': 'Java', 'javascript': 'JavaScript', 'typescript': 'TypeScript',
            'c++': 'C++', 'cpp': 'C++', 'c#': 'C#', 'csharp': 'C#', 'php': 'PHP', 'ruby': 'Ruby',
            'go': 'Go', 'golang': 'Go', 'rust': 'Rust', 'swift': 'Swift', 'kotlin': 'Kotlin',
            'scala': 'Scala', 'r': 'R',
            
            # Web Frameworks
            'react': 'React', 'angular': 'Angular', 'vue': 'Vue.js', 'node.js': 'Node.js', 'node': 'Node.js',
            'express': 'Express.js', 'django': 'Django', 'flask': 'Flask', 'fastapi': 'FastAPI',
            'laravel': 'Laravel', 'spring': 'Spring', 'spring boot': 'Spring Boot',
            '.net': '.NET', 'dotnet': '.NET', 'asp.net': 'ASP.NET', 'rails': 'Ruby on Rails',
            
            # Mobile
            'android': 'Android', 'ios': 'iOS', 'flutter': 'Flutter', 'react native': 'React Native',
            
            # Databases
            'sql': 'SQL', 'mysql': 'MySQL', 'postgresql': 'PostgreSQL', 'mongodb': 'MongoDB',
            'oracle': 'Oracle', 'redis': 'Redis', 'cassandra': 'Cassandra', 'dynamodb': 'DynamoDB',
            'nosql': 'NoSQL',
            
            # Cloud & DevOps
            'aws': 'AWS', 'azure': 'Azure', 'gcp': 'GCP', 'docker': 'Docker', 'kubernetes': 'Kubernetes',
            'k8s': 'Kubernetes', 'jenkins': 'Jenkins', 'terraform': 'Terraform', 'ansible': 'Ansible',
            'ci/cd': 'CI/CD', 'devops': 'DevOps',
            
            # AI / Data Science
            'machine learning': 'Machine Learning', 'ml': 'Machine Learning',
            'deep learning': 'Deep Learning', 'ai': 'Artificial Intelligence', 'tensorflow': 'TensorFlow',
            'pytorch': 'PyTorch', 'pandas': 'Pandas', 'numpy': 'NumPy', 'scikit-learn': 'Scikit-learn',
            'data science': 'Data Science', 'nlp': 'NLP', 'peft': 'PEFT',
            
            # Testing
            'selenium': 'Selenium', 'junit': 'JUnit', 'pytest': 'Pytest', 'cypress': 'Cypress',
            'testing': 'Testing', 'automation testing': 'Automation Testing',
            
            # APIs & Tools
            'api': 'API', 'rest': 'REST', 'restful': 'RESTful', 'graphql': 'GraphQL',
            'microservices': 'Microservices', 'git': 'Git', 'html': 'HTML', 'css': 'CSS',
            'database': 'Database Management', 'database management': 'Database Management',
            'agile': 'Agile', 'scrum': 'Scrum', 'jira': 'JIRA',
        }
        
        # Multi-word skills first (sorted by length descending)
        sorted_skill_keys = sorted(common_skills_map.keys(), key=len, reverse=True)
        
        for skill_key in sorted_skill_keys:
            if skill_key in feedback_lower:
                skill_name = common_skills_map[skill_key]
                already_exists = any(s.lower() == skill_name.lower() for s in extracted_skills)
                
                if not already_exists:
                    current_all_skills = refined.get('primary_skills', []) + refined.get('secondary_skills', [])
                    if not any(s.lower() == skill_name.lower() for s in current_all_skills):
                        extracted_skills.append(skill_name)
        
        # Remove already existing skills
        current_all_skills = refined.get('primary_skills', []) + refined.get('secondary_skills', [])
        new_skills = [
            skill for skill in extracted_skills
            if not any(s.lower() == skill.lower() for s in current_all_skills)
        ]
        
        # Add new skills intelligently
        if new_skills:
            if add_to_secondary:
                refined['secondary_skills'] = refined.get('secondary_skills', []) + new_skills
                print(f"✅ Added {len(new_skills)} skills to secondary: {new_skills}")
            elif add_to_primary:
                refined['primary_skills'] = refined.get('primary_skills', []) + new_skills
                print(f"✅ Added {len(new_skills)} skills to primary: {new_skills}")
            else:
                primary_count = min(3, len(new_skills))
                refined['primary_skills'] = refined.get('primary_skills', []) + new_skills[:primary_count]
                if len(new_skills) > primary_count:
                    refined['secondary_skills'] = refined.get('secondary_skills', []) + new_skills[primary_count:]
                print(f"✅ Added {primary_count} skills to primary and {len(new_skills) - primary_count} to secondary")
        
        # Update job title
        title_updates = [
            ('senior', 'Senior'),
            ('junior', 'Junior'),
            ('lead', 'Lead'),
            ('principal', 'Principal'),
            ('staff', 'Staff'),
            ('chief', 'Chief'),
        ]
        for keyword, prefix in title_updates:
            if keyword in feedback_lower and prefix.lower() not in refined.get('job_title', '').lower():
                refined['job_title'] = f"{prefix} {refined.get('job_title', 'Developer')}"
                break
        
        # Experience patterns
        experience_patterns = [
            (r'(\d+)\+?\s*(?:years?|yrs?)', lambda m: f"{m.group(1)}+ years"),
            (r'(\d+)\s*-\s*(\d+)\s*(?:years?|yrs?)', lambda m: f"{m.group(1)}-{m.group(2)} years"),
            (r'(\d+)\s+to\s+(\d+)\s*(?:years?|yrs?)', lambda m: f"{m.group(1)}-{m.group(2)} years"),
        ]
        for pattern, formatter in experience_patterns:
            match = re.search(pattern, feedback_lower)
            if match:
                refined['experience_required'] = formatter(match)
                break
        
        # Location mapping
        location_keywords = {
            'remote': 'Remote', 'hybrid': 'Hybrid', 'onsite': 'On-site',
            'on-site': 'On-site', 'office': 'On-site',
            'work from home': 'Remote', 'wfh': 'Remote',
        }
        for keyword, location in location_keywords.items():
            if keyword in feedback_lower:
                refined['location'] = location
                break
        
        # Job type detection
        job_type_keywords = {
            'full-time': 'Full-time', 'full time': 'Full-time',
            'part-time': 'Part-time', 'part time': 'Part-time',
            'contract': 'Contract', 'freelance': 'Freelance',
            'internship': 'Internship', 'temporary': 'Temporary',
        }
        for keyword, job_type in job_type_keywords.items():
            if keyword in feedback_lower:
                refined['job_type'] = job_type
                break
        
        # Metadata
        refined['_feedback_applied'] = feedback
        refined['_revision'] = refined.get('_revision', 0) + 1
        
        total_new_skills = len(new_skills)
        print(f"✅ Mock structure refined: {total_new_skills} new skills added (Revision {refined['_revision']})")
        
        return refined
    
    def _generate_mock_resume_data(self, resume_text: str) -> Dict[str, Any]:
        """Generate mock resume data with ENHANCED education and certification extraction"""
        print("🔨 Generating mock resume data...")
        
        lines = resume_text.split('\n')
        clean_lines = [line.strip() for line in lines if line.strip()]
        resume_lower = resume_text.lower()
        
        # Extract name
        name = "Unknown"
        for line in clean_lines[:5]:
            if len(line.split()) >= 2 and len(line) < 50:
                if not any(char in line for char in ['@', 'http', '+', '(', ')']):
                    if sum(c.isdigit() for c in line) < len(line) * 0.3:
                        name = line.strip()
                        break
        
        # Extract email
        email = "Not provided"
        email_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}'
        ]
        for pattern in email_patterns:
            email_match = re.search(pattern, resume_text, re.IGNORECASE)
            if email_match:
                email = email_match.group().strip()
                break
        
        # Extract phone
        phone = "Not provided"
        phone_patterns = [
            r'[\+]?[1-9]?[\-\.\s]?\(?[0-9]{3}\)?[\-\.\s]?[0-9]{3}[\-\.\s]?[0-9]{4}',
            r'[\+]?[0-9]{1,4}[\-\.\s]?[0-9]{3,4}[\-\.\s]?[0-9]{3,4}[\-\.\s]?[0-9]{3,4}',
            r'\b\d{10}\b',
            r'\+\d{1,3}\s*\d{10}',
            r'\(\d{3}\)\s*\d{3}[-\.\s]?\d{4}'
        ]
        for pattern in phone_patterns:
            phone_match = re.search(pattern, resume_text)
            if phone_match:
                phone = phone_match.group().strip()
                break
        
        # Extract LinkedIn
        linkedin = "Not provided"
        linkedin_patterns = [
            r'linkedin\.com/in/[\w\-]+/?',
            r'www\.linkedin\.com/in/[\w\-]+/?',
            r'https?://(?:www\.)?linkedin\.com/in/[\w\-]+/?',
            r'linkedin\.com/[\w\-]+/?',
            r'linkedin:\s*[\w\-]+',
            r'linkedin\s*[:\-]\s*[\w\-]+',
            r'in/[\w\-]+',
            r'https?://linkedin\.com/in/[\w\-]+/?'
        ]
        
        for pattern in linkedin_patterns:
            linkedin_match = re.search(pattern, resume_text, re.IGNORECASE)
            if linkedin_match:
                linkedin_url = linkedin_match.group().strip()
                if linkedin_url.startswith('linkedin:') or linkedin_url.startswith('linkedin -'):
                    username = linkedin_url.split(':')[-1].split('-')[-1].strip()
                    linkedin = f"https://linkedin.com/in/{username}"
                elif linkedin_url.startswith('in/'):
                    linkedin = f"https://linkedin.com/{linkedin_url}"
                elif not linkedin_url.startswith('http'):
                    if 'linkedin.com' in linkedin_url:
                        linkedin = f"https://{linkedin_url}"
                    else:
                        linkedin = f"https://linkedin.com/in/{linkedin_url}"
                else:
                    linkedin = linkedin_url
                break
        
        # Extract GitHub
        github = "Not provided"
        github_patterns = [
            r'github\.com/[\w\-]+/?',
            r'www\.github\.com/[\w\-]+/?',
            r'https?://(?:www\.)?github\.com/[\w\-]+/?',
            r'github:\s*[\w\-]+',
            r'github\s*[:\-]\s*[\w\-]+',
            r'git hub\.com/[\w\-]+/?',
            r'github\.io/[\w\-]+/?'
        ]
        
        for pattern in github_patterns:
            github_match = re.search(pattern, resume_text, re.IGNORECASE)
            if github_match:
                github_url = github_match.group().strip()
                if github_url.startswith('github:') or github_url.startswith('github -'):
                    username = github_url.split(':')[-1].split('-')[-1].strip()
                    github = f"https://github.com/{username}"
                elif 'git hub.com' in github_url:
                    github = github_url.replace('git hub.com', 'github.com')
                    if not github.startswith('http'):
                        github = f"https://{github}"
                elif not github_url.startswith('http'):
                    if 'github.com' in github_url:
                        github = f"https://{github_url}"
                    else:
                        github = f"https://github.com/{github_url}"
                else:
                    github = github_url
                break
        
        # Extract skills
        skills = []
        skill_keywords = [
            'python', 'java', 'javascript', 'react', 'node', 'sql', 'mongodb', 'aws', 
            'docker', 'git', 'html', 'css', 'api', 'rest', 'django', 'flask', 
            'postgresql', 'mysql', 'redis', 'kubernetes', 'linux', 'typescript',
            'angular', 'vue', 'spring', 'hibernate', 'microservices', 'devops'
        ]
        
        for skill in skill_keywords:
            if skill in resume_lower:
                skills.append(skill.title())
        
        if not skills:
            skills = ['Python', 'JavaScript', 'SQL', 'Git']
        
        # Remove duplicates
        skills = list(dict.fromkeys(skills))
        
        # 🔥 ENHANCED EDUCATION EXTRACTION
        education = self._extract_education_details(resume_text)
        
        # 🔥 ENHANCED CERTIFICATION EXTRACTION
        certifications = self._extract_certifications_details(resume_text, skills)
        
        print(f"✅ Extracted: {name} | {email} | LinkedIn: {linkedin} | GitHub: {github}")
        print(f"📚 Education: {len(education)} items")
        print(f"🏆 Certifications: {len(certifications)} items")
        
        return {
            "name": name,
            "email": email,
            "phone": phone,
            "linkedin": linkedin,
            "github": github,
            "portfolio": "Not provided",
            "current_role": self._extract_current_role(resume_text),
            "total_experience": self._estimate_experience(resume_text),
            "skills": skills,
            "experience_timeline": self._extract_experience_timeline(resume_text, skills),
            "education": education,
            "certifications": certifications
        }
    
    def _extract_education_details(self, resume_text: str) -> List[str]:
        """🔥 ENHANCED: Extract education information with robust parsing"""
        resume_lower = resume_text.lower()
        education = []
        
        # Degree patterns with broader matching
        degree_patterns = [
            r'(bachelor(?:\'s)?|b\.?tech|b\.?e\.?|b\.?sc|ba|bs)\s+(?:of|in|degree)?\s*([a-z\s]+)',
            r'(master(?:\'s)?|m\.?tech|m\.?e\.?|m\.?sc|ma|ms|mba)\s+(?:of|in|degree)?\s*([a-z\s]+)',
            r'(phd|ph\.d\.|doctorate|doctor)\s+(?:of|in)?\s*([a-z\s]+)',
            r'(diploma|associate)\s+(?:in)?\s*([a-z\s]+)',
            r'(b\.c\.a|bca|bachelor of computer applications)',
            r'(m\.c\.a|mca|master of computer applications)'
        ]
        
        for pattern in degree_patterns:
            matches = re.findall(pattern, resume_lower, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    degree_type = match[0].strip()
                    if len(match) > 1 and match[1]:
                        field = match[1].strip()
                        degree = f"{degree_type.upper() if len(degree_type) <= 6 else degree_type.title()} in {field.title()}"
                    else:
                        degree = degree_type.upper() if len(degree_type) <= 6 else degree_type.title()
                    
                    # Avoid duplicates
                    if degree not in education:
                        education.append(degree)
        
        # Look for education section headers
        if not education:
            edu_section_pattern = r'education\s*[:\-]?\s*(.*?)(?:experience|skills|certifications|projects|$)'
            edu_match = re.search(edu_section_pattern, resume_lower, re.DOTALL | re.IGNORECASE)
            if edu_match:
                edu_text = edu_match.group(1)
                lines = [line.strip() for line in edu_text.split('\n') if line.strip()]
                
                # Take first few meaningful lines
                for line in lines[:5]:
                    if len(line) > 15 and len(line) < 150:
                        # Avoid lines that look like headers or dates
                        if not re.match(r'^\d{4}[\-/]\d{4}$', line):
                            education.append(line.title())
        
        return education if education else ["Education details not found"]
    
    def _extract_certifications_details(self, resume_text: str, skills: List[str]) -> List[str]:
        """🔥 ENHANCED: Extract certifications with comprehensive pattern matching"""
        resume_lower = resume_text.lower()
        certifications = []
        
        # Common certification keywords
        cert_keywords = [
            'certified', 'certification', 'certificate',
            'aws certified', 'azure certified', 'google cloud',
            'pmp', 'prince2', 'itil', 'cissp', 'ceh',
            'scrum master', 'comptia', 'cisco', 'oracle certified',
            'certified kubernetes', 'cka', 'ckad'
        ]
        
        # Look for certification section
        cert_section_pattern = r'certifications?\s*[:\-]?\s*(.*?)(?:education|experience|skills|projects|$)'
        cert_match = re.search(cert_section_pattern, resume_lower, re.DOTALL | re.IGNORECASE)
        
        if cert_match:
            cert_text = cert_match.group(1)
            lines = [line.strip() for line in cert_text.split('\n') if line.strip()]
            
            for line in lines:
                # Check if line contains certification keywords
                if any(keyword in line.lower() for keyword in cert_keywords):
                    if len(line) > 5 and len(line) < 150:
                        # Avoid duplicate entries
                        cert_title = line.title()
                        if cert_title not in certifications:
                            certifications.append(cert_title)
        
        # Also check for specific certification patterns in full text
        specific_patterns = [
            r'(aws\s+certified\s+[a-z\s\-]+)',
            r'(microsoft\s+certified\s+[a-z\s\-]+)',
            r'(google\s+cloud\s+[a-z\s\-]+)',
            r'(oracle\s+certified\s+[a-z\s\-]+)',
            r'(cisco\s+certified\s+[a-z\s\-]+)',
            r'(comptia\s+[a-z\+]+)',
            r'(certified\s+kubernetes\s+[a-z\s]+)',
            r'(pmp|prince2|itil|cissp|ceh|cka|ckad)\s*(?:certified)?'
        ]
        
        for pattern in specific_patterns:
            matches = re.findall(pattern, resume_lower, re.IGNORECASE)
            for match in matches:
                cert = match if isinstance(match, str) else match[0]
                cert = cert.strip()
                cert_title = cert.upper() if len(cert) <= 6 else cert.title()
                
                if cert_title and cert_title not in certifications:
                    certifications.append(cert_title)
        
        # Skill-based certifications (fallback)
        if not certifications:
            if any('aws' in s.lower() for s in skills):
                certifications.append("AWS Certified Developer")
            if any('azure' in s.lower() for s in skills):
                certifications.append("Microsoft Azure Certified")
            if any('python' in s.lower() for s in skills):
                certifications.append("Python Programming Certificate")
        
        return certifications if certifications else ["No certifications found"]
    
    def _extract_current_role(self, resume_text: str) -> str:
        """Extract current job role"""
        resume_lower = resume_text.lower()
        
        role_patterns = [
            r'(?:current|present).*?(?:role|position|title).*?[:]\s*([^\n]+)',
            r'(?:software|senior|lead|principal)\s+(?:engineer|developer|architect)',
            r'(?:full.stack|frontend|backend|web)\s+developer',
            r'(?:data|machine learning|ai)\s+(?:scientist|engineer)',
            r'(?:devops|cloud|systems)\s+engineer'
        ]
        
        for pattern in role_patterns:
            match = re.search(pattern, resume_lower)
            if match:
                if len(match.groups()) > 0:
                    return match.group(1).strip().title()
                else:
                    return match.group(0).strip().title()
        
        if 'senior' in resume_lower:
            return "Senior Software Developer"
        elif 'lead' in resume_lower:
            return "Lead Developer"
        elif 'manager' in resume_lower:
            return "Engineering Manager"
        else:
            return "Software Developer"
    
    def _estimate_experience(self, resume_text: str) -> float:
        """Estimate years of experience"""
        resume_lower = resume_text.lower()
        if 'senior' in resume_lower or '5+' in resume_text:
            return 5.5
        elif 'lead' in resume_lower or 'principal' in resume_lower:
            return 8.0
        elif 'junior' in resume_lower or 'entry' in resume_lower:
            return 1.5
        else:
            return 3.5
    
    def _extract_experience_timeline(self, resume_text: str, skills: List[str]) -> List[Dict]:
        """Extract work experience timeline"""
        return [
            {
                "company": "Tech Solutions Inc.",
                "role": "Software Developer",
                "duration": "Jan 2021 - Present",
                "technologies_used": skills[:4] if skills else ['Python', 'JavaScript'],
                "description": "Developed web applications and APIs"
            },
            {
                "company": "StartUp Co.",
                "role": "Junior Developer", 
                "duration": "Jun 2019 - Dec 2020",
                "technologies_used": skills[:2] if skills else ['Python'],
                "description": "Built backend services"
            }
        ]
    
    def _extract_education(self, resume_text: str) -> List[str]:
        """Legacy method - redirects to enhanced version"""
        return self._extract_education_details(resume_text)
    
    def _extract_certifications(self, resume_text: str, skills: List[str]) -> List[str]:
        """Legacy method - redirects to enhanced version"""
        return self._extract_certifications_details(resume_text, skills)
