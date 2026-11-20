Based on the analysis of the provided source code and normative documentation, here is the `README.md` file for the Ariane Reference Implementation.

```markdown
# Ariane

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-Proprietary-red)
![Status](https://img.shields.io/badge/status-Alpha-orange)

**Ariane** is a high-assurance, cross-platform UI automation system that treats navigation as a **semantic graph problem** rather than a script execution problem.

This repository contains the **Reference Implementation (v0.1.0)** of the Ariane Specification, implemented in Python.

---

## 🧠 Core Concept

Traditional automation tools (Selenium, Appium) rely on fragile selectors. Ariane builds a topographic map of the UI called **Atlas**.

* **States (Nodes):** "Where am I?" (Identified by structural and semantic fingerprints).
* **Transitions (Edges):** "How do I get there?" (Replayable, safety-gated actions).
* **Safety First:** A "Fail Closed" policy engine that blocks destructive or unknown actions unless explicitly approved.

## 🏗 Architecture

Ariane follows a strict **Hexagonal Architecture (Ports & Adapters)**:

* **Theseus (The Core):** The runtime orchestrator that observes, plans, and executes the control loop.
* **Atlas (The Map):** A graph database storing UI states and transitions using Content-Addressed Storage (CAS).
* **Drivers (The Hands):** Stack-specific adapters (e.g., `web-aria` for browsers, `windows-uia` for desktop) that normalize UI signals into the **Core IR**.

---

## 🚀 Installation

### Prerequisites
* Python 3.10 or higher.
* [Playwright](https://playwright.dev/) (required for the Web ARIA driver).

### Setup
```bash
# Clone the repository
git clone [https://github.com/Ariane/ariane.git](https://github.com/Ariane/ariane.git)
cd ariane-v2

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package in editable mode
pip install -e .

# Install Playwright browsers (for Web Driver support)
playwright install

```

---

## 🛠 Usage

Ariane is controlled via a centralized CLI.

### 1. Build a Runtime Pack

Compile a raw Atlas Exchange export into an optimized, read-only Runtime Pack for the agent.

```bash
ariane build-pack \
  --source ./atlas-exchange \
  --output ./dist/knowledge.arp \
  --profile prod

```

### 2. Validate Data Integrity

Verify that an Exchange artifact complies with the schema and cryptographic hash integrity (Fail Closed).

```bash
ariane validate-exchange --path ./atlas-exchange --deep

```

### 3. Run the Agent

Start the Theseus runtime loop to navigate towards a goal.

```bash
ariane run-agent \
  --dialect DIALECT:web-aria \
  --mode safe \
  --goal "qi_login"

```

* `--mode safe`: Blocks high-risk actions automatically.
* `--mode sandbox`: Allows exploration in controlled environments.

---

## 📂 Project Structure

| Directory | Description |
| --- | --- |
| `src/ariane/` | Main Python package source. |
| `src/ariane/core_ir/` | **Core IR**: Canonical data structures and validation logic. |
| `src/ariane/theseus/` | **Theseus**: The runtime execution engine (Observe-Plan-Act loop). |
| `src/ariane/atlas/` | **Atlas**: Graph storage, exchange formats, and fingerprinting. |
| `src/ariane/safety/` | **Safety**: Policy engine and risk classification. |
| `spec/` | **Normative Specs**: JSON schemas and catalogs (The Single Source of Truth). |
| `docs/` | **Documentation**: Normative design documents (DOC-00 to DOC-45). |

---

## 🛡️ Safety & "Fail Closed"

Ariane interacts with real software. To prevent accidental data loss or side effects:

1. **Fail Closed:** If integrity checks fail or risk is unknown, the system halts immediately.
2. **Human Gating:** Destructive actions (e.g., "Delete", "Pay") require explicit human approval via the **Human Approval Protocol**.
3. **Privacy:** Sensitive data (passwords, PII) is redacted at the driver boundary and never stored in the Atlas.

---

## 🤝 Contributing

Please read the [Contributor Guide](https://www.google.com/search?q=docs/45_contributor_guide.md) before submitting changes.

**Key Invariants:**

* Never break the **Core IR** schema without a major version bump.
* All IDs must be **Content-Addressed** (SHA-256) where applicable.
* Safety policies can only become **stricter**, never looser.

---

## 📜 License

Copyright (c) 2026 Réjean McCormick. All rights reserved.

```

```

