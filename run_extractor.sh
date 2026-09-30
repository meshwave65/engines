#!/bin/bash

BASE="/mnt/hd1tb/projetos/sofia-engines"
VENV_PY="$BASE/venv/bin/python"

TASK_ID=$1

echo "🔥 RUN EXTRACTOR TASK=$TASK_ID"

cd $BASE

exec $VENV_PY universal_extractor.py $TASK_ID
