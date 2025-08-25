#!/usr/bin/env bash
set -e
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install fastapi uvicorn[standard] pydantic sqlalchemy psycopg2-binary httpx pytest python-dotenv
pip install ruff black pdfplumber
echo "Done. Now: cp .env.example .env && make dev"
