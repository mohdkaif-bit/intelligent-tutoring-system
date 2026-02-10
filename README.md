🧠 Intelligent Tutoring System

An AI-powered Intelligent Tutoring System that allows users to upload learning documents, generate embeddings, track learning progress, and interact with content using Retrieval-Augmented Generation (RAG).

The system is built with a FastAPI backend, Vite + React frontend, Dockerized deployment, and is designed to run locally or on AWS EC2.

🚀 Features

📄 Upload and manage learning documents

🔍 Semantic search using embeddings

🧠 RAG-based AI responses

📊 User learning progress tracking

⚡ FastAPI backend with modular architecture

🌐 Vite + React frontend

🐳 Docker & Docker Compose support

☁️ AWS EC2 deployment ready

🏗️ Tech Stack
Backend

Python 3.10

FastAPI

Uvicorn

Sentence Transformers

Vector Store (local storage)

Groq LLM API

Docker

Frontend

React

Vite

TypeScript

Docker

DevOps

Docker & Docker Compose

AWS EC2 (t3.micro – Free Tier)

GitHub

📁 Project Structure
intelligent-tutoring-system/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── documents/
│   │   │       └── progress/
│   │   ├── core/
│   │   ├── services/
│   │   │   └── rag/
│   │   ├── storage/
│   │   └── main.py
│   ├── .env
│   ├── requirements.txt
│   ├── Dockerfile
│   └── README.md
│
├── frontend/
│   ├── src/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── Dockerfile
│   └── README.md
│
├── docker-compose.yml
├── .gitignore
└── README.md

🔑 Environment Variables
Backend (backend/.env)
GROQ_API_KEY=your_groq_api_key_here

Frontend (Docker build arg)
VITE_API_BASE_URL=http://backend:8000

🐳 Docker Setup (Recommended)
1️⃣ Clone Repository
git clone https://github.com/your-username/intelligent-tutoring-system.git
cd intelligent-tutoring-system

2️⃣ Build & Run with Docker Compose
docker-compose up -d --build

3️⃣ Access the App

Frontend:
👉 http://localhost:5173

Backend API:
👉 http://localhost:8000

API Docs:
👉 http://localhost:8000/api/docs

🔗 API Endpoints (Backend)
Method	Endpoint	Description
GET	/	API Health Check
GET	/api/docs	Swagger Docs
POST	/api/v1/documents/upload	Upload document
GET	/api/v1/documents/list	List documents
GET	/api/v1/progress/account	User progress
☁️ AWS EC2 Deployment (Summary)

Create EC2 t3.micro (Amazon Linux)

Open ports:

22 (SSH)

8000 (Backend)

5173 (Frontend)

Install Docker & Docker Compose

Clone repo

Create backend/.env

Run:

docker-compose up -d --build


Open in browser:

http://<EC2_PUBLIC_IP>:5173

⚠️ Important Notes

❌ Do NOT commit .env, node_modules, __pycache__

✅ Always use Docker for production

🔄 Rebuild frontend when changing VITE_API_BASE_URL

🔐 Rotate API keys if exposed accidentally

🛠️ Common Issues
❌ Frontend shows “Failed to fetch”

Ensure:

VITE_API_BASE_URL=http://backend:8000


Rebuild frontend container:

docker-compose up -d --build

📌 Future Improvements

🔐 Authentication (JWT)

🧑‍🎓 Multiple users

☁️ S3 / Managed Vector DB

📈 Advanced analytics dashboard

🤖 Chat-based tutor interface

👨‍💻 Author

Mohd Kaif
📧 Developer of Intelligent Tutoring System
🌐 Built with FastAPI, RAG, and Docker

⭐ Support

If you found this project helpful, give it a ⭐ on GitHub!
