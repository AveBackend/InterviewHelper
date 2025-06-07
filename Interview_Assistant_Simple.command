#!/bin/bash

echo "🚀 Запуск Interview Assistant..."

# Переходим в директорию скрипта
cd "$(dirname "$0")"

# Активируем виртуальное окружение
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Виртуальное окружение активировано"
fi

# Проверяем Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден!"
    echo "Установите Python с python.org"
    read -p "Нажмите Enter для выхода..."
    exit 1
fi

# Проверяем зависимости и устанавливаем если нужно
echo "🔍 Проверяю зависимости..."
python3 -c "import speech_recognition, requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️ Устанавливаю недостающие зависимости..."
    pip3 install SpeechRecognition requests pyaudio 2>/dev/null || pip install SpeechRecognition requests pyaudio
    
    if [ $? -ne 0 ]; then
        echo "❌ Ошибка установки зависимостей"
        echo "Попробуйте вручную: pip install SpeechRecognition requests pyaudio"
        read -p "Нажмите Enter для выхода..."
        exit 1
    fi
fi

# Запускаем приложение
echo "🎤 Запускаю Interview Assistant..."
echo "📋 Приложение готово к работе!"
echo ""

python3 interview_assistant_simple.py

echo ""
echo "👋 Работа завершена. Нажмите любую клавишу для выхода..."
read -n 1 