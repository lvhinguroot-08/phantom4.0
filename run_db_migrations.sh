#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== 1. Resetting Database ==="
sudo -u postgres psql -d phantom -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO postgres; GRANT ALL ON SCHEMA public TO phantom_app; GRANT ALL ON SCHEMA public TO public;"

echo "=== 2. Applying Migrations ==="
for f in "$SCRIPT_DIR"/database/migrations/*.sql; do
    if [ -f "$f" ]; then
        echo "Applying migration: $(basename "$f")"
        sudo -u postgres psql -d phantom -v ON_ERROR_STOP=1 -f "$f"
    fi
done

echo "=== 3. Applying Seeds ==="
for f in "$SCRIPT_DIR"/database/seeds/*.sql; do
    if [ -f "$f" ]; then
        echo "Applying seed: $(basename "$f")"
        sudo -u postgres psql -d phantom -v ON_ERROR_STOP=1 -f "$f"
    fi
done

echo "=== 4. Running Verification SQL Tests ==="
for f in "$SCRIPT_DIR"/database/tests/*.sql; do
    if [ -f "$f" ]; then
        echo "Running test: $(basename "$f")"
        sudo -u postgres psql -d phantom -v ON_ERROR_STOP=1 -f "$f"
    fi
done

echo "=== ALL DATABASE MIGRATIONS, SEEDS, AND TESTS COMPLETED SUCCESSFULLY ==="
