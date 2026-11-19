import json
import os
import re
from datetime import datetime

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

st.set_page_config(page_title="AI Customer Support Agent", layout="wide")

llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0)

CASES_FILE = "cases.json"

# ---------------------------------------------------------------- Company data and tools
COMPANY_POLICIES = """
## Refund Policy
Customers may request a refund within 30 days of delivery for unused items in original packaging.
Refunds are credited to the original payment method within 5-7 business days.
Refunds up to Rs. 10,000 can be approved by the support agent directly.
Refunds above Rs. 10,000 require manager approval and must be escalated.

## Damaged or Defective Items
If an item arrives damaged or defective, the customer must report it within 7 days of delivery.
Once reported, the customer is offered a free replacement or a full refund, including shipping charges.
No return pickup fee is charged for damaged or defective items.

## Delayed Delivery
If an order is delayed by more than 5 days beyond the expected delivery date, the customer gets a Rs. 200 goodwill coupon.
If an order is delayed by more than 10 days, the customer may cancel for a full refund.
For delayed orders, apologise and share the latest tracking status.

## Return Window
Standard returns are accepted within 30 days of delivery.
Items delivered more than 30 days ago are not eligible for return or refund, except manufacturing defects under warranty.

## Warranty and Technical Support
Electronics carry a 1-year manufacturer warranty.
For technical issues, ask the customer to restart and factory reset first.
If the problem continues, raise a warranty claim; warranty claims are handled by the technical team and must be escalated.

## Billing Issues
Duplicate charges are refunded in full within 3-5 business days after verification.
Billing disputes above Rs. 10,000 must be escalated to the finance team.

## Escalation Rules
Always escalate when: the customer mentions legal action, consumer court, or media; there is a safety risk (fire, shock, injury);
the order cannot be found; no policy clearly covers the situation; or the refund amount is above Rs. 10,000.
"""

ORDERS = {
    "ORD-1001": {"customer": "Priya Menon", "item": "Wireless Earbuds", "amount": 2499, "status": "Delivered",
                 "ordered_on": "2026-11-02", "expected_delivery": "2026-11-08", "delivered_on": "2026-11-10"},
    "ORD-1002": {"customer": "Arun Kumar", "item": "Mixer Grinder", "amount": 4999, "status": "Delivered",
                 "ordered_on": "2026-11-10", "expected_delivery": "2026-11-16", "delivered_on": "2026-11-17"},
    "ORD-1003": {"customer": "Sneha Reddy", "item": "Gaming Laptop", "amount": 68000, "status": "In Transit",
                 "ordered_on": "2026-11-01", "expected_delivery": "2026-11-09", "delivered_on": None},
    "ORD-1004": {"customer": "Karthik Raja", "item": "Running Shoes", "amount": 3299, "status": "Delivered",
                 "ordered_on": "2026-09-15", "expected_delivery": "2026-09-20", "delivered_on": "2026-09-20"},
}


def parse_json(text):
    """LLMs sometimes wrap JSON in ``` fences. Strip them and parse."""
    text = re.sub(r"```(?:json)?", "", text).strip()
    return json.loads(text[text.find("{"): text.rfind("}") + 1])


def search_policies(query, top_k=2):
    """Tool 1: simple keyword search over the company policies."""
    sections = [s.strip() for s in COMPANY_POLICIES.split("## ") if s.strip()]
    words = set(re.findall(r"[a-z]+", query.lower()))
    scored = sorted(((len(words & set(re.findall(r"[a-z]+", s.lower()))), s) for s in sections),
                    key=lambda x: x[0], reverse=True)
    results = [s for score, s in scored[:top_k] if score > 0]
    escalation = next(s for s in sections if s.startswith("Escalation Rules"))
    if escalation not in results:
        results.append(escalation)  # always include escalation rules
    return "\n\n".join("## " + r for r in results)


def check_order(order_id):
    """Tool 2: look up an order (returns None if not found)."""
    return ORDERS.get(order_id) if order_id else None


