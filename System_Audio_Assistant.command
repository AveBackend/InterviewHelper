#!/bin/bash

# Получаем директорию скрипта
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "🎧 СИСТЕМНЫЙ АУДИО ПОМОЩНИК"
echo "=="*35
echo "🚀 Запуск Rust + Python System Audio Transcriber..."
echo ""

# Активируем виртуальную среду
if [ -d ".venv" ]; then
    echo "🐍 Активирую Python virtual environment..."
    source .venv/bin/activate
else
    echo "❌ Virtual environment .venv не найдено!"
    echo "💡 Создайте: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    read -p "Нажмите Enter для выхода..."
    exit 1
fi

# Проверяем BlackHole
echo "🔍 Проверяю BlackHole..."
if system_profiler SPAudioDataType | grep -q "BlackHole"; then
    echo "✅ BlackHole найден"
else
    echo "❌ BlackHole не установлен!"
    echo "💡 Установите: brew install blackhole-2ch"
    echo "💡 Затем перезагрузите Mac"
    read -p "Нажмите Enter для выхода..."
    exit 1
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
    
    if ! curl -s http://127.0.0.1:3030/health > /dev/null 2>&1; then
        echo "❌ Не удалось запустить Rust сервер!"
        echo "💡 Запустите вручную: cargo run"
        read -p "Нажмите Enter для выхода..."
        kill $RUST_PID 2>/dev/null
        exit 1
    fi
fi

echo ""
echo "🎧 ИНСТРУКЦИЯ ПО НАСТРОЙКЕ:"
echo "1. Audio MIDI Setup → Create Multi-Output Device"
echo "2. Включите: Built-in Output + BlackHole 2ch"
echo "3. Установите Multi-Output как системный вывод звука"
echo "4. Воспроизведите звук из браузера/приложения"
echo "5. Нажмите Enter в приложении для захвата"
echo ""

# Запускаем Python транскрибер
echo "🐍 Запускаю System Audio Transcriber..."
python system_audio_transcriber.py

# Очистка при выходе
cleanup() {
    echo ""
    echo "🧹 Очистка..."
    if [ ! -z "$RUST_PID" ]; then
        kill $RUST_PID 2>/dev/null
        echo "🛑 Rust сервер остановлен"
    fi
}

trap cleanup EXIT
read -p "Нажмите Enter для завершения..." 