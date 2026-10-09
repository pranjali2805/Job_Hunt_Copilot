# Job_Hunt_Copilot

**An AI-powered job discovery and resume-tailoring assistant built with Python.**

Job-Hunt Copilot helps streamline the job search process by collecting job listings from applicant tracking system (ATS) job boards, filtering and ranking opportunities, tracking matches, and delivering notifications through Telegram.

The goal is to reduce repetitive job searching and resume customization while keeping the candidate in control of every application.

## ✨ Features

* **Automated Job Discovery:** Fetches job listings from configured Greenhouse, Lever, and Ashby job-board APIs.
* **Role-Based Filtering:** Filters opportunities using configurable job titles, locations, experience requirements, and exclusion rules.
* **Semantic Job Matching:** Combines semantic similarity, keyword relevance, and title-fit scoring to rank opportunities.
* **AI-Assisted Resume Tailoring:** Uses a Groq-hosted language model to customize resume content based on candidate-provided experience and skills.
* **Resume PDF Generation:** Renders resume content into a clean, single-column PDF format designed to be easy to parse.
* **Application Tracking:** Records job details and application status in Google Sheets.
* **Telegram Notifications:** Sends job-match digests and supports document delivery.
* **Ranking Audit:** Produces a CSV audit of job scores, filtering decisions, and relevance notes to support manual evaluation.

## 🏗️ Architecture

```text
Configured ATS Job Boards
          |
          v
     Job Fetcher
          |
          v
  Filtering and Ranking
          |
          v
   AI Resume Tailoring
          |
          v
     Resume PDF
          |
          v
 Google Sheets + Telegram
```

The pipeline is designed to combine automated discovery with human review, rather than submit applications automatically.

## 🛠️ Tech Stack

| Component            | Technology                     |
| -------------------- | ------------------------------ |
| Language             | Python                         |
| Job Sources          | Greenhouse, Lever, Ashby APIs  |
| Semantic Matching    | Sentence Transformers          |
| LLM Integration      | Groq API                       |
| Resume Rendering     | HTML, CSS, WeasyPrint          |
| Application Tracking | Google Sheets API              |
| Notifications        | Telegram Bot API               |
| Configuration        | YAML and environment variables |

## 📂 Project Structure

```text
job-copilot/
├── src/
│   ├── fetch.py
│   ├── filters.py
│   ├── match.py
│   ├── llm.py
│   ├── tailor.py
│   ├── render.py
│   ├── ranking_audit.py
│   ├── tracker.py
│   ├── notify.py
│   └── main.py
├── templates/
│   └── resume.html
├── config.yaml
├── companies.yaml
├── requirements.txt
└── README.md
```

Personal configuration and generated files are kept separate from the public source code.

## 🚀 Setup and Installation

### 1. Clone the repository

```bash
git clone https://github.com/pranjali2805/Job_Hunt_Copilot.git
cd Job_Hunt_Copilot
```

### 2. Create a virtual environment

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure credentials

Set up the required local environment variables and service credentials for the Groq API, Google Sheets, Telegram, and PDF rendering.

Configure job sources and matching preferences in `companies.yaml` and `config.yaml`. Add candidate-specific information to local configuration files as required by the application.

**Never commit API keys, bot tokens, Google service-account credentials, personal resumes, or candidate-specific data to GitHub.**

### 4. Run the application

```bash
python -m src.main
```

Run the ranking audit separately when evaluating job relevance:

```bash
python -m src.ranking_audit
```

Some integrations, credentials, and system dependencies must be configured before the application can run successfully. In particular, WeasyPrint may require additional Windows system libraries.

## 🔒 Responsible Design

Job-Hunt Copilot is intended to assist, not replace, candidate judgment.

* Applications are not submitted automatically.
* Generated resumes must be reviewed before use.
* Job scores indicate estimated relevance, not a guarantee of suitability.
* Resume validation and source-fact checks are guardrails, not a guarantee that every generated claim is accurate.
* API availability and job-board coverage depend on the configured sources.

## 📌 Current Status

**Version:** v0.1 — Working prototype under validation.

Job fetching, filtering and ranking, Google Sheets integration, Telegram notifications, and PDF generation have been exercised individually or in prototype workflows. Further validation is needed to establish reliable job relevance, resume-claim verification, and the complete end-to-end resume delivery workflow.

## 🗺️ Planned Improvements

* Evaluate job rankings against a manually labelled dataset.
* Strengthen resume claim validation and visible human-review indicators.
* Complete end-to-end testing of PDF generation, tracking, and Telegram delivery.
* Improve discovery coverage through additional permitted job sources.
* Add setup examples and repeatable tests.

## 👩‍💻 Author

**Pranjali Sawant**

Computer Engineering student interested in Product Management, AI applications, automation, and building practical tools that solve real problems.

---

*Built as a personal project to make the job search process more organized, relevant, and efficient.*
