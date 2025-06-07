#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import speech_recognition as sr
import requests
import json
import sys
import threading
import time
import subprocess
from datetime import datetime

class SimpleInterviewAssistant:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        self.config = self.load_config()
        self.ai_provider = self.config.get('ai_provider', 'ollama')
        
        self.history = []
        
        self.setup_microphone()

    def load_config(self):
        """Загружает конфигурацию из config.json"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {
                "ai_provider": "ollama",
                "ollama": {
                    "base_url": "http://localhost:11434/api",
                    "model": "qwen2:7b"
                },
                "deepseek": {
                    "api_key": "",
                    "model": "deepseek-coder",
                    "base_url": "https://api.deepseek.com/v1"
                },
                "qwen": {
                    "api_key": "",
                    "model": "qwen-max",
                    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
                }
            }

    def setup_microphone(self):
        """Настраивает микрофон"""
        try:
            print("🎤 Настраиваю микрофон...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("✅ Микрофон готов!")
        except Exception as e:
            print(f"❌ Ошибка микрофона: {e}")

    def show_notification(self, title, message):
        """Показывает системное уведомление на macOS"""
        try:
            script = f'''
            display notification "{message}" with title "{title}" sound name "Glass"
            '''
            subprocess.run(['osascript', '-e', script], check=False)
        except:
            pass

    def record_audio(self):
        """Записывает аудио"""
        try:
            print("\n🎤 ЗАПИСЬ НАЧАЛАСЬ! Говорите вопрос...")
            print("⏱️  Максимум 30 секунд. Нажмите Enter когда закончите.")
            
            self.show_notification("🎤 Запись началась", "Говорите вопрос интервьюера")
            
            audio = None
            recording_complete = threading.Event()
            
            def record():
                nonlocal audio
                try:
                    with self.microphone as source:
                        audio = self.recognizer.listen(source, phrase_time_limit=30)
                    recording_complete.set()
                except Exception as e:
                    print(f"❌ Ошибка записи: {e}")
                    recording_complete.set()
            
            record_thread = threading.Thread(target=record)
            record_thread.daemon = True
            record_thread.start()
            
            input()
            print("🛑 Запись остановлена...")
            
            recording_complete.wait(timeout=2)
            
            if audio:
                self.process_audio(audio)
            else:
                print("❌ Аудио не записано")
                
        except KeyboardInterrupt:
            print("\n🛑 Запись прервана")
        except Exception as e:
            print(f"❌ Ошибка: {e}")

    def process_audio(self, audio):
        """Обрабатывает записанное аудио"""
        try:
            print("🔄 Распознаю речь...")
            self.show_notification("🔄 Распознавание", "Обрабатываю речь")
            
            try:
                text = self.recognizer.recognize_google(audio, language="ru-RU")
                text = text.strip()
                
                if not text:
                    print("⚠️ Пустой текст")
                    return
                    
                print(f"🎯 Распознано: {text}")
                self.show_notification("🎯 Распознано", text[:50] + "..." if len(text) > 50 else text)
                
                response = self.send_to_ai(text)
                
                if response:
                    self.history.append({
                        "timestamp": datetime.now().isoformat(),
                        "question": text,
                        "answer": response,
                        "provider": self.ai_provider
                    })
                    
                    self.show_answer(text, response)
                    self.show_notification("✅ Готово!", "Ответ получен")
                else:
                    print("❌ Не удалось получить ответ от AI")
                
            except sr.UnknownValueError:
                print("⚠️ Не удалось распознать речь")
                self.show_notification("⚠️ Не понял", "Попробуйте говорить четче")
            except sr.RequestError as e:
                print(f"❌ Ошибка распознавания: {e}")
                
        except Exception as e:
            print(f"❌ Ошибка обработки: {e}")

    def send_to_ai(self, question):
        """Отправляет вопрос в AI и получает ответ"""
        if self.ai_provider == "ollama":
            return self.send_to_ollama(question)
        elif self.ai_provider == "deepseek":
            return self.send_to_deepseek(question)
        elif self.ai_provider == "qwen":
            return self.send_to_qwen(question)
        else:
            return None

    def send_to_ollama(self, question):
        """Отправляет вопрос в Ollama"""
        try:
            config = self.config.get('ollama', {})
            url = f"{config.get('base_url', 'http://localhost:11434/api')}/generate"
            
            payload = {
                "model": config.get('model', 'qwen2:7b'),
                "prompt": f"Ты помощник для технических собеседований. Отвечай кратко и по делу.\n\nВопрос: {question}",
                "stream": False
            }
            
            print("🤖 Получаю ответ от Ollama...")
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                return response.json().get('response', '')
            else:
                return None
                
        except Exception as e:
            return None

    def send_to_deepseek(self, question):
        """Отправляет вопрос в DeepSeek API"""
        try:
            config = self.config.get('deepseek', {})
            api_key = config.get('api_key', '')
            
            if not api_key:
                return "❌ DeepSeek API ключ не настроен в config.json"
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": config.get('model', 'deepseek-coder'),
                "messages": [
                    {"role": "system", "content": "Ты помощник для технических собеседований. Отвечай кратко, четко и по делу."},
                    {"role": "user", "content": question}
                ],
                "max_tokens": 2000
            }
            
            print("🤖 Получаю ответ от DeepSeek...")
            response = requests.post(
                f"{config.get('base_url', 'https://api.deepseek.com/v1')}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                return f"❌ DeepSeek ошибка: {response.status_code}"
                
        except Exception as e:
            return f"❌ DeepSeek ошибка: {str(e)}"

    def send_to_qwen(self, question):
        """Отправляет вопрос в Qwen API"""
        try:
            config = self.config.get('qwen', {})
            api_key = config.get('api_key', '')
            
            if not api_key:
                return "❌ Qwen API ключ не настроен в config.json"
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": config.get('model', 'qwen-max'),
                "messages": [
                    {"role": "system", "content": "Ты помощник для технических собеседований. Отвечай кратко, четко и по делу."},
                    {"role": "user", "content": question}
                ],
                "max_tokens": 2000
            }
            
            print("🤖 Получаю ответ от Qwen...")
            response = requests.post(
                f"{config.get('base_url', 'https://dashscope.aliyuncs.com/compatible-mode/v1')}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                return f"❌ Qwen ошибка: {response.status_code}"
                
        except Exception as e:
            return f"❌ Qwen ошибка: {str(e)}"

    def show_answer(self, question, answer):
        """Показывает вопрос и ответ в терминале"""
        print("\n" + "="*80)
        print(f"📅 {datetime.now().strftime('%H:%M:%S')}")
        print(f"❓ ВОПРОС: {question}")
        print("-"*80)
        print(f"💡 ОТВЕТ ({self.ai_provider.upper()}):")
        print(answer)
        print("="*80)

    def show_history(self):
        """Показывает историю вопросов и ответов"""
        if not self.history:
            print("📝 История пуста")
            return
        
        print("\n" + "="*80)
        print("📝 ИСТОРИЯ ВОПРОСОВ И ОТВЕТОВ")
        print("="*80)
        
        for i, item in enumerate(self.history[-5:], 1):
            timestamp = datetime.fromisoformat(item['timestamp']).strftime('%H:%M:%S')
            print(f"\n{i}. [{timestamp}] {item['provider'].upper()}")
            print(f"❓ {item['question']}")
            print(f"💡 {item['answer'][:200]}..." if len(item['answer']) > 200 else f"💡 {item['answer']}")
            print("-"*40)
        
        print("="*80)

    def show_settings(self):
        """Показывает настройки"""
        print("\n" + "="*80)
        print("⚙️  НАСТРОЙКИ")
        print("="*80)
        print(f"🤖 Текущий AI провайдер: {self.ai_provider.upper()}")
        print("\nДоступные провайдеры:")
        
        providers = {
            "ollama": "🐙 Ollama (локальный)",
            "deepseek": "🚀 DeepSeek (бесплатный)",
            "qwen": "🌟 Qwen (Alibaba)"
        }
        
        for key, desc in providers.items():
            status = "✅" if key == self.ai_provider else "⭕"
            print(f"  {status} {desc}")
        
        print(f"\n📄 Конфигурация: config.json")
        print(f"📝 История: {len(self.history)} вопросов")
        print("="*80)

    def show_menu(self):
        """Показывает главное меню"""
        print("\n" + "="*60)
        print("📋 ГЛАВНОЕ МЕНЮ")
        print("="*60)
        print("1. 🎤 Записать вопрос")
        print("2. 📝 Показать историю")
        print("3. ⚙️  Показать настройки")
        print("4. 🚪 Выход")
        print("="*60)

    def run(self):
        """Основной цикл программы"""
        print("🤖 Interview Assistant - Упрощенная версия")
        print("="*80)
        print(f"🤖 AI Провайдер: {self.ai_provider.upper()}")
        print("🎤 Распознавание: Google Speech API")
        print("💻 Система: macOS (без глобальных горячих клавиш)")
        print("")
        print("💡 ИНСТРУКЦИЯ:")
        print("   1. Выберите '1' в меню")
        print("   2. Говорите вопрос интервьюера")
        print("   3. Нажмите Enter когда закончите")
        print("   4. Получайте ответ в терминале")
        print("="*80)
        
        self.show_notification("🚀 Interview Assistant", "Упрощенная версия запущена!")

        try:
            while True:
                self.show_menu()
                
                try:
                    choice = input("\n👉 Ваш выбор (1-4): ").strip()
                    
                    if choice == '1':
                        self.record_audio()
                    elif choice == '2':
                        self.show_history()
                    elif choice == '3':
                        self.show_settings()
                    elif choice == '4':
                        print("👋 До свидания!")
                        self.show_notification("👋 Завершение", "До свидания!")
                        break
                    else:
                        print("⚠️ Неверный выбор. Введите 1, 2, 3 или 4")
                        
                except KeyboardInterrupt:
                    print("\n👋 Завершение по Ctrl+C...")
                    break
                    
        except Exception as e:
            print(f"❌ Ошибка: {e}")

def check_dependencies():
    """Проверяет установлены ли все зависимости"""
    required_packages = {
        'speech_recognition': 'pip install SpeechRecognition',
        'requests': 'pip install requests'
    }
    
    missing = []
    for package, install_cmd in required_packages.items():
        try:
            __import__(package)
        except ImportError:
            missing.append((package, install_cmd))
    
    if missing:
        print("❌ Отсутствуют зависимости:")
        for package, cmd in missing:
            print(f"   {cmd}")
        print("\nУстановите и запустите снова.")
        return False
    
    return True

def check_ai_provider(config):
    """Проверяет доступность AI провайдера"""
    provider = config.get('ai_provider', 'ollama')
    
    if provider == 'ollama':
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            return response.status_code == 200
        except:
            print("❌ Ollama не запущен. Запустите: brew services start ollama")
            return False
    
    elif provider in ['deepseek', 'qwen']:
        api_key = config.get(provider, {}).get('api_key', '')
        if not api_key:
            print(f"❌ {provider.title()} API ключ не настроен в config.json")
            return False
        return True
    
    return False

if __name__ == "__main__":
    print("🚀 Запуск Interview Assistant (упрощенная версия)...")
    print("")
    
    if not check_dependencies():
        sys.exit(1)
    
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
    except:
        print("❌ config.json не найден или поврежден")
        sys.exit(1)
    
    if not check_ai_provider(config):
        print(f"💡 Настройте AI провайдера в config.json")
        sys.exit(1)
    
    print("✅ Все проверки пройдены!")
    print("")
    
    assistant = SimpleInterviewAssistant()
    assistant.run() 