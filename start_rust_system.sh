#!/bin/bash

echo "🚀 Запуск Rust + Python Voice Assistant..."
echo ""

# Проверяем Rust
if ! command -v cargo &> /dev/null; then
    echo "❌ Rust не установлен!"
    echo "Установите Rust: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
    exit 1
fi

# Проверяем Python зависимости
echo "🔍 Проверяю Python зависимости..."
python3 -c "import speech_recognition, requests, sseclient" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️ Устанавливаю недостающие зависимости..."
    pip3 install SpeechRecognition requests sseclient-py pyaudio
    if [ $? -ne 0 ]; then
        echo "❌ Ошибка установки Python зависимостей"
        exit 1
    fi
fi

# Проверяем Ollama
echo "🔍 Проверяю Ollama..."
curl -s http://localhost:11434/api/tags > /dev/null
if [ $? -ne 0 ]; then
    echo "❌ Ollama не запущен!"
    echo "Запустите: brew services start ollama"
    echo "Или: ollama serve"
    exit 1
fi

# Компилируем и запускаем Rust сервис
echo "🦀 Компилирую Rust сервис..."
cargo build --release
if [ $? -ne 0 ]; then
    echo "❌ Ошибка компиляции Rust"
    exit 1
fi

echo "🦀 Запускаю Rust сервер..."
cargo run &
RUST_PID=$!

# Ждем запуска Rust сервера
echo "⏳ Ждем запуска Rust сервера..."
sleep 5

# Проверяем что Rust сервер запустился
curl -s http://127.0.0.1:3030/health > /dev/null
if [ $? -ne 0 ]; then
    echo "❌ Rust сервер не запустился!"
    kill $RUST_PID 2>/dev/null
    exit 1
fi

echo "✅ Rust сервер запущен!"
echo "🐍 Запускаю Python клиент..."
echo ""

# Запускаем Python клиент
python3 voice_transcriber.py

# Убиваем Rust сервер при выходе
echo ""
echo "🛑 Завершаю Rust сервер..."
kill $RUST_PID 2>/dev/null
echo "👋 Все процессы завершены!" 