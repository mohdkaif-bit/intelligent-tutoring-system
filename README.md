# 🧠 Intelligent Personalized Tutoring System

> **AI-powered tutoring platform with Retrieval-Augmented Generation (RAG), LangGraph reasoning, hybrid search, persistent memory, and adaptive learning.**

<p align="center">

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green)
![React](https://img.shields.io/badge/React-TypeScript-61dafb)
![Docker](https://img.shields.io/badge/Docker-Containerized-blue)
![LangGraph](https://img.shields.io/badge/LangGraph-Agent-orange)
![License](https://img.shields.io/badge/License-Academic-lightgrey)

</p>

---

# 🚀 Overview

The **Intelligent Personalized Tutoring System (ITS)** is an AI-powered learning platform designed to provide personalized, document-grounded tutoring experiences.

Unlike traditional chatbots, the system combines:

* 📚 Retrieval-Augmented Generation (RAG)
* 🔍 Hybrid Retrieval (BM25 + Semantic Search)
* 🧠 Persistent User Memory
* 🔄 LangGraph Multi-Step Reasoning
* 📊 Quiz Generation & Evaluation
* ✍️ AI-powered Text Reframing

allowing learners to upload study material and receive adaptive, context-aware explanations grounded in their own documents.

---

# ✨ Features

## 📄 Document-based Learning

* Upload PDFs
* Automatic chunking & indexing
* Semantic embeddings generation
* Context-aware responses

---

## 🔍 Hybrid Retrieval

Combines:

* BM25 lexical search
* FAISS semantic similarity search
* Reciprocal Rank Fusion (RRF)

for improved retrieval precision and recall.

---

## 🧠 Personalized Learning

Persistent memory stores:

* Previous conversations
* Learning patterns
* Weak topics
* User preferences

making responses adaptive over time.

---

## 🔄 LangGraph Reasoning Pipeline

```
User Query
      │
      ▼
Retrieve Documents
      │
      ▼
Re-rank Context
      │
      ▼
Summarize (Analysis Mode)
      │
      ▼
Generate Response
      │
      ▼
Update Memory
```

Supports conditional workflows and multi-step reasoning.

---

## 🎯 Multi Learning Modes

* ⚡ Quick Answer
* 📖 Explain Concept
* 🧩 Step-by-Step Solution
* 🔬 Deep Analysis
* ❓ Question Generation

---

## 📝 Quiz Module

* Page-wise quiz generation
* MCQ evaluation
* Automatic scoring
* Performance tracking
* Feedback generation

---

## ✍️ Text Reframing

Converts difficult content into:

* Beginner-friendly explanations
* Simplified language
* Revision notes

while preserving the original meaning.

---

# 🏗️ System Architecture

```
                React Frontend
                       │
                       ▼
                FastAPI Backend
                       │
                       ▼
             LangGraph Reasoning Engine
                       │
        ┌──────────────┼───────────────┐
        │                              │
        ▼                              ▼
 Hybrid Retrieval              Persistent Memory
(BM25 + FAISS)                User Learning History
        │                              │
        └──────────────┬───────────────┘
                       ▼
                  Groq LLM (LLaMA)
```

---

# 🛠️ Tech Stack

## Backend

* FastAPI
* LangChain
* LangGraph
* Groq API
* FAISS
* BM25
* Sentence Transformers
* PyMuPDF

---

## Frontend

* React
* TypeScript
* Vite
* Context API
* React Router

---

## AI / NLP

* Retrieval-Augmented Generation (RAG)
* Hybrid Search
* HuggingFace Transformers
* all-mpnet-base-v2 Embeddings

---

## Infrastructure

* Docker
* Docker Compose
* Environment-based Configuration

---

# 🔐 Authentication

* Google OAuth Login
* Protected Routes
* Session-based Authentication
* User-specific learning history

---

# 📊 Retrieval Evaluation

| Metric               | Score   |
| -------------------- | ------- |
| Recall@K             | **80%** |
| Precision@K          | **65%** |
| Mean Reciprocal Rank | **70%** |
| Hit Rate@K           | **90%** |
| Faithfulness         | **87%** |
| Semantic Similarity  | **80%** |
| Context Utilization  | **77%** |

---

# 📂 Project Structure

```
intelligent-tutoring-system/

├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── services/
│   │   └── storage/
│   ├── scripts/
│   ├── Dockerfile
│   └── requirements.in
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── Dockerfile
│
├── docker-compose.yml
└── README.md
```

---

# ⚡ Running Locally

## Clone

```bash
git clone https://github.com/mohdkaif-bit/intelligent-tutoring-system.git

cd intelligent-tutoring-system
```

---

## Backend

```bash
cd backend

pip install -r requirements.txt

uvicorn main:app --reload
```

---

## Frontend

```bash
cd frontend

npm install

npm run dev
```

---

# 🐳 Running with Docker

```bash
docker compose up --build
```

Backend

```
http://localhost:8000
```

Frontend

```
http://localhost:3000
```

---

# 📸 Demonstration

✅ Complete project demonstration is available.

(https://drive.google.com/file/d/1HVcz0CSOlQGbb2Oagv9LmRJGdFVQyWxm/view?usp=sharing)

---

# 🚀 Future Improvements

* Mastery tracking
* Multi-language tutoring
* Voice interaction
* OCR-based learning
* Knowledge Graph integration
* Reinforcement Learning personalization
* Cloud deployment

---

# 💡 Highlights

✔ Hybrid Retrieval (BM25 + Semantic Search)

✔ LangGraph Multi-step Reasoning

✔ Persistent Memory Adaptation

✔ Multi-mode Tutoring

✔ Quiz Generation & Evaluation

✔ Text Reframing

✔ Dockerized Full Stack Application

✔ Google Authentication

---

# 👨‍💻 Author

**Mohd Kaif**

Machine Learning Engineer

Focused on:

* Retrieval-Augmented Generation (RAG)
* LLM Applications
* Intelligent Tutoring Systems
* LangGraph Agents
* AI-powered Learning Platforms

---

# 📄 License

This project is intended for academic, research, and educational purposes.
