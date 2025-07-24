import os
import json
import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox, ttk, simpledialog
from openai import OpenAI
import subprocess
import re
import threading
import sys
import uuid
import shutil
import platform
from datetime import datetime
import markdown
import html
import venv

NEUROCOD_API_KEY = "sk-b70c2a57d1fb4c29989767b0b5e0823b"

class DarkTheme:
    """Класс для применения темной темы"""
    @staticmethod
    def apply(root):
        root.configure(bg='#1e1e1e')
        style = ttk.Style()
        style.theme_use('clam')
        
        # Настройка цветов
        style.configure('.', background='#1e1e1e', foreground='#dcdcdc')
        style.configure('TFrame', background='#1e1e1e')
        style.configure('TLabel', background='#1e1e1e', foreground='#dcdcdc')
        style.configure('TButton', background='#3c3f41', foreground='#dcdcdc', 
                        borderwidth=1, relief='flat')
        style.map('TButton', background=[('active', '#4e5254')])
        style.configure('TEntry', fieldbackground='#2b2b2b', foreground='#dcdcdc')
        style.configure('TCombobox', fieldbackground='#2b2b2b', foreground='#dcdcdc')
        style.configure('Treeview', background='#252526', fieldbackground='#252526', 
                        foreground='#dcdcdc')
        style.configure('Treeview.Heading', background='#3c3f41', foreground='#dcdcdc')
        style.map('Treeview', background=[('selected', '#4e5254')])
        style.configure('Vertical.TScrollbar', background='#3c3f41', troughcolor='#1e1e1e')
        style.configure('Horizontal.TScrollbar', background='#3c3f41', troughcolor='#1e1e1e')
        style.configure('TLabelframe', background='#1e1e1e', foreground='#dcdcdc')
        style.configure('TLabelframe.Label', background='#1e1e1e', foreground='#dcdcdc')
        
        # Настройка ScrolledText
        text_bg = '#2b2b2b'
        text_fg = '#dcdcdc'
        
        return {
            'text_bg': text_bg,
            'text_fg': text_fg,
            'select_bg': '#4e5254',
            'insert_bg': '#dcdcdc'
        }

class ContextMenu:
    """Контекстное меню для текстовых виджетов"""
    def __init__(self, widget):
        self.widget = widget
        self.menu = tk.Menu(widget, tearoff=0, bg='#3c3f41', fg='#dcdcdc')
        self.menu.add_command(label="Вырезать", command=self.cut)
        self.menu.add_command(label="Копировать", command=self.copy)
        self.menu.add_command(label="Вставить", command=self.paste)
        self.menu.add_command(label="Выделить все", command=self.select_all)
        
        widget.bind("<Button-3>", self.show_menu)
    
    def show_menu(self, event):
        self.menu.tk_popup(event.x_root, event.y_root)
    
    def cut(self):
        self.widget.event_generate("<<Cut>>")
    
    def copy(self):
        self.widget.event_generate("<<Copy>>")
    
    def paste(self):
        self.widget.event_generate("<<Paste>>")
    
    def select_all(self):
        self.widget.tag_add('sel', '1.0', 'end')

