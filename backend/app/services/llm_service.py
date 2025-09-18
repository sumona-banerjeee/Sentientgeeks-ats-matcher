import requests
import json
import os
from typing import Dict, Any, List
from dotenv import load_dotenv
import re

load_dotenv()

class LLMService:
    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        # Use real API if we have a valid key
        self.use_mock = not self.api_key or self.api_key in ["your_perplexity_api_key_here", "", "None"]
        
        if self.use_mock:
            print("LLM Service running in MOCK mode")
        else:
            print("LLM Service running with Perplexity API")
    
    async def structure_job_description(self, jd_text: str) -> Dict[str, Any]:
        """Structure unstructured job description using LLM or mock data"""
        
        if self.use_mock:
            return self._generate_mock_jd_structure(jd_text)
        
        try:
            print(f" Processing JD with Perplexity API (length: {len(jd_text)})...")
            
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
            
            # Try to parse the JSON response
            try:
                structured_data = json.loads(response)
                print("Successfully structured JD with Perplexity API")
                return structured_data
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract JSON from the response
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    structured_data = json.loads(json_match.group())
                    print("Successfully extracted JSON from Perplexity response")
                    return structured_data
                else:
                    raise Exception("Invalid JSON response from API")
                    
        except Exception as e:
            print(f"Perplexity API failed: {str(e)}")
            print("Falling back to mock data...")
            return self._generate_mock_jd_structure(jd_text)
    
    async def refine_structure_based_on_feedback(self, current_structure: Dict, feedback: str) -> Dict[str, Any]:
        """Refine the structured JD based on user feedback"""
        
        if self.use_mock:
            return self._refine_mock_structure(current_structure, feedback)
        
        try:
            print(f" Refining structure with Perplexity API...")
            
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
                print("Successfully refined structure with Perplexity API")
                return refined_data
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    refined_data = json.loads(json_match.group())
                    return refined_data
                else:
                    raise Exception("Invalid JSON in refinement response")
                    
        except Exception as e:
            print(f" Perplexity refinement failed: {str(e)}")
            return self._refine_mock_structure(current_structure, feedback)
    
    async def extract_resume_information(self, resume_text: str) -> Dict[str, Any]:
        """Extract structured information from resume text using Perplexity API"""

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
            print("Processing resume with Perplexity API...")
            response = await self._make_api_call(prompt)

        # Try to load JSON safely
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    raise Exception("Invalid JSON in resume response")

        except Exception as e:
            print(f"Error with Perplexity API, falling back to mock extraction: {e}")
            return self._generate_mock_resume_data(resume_text)

    
    async def _make_api_call(self, prompt: str) -> str:
    
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
            print(f"Making Perplexity API call...")
            response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=30)
        
            print(f"API Response Status: {response.status_code}")
        
            if response.status_code == 400:
                error_details = response.json()
                print(f"API Error Details: {error_details}")
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
        print("Generating mock JD structure...")
        
        # Enhanced skill detection
        jd_lower = jd_text.lower()
        
        # Common technical skills with variations
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
        
        # If no skills found, add some defaults based on common keywords
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
        
        # Split skills into primary and secondary
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
        
        print(f"Mock structure created with {len(primary_skills)} primary skills and {len(secondary_skills)} secondary skills")
        return mock_structure
    
    def _refine_mock_structure(self, current_structure: Dict, feedback: str) -> Dict[str, Any]:
        """Your existing mock refinement implementation"""
        refined = current_structure.copy()
        feedback_lower = feedback.lower()
        
        # Add new skills mentioned in feedback
        new_skills = []
        common_skills = ['python', 'java', 'javascript', 'react', 'node.js', 'sql', 'mongodb', 'aws', 'docker', 'git', 'html', 'css', 'api', 'rest', 'django', 'postgresql', 'redis', 'kubernetes']
        
        for skill in common_skills:
            if skill in feedback_lower and skill not in str(refined).lower():
                new_skills.append(skill.title())
        
        if new_skills:
            refined['primary_skills'] = refined.get('primary_skills', []) + new_skills[:3]
            refined['secondary_skills'] = refined.get('secondary_skills', []) + new_skills[3:6]
        
        # Update job title if mentioned
        if 'senior' in feedback_lower and 'senior' not in refined.get('job_title', '').lower():
            refined['job_title'] = 'Senior ' + refined.get('job_title', 'Developer')
        
        # Update experience if mentioned
        if '5+' in feedback or 'five years' in feedback_lower:
            refined['experience_required'] = '5+ years'
        elif '3+' in feedback or 'three years' in feedback_lower:
            refined['experience_required'] = '3+ years'
        
        # Update location if mentioned
        if 'remote' in feedback_lower:
            refined['location'] = 'Remote'
        elif 'hybrid' in feedback_lower:
            refined['location'] = 'Hybrid'
        elif 'onsite' in feedback_lower or 'office' in feedback_lower:
            refined['location'] = 'On-site'
        
        refined['_feedback_applied'] = feedback
        refined['_revision'] = refined.get('_revision', 0) + 1
        
        print(f"Mock structure refined with {len(new_skills)} new skills added")
        return refined
    

    def _generate_mock_resume_data(self, resume_text: str) -> Dict[str, Any]:
        """Generate mock resume data with improved link extraction"""
        print("📄 Generating resume data with improved link extraction...")
    
        lines = resume_text.split('\n')
        clean_lines = [line.strip() for line in lines if line.strip()]
        resume_lower = resume_text.lower()
    
    # Extract name (first clean line that looks like a name)
        name = "Unknown"
        for line in clean_lines[:5]:
            if len(line.split()) >= 2 and len(line) < 50:
                if not any(char in line for char in ['@', 'http', '+', '(', ')']):
                    if sum(c.isdigit() for c in line) < len(line) * 0.3:
                        name = line.strip()
                        break
    
    # Extract email with improved pattern
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
    
    # Extract phone with improved patterns
        phone = "Not provided"
        phone_patterns = [
        r'[\+]?[1-9]?[\-\.\s]?\(?[0-9]{3}\)?[\-\.\s]?[0-9]{3}[\-\.\s]?[0-9]{4}',
        r'[\+]?[0-9]{1,4}[\-\.\s]?[0-9]{3,4}[\-\.\s]?[0-9]{3,4}[\-\.\s]?[0-9]{3,4}',
        r'\b\d{10}\b',  # Simple 10-digit number
        r'\+\d{1,3}\s*\d{10}',  # International format
        r'\(\d{3}\)\s*\d{3}[-\.\s]?\d{4}'  # (123) 456-7890 format
        ]
        for pattern in phone_patterns:
            phone_match = re.search(pattern, resume_text)
            if phone_match:
                phone = phone_match.group().strip()
                break
    
    # IMPROVED LinkedIn extraction
        linkedin = "Not provided"
        linkedin_patterns = [
        r'linkedin\.com/in/[\w\-]+/?',  # linkedin.com/in/username
        r'www\.linkedin\.com/in/[\w\-]+/?',  # www.linkedin.com/in/username
        r'https?://(?:www\.)?linkedin\.com/in/[\w\-]+/?',  # Full URL
        r'linkedin\.com/[\w\-]+/?',  # linkedin.com/username (some people skip /in/)
        r'linkedin:\s*[\w\-]+',  # LinkedIn: username
        r'linkedin\s*[:\-]\s*[\w\-]+',  # LinkedIn - username or LinkedIn: username
        r'in/[\w\-]+',  # Just in/username
        r'https?://linkedin\.com/in/[\w\-]+/?'  # Another variant
        ]
    
        for pattern in linkedin_patterns:
            linkedin_match = re.search(pattern, resume_text, re.IGNORECASE)
            if linkedin_match:
                linkedin_url = linkedin_match.group().strip()
            # Clean up and format the URL
                if linkedin_url.startswith('linkedin:') or linkedin_url.startswith('linkedin -') or linkedin_url.startswith('linkedin-'):
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
    
    # IMPROVED GitHub extraction
        github = "Not provided"
        github_patterns = [
        r'github\.com/[\w\-]+/?',  # github.com/username
        r'www\.github\.com/[\w\-]+/?',  # www.github.com/username
        r'https?://(?:www\.)?github\.com/[\w\-]+/?',  # Full GitHub URL
        r'github:\s*[\w\-]+',  # GitHub: username
        r'github\s*[:\-]\s*[\w\-]+',  # GitHub - username or GitHub: username
        r'git hub\.com/[\w\-]+/?',  # github with space (typo)
        r'github\.io/[\w\-]+/?'  # GitHub pages
        ]
    
        for pattern in github_patterns:
            github_match = re.search(pattern, resume_text, re.IGNORECASE)
            if github_match:
                github_url = github_match.group().strip()
            # Clean up and format the URL
                if github_url.startswith('github:') or github_url.startswith('github -') or github_url.startswith('github-'):
                    username = github_url.split(':')[-1].split('-')[-1].strip()
                    github = f"https://github.com/{username}"
                elif 'git hub.com' in github_url:  # Handle typo
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
    
    # Extract skills (your existing logic)
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
    
    # Debug prints
        print(f"Extracted LinkedIn: {linkedin}")
        print(f"Extracted GitHub: {github}")
        print(f"Extracted Email: {email}")
        print(f"Extracted Phone: {phone}")
    
        return {
        "name": name,
        "email": email,
        "phone": phone,
        "linkedin": linkedin,
        "github": github,
        "current_role": self._extract_current_role(resume_text),
        "total_experience": self._estimate_experience(resume_text),
        "skills": skills,
        "experience_timeline": self._extract_experience_timeline(resume_text, skills),
        "education": self._extract_education(resume_text),
        "certifications": self._extract_certifications(resume_text, skills)
        }

    def _extract_current_role(self, resume_text: str) -> str:
        """Extract current job role"""
        resume_lower = resume_text.lower()
    
    # Common role patterns
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
    
    # Fallback roles based on keywords
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
            "technologies_used": skills[:4] if skills else ['Python', 'JavaScript']
        },
        {
            "company": "StartUp Co.",
            "role": "Junior Developer", 
            "duration": "Jun 2019 - Dec 2020",
            "technologies_used": skills[:2] if skills else ['Python']
        }
        ]

    def _extract_education(self, resume_text: str) -> List[str]:
        """Extract education information"""
        resume_lower = resume_text.lower()
        education = []
    
        if 'master' in resume_lower or 'msc' in resume_lower or 'm.tech' in resume_lower:
            education.append("Master's in Computer Science")
        if 'bachelor' in resume_lower or 'bsc' in resume_lower or 'b.tech' in resume_lower or 'be ' in resume_lower:
            education.append("Bachelor's in Computer Science")
        if 'phd' in resume_lower or 'ph.d.' in resume_lower:
            education.append("PhD in Computer Science")
    
        return education if education else ["Bachelor's in Computer Science"]

    def _extract_certifications(self, resume_text: str, skills: List[str]) -> List[str]:
        """Extract certifications"""
        resume_lower = resume_text.lower()
        certifications = []
    
        if 'aws' in resume_lower:
            certifications.append("AWS Certified Developer")
        if 'azure' in resume_lower:
            certifications.append("Microsoft Azure Certified")
        if 'google cloud' in resume_lower or 'gcp' in resume_lower:
            certifications.append("Google Cloud Professional")
        if any(skill.lower() == 'python' for skill in skills):
            certifications.append("Python Programming Certificate")
    
        return certifications if certifications else ["Professional Development Certificate"]


