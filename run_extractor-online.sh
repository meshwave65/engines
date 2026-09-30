#!/bin/bash

BASE="$(cd "$(dirname "$0")" && pwd)"
PYTHON="python"

TASK_ID=$1

echo "🔥 RUN EXTRACTOR ONLINE TASK=$TASK_ID"

cd "$BASE"

exec "$PYTHON" universal_extractor-online.py "$TASK_ID"
