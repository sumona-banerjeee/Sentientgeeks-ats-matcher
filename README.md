# SentientGeeks ATS Resume Matcher

An AI-powered **Applicant Tracking System (ATS)** that matches resumes against job descriptions, ranks candidates based on skills and experience, and provides structured insights for recruiters.  

🚀 Built with **FastAPI (backend)** + **Vanilla JavaScript (frontend)**.

---

## ✨ Features
- 📄 **Job Description Processing** – Upload JD as text or PDF, auto-structured into title, skills, qualifications, and responsibilities.  
- ✅ **JD Review & Approval** – Approve or request changes before proceeding.  
- 🎯 **Skills Weightage** – Assign priority (1–100) to required skills.  
- 📂 **Resume Upload** – Upload up to **50 resumes (PDFs)** at once with validation.  
- 🤖 **AI Resume Parsing** – Extracts candidate name, skills, and total experience.  
- 📊 **ATS Matching** – Generates candidate ranking with overall and skill match scores.  
- 🔍 **Candidate Details Modal** – View detailed candidate analysis, education, and certifications.  
- 📥 **Export Results** – Download candidate rankings in CSV or JSON.  

---

## 🛠️ Tech Stack
- **Backend**: FastAPI + Uvicorn  
- **Frontend**: HTML, CSS, Vanilla JavaScript  
- **Database**: SQLite (dev mode, easy to swap for production)  
- **Parsing**: PyMuPDF + NLP-based extraction  
- **Deployment**: Local with Uvicorn (dev), ready for Docker/production  
"# Sentientgeeks-ats-matcher" 
