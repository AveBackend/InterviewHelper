#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import speech_recognition as sr
import requests
import json
import threading
import time
import sys
from datetime import datetime
import sseclient

class VoiceTranscriber:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.rust_api_url = "http://127.0.0.1:3030"
        
        self.setup_microphone()
        
        self.check_rust_service()

    def setup_microphone(self):
        """Настраивает микрофон"""
        try:
            print("🎤 Настраиваю микрофон...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("✅ Микрофон готов!")
        except Exception as e:
            print(f"❌ Ошибка микрофона: {e}")

    def check_rust_service(self):
        """Проверяет доступность Rust сервиса"""
        try:
            print("🔗 Проверяю Rust сервис...")
            response = requests.get(f"{self.rust_api_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Rust сервис доступен: {data.get('service', 'unknown')}")
            else:
                raise Exception(f"HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ Rust сервис недоступен: {e}")
            print("💡 Запустите: cargo run")
            sys.exit(1)

    def record_audio(self):
        """Записывает аудио"""
        try:
            print("\n🎤 ЗАПИСЬ НАЧАЛАСЬ! Говорите вопрос...")
            print("⏱️  Максимум 30 секунд. Нажмите Enter когда закончите.")
            
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
                self.transcribe_and_process(audio)
            else:
                print("❌ Аудио не записано")
                
        except KeyboardInterrupt:
            print("\n🛑 Запись прервана")
        except Exception as e:
            print(f"❌ Ошибка: {e}")

    def transcribe_and_process(self, audio):
        """Транскрибирует аудио и отправляет в Rust сервис"""
        try:
            print("🔄 Транскрибирую речь...")
            
            text = self.recognizer.recognize_google(audio, language="ru-RU")
            text = text.strip()
            
            if not text:
                print("⚠️ Пустой текст")
                return
                
            print(f"🎯 Транскрипция: {text}")
            print("🦀 Отправляю в Rust сервис...")
            print("-" * 80)
            
            self.send_to_rust_streaming(text)
                
        except sr.UnknownValueError:
            print("⚠️ Не удалось распознать речь")
        except sr.RequestError as e:
            print(f"❌ Ошибка распознавания: {e}")
        except Exception as e:
            print(f"❌ Ошибка транскрипции: {e}")

    def send_to_rust_streaming(self, question):
        """Отправляет вопрос в Rust сервис и получает streaming ответ"""
        try:
            payload = {"question": question}
            
            response = requests.post(
                f"{self.rust_api_url}/stream",
                json=payload,
                headers={"Accept": "text/event-stream"},
                stream=True,
                timeout=60
            )
            
            if response.status_code != 200:
                print(f"❌ Ошибка Rust API: {response.status_code}")
                return
            
            client = sseclient.SSEClient(response)
            full_response = []
            
            for event in client.events():
                if event.data:
                    try:
                        data = json.loads(event.data)
                        
                        if data['type'] == 'word':
                            print(data['content'], end=' ', flush=True)
                            full_response.append(data['content'])
                            
                        elif data['type'] == 'done':
                            print("\n" + "="*80)
                            print(f"📅 {datetime.now().strftime('%H:%M:%S')} - Ответ получен!")
                            print(f"💡 Полный ответ: {' '.join(full_response)}")
                            print("="*80)
                            break
                            
                        elif data['type'] == 'error':
                            print(f"\n❌ Ошибка: {data['content']}")
                            break
                            
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            print(f"❌ Ошибка при работе с Rust API: {e}")

    def send_to_rust_simple(self, question):
        """Простой non-streaming запрос (для тестирования)"""
        try:
            payload = {"question": question}
            
            response = requests.post(
                f"{self.rust_api_url}/ask",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print("="*80)
                print(f"📅 {datetime.now().strftime('%H:%M:%S')}")
                print(f"❓ ВОПРОС: {question}")
                print("-"*80)
                print(f"💡 ОТВЕТ (RUST+OLLAMA):")
                print(data['content'])
                print("="*80)
            else:
                print(f"❌ Ошибка API: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Ошибка при работе с Rust API: {e}")

    def show_menu(self):
        """Показывает главное меню"""
        print("\n" + "="*70)
        print("🎤 ГОЛОСОВОЙ ПОМОЩНИК (Python + Rust)")
        print("="*70)
        print("1. 🌊 Записать вопрос (STREAMING - быстро)")
        print("2. 📝 Записать вопрос (обычный режим)")
        print("3. 🚪 Выход")
        print("="*70)

    def run(self):
        """Основной цикл программы"""
        print("🚀 Voice Transcriber + Rust Ollama Service")
        print("="*80)
        print("🐍 Python: Транскрипция речи (Speech Recognition)")
        print("🦀 Rust: Ollama API + максимальная скорость")
        print("⚡ Архитектура: Разделение ответственности")
        print("="*80)

        try:
            while True:
                self.show_menu()
                
                try:
                    choice = input("\n👉 Ваш выбор (1-3): ").strip()
                    
                    if choice == '1':
                        print("🌊 Режим: Streaming (слово за словом)")
                        self.record_audio()
                    elif choice == '2':
                        print("📝 Режим: Обычный (полный ответ)")
                        self.record_audio_simple()
                    elif choice == '3':
                        print("👋 До свидания!")
                        break
                    else:
                        print("⚠️ Неверный выбор. Введите 1, 2 или 3")
                        
                except KeyboardInterrupt:
                    print("\n👋 Завершение по Ctrl+C...")
                    break
                    
        except Exception as e:
            print(f"❌ Ошибка: {e}")

    def record_audio_simple(self):
        """Записывает аудио для простого режима"""
        try:
            print("\n🎤 ЗАПИСЬ НАЧАЛАСЬ! Говорите вопрос...")
            print("⏱️  Максимум 30 секунд. Нажмите Enter когда закончите.")
            
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
                print("🔄 Транскрибирую речь...")
                text = self.recognizer.recognize_google(audio, language="ru-RU")
                text = text.strip()
                
                if text:
                    print(f"🎯 Транскрипция: {text}")
                    print("🦀 Отправляю в Rust сервис...")
                    self.send_to_rust_simple(text)
                else:
                    print("⚠️ Пустой текст")
            else:
                print("❌ Аудио не записано")
                
        except sr.UnknownValueError:
            print("⚠️ Не удалось распознать речь")
        except sr.RequestError as e:
            print(f"❌ Ошибка распознавания: {e}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    print("🚀 Запуск Voice Transcriber...")
    print("💡 Убедитесь что Rust сервис запущен: cargo run")
    print("")
    
    try:
        import speech_recognition
    except ImportError:
        print("❌ Установите SpeechRecognition: pip install SpeechRecognition")
        sys.exit(1)
    
    try:
        import sseclient
    except ImportError:
        print("❌ Установите sseclient: pip install sseclient-py")
        sys.exit(1)
    
    try:
        import requests
    except ImportError:
        print("❌ Установите requests: pip install requests")
        sys.exit(1)
    
    transcriber = VoiceTranscriber()
    transcriber.run() 