# 🧠 Intelligent Personalized Tutoring System

An AI-powered tutoring system that delivers **personalized, document-grounded learning** using **RAG, hybrid retrieval (BM25 + semantic search), LangGraph-based reasoning, and persistent memory**.

---

## 🚀 Overview

This project implements a next-generation **Intelligent Tutoring System (ITS)** that goes beyond traditional LLM-based Q&A systems by incorporating:

* 📚 **Document-grounded learning (RAG)**
* 🧠 **Persistent memory for personalization**
* 🔍 **Hybrid retrieval (BM25 + semantic similarity)**
* 🔄 **Multi-step reasoning using LangGraph**
* 🎯 **Multi-mode learning experience**
* 📊 **Quiz generation & evaluation**
* ✍️ **Text reframing for better understanding**

The system enables learners to upload PDFs and receive **accurate, structured, and adaptive explanations** aligned with their own study material.

---

## 🏗️ System Architecture

The system follows a **modular multi-layer architecture**:

* **Frontend** → React (TypeScript)
* **Backend** → FastAPI (Python)
* **Retrieval Layer** → BM25 + FAISS (Hybrid Search)
* **Reasoning Engine** → LangGraph (multi-node pipeline)
* **LLM** → Groq (LLaMA 3.1)
* **Memory Module** → Persistent user interaction storage

---

## 🔍 Key Features

### 🧠 1. Memory-Based Personalization

* Stores user history (questions, responses, patterns)
* Avoids repetition and adapts explanations
* Tracks weak areas and misconceptions.

---

### 🔎 2. Hybrid Retrieval Pipeline

* Combines:

  * **BM25 (lexical search)**
  * **Semantic similarity (FAISS embeddings)**
* Uses **Reciprocal Rank Fusion (RRF)** for better ranking
* Improves recall + precision significantly

---

### 🔁 3. LangGraph Multi-Step Reasoning

Pipeline includes:

1. Retrieval Node
2. Re-ranking Node
3. Summarization Node (analysis mode)
4. Combine Node
5. Answer Generation Node
6. Memory Update Node

✔ Supports **adaptive workflows & conditional logic**

---

### 🎯 4. Multi-Mode Learning

Supports different interaction modes:

* ⚡ Quick Answer
* 📖 Explain Concept
* 🧩 Step-by-Step Solution
* 🔬 Deep Analysis
* ❓ Question Generation

---

### 📝 5. Quiz System

* Page-wise quiz generation
* MCQ-based evaluation
* Score calculation & feedback
* Tracks learning progress

---

### ✍️ 6. Text Reframing

* Simplifies complex content
* Keeps meaning intact
* Helps in revision & understanding

---

### ⚙️ 7. Adaptive Retrieval

* Dynamic **k value based on mode**
* Re-ranking improves context quality
* Summarization used for long documents

---

## 📊 Evaluation Highlights

| Metric              | Score |
| ------------------- | ----- |
| Recall@K            | 80%   |
| Precision@K         | 65%   |
| MRR                 | 70%   |
| Hit Rate@K          | 90%   |
| Faithfulness        | 87%   |
| Semantic Similarity | 80%   |
| Context Utilization | 77%   |

✔ Demonstrates strong **retrieval accuracy + grounded generation**

---

## 🛠️ Tech Stack

### Backend

* FastAPI
* LangChain + LangGraph
* Groq (LLaMA 3.1)
* FAISS
* BM25

### Frontend

* React (TypeScript)
* REST API integration

### ML / NLP

* HuggingFace Transformers
* Sentence Transformers (all-mpnet-base-v2)

---

## 📂 Project Structure

```
├── backend/           # FastAPI backend
│   ├── api/
│   ├── services/
│   ├── rag/
│   └── models/
│
├── frontend/          # React + TypeScript UI
│
├── docker-compose.yml
├── requirements_freeze.txt
└── README.md
```

---

## ⚡ Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/mohdkaif-bit/your-repo-name.git
cd your-repo-name
```

---

### 2. Run with Docker

```bash
docker-compose up --build
```

---

### 3. Run manually

#### Backend

```bash
cd backend
pip install -r requirements_freeze.txt
uvicorn app.main:app --reload
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## 🧠 Future Improvements

* Advanced learner modeling (mastery tracking)
* Multi-language support
* Voice & OCR integration
* Knowledge graph integration
* Mobile/offline deployment
* Reinforcement learning-based personalization

---

## 📌 Key Contributions

* Hybrid retrieval (BM25 + semantic)
* LangGraph-based reasoning pipeline
* Persistent memory + adaptation layer
* Multi-mode tutoring system
* Quiz + reframing integration

---

## 👨‍💻 Author

**Mohd Kaif**
Machine Learning Engineer
Focused on AI-powered intelligent systems, RAG pipelines, and LLM applications.

---
** Demonstration is available 
## 📜 License

This project is for academic and research purposes.
