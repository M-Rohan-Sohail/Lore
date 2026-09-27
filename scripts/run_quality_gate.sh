#!/bin/bash
set -e
echo "Running pytest with coverage..."
pytest --cov=app.services --cov-report=term-missing --cov-fail-under=85 app/tests/
echo "Quality gate passed!"
