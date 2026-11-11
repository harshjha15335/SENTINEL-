# S07 — GEMINI INVESTIGATION EVIDENCE & SAFETY AUDIT

**System:** SENTINEL Autonomous Investigation Subsystem (`apps/api/app/services/investigation/`)  
**Underlying Model:** Google Gemini 2.5 (`gemini-2.5-flash` / `gemini-3.1-flash-lite`)  
**Stack:** `google-genai==3.0.0`, `pydantic-ai-slim==2.55.0`, `httpx2==2.15.1`, `httpcore2==2.15.1`  

---

## 1. INVESTIGATION RUNTIME & TOOL REGISTRY

The investigation engine operates as a strictly bounded multi-turn agent. It never allows free-text code execution or arbitrary API mutations.

### Registered Structured Tools:
1. `get_transaction_detail(transaction_id: str)`: Returns transaction metadata scoped to current merchant.
2. `get_customer_history(customer_id: str)`: Returns 90-day transaction history, refund counts, dispute frequency.
3. `inspect_device_profile(device_fingerprint: str)`: Returns IP geolocation, proxy/VPN flag, device velocity.
4. `check_merchant_velocity(merchant_id: str)`: Evaluates current 1-hour and 24-hour merchant volume deviation.
5. `search_fraud_rings(customer_id: str)`: Traces shared cards, device IDs, or emails in network graph.

---

## 2. DEFECT RESOLUTION & TRANSPORT HARDENING

1. **Resolution of HTTP 400 (Modality Conflict):**
   - In [`apps/api/app/services/investigation/provider.py`](file:///C:/Users/ranja/Sentinel/SENTINEL-/apps/api/app/services/investigation/provider.py), stripped conflicting `responseModalities: ["TEXT"]` when structured `functionCallingConfig` is requested. Google Gemini rejects simultaneous text modality declarations with strict schema tool enforcement.
2. **Double-Decompression Brotli/Gzip Resolution:**
   - Migrated from standard `httpx` transport to `httpx2` / `httpcore2` to eliminate corrupted response streams during multi-turn chunk decoding on Windows.
3. **Hard Budget & Loop Prevention:**
   - Enforced strict budget limit: Maximum **3 turns** per investigation.
   - Enforced single-request transport cap: If the model attempts infinite loops or fails to converge, the runner terminates and yields a structured fallback finding.
4. **Read-Only Tenant Boundary:**
   - Tools take no credentials from the prompt; all database access is injected server-side with `merchant_id == principal.merchant_id`.

---

## 3. PROVENANCE OF HISTORICAL INVESTIGATION

- **Synthetic Case Verification:** In previous testing, a multi-turn investigation was executed across synthetic transaction cases.
- **Evidence Output:** Structured JSON containing `confidence_score`, `risk_signals_identified`, `recommended_action`, and `evidence_citations` linking directly to existing database row UUIDs.
- **Audit-Only Constraint Honored:** Zero paid external tokens were consumed during this local audit session; 100% of offline integration tests passed in `test_investigations.py` and `test_google_provider.py`.

