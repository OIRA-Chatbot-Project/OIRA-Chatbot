#!/usr/bin/env bash
# Run this whenever you add/remove/rename columns in database.py.
# It backs up the existing DB, then adds any missing columns without touching data.

set -e

cd "$(dirname "$0")/backend"
python migrate_db.py
