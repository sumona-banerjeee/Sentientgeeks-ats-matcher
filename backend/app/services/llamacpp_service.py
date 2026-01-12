"""
llama.cpp Server Service (OpenAI-Compatible API)
Integrates with llama.cpp server using OpenAI Python client
"""

import json
import re
from typing import Dict, Any, List
from openai import OpenAI
from backend.app.config import settings


class LlamaCppService:
    """
    Service for interacting with llama.cpp server via OpenAI-compatible API
    """
    
    def __init__(self):
        # Verify configuration
        if not settings.LLAMACPP_BASE_URL:
            raise ValueError("LLAMACPP_BASE_URL not configured in .env")
        
        if not settings.LLAMACPP_MODEL:
            raise ValueError("LLAMACPP_MODEL not configured in .env")
        
        # Initialize OpenAI client pointing to llama.cpp server
        self.client = OpenAI(
            base_url=settings.LLAMACPP_BASE_URL,
            api_key=settings.LLAMACPP_API_KEY,
            timeout=settings.LLAMACPP_TIMEOUT
        )
        
        self.model = settings.LLAMACPP_MODEL
        
        print(f"LlamaCppService initialized")
        print(f"   Base URL: {settings.LLAMACPP_BASE_URL}")
        print(f"   Model: {self.model}")
    
    def _make_request(
        self, 
        prompt: str, 
        system_prompt: str = None, 
        temperature: float = 0.2,
        enable_thinking: bool = False
    ) -> str:
        """
        Make a request to llama.cpp server
        
        Args:
            prompt: User prompt
            system_prompt: Optional system instruction
            temperature: Sampling temperature (0.0 - 1.0)
            enable_thinking: Enable model thinking mode
        
        Returns:
            Generated text response
        """
        try:
            # Prepare messages
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({"role": "user", "content": prompt})
            
            print(f"llama.cpp Request")
            print(f"   Model: {self.model}")
            print(f"   Prompt Length: {len(prompt)} chars")
            
            # Make request with optional chat_template_kwargs
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 1500
            }
            
            # Add thinking mode if supported
            if hasattr(self.client, 'with_options'):
                kwargs["extra_body"] = {
                    "chat_template_kwargs": {"enable_thinking": enable_thinking}
                }
            
            completion = self.client.chat.completions.create(**kwargs)
            
            # Extract response
            full_text = completion.choices[0].message.content
            
            # Clean response (strip thinking preamble if exists)
            if "Provide answer." in full_text:
                final_answer = full_text.split("Provide answer.")[-1].strip()
            else:
                final_answer = full_text
            
            print(f"llama.cpp Response: {len(final_answer)} chars")
            
            return final_answer.strip()
        
        except Exception as e:
            raise Exception(f"llama.cpp request failed: {str(e)}")
    
    def structure_job_description(self, jd_text: str) -> Dict[str, Any]:
        """
        Extract structured data from job description
        """
        print(" Structuring Job Description with llama.cpp...")
        
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
        print("Extracting Resume Information with llama.cpp...")
        
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
        print(f"Refining structure with llama.cpp based on feedback...")
        
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
        Extract and parse JSON from llama.cpp response
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
        """Check if llama.cpp server is accessible"""
        try:
            response = self._make_request("Hello, are you working?", temperature=0.1)
            return bool(response and len(response) > 0)
        except Exception as e:
            print(f"llama.cpp health check failed: {str(e)}")
            return False


# Singleton instance
_llamacpp_service = None

def get_llamacpp_service() -> LlamaCppService:
    """Get or create LlamaCppService singleton"""
    global _llamacpp_service
    if _llamacpp_service is None:
        _llamacpp_service = LlamaCppService()
    return _llamacpp_service
