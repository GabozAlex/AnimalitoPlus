#!/usr/bin/env python3
"""CLI script to run scrapers manually.

Usage:
    python run_scraper.py              # scrape today
    python run_scraper.py 2026-01-15   # scrape specific date
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.scraper import run_scraper_parallel

fecha = sys.argv[1] if len(sys.argv) > 1 else None
results = run_scraper_parallel(fecha)
print(f"Fecha: {results['fecha']}")
print(f"Total guardados: {results['total']}")
for loteria, info in results["loterias"].items():
    print(f"  {loteria}: {info['scraped']} encontrados, {info['saved']} guardados")
