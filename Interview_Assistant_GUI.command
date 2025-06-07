#!/bin/bash

echo "🚀 Запуск Interview Assistant GUI..."

# Переходим в директорию скрипта
cd "$(dirname "$0")"

# Активируем виртуальное окружение
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Виртуальное окружение активировано"
fi

# Проверяем BlackHole
echo "🔍 Проверяю BlackHole..."
if system_profiler SPAudioDataType | grep -q "BlackHole"; then
    echo "✅ BlackHole найден"
else
    echo "❌ BlackHole не установлен!"
    echo "💡 Установите: brew install blackhole-2ch"
    echo "💡 Затем перезагрузите Mac"
    read -p "Нажмите Enter для продолжения..."
fi

# Проверяем Rust сервис
echo "🔗 Проверяю Rust сервис..."
if curl -s http://127.0.0.1:3030/health > /dev/null 2>&1; then
    echo "✅ Rust сервис доступен"
else
    echo "⚠️ Rust сервис недоступен, запускаю..."
    # Запускаем Rust сервер в фоне
    cargo run --release > rust_server.log 2>&1 &
    RUST_PID=$!
    
    # Ждем запуска
    echo "⏳ Ждем запуска Rust сервера..."
    for i in {1..15}; do
        sleep 1
        if curl -s http://127.0.0.1:3030/health > /dev/null 2>&1; then
            echo "✅ Rust сервер запущен!"
            break
        fi
        echo -n "."
    done
fi

echo ""
echo "🖥️ Запускаю GUI приложение..."

# Запускаем GUI
python3 interview_assistant_gui.py

echo ""
echo "👋 Завершение работы..." 