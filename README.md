# JobMatcher - AI-Powered Job Matching Platform

A comprehensive job matching platform that uses AI and graph-based knowledge representation to connect job seekers with relevant opportunities. Built for the EECE798S Hackathon, this system leverages OpenAI's GPT models, NetworkX graphs, and microservices architecture to provide intelligent job matching capabilities.

## 🚀 Features

### For Job Seekers
- **Smart CV Upload**: AI-powered CV parsing and formatting using GPT-4
- **Intelligent Matching**: Graph-based skill matching algorithm to find relevant job opportunities

### For Companies/HR
- **Job Posting**: Create detailed job descriptions with AI assistance
- **Applicant Management**: View and manage job applications
- **Smart Screening**: AI-powered candidate evaluation and ranking
- **Department Management**: Multi-department support with role-based access

### AI & ML Capabilities
- **Graph Knowledge Representation**: Skills and experience stored as interconnected graphs
- **Intelligent Chat Agent**: LangChain-powered conversational AI for job matching assistance
- **CV Extraction**: Automated parsing of PDF resumes using OpenAI
- **Job Description Generation**: AI-assisted job posting creation
- **Skill Overlap Analysis**: Advanced matching algorithms based on skill graphs

## 🏗️ Architecture

The platform is built using a microservices architecture with the following components:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Database      │
│   (Flask)       │◄──►│   (Flask API)   │◄──►│   (MySQL)       │
│   Port: 3000    │    │   Port: 5000    │    │   Port: 3306    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │
         │              ┌─────────────────┐
         │              │  CV Extraction  │
         │              │     Service     │
         │              │   Port: 3001   │
         │              └─────────────────┘
         │
         │              ┌─────────────────┐
         └──────────────►│ Job Description │
                        │     Service     │
                        │   Port: 3002   │
                        └─────────────────┘
```

## 🛠️ Technology Stack

### Backend Services
- **Flask**: Web framework for API development
- **MySQL**: Primary database for user data, jobs, and applications
- **OpenAI GPT-4**: AI-powered text processing and generation
- **NetworkX**: Graph-based knowledge representation
- **LangChain**: AI agent framework for conversational interfaces

### Frontend
- **Flask Templates**: Server-side rendering with Jinja2
- **Bootstrap**: Responsive UI framework
- **JavaScript**: Interactive client-side functionality
- **Highcharts**: Data visualization (as mentioned in docker-compose)

### AI/ML Components
- **Graph Extraction Chain**: Converts text to knowledge graphs
- **Skill Overlap Analysis**: Advanced matching algorithms
- **Chat Agent**: Conversational AI for user assistance
- **CV Processing**: Automated resume parsing and formatting

## 📦 Installation & Setup

### Prerequisites
- Docker and Docker Compose
- OpenAI API Key
- Git

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd EECE798S_Hackathon/JobMatcher
   ```

2. **Set up environment variables**
   - Update the `OPENAI_API_KEY` in `docker-compose.yml` with your actual API key
   - Modify database credentials if needed

3. **Start the application**
   ```bash
   docker-compose up --build
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:5000
   - CV Extraction API: http://localhost:3001
   - Job Description API: http://localhost:3002

### Manual Setup (Development)

1. **Backend Setup**
   ```bash
   cd backend
   pip install -r requirements.txt
   python app.py
   ```

2. **Frontend Setup**
   ```bash
   cd frontend
   pip install -r requirements.txt
   python app.py
   ```

3. **CV Format Service**
   ```bash
   cd CV-Format
   pip install -r requirements.txt
   python cv_format.py
   ```

4. **Job Description Service**
   ```bash
   cd job-description
   pip install -r requirements.txt
   python job.py
   ```

## 🤖 AI Components

### Graph-Based Knowledge Representation
- Skills and experiences are stored as interconnected graphs
- Enables sophisticated matching algorithms
- Supports skill overlap analysis and recommendation

### LangChain Integration
- Conversational AI agent for user assistance
- Tool-based architecture for graph operations
- ReAct pattern for intelligent decision making

### OpenAI Integration
- GPT-4 for CV parsing and formatting
- Job description generation
- Natural language processing for text extraction

## 🔧 API Endpoints

## 🚀 Usage

### For Job Seekers
1. Register and create a profile
2. Upload your CV (PDF format)

### For HR/Companies
1. Register as a company user
2. Create job postings with AI assistance
3. Match candidates with jobs

## 🚀 Live Demo

### 🤖 **AI Agent in Action**

Experience our intelligent HR agent answering complex queries about candidates and job matches:

```bash
# Example: Query about candidate skills
Question: "Does John have Python skills?"

🤖 Agent Response:
I need to find information about John to determine if he has Python skills. I'll start by locating John's candidate node in the knowledge graph.

Action: find_nodes  
Action Input: label_contains='John'

Result: Found candidate node for John Doe

Action: neighbors  
Action Input: 'cand:john_doe'

Result: {
  "studied": ["degree:bsc_computer_science"],
  "worked_as": ["role:data_scientist"],
  "has_skill": ["skill:python", "skill:sql", "skill:ms_office"],
  "has_project": ["project:churn_prediction"],
  "has_cert": ["certification:aws_certified_ml"]
}

✅ Final Answer: Yes, John has Python skills.
```
### Tasks Done
1. CV Extraction – Extracted text from pdf resumes and formatted it as JSON using LLM.
2. Job Description – Used an LLM to standardize and format job descriptions.
3. Graph Schema – Generated nodes and edges from extracted CVs and Jobs with an LLM.
4. Graph Construction – Built the graph using NetworkX. (See demo demo_798_graph.mp4)
5. Frontend - Fully implemented usinh html + css (See demo UI.mp4)
6. Docker - Implemented but needs improvements

### Future Work
1. update docker implementation for the e2e system to work
2. Automate sending emails to top matching candidates

Graph Querying – Queried the graph using LangChain.
### Team Members
1. Aline Hassan
2. Jenny Haddad
3. Zainab Saad

---

**Built with ❤️ for EECE798S Hackathon**

