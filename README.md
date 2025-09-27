# 💇 Friseur Rechnungen – Offline Tool

[![Build Status](https://github.com/DEIN_GITHUB_USER/friseur-rechnungen/actions/workflows/ci.yml/badge.svg)](https://github.com/DEIN_GITHUB_USER/friseur-rechnungen/actions)

Ein **offlinefähiges Rechnungsprogramm** mit klarer FE/BE-Trennung – entwickelt für den Einsatz ohne Cloud, aber mit professioneller Architektur und Möglichkeit zur späteren Erweiterung (Hosting, Multi-User, Cloud-Sync).

---

## ✨ Features (geplant)
- Kundenverwaltung (Stammkunden speichern, Autocomplete im Formular)
- Profile (verschiedene Absender, z. B. Friseursalon, Altersheim XY)
- Rechnungen erstellen:
  - Automatische Rechnungsnummer (`YY|laufendeNummer`)
  - Datumsauswahl
  - PDF-Erstellung (A4 Standard)
  - PDF Layouts: A4 & 4×A6 auf A4
  - Optional: E-Rechnung (XRechnung / ZUGFeRD)
- Export: CSV/Excel & Monats-/Jahres-Sammelrechnungen
- Offline-First: SQLite als Datenbasis
- Desktop-App: Tauri v2 bündelt Backend + Frontend + DB in **eine ausführbare Datei**

---

## 🛠 Tech Stack
- **Frontend**: [Next.js](https://nextjs.org/docs/app) (App Router, Static Export), [shadcn/ui](https://ui.shadcn.com)
- **Backend**: [FastAPI](https://fastapi.tiangolo.com), [SQLite](https://sqlite.org), [ReportLab](https://www.reportlab.com/docs/reportlab-userguide.pdf) (PDF)
- **E-Rechnung**: XRechnung (KoSIT Specs), ZUGFeRD (PDF/A-3 + XML)
- **Desktop-App**: [Tauri v2](https://v2.tauri.app/) mit Python-Sidecar (via [PyInstaller](https://pyinstaller.org/))

---

## 📂 Ordnerstruktur

```
backend/    # FastAPI, SQLite, PDF/E-Rechnung
frontend/   # Next.js + shadcn/ui
src-tauri/  # Tauri App-Shell, Sidecar-Konfig
.github/    # CI/CD, Issue-Templates, PR-Template
README.md
```

---

## 🚀 Entwicklung

### Backend (FastAPI)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn sqlmodel reportlab
uvicorn main:app --reload --port 8000
```
Swagger-UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### Frontend (Next.js + shadcn/ui)
```bash
cd frontend
npm install
npm run dev
```
Standard-URL: [http://localhost:3000](http://localhost:3000)

---

### Desktop (Tauri v2)
```bash
cd src-tauri
cargo tauri dev
```

---

## 🧪 Tests

### Backend
- Framework: [pytest](https://docs.pytest.org/) + [httpx](https://www.python-httpx.org/) für API-Tests
- Coverage mit [pytest-cov](https://pytest-cov.readthedocs.io/)
- Tests liegen in `backend/tests/`

Beispiel:
```bash
cd backend
pytest --cov=.
```

### Frontend
- [Jest](https://jestjs.io/) + [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- Unit-Tests für Komponenten
- Integrationstests für Formulare (Invoice Form)

Beispiel:
```bash
cd frontend
npm run test
```

---

## 🤖 CI/CD Pipeline (GitHub Actions)

Datei: `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest --cov=.

  frontend-tests:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npm run test
```

- Jeder Commit/PR auf `main` triggert die Pipeline  
- Badge oben zeigt Status: ✅ Passed / ❌ Failed

---

## 📑 Projektphasen (Roadmap)

- [ ] Phase 0 – Repo-Bootstrap (Ordner, CI/CD, Readme, Templates)
- [ ] Phase 1 – Backend-Skeleton (FastAPI Healthcheck)
- [ ] Phase 2 – DB-Anbindung (SQLite via SQLModel)
- [ ] Phase 3 – Models + CRUD (Kunden, Profile)
- [ ] Phase 4 – Invoice-Core (Rechnung, Nummernlogik)
- [ ] Phase 5 – PDF-Renderer (A4)
- [ ] Phase 6 – PDF-Renderer (A6x4)
- [ ] Phase 7 – Frontend Bootstrap (Next.js + shadcn/ui)
- [ ] Phase 8 – Invoice-Form (Autocomplete, Submit)
- [ ] Phase 9 – CORS + Env-Konfig
- [ ] Phase 10 – Next Static Export
- [ ] Phase 11 – E-Invoice Foundations (XRechnung/ZUGFeRD)
- [ ] Phase 12 – Prototype E-Invoice
- [ ] Phase 13 – Tauri Shell
- [ ] Phase 14 – Backend Sidecar
- [ ] Phase 15 – Release & Docs

---

## ✅ Definition of Done (pro Feature)
- [ ] API-Endpoints funktionieren & Tests grün  
- [ ] UI-Komponenten nutzbar (shadcn/ui Standards)  
- [ ] CI/CD Pipeline grün (Backend + Frontend Tests)  
- [ ] README/Docs aktualisiert  
- [ ] Keine Secrets im Code  
- [ ] Build mit `tauri dev` lauffähig  
- [ ] PDF-Ausgabe geprüft  
- [ ] (optional) E-Rechnung validiert (Validator)  

---

## 📚 Referenzen (Docs)
- FastAPI: https://fastapi.tiangolo.com  
- SQLModel: https://sqlmodel.tiangolo.com  
- ReportLab Guide: https://www.reportlab.com/docs/reportlab-userguide.pdf  
- Next.js App Router: https://nextjs.org/docs/app  
- Next.js Static Export: https://nextjs.org/docs/app/guides/static-exports  
- shadcn/ui Components: https://ui.shadcn.com  
- Tauri v2 Docs: https://v2.tauri.app/  
- PyInstaller: https://pyinstaller.org/  
- XRechnung (KoSIT FAQ): https://en.e-rechnung-bund.de/e-invoicing-faq/xrechnung/  
