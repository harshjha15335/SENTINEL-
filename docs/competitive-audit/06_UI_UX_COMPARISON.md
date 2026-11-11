# 06 — EXTREME UI/UX AND PRODUCT EXPERIENCE AUDIT

**Comparison:** SENTINEL V2 Design System vs Fraud Risk Manager Frontend  
**Auditor:** Senior UI/UX Engineer & Product Specialist  

---

## 1. DESIGN SYSTEM & VISUAL IDENTITY

| UX Dimension | SENTINEL V2 (Ours) | Fraud Risk Manager (Competitor) | Winner & Assessment |
| :--- | :--- | :--- | :---: |
| **Visual Tone & Theme** | Dark fintech terminal aesthetic, IBM Plex typography | Modern clean dashboard, Inter / Sans-serif typography | **TIED** (Both look visually credible). |
| **Information Density** | High density (AG Grid tables, compact stat badges) | Medium density (Cards, simple HTML tables) | **SENTINEL** (Better for high-volume fraud teams). |
| **Navigation Model** | Persistent desktop sidebar (13 deep routes), collapsible mobile bar | Top bar navigation tabs | **SENTINEL** (Enterprise enterprise workflow hierarchy). |
| **Component Virtualization**| AG Grid virtualized DOM rendering | Unvirtualized standard HTML table | **SENTINEL** (Scales to 50,000 transactions smoothly). |
| **Accessibility (a11y)** | Skip to content, ARIA labels, full keyboard focus rings | Standard accessible tags | **SENTINEL** (Formally tested with `@axe-core`). |

---

## 2. SCREEN-BY-SCREEN COMPARISON

| Screen / Feature | SENTINEL Score | FRM Score | Winner | Key Strengths & Weaknesses |
| :--- | :---: | :---: | :---: | :--- |
| **Command Center / Dashboard**| **9.5** | **8.8** | **SENTINEL** | SENTINEL separates Sandbox vs Simulated volume; FRM has clean metric cards. |
| **Transactions Table** | **9.6** | **8.0** | **SENTINEL** | SENTINEL's AG Grid provides multi-column sorting, filtering, and risk banding. |
| **Review Queue & Detail** | **9.8** | **8.2** | **SENTINEL** | SENTINEL features the **Investigation Workbench** (AI summary, evidence, approvals). |
| **Policy Lab / Thresholds** | **9.4** | **8.5** | **SENTINEL** | SENTINEL's slider dynamically recalculates merchant savings and flag rates. |
| **Batch Scoring Interface** | **0.0** | **9.2** | **FRM** | FRM provides a working CSV drag-and-drop batch scorer; SENTINEL lacks this. |
| **Network Entity Graph** | **8.2** | **9.0** | **FRM** | FRM's NetworkX visualization makes fraud rings more immediately intuitive to casual judges. |
| **Sandbox Checkout Flow** | **9.5** | **0.0** | **SENTINEL** | SENTINEL embeds real PayPal JS SDK checkout; FRM has zero checkout experience. |

