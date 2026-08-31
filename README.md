# PIICompass

Automated PII data-flow mapper and GDPR Article 30 record drafter.

PIICompass scans a codebase and a database schema, works out where personal
data is collected, where it travels, and where it exits the system, and drafts
the "record of processing activities" that GDPR Article 30(1) requires. It turns
a manual, interview-driven spreadsheet exercise into a reproducible scan.

Everything factual is decided by a deterministic, rule-based pipeline that a
reviewer can audit line by line. An optional AI layer only polishes the prose of
the drafted record and never invents facts. When no API key is set, the tool
runs fully in its deterministic mode.

## What it produces

Pointed at the bundled synthetic sample (a fictional "MapleHealth" portal), a
single run reports:

- 22 personal-data fields across 8 tables, 2 of them special-category (Article 9)
  health data.
- 7 processing activities with drafted purposes.
- 12 traced data flows, including 3 cross-border transfers to US processors
  (payment, email, analytics) that need a safeguard.
- A ready-to-review Article 30(1) record covering controller, purposes, data
  subjects, data categories, recipients, transfers, retention, and security
  measures.

## Why the numbers are trustworthy

Three properties, each one a thing a Technology Risk reviewer looks for:

1. Sealed answer key. The detection quality (precision 0.91, recall 0.95, F1
   0.93 on 48 columns) is measured against a hand-labelled ground truth in
   `ground_truth/`. The scanning pipeline is provably forbidden to read that
   file: a static source scan rejects any reference to it, and a runtime audit
   hook blocks any attempt to open it during a run. A booby-trap unit test
   proves the hook fires. Only the evaluator reads the key, and only after the
   scan is done.
2. Determinism. Every run produces byte-identical artifacts, verified by a
   SHA-256 manifest and a determinism test. A single seed governs any ordering.
3. Honest limitations. The tool ships with its own known misses on display: it
   cannot see inside a free-text `notes` column (a false negative) and it
   over-flags reference-grade columns like `city_name` (false positives). These
   are surfaced in the dashboard, not hidden.

## Quickstart

Requires Python 3.11 or newer.

### Windows 11 (PowerShell)

```powershell
cd path\to\piicompass
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env   # optional; edit to add an ANTHROPIC_API_KEY
python run.py
```

If PowerShell blocks activation with "running scripts is disabled on this
system", run this once in the same window, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

An alternative that avoids the policy entirely is Command Prompt:
`.venv\Scripts\activate.bat`.

### macOS or Linux

```bash
cd path/to/piicompass
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env   # optional
python run.py
```

Then open http://127.0.0.1:8000 in a browser.

To generate the artifacts without starting the server:

```
python -m piicompass.pipeline
```

## How it works

1. `schema_scanner` parses CREATE TABLE statements and classifies each column.
2. `code_scanner` walks the Python source with the `ast` module, finds where PII
   enters (request and payload reads) and traces it to sinks: data stores, third
   party services, logs, and file exports. Vendor calls are matched against
   `vendors.py` to attach a recipient and a country, which is how cross-border
   transfers are detected.
3. `classifier` is the shared rule engine that maps an identifier to a GDPR data
   category, with the exact rule and a confidence for every decision.
4. `flow_graph` assembles the activities, destinations, and edges.
5. `article30` drafts the record; `ai_draft` optionally refines its prose.
6. `firewall` seals the ground truth; `evaluate` scores the scan against it.
7. `app` serves the dashboard; `render_svg` draws the flow map and chart with no
   external chart library.

## Project structure

```
piicompass/
  run.py                     single-command entry point
  requirements.txt
  .env.example
  sample_app/                synthetic scan target (schema + code)
  ground_truth/              sealed answer key (pipeline may not read this)
  src/piicompass/            the pipeline and web app
  templates/  static/        dashboard view and stylesheet
  tests/                     36 unit tests
  artifacts/                 generated outputs (regenerated on each run)
```

## Tests

```
python -m unittest discover -s tests -v
```

## Scope and honesty

The bundled data is synthetic and labelled as such throughout the UI. All
metrics here are signal recovery on synthetic data. Running PIICompass against a
real schema and codebase is the next step before any figure describes a live
system. Retention periods, legal bases, and controller identity cannot be
inferred from code and are left as clearly marked fields for a human to
complete. This tool drafts and evidences a record of processing; it does not
replace a data protection officer's review.
