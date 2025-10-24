import requests
import json
import re
from typing import Dict, Any, List
from backend.app.config import settings


class OllamaService:
    """
    Service for interacting with Ollama inference endpoint
    """
    
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip('/')
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT
        
        # Verify configuration
        if not self.base_url or self.base_url == "":
            raise ValueError("OLLAMA_BASE_URL not configured in .env")
        
        if not self.model:
            raise ValueError("OLLAMA_MODEL not configured in .env")
        
        print(f"✅ OllamaService initialized: {self.base_url} | Model: {self.model}")
    
    def _make_request(self, prompt: str, system_prompt: str = None, temperature: float = 0.2) -> str:
        """
        Make a request to Ollama inference endpoint
        
        Args:
            prompt: User prompt
            system_prompt: Optional system instruction
            temperature: Sampling temperature (0.0 - 1.0)
        
        Returns:
            Generated text response
        """
        try:
            # Prepare payload
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "top_p": 0.9,
                    "top_k": 40
                }
            }
            
            # Add system prompt if provided
            if system_prompt:
                payload["system"] = system_prompt
            
            print(f"📡 Ollama Request to {self.base_url}/api/generate")
            print(f"   Model: {self.model}")
            print(f"   Prompt Length: {len(prompt)} chars")
            
            # Make request
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract response text
            generated_text = result.get("response", "")
            
            if not generated_text:
                raise ValueError("Empty response from Ollama")
            
            print(f"✅ Ollama Response: {len(generated_text)} chars")
            
            return generated_text.strip()
        
        except requests.exceptions.Timeout:
            raise Exception(f"Ollama request timeout after {self.timeout}s")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Cannot connect to Ollama at {self.base_url}")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"Ollama HTTP error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"Ollama request failed: {str(e)}")
    
    def structure_job_description(self, jd_text: str) -> Dict[str, Any]:
        """
        Extract structured data from job description
        """
        print("🔍 Structuring Job Description with Ollama...")
        
        system_prompt = """You are an expert HR assistant specializing in analyzing job descriptions. 
Extract information and return ONLY valid JSON with no extra text."""
        
        prompt = f"""Analyze this job description and extract information into JSON format.

Required JSON structure:
{{
    "job_title": "string",
    "company": "string or 'Not specified'",
    "location": "string or 'Not specified'",
    "experience_required": "string (e.g., '3-5 years')",
    "primary_skills": ["skill1", "skill2", ...],
    "secondary_skills": ["skill1", "skill2", ...],
    "responsibilities": ["resp1", "resp2", ...],
    "qualifications": ["qual1", "qual2", ...],
    "job_type": "Full-time|Part-time|Contract|etc"
}}

Job Description:
{jd_text[:2000]}

Return ONLY the JSON object, no explanations.
"""
        
        response = self._make_request(prompt, system_prompt, temperature=0.1)
        
        # Parse JSON from response
        return self._parse_json_response(response, "job description")
    
    def extract_resume_information(self, resume_text: str) -> Dict[str, Any]:
        """
        Extract structured data from resume
        """
        print("🔍 Extracting Resume Information with Ollama...")
        
        system_prompt = """You are an expert resume parser. Extract information accurately and return ONLY valid JSON."""
        
        prompt = f"""Extract resume information and return as JSON.

Required JSON structure:
{{
    "name": "Full name",
    "email": "email@example.com",
    "phone": "phone number",
    "linkedin": "LinkedIn URL or 'Not provided'",
    "github": "GitHub URL or 'Not provided'",
    "portfolio": "Portfolio URL or 'Not provided'",
    "current_role": "Current job title",
    "total_experience": 0,
    "skills": ["skill1", "skill2", "skill3"],
    "education": ["degree1", "degree2"],
    "certifications": ["cert1", "cert2"],
    "experience_timeline": [
        {{
            "company": "Company name",
            "role": "Job title",
            "duration": "Time period",
            "technologies_used": ["tech1", "tech2"]
        }}
    ]
}}

IMPORTANT:
- skills MUST be an array of strings
- Extract ALL technical skills
- total_experience must be a number (years)

Resume Text:
{resume_text[:2000]}

Return ONLY valid JSON.
"""
        
        response = self._make_request(prompt, system_prompt, temperature=0.1)
        
        # Parse and normalize
        parsed = self._parse_json_response(response, "resume")
        
        # Ensure skills is an array
        if 'skills' in parsed:
            if isinstance(parsed['skills'], dict):
                parsed['skills'] = list(parsed['skills'].values())
            elif isinstance(parsed['skills'], str):
                parsed['skills'] = [s.strip() for s in parsed['skills'].split(',') if s.strip()]
            elif not isinstance(parsed['skills'], list):
                parsed['skills'] = []
        else:
            parsed['skills'] = []
        
        return parsed
    
    def refine_structure_based_on_feedback(self, current_structure: Dict, feedback: str) -> Dict[str, Any]:
        """
        Refine JD structure based on user feedback
        """
        print(f"🔧 Refining structure with Ollama based on feedback...")
        
        system_prompt = """You are an expert at refining job descriptions based on feedback. 
Apply changes precisely and return ONLY the updated JSON."""
        
        prompt = f"""Refine this job description structure based on user feedback.

Current Structure:
{json.dumps(current_structure, indent=2)}

User Feedback:
"{feedback}"

Instructions:
1. Apply the requested changes precisely
2. Preserve all other fields unchanged
3. Maintain the exact JSON structure
4. Return ONLY valid JSON

Return the updated structure:
"""
        
        response = self._make_request(prompt, system_prompt, temperature=0.1)
        
        return self._parse_json_response(response, "refinement")
    
    def _parse_json_response(self, response: str, operation: str) -> Dict[str, Any]:
        """
        Extract and parse JSON from Ollama response
        """
        try:
            # Try direct parsing first
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                pass
            
            # Extract from markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # Look for JSON object anywhere
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
            print(f"Could not extract JSON from response")
            print(f"Response preview: {response[:200]}")
            
            return {"error": f"Failed to parse {operation}", "raw_response": response[:500]}
        
        except Exception as e:
            print(f"Parse error in {operation}: {str(e)}")
            return {"error": f"Failed to parse {operation}", "exception": str(e)}
    
    def health_check(self) -> bool:
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
        
            if response.status_code == 200:
                print(f"Ollama service is healthy")
                return True
            else:
                print(f"Ollama service returned status {response.status_code}")
                return False
    
        except Exception as e:
            print(f"Ollama health check failed: {str(e)}")
            return False


# Singleton instance
_ollama_service = None

def get_ollama_service() -> OllamaService:
    
    # Get or create OllamaService singleton

    global _ollama_service
    if _ollama_service is None:
        _ollama_service = OllamaService()
    return _ollama_service