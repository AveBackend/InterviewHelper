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
import pyaudio
import wave
import numpy as np

class SystemAudioTranscriber:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.rust_api_url = "http://127.0.0.1:3030"
        
        self.audio_format = pyaudio.paInt16
        self.channels = 2
        self.rate = 44100
        self.chunk_size = 1024
        self.recording = False
        
        self.audio = pyaudio.PyAudio()
        
        self.find_blackhole_device()
        
        self.check_rust_service()

    def find_blackhole_device(self):
        """Находит BlackHole аудио устройство"""
        self.blackhole_device = None
        
        print("🔍 Ищу BlackHole устройство...")
        
        for i in range(self.audio.get_device_count()):
            device_info = self.audio.get_device_info_by_index(i)
            device_name = device_info['name'].lower()
            
            print(f"   Устройство {i}: {device_info['name']}")
            
            if 'blackhole' in device_name:
                self.blackhole_device = i
                print(f"✅ Найдено BlackHole устройство: {device_info['name']} (ID: {i})")
                break
        
        if self.blackhole_device is None:
            print("❌ BlackHole устройство не найдено!")
            print("💡 Инструкция:")
            print("   1. Установите: brew install blackhole-2ch")
            print("   2. Перезагрузите Mac")
            print("   3. Audio MIDI Setup → Create Multi-Output Device")
            print("   4. Включите Built-in Output + BlackHole 2ch")
            print("   5. Установите этот Multi-Output как системный выход звука")
            sys.exit(1)

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

    def record_system_audio(self, duration=30):
        """Записывает системное аудио"""
        try:
            print(f"\n🎧 ЗАХВАТ СИСТЕМНОГО ЗВУКА!")
            print(f"⏱️  Максимум {duration} секунд. Нажмите Enter когда закончите.")
            print("🔊 Убедитесь что звук из браузера/приложений идёт через Multi-Output Device")
            
            stream = self.audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=self.blackhole_device,
                frames_per_buffer=self.chunk_size
            )
            
            audio_data = []
            self.recording = True
            recording_complete = threading.Event()
            
            def record():
                try:
                    frames = []
                    start_time = time.time()
                    
                    while self.recording and (time.time() - start_time) < duration:
                        data = stream.read(self.chunk_size, exception_on_overflow=False)
                        frames.append(data)
                        
                        audio_array = np.frombuffer(data, dtype=np.int16)
                        volume = np.sqrt(np.mean(audio_array**2))
                        
                        if volume > 500:
                            print("🔉", end="", flush=True)
                        else:
                            print(".", end="", flush=True)
                    
                    audio_data.extend(frames)
                    recording_complete.set()
                    
                except Exception as e:
                    print(f"\n❌ Ошибка записи: {e}")
                    recording_complete.set()
            
            record_thread = threading.Thread(target=record)
            record_thread.daemon = True
            record_thread.start()
            
            input()
            self.recording = False
            print("\n🛑 Запись остановлена...")
            
            recording_complete.wait(timeout=2)
            stream.close()
            
            if audio_data:
                temp_filename = "temp_system_audio.wav"
                with wave.open(temp_filename, 'wb') as wf:
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(self.audio.get_sample_size(self.audio_format))
                    wf.setframerate(self.rate)
                    wf.writeframes(b''.join(audio_data))
                
                self.transcribe_system_audio(temp_filename)
            else:
                print("❌ Аудио не записано")
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")

    def transcribe_system_audio(self, audio_file):
        """Транскрибирует системное аудио"""
        try:
            print("🔄 Транскрибирую системный звук...")
            
            with sr.AudioFile(audio_file) as source:
                audio = self.recognizer.record(source)
            
            text = self.recognizer.recognize_google(audio, language="ru-RU")
            text = text.strip()
            
            if not text:
                print("⚠️ В записи не обнаружена речь")
                return
                
            print(f"🎯 Транскрипция системного звука: {text}")
            print("🦀 Отправляю в Rust сервис...")
            print("-" * 80)
            
            self.send_to_rust_streaming(text)
            
            import os
            try:
                os.remove(audio_file)
            except:
                pass
                
        except sr.UnknownValueError:
            print("⚠️ В системном звуке не распознана речь")
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
                            chunk = data['content']
                            print(chunk, end='', flush=True)
                            full_response.append(chunk)
                            
                        elif data['type'] == 'done':
                            print("\n" + "="*80)
                            print(f"📅 {datetime.now().strftime('%H:%M:%S')} - Ответ получен!")
                            
                            clean_response = data['content']
                            
                            print(f"💡 Полный ответ: {clean_response}")
                            print("="*80)
                            break
                            
                        elif data['type'] == 'error':
                            print(f"\n❌ Ошибка: {data['content']}")
                            break
                            
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            print(f"❌ Ошибка при работе с Rust API: {e}")

    def monitor_system_audio(self):
        """Непрерывный мониторинг системного аудио"""
        print("\n🎧 РЕЖИМ МОНИТОРИНГА СИСТЕМНОГО ЗВУКА")
        print("="*70)
        print("💡 Нажмите Enter когда услышите вопрос интервьюера")
        print("🔊 Звук должен идти через Multi-Output Device с BlackHole")
        print("🛑 Нажмите Ctrl+C для выхода")
        print("="*70)
        
        try:
            while True:
                input("\n👉 Нажмите Enter чтобы начать захват звука...")
                self.record_system_audio(duration=30)
                
        except KeyboardInterrupt:
            print("\n👋 Завершение мониторинга...")

    def show_menu(self):
        """Показывает главное меню"""
        print("\n" + "="*70)
        print("🎧 СИСТЕМНЫЙ АУДИО ПОМОЩНИК (Python + Rust)")
        print("="*70)
        print("1. 🎯 Одиночный захват (30 сек)")
        print("2. 🔄 Непрерывный мониторинг")
        print("3. 🔧 Показать аудио устройства")
        print("4. 🚪 Выход")
        print("="*70)

    def show_audio_devices(self):
        """Показывает доступные аудио устройства"""
        print("\n📱 ДОСТУПНЫЕ АУДИО УСТРОЙСТВА:")
        print("="*50)
        
        for i in range(self.audio.get_device_count()):
            device_info = self.audio.get_device_info_by_index(i)
            device_type = "🎤" if device_info['maxInputChannels'] > 0 else "🔊"
            current = " ← ТЕКУЩЕЕ" if i == self.blackhole_device else ""
            
            print(f"{device_type} {i}: {device_info['name']}{current}")
        
        print("="*50)

    def run(self):
        """Основной цикл программы"""
        print("🚀 System Audio Transcriber + Rust Ollama Service")
        print("="*80)
        print("🎧 Захват: Системный звук (BlackHole)")
        print("🦀 Обработка: Rust + Ollama")
        print("⚡ Режим: Real-time streaming")
        print("="*80)

        try:
            while True:
                self.show_menu()
                
                try:
                    choice = input("\n👉 Ваш выбор (1-4): ").strip()
                    
                    if choice == '1':
                        print("🎯 Режим: Одиночный захват")
                        self.record_system_audio()
                    elif choice == '2':
                        print("🔄 Режим: Непрерывный мониторинг")
                        self.monitor_system_audio()
                    elif choice == '3':
                        self.show_audio_devices()
                    elif choice == '4':
                        print("👋 До свидания!")
                        break
                    else:
                        print("⚠️ Неверный выбор. Введите 1, 2, 3 или 4")
                        
                except KeyboardInterrupt:
                    print("\n👋 Завершение по Ctrl+C...")
                    break
                    
        except Exception as e:
            print(f"❌ Ошибка: {e}")
        finally:
            self.audio.terminate()

if __name__ == "__main__":
    print("🚀 Запуск System Audio Transcriber...")
    print("💡 Убедитесь что Rust сервис запущен: cargo run")
    print("")
    
    required_packages = {
        'speech_recognition': 'SpeechRecognition',
        'sseclient': 'sseclient-py', 
        'requests': 'requests',
        'pyaudio': 'pyaudio',
        'numpy': 'numpy'
    }
    
    missing = []
    for module, package in required_packages.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    
    if missing:
        print("❌ Установите недостающие зависимости:")
        print(f"   pip install {' '.join(missing)}")
        sys.exit(1)
    
    transcriber = SystemAudioTranscriber()
    transcriber.run() 