class NeuroCodApp:
    def __init__(self, root):
        self.root = root
        root.title("NeuroCod Pro - AI Development Suite")
        root.geometry("1200x800")
        
        # Применение темной темы
        text_colors = DarkTheme.apply(root)
        
        # API Key Setup
        self.api_key = tk.StringVar(value=NEUROCOD_API_KEY)
        
        # Project settings
        default_dir = os.path.join(os.path.expanduser("~"), "NeuroCodProjects")
        self.project_dir = tk.StringVar(value=default_dir)
        self.current_project_path = ""
        self.current_project_data = {}
        self.current_file = None
        
        # История и состояние
        self.project_history = []
        self.chat_history = []
        self.project_steps = []
        self.current_step = 0
        self.project_id = str(uuid.uuid4())[:8]
        
        # Настройки AI
        self.model = "deepseek-coder"
        self.temperature = 0.7
        
        # Создание интерфейса
        self.create_widgets(text_colors)
        self.load_config()
        self.load_project_history()
        
        # Приветственное сообщение
        self.add_to_chat("NeuroCod: Добро пожаловать! Опишите проект, который вы хотите создать.", "ai")
    
    def resource_path(self, relative_path):
        """Получение пути к ресурсам для PyInstaller"""
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)
    
    def browse_directory(self):
        """Выбор директории проекта"""
        directory = filedialog.askdirectory(
            title="Выберите папку для проектов",
            initialdir=self.project_dir.get()
        )
        if directory:
            self.project_dir.set(directory)
            self.add_to_chat(f"Установлена папка проектов: {directory}", "system")
    
    def create_widgets(self, text_colors):
        """Создание основного интерфейса приложения"""
        # Создание основных панелей
        main_pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=4, bg='#252526')
        main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Левая панель - Управление проектом и чат
        left_frame = ttk.Frame(main_pane, width=400)
        main_pane.add(left_frame)
        
        # Правая панель - Редактор кода и обозреватель файлов
        right_frame = ttk.Frame(main_pane)
        main_pane.add(right_frame)
        
        # Конфигурация панелей
        main_pane.paneconfig(left_frame, minsize=300, stretch="never")
        main_pane.paneconfig(right_frame, minsize=500)
        
        # --- ЛЕВАЯ ПАНЕЛЬ ---
        notebook = ttk.Notebook(left_frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Вкладка чата
        chat_frame = ttk.Frame(notebook)
        notebook.add(chat_frame, text="AI Чат", padding=5)
        
        # Вкладка проекта
        project_frame = ttk.Frame(notebook)
        notebook.add(project_frame, text="Проект", padding=5)
        
        # Вкладка истории
        history_frame = ttk.Frame(notebook)
        notebook.add(history_frame, text="История", padding=5)
        
        # --- ВКЛАДКА ЧАТА ---
        # Информация о проекте
        info_frame = ttk.LabelFrame(chat_frame, text="Текущий проект")
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.project_name_var = tk.StringVar(value="Новый проект")
        ttk.Label(info_frame, text="Название:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        name_entry = ttk.Entry(info_frame, textvariable=self.project_name_var, width=30)
        name_entry.grid(row=0, column=1, padx=5, pady=2, sticky="we")
        
        ttk.Label(info_frame, text="Папка:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        dir_entry = ttk.Entry(info_frame, textvariable=self.project_dir, width=30)
        dir_entry.grid(row=1, column=1, padx=5, pady=2, sticky="we")
        browse_btn = ttk.Button(info_frame, text="Обзор", command=self.browse_directory, width=8)
        browse_btn.grid(row=1, column=2, padx=5, pady=2)
        
        # История чата
        chat_history_frame = ttk.LabelFrame(chat_frame, text="Диалог")
        chat_history_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.chat_display = scrolledtext.ScrolledText(
            chat_history_frame, 
            wrap=tk.WORD, 
            state='disabled', 
            height=15,
            bg=text_colors['text_bg'],
            fg=text_colors['text_fg'],
            insertbackground=text_colors['insert_bg'],
            selectbackground=text_colors['select_bg']
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.chat_display.tag_config("user", foreground="#569cd6")
        self.chat_display.tag_config("ai", foreground="#4ec9b0")
        self.chat_display.tag_config("system", foreground="#d7ba7d")
        self.chat_display.tag_config("error", foreground="#f44747")
        
        # Контекстное меню для чата
        ContextMenu(self.chat_display)
        
        # Ввод сообщения
        input_frame = ttk.Frame(chat_frame)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Кнопка для прикрепления файлов
        attach_btn = ttk.Button(input_frame, text="📎", width=3, command=self.attach_file)
        attach_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.user_input = ttk.Entry(input_frame)
        self.user_input.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=(0,5))
        self.user_input.bind("<Return>", lambda event: self.send_message())
        
        send_btn = ttk.Button(input_frame, text="Отправить", command=self.send_message, width=10)
        send_btn.pack(side=tk.RIGHT)
        
        # Контекстное меню для ввода
        ContextMenu(self.user_input)
        
        # Кнопки действий
        btn_frame = ttk.Frame(chat_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(btn_frame, text="Создать проект", command=self.create_project, width=15).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Следующий шаг", command=self.next_step, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Обновить код", command=self.refresh_code, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Очистить чат", command=self.clear_chat, width=10).pack(side=tk.RIGHT, padx=2)
        
        # --- ВКЛАДКА ПРОЕКТА ---
        # Структура проекта
        struct_frame = ttk.LabelFrame(project_frame, text="Структура проекта")
        struct_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Дерево файлов
        self.file_tree = ttk.Treeview(struct_frame)
        self.file_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.file_tree.bind("<<TreeviewSelect>>", self.on_file_select)
        
        # Действия с проектом
        action_frame = ttk.Frame(project_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(action_frame, text="Открыть в VS Code", command=self.open_vscode, width=16).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Запустить проект", command=self.run_project, width=14).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Тестировать", command=self.test_project, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Экспортировать", command=self.export_project, width=12).pack(side=tk.RIGHT, padx=2)
        
        # --- ВКЛАДКА ИСТОРИИ ---
        # Список истории проектов
        history_list_frame = ttk.LabelFrame(history_frame, text="История проектов")
        history_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ("id", "name", "path", "created")
        self.history_tree = ttk.Treeview(history_list_frame, columns=columns, show="headings", height=10)
        
        self.history_tree.heading("id", text="ID")
        self.history_tree.heading("name", text="Название")
        self.history_tree.heading("path", text="Путь")
        self.history_tree.heading("created", text="Создан")
        
        self.history_tree.column("id", width=50, anchor="center")
        self.history_tree.column("name", width=150)
        self.history_tree.column("path", width=250)
        self.history_tree.column("created", width=120, anchor="center")
        
        self.history_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.history_tree.bind("<<TreeviewSelect>>", self.on_history_select)
        
        # Действия с историей
        history_btn_frame = ttk.Frame(history_frame)
        history_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(history_btn_frame, text="Загрузить проект", command=self.load_selected_project, width=15).pack(side=tk.LEFT, padx=2)
        ttk.Button(history_btn_frame, text="Удалить проект", command=self.delete_selected_project, width=15).pack(side=tk.LEFT, padx=2)
        ttk.Button(history_btn_frame, text="Обновить список", command=self.load_project_history, width=12).pack(side=tk.RIGHT, padx=2)
        
        # --- ПРАВАЯ ПАНЕЛЬ ---
        # Редактор кода
        editor_frame = ttk.LabelFrame(right_frame, text="Редактор кода")
        editor_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.code_editor = scrolledtext.ScrolledText(
            editor_frame, 
            wrap=tk.NONE, 
            font=("Consolas", 11),
            bg=text_colors['text_bg'],
            fg=text_colors['text_fg'],
            insertbackground=text_colors['insert_bg'],
            selectbackground=text_colors['select_bg']
        )
        self.code_editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Контекстное меню для редактора кода
        ContextMenu(self.code_editor)
        
        # Действия редактора
        editor_btn_frame = ttk.Frame(editor_frame)
        editor_btn_frame.pack(fill=tk.X, padx=5, pady=(0,5))
        
        ttk.Button(editor_btn_frame, text="Сохранить", command=self.save_current_file, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(editor_btn_frame, text="Проверить код", command=self.check_code, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(editor_btn_frame, text="Оптимизировать", command=self.optimize_code, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(editor_btn_frame, text="Запустить", command=self.execute_code, width=10).pack(side=tk.RIGHT, padx=2)
        
        # Панель документации
        doc_frame = ttk.LabelFrame(right_frame, text="Документация")
        doc_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.doc_display = scrolledtext.ScrolledText(
            doc_frame, 
            wrap=tk.WORD, 
            state='disabled',
            bg=text_colors['text_bg'],
            fg=text_colors['text_fg'],
            insertbackground=text_colors['insert_bg'],
            selectbackground=text_colors['select_bg']
        )
        self.doc_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Контекстное меню для документации
        ContextMenu(self.doc_display)
        
        # Строка состояния
        status_bar = ttk.Frame(self.root, relief="sunken", padding=3)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_var = tk.StringVar(value="Готов к работе")
        status_label = ttk.Label(status_bar, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT, padx=5)
        
        version_label = ttk.Label(status_bar, text=f"NeuroCod v4.2 | {datetime.now().year}")
        version_label.pack(side=tk.RIGHT, padx=5)
    
    def attach_file(self):
        """Прикрепление файла к проекту"""
        file_path = filedialog.askopenfilename(
            title="Выберите файл для прикрепления",
            filetypes=[("Все файлы", "*.*")]
        )
        
        if not file_path:
            return
            
        try:
            # Для текстовых файлов читаем содержимое
            if file_path.endswith(('.txt', '.py', '.js', '.html', '.css', '.json', '.md')):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.add_to_chat(f"Прикреплен файл: {os.path.basename(file_path)}\nСодержимое:\n{content}", "system")
            else:
                # Для бинарных файлов просто добавляем информацию
                self.add_to_chat(f"Прикреплен файл: {os.path.basename(file_path)} (бинарный)", "system")
            
            # Добавляем файл в проект
            if self.current_project_data:
                rel_path = os.path.basename(file_path)
                self.current_project_data.setdefault('files', []).append({
                    "path": rel_path,
                    "content": content if 'content' in locals() else "<binary file>"
                })
                self.update_file_tree()
            
            self.set_status(f"Файл прикреплен: {os.path.basename(file_path)}")
        except Exception as e:
            self.add_to_chat(f"Ошибка прикрепления файла: {str(e)}", "error")
    
    def send_message(self):
        """Отправка сообщения пользователя AI"""
        user_text = self.user_input.get()
        if not user_text:
            return
            
        self.add_to_chat("Вы: " + user_text, "user")
        self.user_input.delete(0, tk.END)
        self.chat_history.append({"role": "user", "content": user_text})
        
        threading.Thread(target=self.get_ai_response).start()
    
    def get_ai_response(self):
        """Получение ответа от DeepSeek API"""
        self.set_status("Запрос к NeuroCod AI...")
        try:
            client = OpenAI(
                api_key=self.api_key.get(),
                base_url="https://api.deepseek.com/v1"
            )
            
            # Подготовка сообщений с контекстом проекта
            messages = [{"role": "system", "content": self.get_system_prompt()}]
            messages.extend(self.chat_history[-10:])
            
            if self.current_project_data:
                messages.append({
                    "role": "system",
                    "content": f"Текущий проект: {self.project_name_var.get()}\n" +
                               f"Описание: {self.current_project_data.get('description', '')}\n" +
                               f"Файлы: {', '.join([f['path'] for f in self.current_project_data.get('files', [])])}"
                })
            
            response = client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=messages,
                max_tokens=4000
            )
            
            ai_text = response.choices[0].message.content
            self.add_to_chat("NeuroCod: " + ai_text, "ai")
            self.chat_history.append({"role": "assistant", "content": ai_text})
            self.process_ai_response(ai_text)
            
        except Exception as e:
            self.add_to_chat(f"Ошибка: {str(e)}", "error")
            self.set_status("Ошибка запроса")
    
    def get_system_prompt(self):
        """Системный промпт для AI"""
        return (
            "Ты NeuroCod - AI ассистент для создания проектов. Отвечай строго в формате JSON. "
            "Формат ответа:\n"
            "{\n"
            "  \"action\": \"create|update|clarify|complete\",\n"
            "  \"project_name\": \"название\",\n"
            "  \"description\": \"описание\",\n"
            "  \"files\": [\n"
            "    {\"path\": \"путь/файл1\", \"content\": \"содержимое\"},\n"
            "    ...\n"
            "  ],\n"
            "  \"requirements\": [\"библиотека1\", ...],\n"
            "  \"documentation\": \"markdown документация\",\n"
            "  \"next_steps\": [\"шаг1\", \"шаг2\"]\n"
            "}\n\n"
            "Правила:\n"
            "1. Для новых проектов используй action: 'create'\n"
            "2. Для обновления кода используй action: 'update'\n"
            "3. Если нужно уточнение, используй action: 'clarify' и задай вопрос\n"
            "4. Для завершения проекта используй action: 'complete'\n"
            "5. Всегда включай документацию в формате Markdown\n"
            "6. Предлагай следующие шаги разработки\n"
            "7. Для существующих проектов анализируй текущее состояние"
        )
    
    def process_ai_response(self, ai_text):
        """Обработка ответа AI и обновление проекта"""
        try:
            project_data = self.extract_json(ai_text)
            if not project_data:
                raise ValueError("Не удалось извлечь JSON из ответа AI")
                
            action = project_data.get("action", "create")
            
            if action == "clarify":
                clarification = project_data.get("question", "Пожалуйста, уточните ваши требования.")
                self.add_to_chat(f"NeuroCod: {clarification}", "ai")
                return
            
            # Обновление данных проекта
            self.current_project_data = project_data
            if "project_name" in project_data:
                self.project_name_var.set(project_data["project_name"])
            
            if "documentation" in project_data:
                self.show_documentation(project_data["documentation"])
            
            if "next_steps" in project_data:
                self.project_steps = project_data["next_steps"]
                self.current_step = 0
                self.show_next_step()
            
            self.update_file_tree()
            
            if action == "complete":
                self.add_to_chat("NeuroCod: Проект успешно завершен!", "system")
                self.set_status("Проект завершен")
            
            self.set_status("Ответ обработан")
            
        except Exception as e:
            self.add_to_chat(f"Ошибка обработки ответа: {str(e)}", "error")
            self.set_status("Ошибка обработки")
    
    def extract_json(self, text):
        """Извлечение JSON из ответа AI"""
        try:
            json_match = re.search(r'```json\s*({.*?})\s*```', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
            return json.loads(text)
        except Exception as e:
            self.add_to_chat(f"Ошибка парсинга JSON: {str(e)}", "error")
            return None
    
    def add_to_chat(self, message, sender):
        """Добавление сообщения в чат"""
        self.chat_display.config(state='normal')
        
        if sender == "user":
            self.chat_display.insert(tk.END, message + "\n", "user")
        elif sender == "ai":
            self.chat_display.insert(tk.END, message + "\n\n", "ai")
        elif sender == "system":
            self.chat_display.insert(tk.END, message + "\n", "system")
        else:
            self.chat_display.insert(tk.END, message + "\n", "error")
            
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)
    
    def update_file_tree(self):
        """Обновление дерева файлов проекта"""
        if not self.file_tree:
            return
            
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        files = self.current_project_data.get("files", [])
        for file in files:
            path = file["path"]
            parts = path.split("/")
            parent = ""
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    self.file_tree.insert(parent, "end", text=part, values=(path, "file"))
                else:
                    existing = self.find_tree_item(parent, part)
                    if not existing:
                        parent = self.file_tree.insert(parent, "end", text=part, values=("/".join(parts[:i+1]), "folder"))
                    else:
                        parent = existing
    
    def find_tree_item(self, parent, text):
        """Поиск элемента в дереве файлов"""
        for child in self.file_tree.get_children(parent):
            if self.file_tree.item(child, "text") == text:
                return child
        return None
    
    def on_file_select(self, event):
        """Обработка выбора файла в дереве"""
        if not self.code_editor:
            return
            
        selected = self.file_tree.selection()
        if not selected:
            return
            
        item = selected[0]
        values = self.file_tree.item(item, "values")
        if values and len(values) > 0 and values[1] == "file":
            path = values[0]
            for file in self.current_project_data.get("files", []):
                if file["path"] == path:
                    self.code_editor.delete(1.0, tk.END)
                    self.code_editor.insert(tk.END, file.get("content", ""))
                    self.current_file = path
                    self.set_status(f"Открыт файл: {path}")
                    break
    
    def save_current_file(self):
        """Сохранение текущего файла в редакторе"""
        if not hasattr(self, "current_file") or not self.current_file:
            return
            
        content = self.code_editor.get(1.0, tk.END)
        
        for file in self.current_project_data.get("files", []):
            if file["path"] == self.current_file:
                file["content"] = content
                break
        
        self.add_to_chat(f"Файл {self.current_file} сохранен", "system")
        self.set_status(f"Файл сохранен: {self.current_file}")
    
    def show_documentation(self, markdown_text):
        """Отображение документации"""
        self.doc_display.config(state='normal')
        self.doc_display.delete(1.0, tk.END)
        
        html_content = markdown.markdown(markdown_text)
        plain_text = html.unescape(re.sub('<[^<]+?>', '', html_content))
        
        self.doc_display.insert(tk.END, plain_text)
        self.doc_display.config(state='disabled')
    
    def show_next_step(self):
        """Отображение следующего шага разработки"""
        if self.current_step < len(self.project_steps):
            step = self.project_steps[self.current_step]
            self.add_to_chat(f"Следующий шаг: {step}", "system")
            self.current_step += 1
        else:
            self.add_to_chat("Все шаги выполнены!", "system")
    
    def next_step(self):
        """Выполнение следующего шага разработки"""
        self.show_next_step()
        if self.current_step <= len(self.project_steps):
            self.add_to_chat("Вы: Реализуй следующий шаг", "user")
            self.chat_history.append({"role": "user", "content": "Реализуй следующий шаг"})
            threading.Thread(target=self.get_ai_response).start()
    
    def refresh_code(self):
        """Запрос к AI на проверку и обновление кода"""
        self.add_to_chat("Вы: Проверь и обнови код проекта", "user")
        self.chat_history.append({"role": "user", "content": "Проверь и обнови код проекта"})
        threading.Thread(target=self.get_ai_response).start()
    
    def create_project(self):
        """Создание проекта из текущих данных"""
        if not self.current_project_data:
            self.add_to_chat("Ошибка: нет данных проекта для создания", "error")
            return
            
        self.set_status("Создание проекта...")
        try:
            base_dir = filedialog.askdirectory(
                title="Выберите папку для проекта",
                initialdir=self.project_dir.get()
            )
            
            if not base_dir:
                return
                
            self.project_dir.set(base_dir)
            project_name = self.project_name_var.get()
            project_path = os.path.join(base_dir, project_name)
            os.makedirs(project_path, exist_ok=True)
            
            # Создание виртуального окружения Python
            venv_path = os.path.join(project_path, "venv")
            venv.create(venv_path, with_pip=True)
            self.add_to_chat(f"Создано виртуальное окружение Python: {venv_path}", "system")
            
            # Создание файлов
            for file in self.current_project_data.get("files", []):
                file_path = os.path.join(project_path, file['path'])
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(file.get('content', ''))
            
            # Создание requirements.txt
            requirements = self.current_project_data.get('requirements', [])
            if requirements:
                req_path = os.path.join(project_path, 'requirements.txt')
                with open(req_path, 'w') as f:
                    f.write("\n".join(requirements))
                
                # Установка зависимостей в виртуальном окружении
                if sys.platform == "win32":
                    pip_path = os.path.join(venv_path, "Scripts", "pip.exe")
                else:
                    pip_path = os.path.join(venv_path, "bin", "pip")
                
                if os.path.exists(pip_path):
                    try:
                        subprocess.run([pip_path, "install", "-r", req_path], 
                                      cwd=project_path, check=True)
                        self.add_to_chat("Зависимости установлены в виртуальном окружении", "system")
                    except subprocess.CalledProcessError as e:
                        self.add_to_chat(f"Ошибка установки зависимостей: {str(e)}", "error")
            
            # Создание документации
            documentation = self.current_project_data.get('documentation', '')
            if documentation:
                with open(os.path.join(project_path, 'DOCUMENTATION.md'), 'w', encoding='utf-8') as f:
                    f.write(documentation)
            
            # Добавление в историю
            self.add_to_project_history(project_name, project_path)
            self.current_project_path = project_path
            self.add_to_chat(f"Проект создан: {project_path}", "system")
            self.set_status(f"Проект создан: {project_name}")
            self.open_vscode()
            
        except Exception as e:
            self.add_to_chat(f"Ошибка создания проекта: {str(e)}", "error")
            self.set_status("Ошибка создания проекта")
    
    def add_to_project_history(self, name, path):
        """Добавление проекта в историю"""
        project_id = str(uuid.uuid4())[:8]
        created = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        self.project_history.append({
            "id": project_id,
            "name": name,
            "path": path,
            "created": created
        })
        
        history_file = os.path.join(os.path.dirname(__file__), "neurocod_history.json")
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(self.project_history, f, ensure_ascii=False, indent=2)
        
        self.load_project_history()
    
    def load_project_history(self):
        """Загрузка истории проектов из файла"""
        if not self.history_tree:
            return
            
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        history_file = os.path.join(os.path.dirname(__file__), "neurocod_history.json")
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    self.project_history = json.load(f)
            except:
                self.project_history = []
        
        for project in self.project_history:
            self.history_tree.insert("", "end", values=(
                project["id"],
                project["name"],
                project["path"],
                project["created"]
            ))
    
    def on_history_select(self, event):
        """Обработка выбора элемента истории"""
        selected = self.history_tree.selection()
        if selected:
            item = selected[0]
            values = self.history_tree.item(item, "values")
            if values:
                self.project_name_var.set(values[1])
                self.project_dir.set(values[2])
    
    def load_selected_project(self):
        """Загрузка выбранного проекта из истории"""
        selected = self.history_tree.selection()
        if not selected:
            return
            
        item = selected[0]
        values = self.history_tree.item(item, "values")
        if not values:
            return
            
        project_path = values[2]
        if not os.path.exists(project_path):
            self.add_to_chat(f"Ошибка: путь не существует {project_path}", "error")
            return
            
        self.current_project_path = project_path
        self.project_name_var.set(values[1])
        
        # Сканирование файлов проекта
        files = []
        for root, _, filenames in os.walk(project_path):
            for filename in filenames:
                if filename.startswith('venv') and 'python' in filename.lower():
                    continue  # Пропускаем файлы виртуального окружения
                    
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, project_path)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except:
                    content = "<binary file>"
                
                files.append({"path": rel_path, "content": content})
        
        # Загрузка документации
        documentation = ""
        doc_path = os.path.join(project_path, "DOCUMENTATION.md")
        if os.path.exists(doc_path):
            with open(doc_path, 'r', encoding='utf-8') as f:
                documentation = f.read()
        
        # Создание данных проекта
        self.current_project_data = {
            "project_name": values[1],
            "description": f"Загруженный проект: {values[1]}",
            "files": files,
            "requirements": self.get_requirements(project_path),
            "documentation": documentation
        }
        
        # Обновление интерфейса
        self.update_file_tree()
        self.show_documentation(documentation)
        self.add_to_chat(f"Проект {values[1]} загружен", "system")
        self.set_status(f"Проект загружен: {values[1]}")
    
    def get_requirements(self, project_path):
        """Получение зависимостей из requirements.txt"""
        req_path = os.path.join(project_path, "requirements.txt")
        if os.path.exists(req_path):
            with open(req_path, 'r') as f:
                return [line.strip() for line in f if line.strip()]
        return []
    
    def delete_selected_project(self):
        """Удаление проекта из истории"""
        selected = self.history_tree.selection()
        if not selected:
            return
            
        item = selected[0]
        values = self.history_tree.item(item, "values")
        if not values:
            return
            
        project_id = values[0]
        
        if not messagebox.askyesno("Удаление проекта", "Удалить проект из истории?"):
            return
            
        self.project_history = [p for p in self.project_history if p["id"] != project_id]
        
        history_file = os.path.join(os.path.dirname(__file__), "neurocod_history.json")
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(self.project_history, f, ensure_ascii=False, indent=2)
        
        self.load_project_history()
        self.add_to_chat(f"Проект {values[1]} удален из истории", "system")
    
    def open_vscode(self):
        """Открытие проекта в VSCode"""
        if not self.current_project_path:
            self.add_to_chat("Ошибка: нет активного проекта", "error")
            return
            
        try:
            if sys.platform == "win32":
                subprocess.Popen(["code", self.current_project_path], shell=True)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-a", "Visual Studio Code", self.current_project_path])
            else:
                subprocess.Popen(["code", self.current_project_path])
                
            self.add_to_chat(f"Проект открыт в VS Code: {self.current_project_path}", "system")
            self.set_status("Проект открыт в VS Code")
        except Exception as e:
            self.add_to_chat(f"Ошибка открытия в VS Code: {str(e)}", "error")
    
    def run_project(self):
        """Запуск проекта"""
        if not self.current_project_path:
            self.add_to_chat("Ошибка: нет активного проекта", "error")
            return
            
        main_file = simpledialog.askstring("Запуск проекта", "Введите путь к основному файлу:", 
                                          initialvalue="main.py")
        if not main_file:
            return
            
        main_path = os.path.join(self.current_project_path, main_file)
        if not os.path.exists(main_path):
            self.add_to_chat(f"Ошибка: файл не найден {main_path}", "error")
            return
            
        try:
            # Определяем путь к интерпретатору в виртуальном окружении
            venv_python = self.get_venv_python()
            
            if venv_python:
                subprocess.Popen([venv_python, main_path], cwd=self.current_project_path)
                self.add_to_chat(f"Запущен файл в виртуальном окружении: {main_file}", "system")
            else:
                if sys.platform == "win32":
                    subprocess.Popen(["python", main_path], cwd=self.current_project_path, shell=True)
                else:
                    subprocess.Popen(["python3", main_path], cwd=self.current_project_path)
                self.add_to_chat(f"Запущен файл: {main_file}", "system")
                
            self.set_status(f"Запуск проекта: {main_file}")
        except Exception as e:
            self.add_to_chat(f"Ошибка запуска: {str(e)}", "error")
    
    def get_venv_python(self):
        """Получение пути к интерпретатору в виртуальном окружении"""
        if not self.current_project_path:
            return None
            
        venv_path = os.path.join(self.current_project_path, "venv")
        if not os.path.exists(venv_path):
            return None
            
        if sys.platform == "win32":
            python_path = os.path.join(venv_path, "Scripts", "python.exe")
        else:
            python_path = os.path.join(venv_path, "bin", "python")
            
        return python_path if os.path.exists(python_path) else None
    
    def test_project(self):
        """Запуск тестов проекта"""
        if not self.current_project_path:
            self.add_to_chat("Ошибка: нет активного проекта", "error")
            return
            
        try:
            test_path = os.path.join(self.current_project_path, "tests")
            if not os.path.exists(test_path):
                self.add_to_chat("Тесты не найдены", "system")
                return
                
            # Определяем путь к интерпретатору в виртуальном окружении
            venv_python = self.get_venv_python()
            
            if venv_python:
                process = subprocess.Popen([venv_python, "-m", "pytest"], 
                                         cwd=self.current_project_path,
                                         stdout=subprocess.PIPE, 
                                         stderr=subprocess.PIPE)
            else:
                if sys.platform == "win32":
                    process = subprocess.Popen(["pytest"], 
                                             cwd=self.current_project_path,
                                             stdout=subprocess.PIPE, 
                                             stderr=subprocess.PIPE, 
                                             shell=True)
                else:
                    process = subprocess.Popen(["pytest"], 
                                             cwd=self.current_project_path,
                                             stdout=subprocess.PIPE, 
                                             stderr=subprocess.PIPE)
                
            stdout, stderr = process.communicate()
            
            self.add_to_chat("Результаты тестов:", "system")
            self.add_to_chat(stdout.decode("utf-8", "ignore"), "system")
            
            if stderr:
                self.add_to_chat("Ошибки тестов:", "error")
                self.add_to_chat(stderr.decode("utf-8", "ignore"), "error")
                
            self.set_status("Тестирование завершено")
        except Exception as e:
            self.add_to_chat(f"Ошибка выполнения тестов: {str(e)}", "error")
    
    def export_project(self):
        """Экспорт проекта как zip-архива"""
        if not self.current_project_path:
            self.add_to_chat("Ошибка: нет активного проекта", "error")
            return
            
        export_path = filedialog.askdirectory(title="Выберите папку для экспорта")
        if not export_path:
            return
            
        try:
            project_name = self.project_name_var.get()
            zip_path = os.path.join(export_path, f"{project_name}.zip")
            shutil.make_archive(os.path.join(export_path, project_name), 'zip', self.current_project_path)
            
            self.add_to_chat(f"Проект экспортирован: {zip_path}", "system")
            self.set_status(f"Проект экспортирован: {zip_path}")
        except Exception as e:
            self.add_to_chat(f"Ошибка экспорта: {str(e)}", "error")
    
    def check_code(self):
        """Проверка кода"""
        if not hasattr(self, "current_file") or not self.current_file:
            self.add_to_chat("Ошибка: нет выбранного файла", "error")
            return
            
        content = self.code_editor.get(1.0, tk.END)
        if not content:
            return
            
        self.add_to_chat(f"Вы: Проверь код файла {self.current_file}", "user")
        self.chat_history.append({
            "role": "user", 
            "content": f"Проверь следующий код на ошибки:\n```\n{content}\n```"
        })
        threading.Thread(target=self.get_ai_response).start()
        self.set_status("Проверка кода...")
    
    def optimize_code(self):
        """Оптимизация кода"""
        if not hasattr(self, "current_file") or not self.current_file:
            self.add_to_chat("Ошибка: нет выбранного файла", "error")
            return
            
        content = self.code_editor.get(1.0, tk.END)
        if not content:
            return
            
        self.add_to_chat(f"Вы: Оптимизируй код файла {self.current_file}", "user")
        self.chat_history.append({
            "role": "user", 
            "content": f"Оптимизируй следующий код:\n```\n{content}\n```"
        })
        threading.Thread(target=self.get_ai_response).start()
        self.set_status("Оптимизация кода...")
    
    def execute_code(self):
        """Выполнение выбранного фрагмента кода"""
        if not hasattr(self, "current_file") or not self.current_file:
            self.add_to_chat("Ошибка: нет выбранного файла", "error")
            return
            
        try:
            # Сохранение текущего файла
            self.save_current_file()
            
            # Выполнение кода
            file_path = os.path.join(self.current_project_path, self.current_file)
            if not os.path.exists(file_path):
                self.add_to_chat(f"Ошибка: файл не найден {file_path}", "error")
                return
                
            # Определяем путь к интерпретатору в виртуальном окружении
            venv_python = self.get_venv_python()
            
            if venv_python:
                process = subprocess.Popen(
                    [venv_python, file_path], 
                    cwd=self.current_project_path,
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE
                )
                self.add_to_chat(f"Выполнение в виртуальном окружении: {self.current_file}", "system")
            else:
                if sys.platform == "win32":
                    process = subprocess.Popen(
                        ["python", file_path], 
                        cwd=self.current_project_path,
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE, 
                        shell=True
                    )
                else:
                    process = subprocess.Popen(
                        ["python3", file_path], 
                        cwd=self.current_project_path,
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE
                    )
                
            stdout, stderr = process.communicate()
            
            self.add_to_chat("Результат выполнения:", "system")
            if stdout:
                self.add_to_chat(stdout.decode("utf-8", "ignore"), "system")
            if stderr:
                self.add_to_chat(stderr.decode("utf-8", "ignore"), "error")
                
            self.set_status("Код выполнен")
        except Exception as e:
            self.add_to_chat(f"Ошибка выполнения: {str(e)}", "error")
    
    def clear_chat(self):
        """Очистка истории чата"""
        self.chat_display.config(state='normal')
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state='disabled')
        self.chat_history = []
        self.add_to_chat("Чат очищен", "system")
        self.set_status("Чат очищен")
    
    def load_config(self):
        """Загрузка конфигурации приложения"""
        config_path = os.path.join(os.path.dirname(__file__), "neurocod_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.api_key.set(config.get("api_key", NEUROCOD_API_KEY))
                    self.project_dir.set(config.get("project_dir", self.project_dir.get()))
            except:
                pass
    
    def save_config(self):
        """Сохранение конфигурации приложения"""
        config = {
            "api_key": self.api_key.get(),
            "project_dir": self.project_dir.get()
        }
        
        config_path = os.path.join(os.path.dirname(__file__), "neurocod_config.json")
        with open(config_path, 'w') as f:
            json.dump(config, f)
    
    def set_status(self, message):
        """Обновление строки состояния"""
        self.status_var.set(message)
        self.root.update_idletasks()
    
    def on_closing(self):
        """Обработка закрытия приложения"""
        self.save_config()
        self.root.destroy()

def create_installer():
    """Создание установщика приложения"""
    # Эта функция предназначена для отдельного скрипта установки
    # Здесь просто демонстрация концепции
    print("Создание установщика...")
    # На практике используйте PyInstaller для создания .exe:
    # pyinstaller --onefile --windowed --icon=app.ico --name "NeuroCod" app.py
    
    # Затем используйте Inno Setup для создания инсталлятора:
    # https://jrsoftware.org/isinfo.php

if __name__ == "__main__":
    root = tk.Tk()
    app = NeuroCodApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()