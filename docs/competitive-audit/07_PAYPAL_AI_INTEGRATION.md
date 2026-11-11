# 07 — PAYPAL AND AI INTEGRATION AUDIT

**Focus Area:** Sponsor Alignment, PayPal API Utilization, and Generative AI Implementation  
**Auditor:** Principal Fintech Integration Specialist & AI Systems Architect  

---

## 1. PAYPAL API INTEGRATION COMPARISON

```
+-----------------------------------------------------------------------------------------------------------------+
|                                          PAYPAL INTEGRATION MATRIX                                              |
+---------------------------------+---------------------------------------+---------------------------------------+
| Feature / API Path              | SENTINEL (Ours)                       | Fraud Risk Manager (Competitor)       |
+---------------------------------+---------------------------------------+---------------------------------------+
| PayPal Orders v2 REST API       | VERIFIED WORKING (Create & Capture)   | NOT IMPLEMENTED (0 PayPal APIs)       |
| PayPal Experience Context       | VERIFIED WORKING (Return/Cancel URLs) | NOT IMPLEMENTED                       |
| Real Sandbox Buyer Flow         | VERIFIED WORKING ($25 Captured Order) | NOT IMPLEMENTED                       |
| Webhook Intake & Verification   | VERIFIED WORKING (RSA SHA256 against cert)| NOT IMPLEMENTED (0 Webhooks)      |
| Supabase Durable Inbox Bridge   | VERIFIED WORKING (PostgreSQL Queue)   | NOT IMPLEMENTED                       |
| Sandbox Status / Health Check   | VERIFIED WORKING (`/settings/paypal`) | NOT IMPLEMENTED                       |
+---------------------------------+---------------------------------------+---------------------------------------+
```

### The Decisive Hackathon Difference:
SENTINEL is built directly upon the PayPal ecosystem. It ingests genuine PayPal Sandbox buyer checkouts, handles authentic cryptographic webhook callbacks, and performs real-time decisioning during the PayPal transaction lifecycle. Fraud Risk Manager is a standalone generic prototype that does not interact with PayPal in any capacity.

---

## 2. GENERATIVE AI & AGENT IMPLEMENTATION COMPARISON

| AI Dimension | SENTINEL (Ours) | Fraud Risk Manager (Competitor) |
| :--- | :--- | :--- |
| **Underlying Model** | Google Gemini 2.5 (`gemini-2.5-flash` / `gemini-3.1-flash-lite`) | **NONE** (0 LLM models) |
| **Interaction Pattern** | Multi-turn Autonomous Investigation Agent (3-turn budget) | **NONE** (Static XGBoost scoring only) |
| **Tool Registry & Grounding**| 5 Scoped Read-Only Tools (Transaction, Customer, Device, Velocity, Graph) | **NONE** |
| **Hallucination Defense** | Strict Pydantic JSON schemas, modality stripping, evidence citations | **NONE** |
| **Human-in-the-Loop** | Synthesized findings presented in UI; analyst approves resolution | **NONE** |

### Strategic Conclusion:
For a hackathon titled the **PayPal AI Hackathon**, Fraud Risk Manager fails to fulfill both primary thematic requirements (neither PayPal nor AI). SENTINEL implements both genuine PayPal Orders v2 integration and autonomous Gemini 2.5 multi-turn agent investigations.

