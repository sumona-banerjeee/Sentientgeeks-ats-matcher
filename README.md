## SentientGeeks ATS Resume Matcher

An AI-powered **Applicant Tracking System (ATS)** that matches resumes against job descriptions, ranks candidates based on skills and experience, and provides structured insights for recruiters.

Built with **FastAPI (Backend)** and **Vanilla JavaScript (Frontend)**.

---

## Features

- **Job Description Processing**  
  Upload JD as text or PDF. Automatically extracts and structures information into title, skills, qualifications, and responsibilities.

- **JD Review & Approval**  
  Review and approve structured job descriptions before continuing.

- **Skills Weightage System**  
  Assign priority (scale 1–100) to required skills for better candidate scoring.

- **Bulk Resume Upload**  
  Upload up to **50 PDF resumes** at once with validation checks.

- **AI Resume Parsing**  
  Automatically extracts:
  - Candidate name  
  - Skills  
  - Total experience

- **ATS Matching Engine**  
  Compares resumes to the JD, producing:
  - Candidate rankings  
  - Overall match score  
  - Skill match score

- **Candidate Insights Modal**  
  View detailed information for each candidate, including:
  - Skill match analysis  
  - Education  
  - Certifications
  - Direct Link for visiting sites like LinkedIn, Github
  - Directly get the contact information for easy access for the HR team.

- **Export Results**  
  Download ranked candidates as **CSV** or **JSON**.

---

## Tech Stack

### Frontend

- HTML, CSS, JavaScript (Vanilla)

### Backend

- **FastAPI** – API framework  
- **SQLite** – Default development DB (easily swappable)  
- **PDF Processing:** PyMuPDF  
- **NLP:** spaCy  
- **LLM Integration:** Perplexity Pro API

### Additional Libraries

**pandas**, **numpy**, **scikit-learn**, **python-dotenv**, **sqlalchemy**, **jinja2**

---

## Project Folder Structure
```
sentientgeeks_ats_resume_matcher/
├── frontend/
│ ├── static/
│ │ ├── css/
│ │ │ ├── style.css
│ │ │ └── components.css
│ │ ├── js/
│ │ │ ├── main.js
│ │ │ ├── jd-processor.js
│ │ │ ├── resume-uploader.js
│ │ │ └── matcher.js
│ │ └── assets/
│ │ └── images/
│ └── templates/
│ └── index.html
├── backend/
│ ├── .env
│ ├── app/
│ │ ├── main.py
│ │ ├── models/
│ │ │ ├── database.py
│ │ │ ├── jd_models.py
│ │ │ └── resume_models.py
│ │ ├── services/
│ │ │ ├── pdf_processor.py
│ │ │ ├── jd_processor.py
│ │ │ ├── resume_processor.py
│ │ │ ├── llm_service.py
│ │ │ └── matching_engine.py
│ │ ├── api/
│ │ │ ├── jd_routes.py
│ │ │ ├── resume_routes.py
│ │ │ └── matching_routes.py
│ │ └── utils/
│ │ ├── config.py
│ │ └── helpers.py
├── data/
│ ├── uploads/
│ │ ├── jds/
│ │ └── resumes/
│ └── processed/
├── tests/
│ ├── test_jd_processor.py
│ ├── test_resume_processor.py
│ └── test_matching.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── run.py
```
**git clone** https://github.com/yourusername/sentientgeeks_ats_resume_matcher.git

## Require Libraries with the Versions
```
fastapi==0.104.1
uvicorn==0.24.0
python-multipart==0.0.6
jinja2==3.1.2
python-dotenv==1.0.0
sqlalchemy==2.0.23
alembic==1.13.1
PyMuPDF==1.23.8
spacy==3.7.2
pandas==2.1.4
numpy==1.25.2
scikit-learn==1.3.2
requests==2.31.0
aiofiles==24.1.0
pydantic==2.5.2
psycopg2-binary>=2.9.5
asyncpg>=0.28.0
```

## Setup Instructions
```
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
**Run the Application:** python run.py
```

## Set Up Environment Variables
```
DATABASE_URL=sqlite:///./ats_matcher.db
PERPLEXITY_API_KEY=your_api_key_here
SECRET_KEY=your_secret_key_here
DEBUG=True
UPLOAD_DIR=./data/uploads
MAX_FILE_SIZE=10485760
ALLOWED_EXTENSIONS=pdf,doc,docx
```



