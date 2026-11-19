# AI Customer Support Agent

An LLM-powered customer support agent that reads a customer complaint, classifies it, checks order data, searches company policies, decides whether to **resolve** or **escalate** the issue, drafts a reply email, and tracks unresolved cases.

Built with **Python**, **LangChain**, **Google Gemini** and **Streamlit**.

> This is a learning project. The order data and company policies are sample data kept inside the code, not connected to a real store or database.

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [What the Agent Does](#what-the-agent-does)
3. [How It Works](#how-it-works)
4. [Tech Stack](#tech-stack)
5. [Project Structure](#project-structure)
6. [Setup and Installation](#setup-and-installation)
7. [Running the Project](#running-the-project)
8. [Using the App](#using-the-app)
9. [Sample Complaints to Test](#sample-complaints-to-test)
10. [Sample Data](#sample-data)
11. [Customizing the Project](#customizing-the-project)
12. [Limitations](#limitations)
13. [Future Improvements](#future-improvements)
14. [Security Notes](#security-notes)

---

## Problem Statement

Businesses receive hundreds of customer complaints, requests, refund queries and technical questions every day. Human agents cannot handle all of them quickly. This project shows how an AI agent can handle the routine cases automatically and pass the risky or unclear ones to a human.

## What the Agent Does

| Capability | How it is done |
|---|---|
| Reads customer complaints and emails | Text pasted into the app, or loaded from `customer_complaint.txt` |
| Classifies the issue | The LLM returns category, priority, sentiment, order ID and a summary |
| Searches company policies | A keyword-search tool over the policy text |
| Checks order information using tools | A lookup tool over the order data |
| Decides to resolve or escalate | The LLM decides using the policies, the order data and the escalation rules |
| Drafts a response | The LLM writes a polite reply email |
| Tracks unresolved cases | Every ticket is logged to `cases.json`. Escalated cases stay open until marked resolved |

## How It Works

The agent is a four-stage pipeline:

```
Customer complaint
        |
        v
[Stage 1] Classify the complaint            (LLM call)
        |   category, priority, sentiment, order_id, summary
        v
[Stage 2] Use tools                         (plain Python functions)
        |   check_order()      -> order details
        |   search_policies()  -> relevant policy sections
        v
[Stage 3] Decide and draft a reply          (LLM call)
        |   RESOLVE or ESCALATE + reason + action + email reply
        v
[Stage 4] Track the case                    (saved to cases.json)
            RESOLVED  or  OPEN - ESCALATED
```

**Stage 1: Classification.** The LLM reads the message and returns a JSON object with the category (REFUND, DELIVERY, DAMAGED_ITEM, TECHNICAL, BILLING, ACCOUNT, OTHER), priority, sentiment, order ID and customer name.

**Stage 2: Tools.** The order ID from Stage 1 is used to look up the order. The category and summary are used to find the most relevant policy sections. The escalation rules are always included, so the agent can check them.

**Stage 3: Decision and reply.** The LLM gets the complaint, classification, order data and policies. It must return `RESOLVE` or `ESCALATE`, with a reason, a concrete action, and a draft reply email.

**Stage 4: Tracking.** Each ticket is saved with a case ID, timestamp, customer, order ID, category, priority, decision and status.

### When the agent escalates

The agent escalates to a human when any of these is true (defined in the policy text):

- The customer mentions legal action, consumer court or the media
- There is a safety risk (fire, electric shock, injury)
- The order cannot be found
- No policy clearly covers the situation
- The refund amount is above Rs. 10,000
- A warranty claim is needed (handled by the technical team)

## Tech Stack

- **Python** 3.10 or newer
- **uv** for dependency and environment management
- **LangChain** (`langchain-google-genai`) as the LLM interface
- **Google Gemini** (`gemini-3.8-flash`) as the model
- **Streamlit** for the web interface
- **pandas** for showing case tables
- **python-dotenv** for loading the API key from a `.env` file
- **Jupyter Notebook** for stage-by-stage analysis

## Project Structure

```
.
├── app.py                          # Streamlit web app (UI + full agent pipeline)
├── support_agent_analysis.ipynb    # Notebook: runs the pipeline stage by stage
├── customer_complaint.txt          # Sample complaint used as test input
├── pyproject.toml                  # Project dependencies (uv)
├── uv.lock                         # Locked dependency versions (uv)
├── .python-version                 # Python version (uv)
├── .gitignore                      # Keeps .env, cases.json etc. out of Git
├── README.md                       # This file
├── .env                            # Your API key (NOT uploaded to GitHub)
└── cases.json                      # Created automatically when you process tickets
```

`app.py` and the notebook both contain the sample policies, order data, tools and prompts, so each file can run on its own.

## Setup and Installation

### Prerequisites

- Python 3.10 or newer
- [uv](https://docs.astral.sh/uv/) installed
- A Google Gemini API key from [Google AI Studio](https://aistudio.google.com/)

### Steps

**1. Clone the repository**

```bash
git clone https://github.com/<your-username>/<your-repo-name>.git
cd <your-repo-name>
```

**2. Create the `.env` file**

Create a file named `.env` in the project folder with this line:

```
GOOGLE_API_KEY=your_google_api_key_here
```

**3. Install dependencies**

```bash
uv sync
```

This creates a virtual environment and installs everything listed in `pyproject.toml`.

If you set up the project yourself from scratch instead of cloning it, add the packages with:

```bash
uv add python-dotenv langchain-google-genai streamlit pandas
```

## Running the Project

### Option 1: Streamlit web app

```bash
uv run streamlit run app.py
```

The app opens in your browser at `http://localhost:8501` (Streamlit uses the next free port, such as 8502, if 8501 is busy).

### Option 2: Jupyter notebook

```bash
uv run jupyter notebook
```

If Jupyter is not installed yet, add it first with `uv add jupyter`.

Open `support_agent_analysis.ipynb` and run the cells in order. You will see the output of each stage: classification, order and policy lookup, decision and draft reply, and the case log.

## Using the App

1. **New Ticket tab:** Click **Load sample complaint**, or paste your own customer message.
2. Click **Process Ticket**.
3. The right side shows, in order:
   1. **Classification:** category, priority, sentiment and a summary
   2. **Order Check:** the order data found (or a warning if not found), plus the policies used
   3. **Decision:** a green `RESOLVE` or red `ESCALATE` box with the reason
   4. **Draft Reply:** the email reply for the customer
4. **Case Tracker tab:** Shows unresolved cases. Select a case and click **Mark resolved** to close it. The "All cases" section shows the full history.

## Sample Complaints to Test

These use the sample order IDs below, so the order check works. The expected results depend on the policies in the code. The wording of the reply may vary between runs.

**1. Return within the window (expected: RESOLVE)**

```
Subject: Return request

Hi, I ordered Wireless Earbuds (order ORD-1001) and received them last week.
They are unused and in the original box, but I changed my mind and would like to return them for a refund.

Thanks,
Priya Menon
```

**2. Delayed order with a legal threat (expected: ESCALATE)**

```
Subject: URGENT - Laptop not delivered

My Gaming Laptop order ORD-1003 was supposed to arrive on November 9th and it is
still not here. This is completely unacceptable! If I don't get my refund today,
I will file a case in consumer court and post about this on social media.

Sneha Reddy
```

**3. Order not found (expected: ESCALATE)**

```
Subject: Where is my order?

Hi, I placed an order ORD-9999 for a smartwatch 5 days ago and haven't received
any update. Can you tell me the status?

Ramesh
```

**4. Safety risk (expected: ESCALATE)**

```
Subject: Mixer Grinder sparking!

Order ORD-1002 - when I switched on the Mixer Grinder today, it started sparking
and I got a small electric shock. I am scared to use it again. Please look into this immediately.

Arun Kumar
```

## Sample Data

### Orders

| Order ID | Customer | Item | Amount (Rs.) | Status |
|---|---|---|---|---|
| ORD-1001 | Priya Menon | Wireless Earbuds | 2,499 | Delivered |
| ORD-1002 | Arun Kumar | Mixer Grinder | 4,999 | Delivered |
| ORD-1003 | Sneha Reddy | Gaming Laptop | 68,000 | In Transit (delayed) |
| ORD-1004 | Karthik Raja | Running Shoes | 3,299 | Delivered (over 30 days ago) |

### Policies (summary)

- **Refunds:** within 30 days of delivery for unused items. The agent can approve up to Rs. 10,000. Anything above needs a manager.
- **Damaged items:** must be reported within 7 days of delivery. The customer gets a replacement or a full refund.
- **Delayed delivery:** a Rs. 200 coupon if delayed by more than 5 days. Cancellation with a full refund if delayed by more than 10 days.
- **Warranty:** 1 year on electronics. Warranty claims are escalated to the technical team.
- **Billing:** duplicate charges are refunded. Disputes above Rs. 10,000 go to the finance team.

## Customizing the Project

- **Change the policies:** edit the `COMPANY_POLICIES` text in `app.py` and in the notebook. Each section starts with `## Title`.
- **Add or change orders:** edit the `ORDERS` dictionary in both files.
- **Change the model:** edit the `ChatGoogleGenerativeAI(model="...")` line.
- **Change the reply style:** edit the Stage 3 prompt (`decision_prompt`).
- **Change the case storage file:** edit `CASES_FILE` in `app.py`.

## Limitations

- **Sample data only:** orders and policies are hardcoded, not connected to a real system.
- **Simple policy search:** it matches keywords, not meaning, so it can miss relevant policies if the wording differs.
- **LLM mistakes:** the model can occasionally promise something not in the policies, for example a return pickup. Always review drafts before sending.
- **No email integration:** the agent drafts replies but does not send them.
- **Local case tracking:** cases are stored in a local `cases.json` file, with no login or multi-user support.
- **English only:** the prompts and policies are written in English.

## Future Improvements

- Replace the keyword search with embeddings and a vector database (Chroma or FAISS)
- Connect the order lookup to a real database or e-commerce API
- Read emails directly from Gmail and send approved replies
- Add a human approval step before sending replies
- Store cases in a proper database such as SQLite or PostgreSQL
- Support more languages, including Tamil and Hindi
- Add automated tests and a dashboard of case statistics

## Security Notes

- Never commit your `.env` file. It is listed in `.gitignore`.
- If an API key was ever uploaded to GitHub by mistake, delete it in the provider's dashboard and create a new one.
- Do not paste real customer personal data into a public demo.
