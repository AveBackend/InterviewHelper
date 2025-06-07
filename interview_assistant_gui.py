#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
import requests
import json
import speech_recognition as sr
import pyaudio
import wave
import numpy as np
import sseclient
from datetime import datetime
import sys
import os
import subprocess
import tempfile
import base64

class InterviewAssistantGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎧 Interview Assistant - System Audio")
        self.root.geometry("900x700")
        self.root.configure(bg='#2b2b2b')
        
        self.rust_api_url = "http://127.0.0.1:3030"
        self.recording = False
        self.generating = False
        self.blackhole_device = None
        
        self.selection_window = None
        self.selecting = False
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        
        self.conversation_history = []
        self.max_history_length = 10
        self.context_enabled = True
        
        self.auto_scroll = True
        self.user_scrolling = False
        self.last_user_scroll_time = 0
        
        self.setup_audio()
        
        self.create_interface()
        
        self.check_services()

    def setup_audio(self):
        """Настройка аудио системы"""
        try:
            self.recognizer = sr.Recognizer()
            self.audio = pyaudio.PyAudio()
            self.find_blackhole_device()
        except Exception as e:
            messagebox.showerror("Ошибка аудио", f"Не удалось инициализировать аудио: {e}")
            sys.exit(1)

    def find_blackhole_device(self):
        """Поиск BlackHole устройства"""
        for i in range(self.audio.get_device_count()):
            device_info = self.audio.get_device_info_by_index(i)
            if 'blackhole' in device_info['name'].lower():
                self.blackhole_device = i
                return
        
        messagebox.showwarning(
            "BlackHole не найден",
            "BlackHole аудио устройство не найдено!\n\n"
            "Инструкция:\n"
            "1. Установите: brew install blackhole-2ch\n"
            "2. Перезагрузите Mac\n"
            "3. Audio MIDI Setup → Create Multi-Output Device\n"
            "4. Включите Built-in Output + BlackHole 2ch"
        )

    def create_interface(self):
        """Создание графического интерфейса"""
        style = ttk.Style()
        style.theme_use('clam')
        
        title_frame = tk.Frame(self.root, bg='#2b2b2b')
        title_frame.pack(fill='x', padx=10, pady=5)
        
        title_label = tk.Label(
            title_frame,
            text="🎧 Interview Assistant - System Audio",
            font=('Arial', 16, 'bold'),
            fg='#ffffff',
            bg='#2b2b2b'
        )
        title_label.pack()
        
        self.status_frame = tk.Frame(self.root, bg='#2b2b2b')
        self.status_frame.pack(fill='x', padx=10, pady=5)
        
        self.rust_status = tk.Label(
            self.status_frame,
            text="🔗 Rust Service: Проверка...",
            font=('Arial', 10),
            fg='#ffaa00',
            bg='#2b2b2b'
        )
        self.rust_status.pack(side='left')
        
        self.audio_status = tk.Label(
            self.status_frame,
            text="🎤 BlackHole: Проверка...",
            font=('Arial', 10),
            fg='#ffaa00',
            bg='#2b2b2b'
        )
        self.audio_status.pack(side='right')
        
        self.history_status = tk.Label(
            self.status_frame,
            text="💬 История: 0 сообщений",
            font=('Arial', 10),
            fg='#4CAF50',
            bg='#2b2b2b'
        )
        self.history_status.pack(side='left', padx=(20, 0))
        
        control_frame = tk.Frame(self.root, bg='#2b2b2b')
        control_frame.pack(fill='x', padx=10, pady=10)
        
        self.record_button = tk.Button(
            control_frame,
            text="🎤 Начать захват звука",
            font=('Arial', 12, 'bold'),
            bg='#4CAF50',
            fg='white',
            activebackground='#45a049',
            command=self.toggle_recording,
            height=2,
            width=20
        )
        self.record_button.pack(side='left', padx=5)
        
        self.stop_generation_button = tk.Button(
            control_frame,
            text="⏹️ Стоп генерация",
            font=('Arial', 12, 'bold'),
            bg='#ff9800',
            fg='white',
            activebackground='#e68900',
            command=self.stop_generation,
            height=2,
            width=15,
            state='disabled'
        )
        self.stop_generation_button.pack(side='left', padx=5)
        
        self.clear_button = tk.Button(
            control_frame,
            text="🗑️ Очистить",
            font=('Arial', 12),
            bg='#f44336',
            fg='white',
            activebackground='#da190b',
            command=self.clear_log,
            height=2,
            width=12
        )
        self.clear_button.pack(side='right', padx=5)
        
        ocr_state = 'normal'
        
        self.quick_ocr_button = tk.Button(
            control_frame,
            text="⚡ Быстрый OCR",
            font=('Arial', 11, 'bold'),
            bg='#673AB7',
            fg='white',
            activebackground='#5E35B1',
            command=self.quick_ocr_capture,
            height=2,
            width=12,
            state=ocr_state
        )
        self.quick_ocr_button.pack(side='left', padx=2)
        
        self.context_toggle_button = tk.Button(
            control_frame,
            text="🧠 Контекст: ВКЛ",
            font=('Arial', 10, 'bold'),
            bg='#4CAF50',
            fg='white',
            activebackground='#45a049',
            command=self.toggle_context,
            height=2,
            width=12
        )
        self.context_toggle_button.pack(side='left', padx=2)
        
        self.clear_history_button = tk.Button(
            control_frame,
            text="🗑️ Очистить\nисторию",
            font=('Arial', 9, 'bold'),
            bg='#ff5722',
            fg='white',
            activebackground='#e64a19',
            command=self.clear_conversation_history,
            height=2,
            width=10
        )
        self.clear_history_button.pack(side='left', padx=2)
        
        self.auto_scroll_button = tk.Button(
            control_frame,
            text="📜 Авто-\nпрокрутка",
            font=('Arial', 9, 'bold'),
            bg='#4CAF50',
            fg='white',
            activebackground='#45a049',
            command=self.toggle_auto_scroll,
            height=2,
            width=10
        )
        self.auto_scroll_button.pack(side='left', padx=2)
        
        image_frame = tk.Frame(self.root, bg='#2b2b2b')
        image_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(
            image_frame,
            text="📸 Анализ изображений:",
            font=('Arial', 12, 'bold'),
            fg='#ffffff',
            bg='#2b2b2b'
        ).pack(anchor='w')
        
        self.drop_frame = tk.Frame(
            image_frame,
            bg='#404040',
            relief='ridge',
            bd=2,
            height=80
        )
        self.drop_frame.pack(fill='x', pady=5)
        self.drop_frame.pack_propagate(False)
        
        self.drop_label = tk.Label(
            self.drop_frame,
            text="📁 Перетащите изображение сюда или нажмите для выбора файла\n"
                 "Поддерживаются: PNG, JPG, JPEG, GIF, BMP",
            font=('Arial', 10),
            fg='#cccccc',
            bg='#404040',
            justify='center'
        )
        self.drop_label.pack(expand=True)
        
        comment_frame = tk.Frame(image_frame, bg='#2b2b2b')
        comment_frame.pack(fill='x', pady=5)
        
        tk.Label(
            comment_frame,
            text="💬 Комментарий к изображению:",
            font=('Arial', 10, 'bold'),
            fg='#ffffff',
            bg='#2b2b2b'
        ).pack(anchor='w')
        
        self.image_comment = tk.Text(
            comment_frame,
            height=2,
            wrap=tk.WORD,
            bg='#1e1e1e',
            fg='#ffffff',
            font=('Arial', 10),
            insertbackground='white'
        )
        self.image_comment.pack(fill='x', pady=2)
        
        self.setup_drag_drop()
        
        self.setup_hotkeys()
        
        question_frame = tk.Frame(self.root, bg='#2b2b2b')
        question_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(
            question_frame,
            text="✏️ Редактировать запрос:",
            font=('Arial', 12, 'bold'),
            fg='#ffffff',
            bg='#2b2b2b'
        ).pack(anchor='w')
        
        input_frame = tk.Frame(question_frame, bg='#2b2b2b')
        input_frame.pack(fill='x', pady=5)
        
        self.question_text = tk.Text(
            input_frame,
            height=3,
            wrap=tk.WORD,
            bg='#1e1e1e',
            fg='#ffffff',
            font=('Arial', 11),
            insertbackground='white'
        )
        self.question_text.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        self.send_button = tk.Button(
            input_frame,
            text="📤\nОтправить",
            font=('Arial', 10, 'bold'),
            bg='#2196F3',
            fg='white',
            activebackground='#1976D2',
            command=self.send_question,
            width=10
        )
        self.send_button.pack(side='right')
        
        self.paste_text_button = tk.Button(
            input_frame,
            text="📋\nВставить\nтекст",
            font=('Arial', 9, 'bold'),
            bg='#FF9800',
            fg='white',
            activebackground='#F57C00',
            command=self.paste_text_from_clipboard,
            width=8
        )
        self.paste_text_button.pack(side='right', padx=(0, 5))
        
        self.paste_image_button = tk.Button(
            input_frame,
            text="🖼️\nВставить\nкартинку",
            font=('Arial', 9, 'bold'),
            bg='#9C27B0',
            fg='white',
            activebackground='#7B1FA2',
            command=self.paste_image_from_clipboard,
            width=8
        )
        self.paste_image_button.pack(side='right', padx=(0, 5))
        
        self.recording_frame = tk.Frame(self.root, bg='#2b2b2b')
        self.recording_frame.pack(fill='x', padx=10, pady=5)
        
        self.recording_indicator = tk.Label(
            self.recording_frame,
            text="⚪ Готов к записи",
            font=('Arial', 12, 'bold'),
            fg='#888888',
            bg='#2b2b2b'
        )
        self.recording_indicator.pack()
        
        log_frame = tk.Frame(self.root, bg='#2b2b2b')
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        log_header_frame = tk.Frame(log_frame, bg='#2b2b2b')
        log_header_frame.pack(fill='x')
        
        tk.Label(
            log_header_frame,
            text="📋 Лог вопросов и ответов:",
            font=('Arial', 12, 'bold'),
            fg='#ffffff',
            bg='#2b2b2b'
        ).pack(side='left')
        
        self.jump_to_end_button = tk.Button(
            log_header_frame,
            text="⬇️ В конец",
            font=('Arial', 9, 'bold'),
            bg='#2196F3',
            fg='white',
            activebackground='#1976D2',
            command=self.jump_to_end,
            height=1,
            width=8
        )
        self.jump_to_end_button.pack(side='right')
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            width=80,
            height=20,
            bg='#1e1e1e',
            fg='#ffffff',
            font=('Consolas', 11),
            insertbackground='white'
        )
        self.log_text.pack(fill='both', expand=True, pady=5)
        
        self.setup_scroll_tracking()
        
        settings_frame = tk.Frame(self.root, bg='#2b2b2b')
        settings_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(
            settings_frame,
            text="⚙️ Настройки:",
            font=('Arial', 10, 'bold'),
            fg='#ffffff',
            bg='#2b2b2b'
        ).pack(side='left')
        
        self.duration_var = tk.StringVar(value="30")
        tk.Label(
            settings_frame,
            text="Длительность записи (сек):",
            font=('Arial', 10),
            fg='#ffffff',
            bg='#2b2b2b'
        ).pack(side='left', padx=(20, 5))
        
        duration_entry = tk.Entry(
            settings_frame,
            textvariable=self.duration_var,
            width=5,
            font=('Arial', 10)
        )
        duration_entry.pack(side='left')
        
        self.history_length_var = tk.StringVar(value="10")
        tk.Label(
            settings_frame,
            text="Длина истории:",
            font=('Arial', 10),
            fg='#ffffff',
            bg='#2b2b2b'
        ).pack(side='left', padx=(20, 5))
        
        history_entry = tk.Entry(
            settings_frame,
            textvariable=self.history_length_var,
            width=3,
            font=('Arial', 10)
        )
        history_entry.pack(side='left')
        
        history_entry.bind('<Return>', self.update_history_length)

    def check_services(self):
        """Проверка доступности сервисов"""
        try:
            response = requests.get(f"{self.rust_api_url}/health", timeout=5)
            if response.status_code == 200:
                self.rust_status.config(text="🔗 Rust Service: ✅ Работает", fg='#4CAF50')
            else:
                raise Exception(f"HTTP {response.status_code}")
        except Exception as e:
            self.rust_status.config(text="🔗 Rust Service: ❌ Недоступен", fg='#f44336')
            self.log("❌ Rust сервис недоступен. Запустите: cargo run")
        
        if self.blackhole_device is not None:
            self.audio_status.config(text="🎤 BlackHole: ✅ Найден", fg='#4CAF50')
        else:
            self.audio_status.config(text="🎤 BlackHole: ❌ Не найден", fg='#f44336')
        
        self.update_history_status()
        
        self.update_send_button_state()

    def log(self, message):
        """Добавление сообщения в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.smart_scroll_to_end()
        self.root.update_idletasks()

    def clear_log(self):
        """Очистка лога"""
        self.log_text.delete(1.0, tk.END)

    def toggle_recording(self):
        """Переключение записи"""
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        """Начало записи"""
        if self.blackhole_device is None:
            messagebox.showerror("Ошибка", "BlackHole устройство не найдено!")
            return
        
        self.recording = True
        self.record_button.config(text="🛑 Остановить запись", bg='#f44336')
        self.recording_indicator.config(text="🔴 Запись...", fg='#f44336')
        
        duration = int(self.duration_var.get())
        threading.Thread(target=self.record_audio, args=(duration,), daemon=True).start()

    def stop_recording(self):
        """Остановка записи"""
        self.recording = False
        self.record_button.config(text="🎤 Начать захват звука", bg='#4CAF50')
        self.recording_indicator.config(text="⚪ Готов к записи", fg='#888888')

    def record_audio(self, duration=30):
        """Запись системного аудио"""
        try:
            self.log(f"🎧 Начинаю захват системного звука ({duration} сек)")
            
            audio_format = pyaudio.paInt16
            channels = 2
            rate = 44100
            chunk_size = 1024
            
            stream = self.audio.open(
                format=audio_format,
                channels=channels,
                rate=rate,
                input=True,
                input_device_index=self.blackhole_device,
                frames_per_buffer=chunk_size
            )
            
            frames = []
            start_time = time.time()
            
            while self.recording and (time.time() - start_time) < duration:
                try:
                    data = stream.read(chunk_size, exception_on_overflow=False)
                    frames.append(data)
                    
                    audio_array = np.frombuffer(data, dtype=np.int16)
                    volume = np.sqrt(np.mean(audio_array**2))
                    
                    if volume > 500:
                        self.recording_indicator.config(text="🔴 Записываю звук...", fg='#4CAF50')
                    else:
                        self.recording_indicator.config(text="🔴 Жду звук...", fg='#f44336')
                        
                except Exception as e:
                    break
            
            stream.close()
            self.stop_recording()
            
            if frames:
                temp_filename = "temp_system_audio.wav"
                with wave.open(temp_filename, 'wb') as wf:
                    wf.setnchannels(channels)
                    wf.setsampwidth(self.audio.get_sample_size(audio_format))
                    wf.setframerate(rate)
                    wf.writeframes(b''.join(frames))
                
                self.transcribe_audio(temp_filename)
            else:
                self.log("❌ Аудио не записано")
                
        except Exception as e:
            self.log(f"❌ Ошибка записи: {e}")
            self.stop_recording()

    def transcribe_audio(self, audio_file):
        """Транскрипция аудио и получение ответа"""
        try:
            self.log("🔄 Транскрибирую аудио...")
            
            with sr.AudioFile(audio_file) as source:
                audio = self.recognizer.record(source)
            
            text = self.recognizer.recognize_google(audio, language="ru-RU")
            text = text.strip()
            
            if not text:
                self.log("⚠️ Речь не распознана")
                return
            
            self.log(f"🎯 Вопрос: {text}")
            
            self.question_text.delete(1.0, tk.END)
            self.question_text.insert(1.0, text)
            
            self.log("🦀 Получаю ответ от AI...")
            
            self.get_ai_response(text)
            
            try:
                os.remove(audio_file)
            except:
                pass
                
        except sr.UnknownValueError:
            self.log("⚠️ Речь не распознана")
        except sr.RequestError as e:
            self.log(f"❌ Ошибка API распознавания: {e}")
        except Exception as e:
            self.log(f"❌ Ошибка транскрипции: {e}")

    def get_ai_response(self, question):
        """Получение ответа от AI"""
        try:
            self.generating = True
            self.stop_generation_button.config(state='normal')
            
            self.update_send_button_state()
            
            self.conversation_history.append({
                "role": "user", 
                "content": question,
                "timestamp": datetime.now().isoformat()
            })
            
            if len(self.conversation_history) > self.max_history_length * 2:
                self.conversation_history = self.conversation_history[-self.max_history_length * 2:]
            
            self.update_history_status()
            
            self.log_conversation_context()
            
            payload = {
                "question": question,
                "conversation_history": self.conversation_history if self.context_enabled else [],
                "context_enabled": self.context_enabled
            }
            
            response = requests.post(
                f"{self.rust_api_url}/stream",
                json=payload,
                headers={"Accept": "text/event-stream"},
                stream=True,
                timeout=60
            )
            
            if response.status_code != 200:
                self.log(f"❌ Ошибка API: {response.status_code}")
                self.generating = False
                self.stop_generation_button.config(state='disabled')
                self.update_send_button_state()
                return
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert(tk.END, f"[{timestamp}] 💭 Ответ AI: ")
            self.smart_scroll_to_end()
            
            full_response = ""
            
            client = sseclient.SSEClient(response)
            
            for event in client.events():
                if not self.generating:
                    self.log_text.insert(tk.END, " [ОСТАНОВЛЕНО]\n")
                    break
                    
                if event.data:
                    try:
                        data = json.loads(event.data)
                        
                        if data['type'] == 'word':
                            chunk = data['content']
                            full_response += chunk
                            self.log_text.insert(tk.END, chunk)
                            self.smart_scroll_to_end()
                            self.root.update_idletasks()
                            
                        elif data['type'] == 'done':
                            final_answer = data['content']
                            self.log_text.insert(tk.END, "\n")
                            self.log(f"✅ Полный ответ: {final_answer}")
                            
                            if self.context_enabled:
                                self.conversation_history.append({
                                    "role": "assistant",
                                    "content": final_answer or full_response,
                                    "timestamp": datetime.now().isoformat()
                                })
                                self.update_history_status()
                            
                            self.log("="*60)
                            break
                            
                        elif data['type'] == 'error':
                            self.log_text.insert(tk.END, "\n")
                            self.log(f"❌ Ошибка AI: {data['content']}")
                            break
                            
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            self.log(f"❌ Ошибка получения ответа: {e}")
        finally:
            self.generating = False
            self.stop_generation_button.config(state='disabled')
            self.update_send_button_state()

    def update_send_button_state(self):
        """Обновление состояния кнопки отправки в зависимости от генерации"""
        if self.generating:
            self.send_button.config(
                text="⏹️\nОстановить\nи отправить",
                bg='#FF5722',
                activebackground='#E64A19'
            )
        else:
            self.send_button.config(
                text="📤\nОтправить",
                bg='#2196F3',
                activebackground='#1976D2'
            )

    def update_streaming_response(self, response_text):
        """Удалена - больше не используется"""
        pass

    def update_last_line(self, new_text):
        """Устаревшая функция - удалена"""
        pass

    def run(self):
        """Запуск приложения"""
        self.log("🚀 Interview Assistant запущен!")
        self.log("💡 Инструкция:")
        self.log("   1. Убедитесь что звук идет через Multi-Output Device")
        self.log("   2. Нажмите 'Начать захват звука'")
        self.log("   3. Говорите или воспроизводите вопрос")
        self.log("   4. Нажмите 'Остановить запись' или дождитесь автостопа")
        self.log("   5. Перетащите изображение в область drag&drop для анализа")
        self.log("⌨️  Горячие клавиши:")
        self.log("   • Cmd+V - автоматическая вставка (текст или изображение)")
        self.log("   • Cmd+Shift+V - принудительная вставка изображения")
        self.log("💡 Быстрый OCR: Cmd+Shift+4 → выделить → Cmd+V")
        self.log("🧠 История диалога:")
        self.log("   • AI запоминает предыдущие вопросы и ответы")
        self.log("   • Кнопка 'Контекст' - включить/выключить память")
        self.log("   • Кнопка 'Очистить историю' - сбросить память")
        self.log("   • Настройка 'Длина истории' - количество запоминаемых сообщений")
        self.log("📜 Управление прокруткой:")
        self.log("   • Кнопка 'Авто-прокрутка' - включить/выключить автоматическую прокрутку")
        self.log("   • Кнопка '⬇️ В конец' - быстрый переход к последним сообщениям")
        self.log("   • Автопрокрутка останавливается на 3 секунды при ручной прокрутке")
        self.log("="*60)
        
        self.root.mainloop()

    def stop_generation(self):
        """Остановка генерации ответа"""
        self.generating = False
        self.stop_generation_button.config(state='disabled')
        self.update_send_button_state()
        self.log("🛑 Генерация остановлена пользователем")

    def send_question(self):
        """Отправка текстового вопроса"""
        question = self.question_text.get(1.0, tk.END).strip()
        if not question:
            messagebox.showwarning("Пустой запрос", "Введите вопрос в текстовое поле")
            return
        
        if self.generating:
            self.log("🛑 Остановка текущей генерации для нового вопроса...")
            self.generating = False
            self.root.after(100, lambda: self._send_new_question(question))
        else:
            self._send_new_question(question)

    def _send_new_question(self, question):
        """Отправка нового вопроса (внутренний метод)"""
        self.log(f"✏️ Текстовый вопрос: {question}")
        self.log("🦀 Получаю ответ от AI...")
        
        threading.Thread(target=self.get_ai_response, args=(question,), daemon=True).start()

    def setup_drag_drop(self):
        """Настройка drag&drop функциональности"""
        self.drop_label.bind('<Button-1>', self.select_image_file)
        self.drop_frame.bind('<Button-1>', self.select_image_file)
        
        self.drop_label.bind('<Button-1>', self.select_image_file)

    def select_image_file(self, event=None):
        """Выбор файла изображения"""
        try:
            file_path = filedialog.askopenfilename(
                title="Выберите изображение для анализа",
                initialdir=os.path.expanduser("~/Desktop"),
                filetypes=[
                    ("Изображения", "*.png *.jpg *.jpeg *.gif *.bmp"),
                    ("PNG файлы", "*.png"),
                    ("JPG файлы", "*.jpg *.jpeg"),
                    ("Все файлы", "*.*")
                ]
            )
            
            if file_path:
                self.process_image_file(file_path)
                
        except Exception as e:
            self.log(f"❌ Ошибка выбора файла: {e}")

    def process_image_file(self, file_path):
        """Обработка выбранного изображения"""
        try:
            self.log(f"📁 Обрабатываю изображение: {os.path.basename(file_path)}")
            
            self.drop_label.config(
                text=f"✅ Выбрано: {os.path.basename(file_path)}\n"
                     "Нажмите снова для выбора другого файла",
                fg='#90EE90'
            )
            
            threading.Thread(target=self.perform_ocr_analysis, args=(file_path,), daemon=True).start()
            
        except Exception as e:
            self.log(f"❌ Ошибка обработки изображения: {e}")

    def perform_ocr_analysis(self, image_path):
        """Выполнение OCR анализа изображения"""
        try:
            self.log("🔍 Распознаю текст из изображения...")
            
            user_comment = self.image_comment.get(1.0, tk.END).strip()
            
            extracted_text = ""
            
            extracted_text = self.extract_text_online_ocr(image_path)
            
            if not extracted_text:
                extracted_text = self.manual_text_input(image_path)
            
            if extracted_text:
                self.log(f"📝 Распознанный текст: {extracted_text}")
                
                if user_comment:
                    final_query = f"Комментарий: {user_comment}\n\nТекст с изображения: {extracted_text}"
                else:
                    final_query = f"Текст с изображения: {extracted_text}"
                
                self.question_text.delete(1.0, tk.END)
                self.question_text.insert(1.0, final_query)
                
                self.log("🦀 Получаю ответ от AI...")
                
                self.get_ai_response(final_query)
            else:
                self.log("⚠️ Не удалось распознать текст из изображения")
                
        except Exception as e:
            self.log(f"❌ Ошибка OCR анализа: {e}")

    def extract_text_online_ocr(self, image_path):
        """Извлечение текста с помощью бесплатного online OCR API"""
        try:
            self.log("🌐 Пробую online OCR...")
            
            url = "https://api.ocr.space/parse/image"
            
            with open(image_path, 'rb') as f:
                files = {'file': f}
                data = {
                    'apikey': 'helloworld',
                    'language': 'rus',
                    'OCREngine': '2'
                }
                
                response = requests.post(url, files=files, data=data, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('OCRExitCode') == 1:
                        text = ""
                        for parsed_result in result.get('ParsedResults', []):
                            text += parsed_result.get('ParsedText', '')
                        return text.strip()
                
            return ""
            
        except Exception as e:
            self.log(f"⚠️ Online OCR ошибка: {e}")
            return ""

    def manual_text_input(self, image_path):
        """Ручной ввод текста с изображения"""
        try:
            subprocess.run(['open', image_path])
            
            result = messagebox.askquestion(
                "Ручной ввод текста",
                "Изображение открыто в системном просмотрщике.\n\n"
                "Online OCR не смог распознать текст.\n"
                "Хотите ввести текст вручную?"
            )
            
            if result == 'yes':
                text_window = tk.Toplevel(self.root)
                text_window.title("Введите текст с изображения")
                text_window.geometry("500x300")
                text_window.configure(bg='#2b2b2b')
                
                tk.Label(
                    text_window,
                    text="Введите текст, который видите на изображении:",
                    font=('Arial', 12),
                    fg='#ffffff',
                    bg='#2b2b2b'
                ).pack(pady=10)
                
                text_input = tk.Text(
                    text_window,
                    height=10,
                    wrap=tk.WORD,
                    bg='#1e1e1e',
                    fg='#ffffff',
                    font=('Arial', 11),
                    insertbackground='white'
                )
                text_input.pack(fill='both', expand=True, padx=10, pady=5)
                
                result_text = {"text": ""}
                
                def save_text():
                    result_text["text"] = text_input.get(1.0, tk.END).strip()
                    text_window.destroy()
                
                def cancel_input():
                    text_window.destroy()
                
                button_frame = tk.Frame(text_window, bg='#2b2b2b')
                button_frame.pack(pady=10)
                
                tk.Button(
                    button_frame,
                    text="✅ Сохранить",
                    command=save_text,
                    bg='#4CAF50',
                    fg='white',
                    font=('Arial', 10, 'bold')
                ).pack(side='left', padx=5)
                
                tk.Button(
                    button_frame,
                    text="❌ Отмена",
                    command=cancel_input,
                    bg='#f44336',
                    fg='white',
                    font=('Arial', 10, 'bold')
                ).pack(side='left', padx=5)
                
                text_input.focus_set()
                text_window.wait_window()
                
                return result_text["text"]
            
            return ""
            
        except Exception as e:
            self.log(f"⚠️ Ошибка ручного ввода: {e}")
            return ""

    def paste_text_from_clipboard(self, event=None):
        """Вставка текста из буфера обмена"""
        try:
            clipboard_text = self.root.clipboard_get()
            
            if clipboard_text:
                self.question_text.insert(tk.END, clipboard_text)
                self.log("📝 Текст вставлен из буфера обмена")
            else:
                messagebox.showwarning("Пустой буфер", "Буфер обмена пуст")
                
        except Exception as e:
            self.log(f"❌ Ошибка вставки текста: {e}")

    def paste_image_from_clipboard(self, event=None):
        """Вставка изображения из буфера обмена"""
        try:
            self.log("🖼️ Проверяю буфер обмена на наличие изображения...")
            
            temp_image_path = self.save_clipboard_image_macos()
            
            if temp_image_path:
                self.log("✅ Изображение найдено в буфере обмена")
                self.process_image_file(temp_image_path)
            else:
                self.suggest_screenshot_alternative()
                
        except Exception as e:
            self.log(f"❌ Ошибка вставки изображения: {e}")

    def save_clipboard_image_macos(self):
        """Сохранение изображения из буфера обмена на macOS"""
        try:
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_file.close()
            
            result = subprocess.run([
                'osascript', '-e',
                f'try\n'
                f'    set theImage to the clipboard as «class PNGf»\n'
                f'    set theFile to open for access POSIX file "{temp_file.name}" with write permission\n'
                f'    write theImage to theFile\n'
                f'    close access theFile\n'
                f'    return "success"\n'
                f'on error\n'
                f'    return "error"\n'
                f'end try'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and "success" in result.stdout:
                return temp_file.name
            else:
                try:
                    os.unlink(temp_file.name)
                except:
                    pass
                return None
                
        except Exception as e:
            self.log(f"⚠️ Не удалось извлечь изображение: {e}")
            return None

    def suggest_screenshot_alternative(self):
        """Предлагает альтернативный способ получения скриншота"""
        self.log("💡 В буфере обмена нет изображения")
        
        result = messagebox.askquestion(
            "Нет изображения", 
            "В буфере обмена нет изображения.\n\n"
            "Хотите сделать скриншот?\n\n"
            "ДА - Сделать скриншот (Cmd+Shift+4)\n"
            "НЕТ - Отмена"
        )
        
        if result == 'yes':
            self.log("📸 Используйте Cmd+Shift+4 для создания скриншота")
            self.log("📋 Скриншот автоматически скопируется в буфер обмена")
            self.log("🔄 Затем нажмите кнопку 'Вставить картинку' снова")
            
            messagebox.showinfo(
                "Инструкция",
                "1. Нажмите Cmd+Shift+4\n"
                "2. Выделите область для скриншота\n"
                "3. Скриншот скопируется в буфер обмена\n"
                "4. Нажмите 'Вставить картинку' снова"
            )

    def setup_hotkeys(self):
        """Настройка горячих клавиш"""
        self.root.bind('<Command-v>', self.auto_paste_from_clipboard)
        self.root.bind('<Command-Shift-v>', self.paste_image_from_clipboard)
        
        self.root.focus_set()

    def auto_paste_from_clipboard(self, event=None):
        """Автоматическая вставка из буфера обмена (определяет тип содержимого)"""
        try:
            self.log("📋 Проверяю содержимое буфера обмена...")
            
            temp_image_path = self.save_clipboard_image_macos()
            
            if temp_image_path:
                self.log("🖼️ Найдено изображение в буфере обмена")
                self.process_image_file(temp_image_path)
            else:
                try:
                    clipboard_text = self.root.clipboard_get()
                    if clipboard_text and clipboard_text.strip():
                        self.log("📝 Найден текст в буфере обмена")
                        current_text = self.question_text.get(1.0, tk.END).strip()
                        if current_text:
                            self.question_text.insert(tk.END, "\n" + clipboard_text)
                        else:
                            self.question_text.insert(1.0, clipboard_text)
                    else:
                        self.log("⚠️ Буфер обмена пуст")
                        messagebox.showinfo("Пустой буфер", "Буфер обмена пуст или содержит неподдерживаемый тип данных")
                except:
                    self.log("⚠️ Не удалось получить содержимое буфера обмена")
                    
        except Exception as e:
            self.log(f"❌ Ошибка автоматической вставки: {e}")

    def update_history_length(self, event):
        """Обновление длины истории"""
        try:
            new_length = self.history_length_var.get()
            if new_length.isdigit():
                self.max_history_length = int(new_length)
                self.log(f"🔄 Длина истории обновлена до {self.max_history_length} сообщений")
            else:
                self.log("⚠️ Некорректный ввод длины истории")
        except Exception as e:
            self.log(f"❌ Ошибка обновления истории: {e}")

    def update_history_status(self):
        """Обновление статуса истории"""
        self.history_status.config(text=f"💬 История: {len(self.conversation_history) // 2} сообщений")

    def log_conversation_context(self):
        """Логирование контекста диалога"""
        if self.conversation_history and self.context_enabled:
            self.log(f"📚 Отправляю {len(self.conversation_history)} сообщений из истории")
        else:
            self.log("📭 История пуста или отключена, отправляю без контекста")

    def toggle_context(self):
        """Включение/выключение контекста"""
        self.context_enabled = not self.context_enabled
        if self.context_enabled:
            self.context_toggle_button.config(text="🧠 Контекст: ВКЛ", bg='#4CAF50')
            self.log("✅ Контекст диалога включен")
        else:
            self.context_toggle_button.config(text="🧠 Контекст: ВЫКЛ", bg='#607D8B')
            self.log("❌ Контекст диалога выключен")

    def clear_conversation_history(self):
        """Очистка истории диалога"""
        self.conversation_history = []
        self.update_history_status()
        self.log("🗑️ История диалога очищена")

    def quick_ocr_capture(self):
        """Быстрый OCR захват"""
        self.start_screen_capture()

    def toggle_auto_scroll(self):
        """Переключение автопрокрутки"""
        self.auto_scroll = not self.auto_scroll
        if self.auto_scroll:
            self.auto_scroll_button.config(text="📜 Авто-\nпрокрутка", bg='#4CAF50')
            self.log("✅ Автопрокрутка включена")
        else:
            self.auto_scroll_button.config(text="📜 Авто-\nпрокрутка", bg='#607D8B')
            self.log("❌ Автопрокрутка выключена")

    def setup_scroll_tracking(self):
        """Настройка отслеживания прокрутки"""
        self.log_text.bind('<MouseWheel>', self.on_scroll)
        self.log_text.bind('<Button-4>', self.on_scroll)
        self.log_text.bind('<Button-5>', self.on_scroll)
        
        self.log_text.bind('<Up>', self.on_keyboard_scroll)
        self.log_text.bind('<Down>', self.on_keyboard_scroll)
        self.log_text.bind('<Prior>', self.on_keyboard_scroll)
        self.log_text.bind('<Next>', self.on_keyboard_scroll)

    def on_scroll(self, event):
        """Обработка события прокрутки мышью"""
        self.user_scrolling = True
        self.last_user_scroll_time = time.time()
        return None
        
    def on_keyboard_scroll(self, event):
        """Обработка прокрутки клавиатурой"""
        self.last_user_scroll_time = time.time()
        return None

    def smart_scroll_to_end(self):
        """Умная прокрутка - прокручивает только если нужно"""
        if not self.auto_scroll:
            return
            
        if time.time() - self.last_user_scroll_time < 3:
            return
            
        try:
            scroll_position = self.log_text.yview()[1]
            if scroll_position > 0.9:
                self.log_text.see(tk.END)
        except:
            self.log_text.see(tk.END)

    def is_user_at_bottom(self):
        """Проверяет, находится ли пользователь в конце чата"""
        try:
            scroll_position = self.log_text.yview()[1]
            return scroll_position > 0.95
        except:
            return True

    def jump_to_end(self):
        """Переход в конец чата"""
        self.log_text.see(tk.END)

if __name__ == "__main__":
    try:
        app = InterviewAssistantGUI()
        app.run()
    except KeyboardInterrupt:
        print("👋 Завершение работы...")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}") 