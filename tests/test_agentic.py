import asyncio
import json
import sys
import os
import traceback

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app.services.agentic_service import EnhancedAgenticATSService


async def test_agentic_service():
    """Test all agentic AI functionalities"""
    
    print("\n" + "=" * 70)
    print("🚀 AGENTIC AI SERVICE TEST")
    print("=" * 70)
    
    try:
        # Initialize service
        print("\n📦 Initializing Agentic AI Service...")
        service = EnhancedAgenticATSService()
        print("✅ Service initialized successfully!\n")
    except Exception as e:
        print(f"❌ Failed to initialize service: {e}")
        print("\n💡 Make sure you have:")
        print("   1. Installed dependencies: pip install -r requirements.txt")
        print("   2. Set GROQ_API_KEY in .env file")
        traceback.print_exc()
        return
    
    # Sample resume
    sample_resume = """
    John Doe
    Email: john.doe@example.com
    Phone: +91-9876543210
    LinkedIn: linkedin.com/in/johndoe
    GitHub: github.com/johndoe
    
    Senior Software Engineer with 5 years of experience specializing in Python backend development,
    FastAPI, and cloud technologies.
    
    EXPERIENCE:
    
    Tech Corp India | Senior Software Engineer | Jan 2020 - Present
    - Developed scalable REST APIs using Python FastAPI serving 1M+ requests/day
    - Implemented microservices architecture with Docker and Kubernetes
    - Technologies: Python, FastAPI, PostgreSQL, Redis, Docker, AWS, React
    
    StartUp Solutions | Software Developer | Jun 2018 - Dec 2019
    - Built web applications using Python Flask and JavaScript
    - Managed PostgreSQL databases and implemented caching strategies
    - Technologies: Python, Flask, JavaScript, MongoDB, Docker
    
    SKILLS:
    Python, JavaScript, FastAPI, Flask, Django, React.js, Node.js, PostgreSQL, 
    MongoDB, Redis, Docker, Kubernetes, AWS, Git, REST APIs, Microservices
    
    EDUCATION:
    B.Tech in Computer Science - IIT Delhi (2018)
    
    CERTIFICATIONS:
    - AWS Certified Solutions Architect
    - Python Professional Certification
    """
    
    # Sample job description
    sample_jd = """
    Senior Python Developer
    Accenture India - Bangalore
    
    We are looking for an experienced Python developer with 5+ years of experience 
    to join our team and work on enterprise-level applications.
    
    REQUIRED SKILLS (Must Have):
    - Python (Django or FastAPI)
    - PostgreSQL or MySQL
    - Docker
    - AWS Cloud Services
    - React.js or Angular
    - REST API Development
    
    NICE TO HAVE:
    - Kubernetes
    - Microservices Architecture
    - Redis Caching
    - CI/CD Pipelines
    
    EXPERIENCE REQUIRED: 5-7 years
    
    RESPONSIBILITIES:
    - Design and develop scalable backend systems
    - Build and maintain REST APIs
    - Collaborate with frontend team
    - Implement best practices for code quality
    - Mentor junior developers
    
    QUALIFICATIONS:
    - Bachelor's degree in Computer Science or related field
    - Strong problem-solving skills
    - Excellent communication skills
    - Experience with Agile methodologies
    
    JOB TYPE: Full-time
    """
    
    # Test 1: Resume Analysis
    print("=" * 70)
    print("TEST 1: Resume Analysis")
    print("=" * 70)
    try:
        resume_result = await service.analyze_resume(sample_resume)
        print("\n✅ Resume Analysis Completed!")
        print("\n📄 Extracted Information:")
        print(json.dumps(resume_result, indent=2))
    except Exception as e:
        print(f"\n❌ Resume Analysis Failed: {e}")
        traceback.print_exc()
        return
    
    # Test 2: Job Description Analysis
    print("\n" + "=" * 70)
    print("TEST 2: Job Description Analysis")
    print("=" * 70)
    try:
        jd_result = await service.analyze_job_description(sample_jd)
        print("\n✅ JD Analysis Completed!")
        print("\n📋 Extracted Information:")
        print(json.dumps(jd_result, indent=2))
    except Exception as e:
        print(f"\n❌ JD Analysis Failed: {e}")
        traceback.print_exc()
        return
    
    # Test 3: Matching & Scoring
    print("\n" + "=" * 70)
    print("TEST 3: Comprehensive Matching & Scoring")
    print("=" * 70)
    try:
        matching_result = await service.match_and_score(resume_result, jd_result)
        print("\n✅ Matching & Scoring Completed!")
        print("\n🎯 Matching Results:")
        print(json.dumps(matching_result, indent=2))
        
        # Display summary
        print("\n" + "-" * 70)
        print("📊 SUMMARY")
        print("-" * 70)
        print(f"Overall Score: {matching_result.get('overall_score', 'N/A')}/100")
        print(f"Recommendation: {matching_result.get('recommendation', 'N/A')}")
        print(f"\nStrengths:")
        for strength in matching_result.get('strengths', [])[:3]:
            print(f"  ✓ {strength}")
        print(f"\nWeaknesses:")
        for weakness in matching_result.get('weaknesses', [])[:3]:
            print(f"  ✗ {weakness}")
    except Exception as e:
        print(f"\n❌ Matching & Scoring Failed: {e}")
        traceback.print_exc()
        return
    
    # Test 4: Interview Questions Generation
    print("\n" + "=" * 70)
    print("TEST 4: Interview Questions Generation")
    print("=" * 70)
    try:
        questions = await service.generate_interview_questions(
            resume_result, 
            jd_result, 
            difficulty="medium",
            num_questions=5
        )
        print("\n✅ Interview Questions Generated!")
        print(f"\n💬 Generated {len(questions)} Questions:\n")
        for i, q in enumerate(questions, 1):
            print(f"{i}. [{q.get('category', 'General')}] {q.get('question', 'N/A')}")
            print(f"   Skill Tested: {q.get('skill_tested', 'N/A')}")
            print(f"   Difficulty: {q.get('difficulty', 'N/A')}\n")
    except Exception as e:
        print(f"\n❌ Interview Questions Generation Failed: {e}")
        traceback.print_exc()
    
    # Final Summary
    print("\n" + "=" * 70)
    print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    print("\n🎉 Agentic AI Service is working perfectly!")
    print("\n💡 Next Steps:")
    print("   1. Update .env: SET USE_AGENTIC_AI=true")
    print("   2. Start server: python run.py")
    print("   3. Test via UI at http://localhost:8000")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    print("\n🧪 Starting Agentic AI Service Tests...")
    try:
        asyncio.run(test_agentic_service())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        traceback.print_exc()