# Sandbox - Livre d'or (FastAPI + React + SQLite)

Mini projet de demonstration pour simuler un environnement de travail.

## Stack

- Backend: FastAPI
- Frontend: React (Vite)
- DB: SQLite

## Prerequis

- Python 3.10+
- Node.js 18+

## Installation

### 1) Backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2) Frontend

```bash
cd frontend
npm install
```

## Configuration

Les fichiers `.env.example` et `.env` sont centralises a la racine du sandbox:

- `.env.example`
- `.env`

Un seul fichier contient les variables backend et frontend (`VITE_*`).

## Lancer l'application

Ouvrir deux terminaux:

### Terminal 1 - API

```bash
cd backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

### Terminal 2 - Frontend

```bash
cd frontend
npm run dev
```

## Scripts de demarrage rapide

Depuis `IA-xercice/sandbox`:

### Bash

```bash
chmod +x dev.sh
./dev.sh all    # lance API + Front
./dev.sh api    # lance API seule
./dev.sh front  # lance Front seul
./dev.sh stop   # arrete l'API
```

### PowerShell

```powershell
.\dev.ps1 all    # lance API + Front
.\dev.ps1 api    # lance API seule
.\dev.ps1 front  # lance Front seul
.\dev.ps1 stop   # arrete l'API
```

En mode `all`, l'API tourne en job PowerShell `guestbook-api`.
Pour verifier les logs:

```powershell
Get-Job
Receive-Job -Name guestbook-api -Keep
```

Puis ouvrir:

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs

## Fonctionnalites

- Afficher les messages du livre d'or
- Ajouter un message (nom + contenu)
- Persistance SQLite locale
