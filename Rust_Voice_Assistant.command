#!/bin/bash

# Переходим в директорию скрипта
cd "$(dirname "$0")"

# Запускаем систему
./start_rust_system.sh

echo ""
echo "👋 Нажмите любую клавишу для выхода..."
read -n 1 