# ---------------------------------------------------------------- Case tracking
def load_cases():
    if not os.path.exists(CASES_FILE):
        return []
    with open(CASES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cases(cases):
    with open(CASES_FILE, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)


def log_case(classification, decision):
    cases = load_cases()
    case = {
        "case_id": f"CASE-{len(cases) + 1:04d}",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "customer": classification.get("customer_name"),
        "order_id": classification.get("order_id"),
        "category": classification.get("category"),
        "priority": classification.get("priority"),
        "decision": decision["decision"],
        "status": "RESOLVED" if decision["decision"] == "RESOLVE" else "OPEN - ESCALATED",
    }
    cases.append(case)
    save_cases(cases)
    return case


# ---------------------------------------------------------------- Agent pipeline
def run_agent(complaint):
    # Stage 1: classify
    classify_prompt = f"""
    You are a customer support triage assistant.

    Read the customer message below and return ONLY a JSON object (no extra text) with these keys:
    - "category": one of REFUND, DELIVERY, DAMAGED_ITEM, TECHNICAL, BILLING, ACCOUNT, OTHER
    - "priority": one of LOW, MEDIUM, HIGH, URGENT
    - "sentiment": one of ANGRY, NEUTRAL, HAPPY
    - "order_id": the order ID mentioned (like ORD-1234) or null
    - "customer_name": the customer's name or null
    - "summary": one-sentence summary of the problem

    Customer message:
    {complaint}
    """
    classification = parse_json(llm.invoke(classify_prompt).text)
    # Stage 2: tools
    order = check_order(classification.get("order_id"))
    policies = search_policies(f"{classification.get('category', '')} {classification.get('summary', '')}")
    # Stage 3: decide and draft
    today = datetime.now().strftime("%Y-%m-%d")
    decision_prompt = f"""
    You are a senior customer support agent. Today's date is {today}.

    Decide whether you can RESOLVE this issue yourself or must ESCALATE it to a human,
    using ONLY the company policies and order information below. Do not invent policies.

    Return ONLY a JSON object (no extra text) with these keys:
    - "decision": "RESOLVE" or "ESCALATE"
    - "reason": 1-2 sentences explaining the decision, referring to the policy used
    - "action": the concrete action to take (e.g. "Issue full refund of Rs. 4999", "Send to manager for approval")
    - "reply": a polite, empathetic email reply to the customer (under 120 words), signed "Support Team".
              If escalating, tell the customer a specialist will contact them within 24 hours.

    Customer message:
    {complaint}

    Classification:
    {json.dumps(classification, indent=2)}

    Order information:
    {json.dumps(order, indent=2) if order else "ORDER NOT FOUND"}

    Company policies:
    {policies}
    """
    decision = parse_json(llm.invoke(decision_prompt).text)
    # Stage 4: track
    case = log_case(classification, decision)
    return {"classification": classification, "order": order, "policies": policies,
            "decision": decision, "case": case}


# ---------------------------------------------------------------- UI
st.title("AI Customer Support Agent")
tab_ticket, tab_tracker = st.tabs(["New Ticket", "Case Tracker"])

with tab_ticket:
    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.subheader("Customer Complaint / Email")
        if st.button("Load sample complaint"):
            with open("customer_complaint.txt", "r", encoding="utf-8") as f:
                st.session_state["complaint_text"] = f.read()

        complaint_input = st.text_area(
            label="Paste the customer's message",
            height=400,
            key="complaint_text",
            placeholder="Paste the customer complaint or email here...",
            label_visibility="collapsed",
        )
        analyze_clicked = st.button("Process Ticket", type="primary", use_container_width=True)

    if analyze_clicked:
        if not complaint_input.strip():
            with left_col:
                st.warning("Please paste a customer message first.")
        else:
            with st.spinner("Agent is working on the ticket..."):
                try:
                    st.session_state["result"] = run_agent(complaint_input)
                except Exception as e:
                    st.session_state["result"] = None
                    with left_col:
                        st.error(f"Something went wrong: {e}")

    result = st.session_state.get("result")
    with right_col:
        if result:
            c, d = result["classification"], result["decision"]

            st.subheader("1. Classification")
            col1, col2, col3 = st.columns(3)
            col1.metric("Category", c.get("category", "-"))
            col2.metric("Priority", c.get("priority", "-"))
            col3.metric("Sentiment", c.get("sentiment", "-"))
            st.caption(c.get("summary", ""))

            st.subheader("2. Order Check")
            if result["order"]:
                st.json(result["order"])
            else:
                st.warning("Order not found in the system.")
            with st.expander("Policies the agent used"):
                st.text(result["policies"])

            st.subheader("3. Decision")
            if d["decision"] == "RESOLVE":
                st.success(f"RESOLVE: {d.get('action', '')}")
            else:
                st.error(f"ESCALATE: {d.get('action', '')}")
            st.write(d.get("reason", ""))

            st.subheader("4. Draft Reply")
            st.text_area("Draft", value=d.get("reply", ""), height=220, label_visibility="collapsed")
            st.caption(f"Logged as {result['case']['case_id']} ({result['case']['status']})")
        else:
            st.info("The agent's analysis will appear here.")

with tab_tracker:
    st.subheader("Unresolved Cases")
    all_cases = load_cases()
    open_cases = [c for c in all_cases if c["status"] != "RESOLVED"]
    if open_cases:
        st.dataframe(pd.DataFrame(open_cases), use_container_width=True, hide_index=True)
        col_a, col_b = st.columns([2, 1])
        selected = col_a.selectbox("Mark a case as resolved", [c["case_id"] for c in open_cases])
        if col_b.button("Mark resolved"):
            for c in all_cases:
                if c["case_id"] == selected:
                    c["status"] = "RESOLVED"
            save_cases(all_cases)
            st.rerun()
    else:
        st.success("No unresolved cases.")

    with st.expander("All cases"):
        if all_cases:
            st.dataframe(pd.DataFrame(all_cases), use_container_width=True, hide_index=True)
        else:
            st.write("No cases yet.")
