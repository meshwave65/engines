#!/bin/bash

set -e

BASE="/mnt/hd1tb/projetos/sofia-engines"
cd $BASE

source venv/bin/activate

echo "🚀 SOFIA ENGINES START"

python worker_daemon.py
