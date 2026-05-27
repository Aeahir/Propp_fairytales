import os
import json
import uuid
import re
import datetime
import threading
from typing import Literal
import customtkinter as ctk
from tkinter import messagebox

# Импорт официального клиента OpenAI
from openai import OpenAI

# Настройки UI
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class ProppFairytaleApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Сказочный вестник")
        self.geometry("1200x800")

        # Настройки хранения библиотеки
        self.library_dir = "./fairy_tales_library"
        os.makedirs(self.library_dir, exist_ok=True)
        self.selected_fairytale_data = None  # Сюда пишем данные выбранной сказки из архива

        # Сетка главного окна
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Сборка интерфейса
        self.setup_sidebar()
        self.setup_main_area()
        
        # Первоначальная загрузка списка библиотеки
        self.load_library_list()

        self.log("Приложение готово.")
        self.log("Используется стандартный OpenAI-совместимый клиент.")
        self.log("Для старта укажите Base URL, API-ключ и выберите модель.")

    def log(self, message: str):
        """Логирование событий."""
        self.console_textbox.configure(state="normal")
        self.console_textbox.insert("end", f"> {message}\n")
        self.console_textbox.see("end")
        self.console_textbox.configure(state="disabled")

    # ================= UI Компоненты =================

    def setup_sidebar(self):
        """Панель настроек API и логирования."""
        self.sidebar = ctk.CTkFrame(self, width=320, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.sidebar.grid_rowconfigure(9, weight=1)

        # Заголовок
        self.logo_label = ctk.CTkLabel(self.sidebar, text="Настройки эндпоинта", font=ctk.CTkFont(size=15, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # API Base URL
        self.host_label = ctk.CTkLabel(self.sidebar, text="API Base URL:")
        self.host_label.grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")
        self.host_entry = ctk.CTkEntry(self.sidebar, placeholder_text="https://api.openai.com/v1")
        self.host_entry.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.host_entry.insert(0, "https://api.openai.com/v1")

        # API Key
        self.key_label = ctk.CTkLabel(self.sidebar, text="API Key:")
        self.key_label.grid(row=3, column=0, padx=20, pady=(5, 0), sticky="w")
        self.key_entry = ctk.CTkEntry(self.sidebar, placeholder_text="sk-...", show="*")
        self.key_entry.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        # Автоподстановка ключа из переменных окружения (если есть)
        env_key = os.environ.get("OPENAI_API_KEY", "")
        if env_key:
            self.key_entry.insert(0, env_key)

        # Выбор модели
        self.llm_label = ctk.CTkLabel(self.sidebar, text="Модель генерации (LLM):")
        self.llm_label.grid(row=5, column=0, padx=20, pady=(5, 0), sticky="w")
        self.llm_entry = ctk.CTkEntry(self.sidebar, placeholder_text="gpt-4o-mini")
        self.llm_entry.grid(row=6, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.llm_entry.insert(0, "gpt-4o-mini")

        # Консоль событий
        self.console_label = ctk.CTkLabel(self.sidebar, text="Ход генерации:")
        self.console_label.grid(row=8, column=0, padx=20, pady=(15, 0), sticky="w")

        self.console_textbox = ctk.CTkTextbox(self.sidebar, height=300, font=("Courier New", 11))
        self.console_textbox.grid(row=9, column=0, padx=20, pady=(5, 20), sticky="nsew")
        self.console_textbox.configure(state="disabled")

    def setup_main_area(self):
        """Правая рабочая зона (ввод, управление, вкладки)."""
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        self.main_area.grid_rowconfigure(1, weight=3)  # Ввод новости
        self.main_area.grid_rowconfigure(3, weight=4)  # Вывод сказки
        self.main_area.grid_columnconfigure(0, weight=1)

        # Поле ввода взрослой новости
        self.input_label = ctk.CTkLabel(self.main_area, text="Исходная мировая новость:", font=ctk.CTkFont(size=14, weight="bold"))
        self.input_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        self.news_textbox = ctk.CTkTextbox(self.main_area)
        self.news_textbox.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        # Панель управления (Запуск генерации и сохранение)
        self.control_panel = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.control_panel.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        self.control_panel.grid_columnconfigure(0, weight=2)
        self.control_panel.grid_columnconfigure(1, weight=2)
        self.control_panel.grid_columnconfigure(2, weight=1)

        # Кнопка запуска
        self.generate_btn = ctk.CTkButton(
            self.control_panel, 
            text="Переложить новость на сказку 🪄✨", 
            fg_color="green", 
            hover_color="darkgreen",
            command=self.start_adaptation_thread
        )
        self.generate_btn.grid(row=0, column=0, padx=(0, 10), pady=5, sticky="ew")

        # Поле нейминга сказки для сохранения
        self.title_entry = ctk.CTkEntry(self.control_panel, placeholder_text="Название сказки...")
        self.title_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        self.reset_title_entry()

        # Кнопка сохранения в локальную библиотеку
        self.save_btn = ctk.CTkButton(
            self.control_panel, 
            text="Сохранить в Библиотеку 💾", 
            fg_color="orange", 
            hover_color="#d67d00",
            command=self.save_current_fairytale
        )
        self.save_btn.grid(row=0, column=2, padx=(10, 0), pady=5, sticky="ew")

        # Вкладки вывода результатов
        self.tab_view = ctk.CTkTabview(self.main_area)
        self.tab_view.grid(row=3, column=0, padx=10, pady=(5, 10), sticky="nsew")
        
        self.tab_fairytale = self.tab_view.add("Русская народная сказка")
        self.tab_propp = self.tab_view.add("Пропповский анализ")
        self.tab_glossary = self.tab_view.add("Толковый словарик и Мораль")
        self.tab_library = self.tab_view.add("Библиотека")

        # Вкладка 1: Сказка
        self.tab_fairytale.grid_rowconfigure(0, weight=1)
        self.tab_fairytale.grid_columnconfigure(0, weight=1)
        self.output_textbox = ctk.CTkTextbox(self.tab_fairytale, font=("Georgia", 13))
        self.output_textbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Вкладка 2: Анализ по Проппу
        self.tab_propp.grid_rowconfigure(0, weight=1)
        self.tab_propp.grid_columnconfigure(0, weight=1)
        self.propp_textbox = ctk.CTkTextbox(self.tab_propp, font=("Courier New", 12))
        self.propp_textbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Вкладка 3: Словарик и Мораль
        self.tab_glossary.grid_rowconfigure(0, weight=1)
        self.tab_glossary.grid_columnconfigure(0, weight=1)
        self.glossary_textbox = ctk.CTkTextbox(self.tab_glossary, font=("Georgia", 13))
        self.glossary_textbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Вкладка 4: Библиотека сказок (Разделенная область)
        self.tab_library.grid_rowconfigure(0, weight=1)
        self.tab_library.grid_columnconfigure(0, weight=1) # Левая колонка - скролл со списком
        self.tab_library.grid_columnconfigure(1, weight=3) # Правая колонка - окно просмотра

        # Левый фрейм внутри вкладки Библиотеки (Список сказок + Кнопка восстановления)
        self.lib_left_frame = ctk.CTkFrame(self.tab_library, fg_color="transparent")
        self.lib_left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.lib_left_frame.grid_rowconfigure(0, weight=1)
        self.lib_left_frame.grid_columnconfigure(0, weight=1)

        self.library_scroll = ctk.CTkScrollableFrame(self.lib_left_frame, label_text="Архив сказок")
        self.library_scroll.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        self.restore_btn = ctk.CTkButton(
            self.lib_left_frame, 
            text="Показать во вкладках 📂", 
            fg_color="#1f538d",
            command=self.restore_selected_to_tabs
        )
        self.restore_btn.grid(row=1, column=0, sticky="ew", padx=2, pady=5)

        # Правый текстовый виджет просмотра в Библиотеке
        self.library_viewer = ctk.CTkTextbox(self.tab_library, font=("Georgia", 13))
        self.library_viewer.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

    def reset_title_entry(self):
        """Обновляет название сказки по умолчанию на текущее время."""
        self.title_entry.delete(0, "end")
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        self.title_entry.insert(0, f"Сказка от {now_str}")

    # ================= Логика архива / Библиотеки =================

    def safe_filename(self, name: str) -> str:
        """Очищает название от спецсимволов для безопасного сохранения файла."""
        clean = re.sub(r'[^a-zA-Z0-9а-яА-ЯёЁ_\- ]', '', name).strip()
        return clean.replace(' ', '_')

    def save_current_fairytale(self):
        """Сохраняет текущую сгенерированную сказку в JSON-файл."""
        title = self.title_entry.get().strip()
        news = self.news_textbox.get("1.0", "end-1c").strip()
        fairytale = self.output_textbox.get("1.0", "end-1c").strip()
        propp = self.propp_textbox.get("1.0", "end-1c").strip()
        glossary = self.glossary_textbox.get("1.0", "end-1c").strip()

        if not title:
            self.log("ОШИБКА сохранения: Введите название для сказки!")
            return
        if not fairytale or fairytale.startswith("Текст сказки появится здесь"):
            self.log("ОШИБКА сохранения: Текст сказки пуст. Сгенерируйте её сначала!")
            return

        filename = f"{self.safe_filename(title)}.json"
        filepath = os.path.join(self.library_dir, filename)

        data_to_save = {
            "title": title,
            "news": news,
            "fairytale": fairytale,
            "propp": propp,
            "glossary": glossary,
            "timestamp": datetime.datetime.now().isoformat()
        }

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)
            self.log(f"Сказка успешно сохранена в файл: {filename}")
            self.load_library_list()  # Перезагружаем список в UI
        except Exception as e:
            self.log(f"ОШИБКА при записи файла сказки: {e}")

    def load_library_list(self):
        """Сканирует папку библиотеки и обновляет список кнопок."""
        # Очищаем старые кнопки
        for widget in self.library_scroll.winfo_children():
            widget.destroy()

        if not os.path.exists(self.library_dir):
            return

        files = sorted(os.listdir(self.library_dir))
        json_files = [f for f in files if f.endswith(".json")]

        if not json_files:
            no_files_label = ctk.CTkLabel(self.library_scroll, text="Библиотека пуста", text_color="gray")
            no_files_label.pack(pady=10)
            return

        for file in json_files:
            filepath = os.path.join(self.library_dir, file)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                title = data.get("title", file)
                
                # Создаем интерактивную кнопку для каждой сказки
                btn = ctk.CTkButton(
                    self.library_scroll,
                    text=title,
                    anchor="w",
                    fg_color="transparent",
                    text_color="white" if ctk.get_appearance_mode() == "Dark" else "black",
                    hover_color=("gray70", "gray30"),
                    command=lambda fp=filepath: self.load_fairytale_to_viewer(fp)
                )
                btn.pack(fill="x", padx=5, pady=2)
            except Exception as e:
                print(f"Ошибка чтения {file}: {e}")

    def load_fairytale_to_viewer(self, filepath: str):
        """Загружает содержимое файла в правое окно просмотра библиотеки."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.selected_fairytale_data = data  # Кэшируем данные
            
            # Формируем красивый сводный вид
            view_text = f"=== НАЗВАНИЕ: {data.get('title')} ===\n\n"
            view_text += f"--- ИСХОДНАЯ НОВОСТЬ ---\n{data.get('news')}\n\n"
            view_text += f"--- СКАЗКА ---\n{data.get('fairytale')}\n\n"
            view_text += f"--- ПРОППОВСКИЙ РАЗБОР ---\n{data.get('propp')}\n\n"
            view_text += f"--- СЛОВАРИК И МОРАЛЬ ---\n{data.get('glossary')}\n"

            self.update_textbox_safe(self.library_viewer, view_text)
            self.log(f"В архивном просмотрщике открыта сказка: {data.get('title')}")
        except Exception as e:
            self.log(f"Не удалось открыть файл сказки: {e}")

    def restore_selected_to_tabs(self):
        """Восстанавливает выбранную из архива сказку во все основные рабочие вкладки редактора."""
        if not self.selected_fairytale_data:
            self.log("ОШИБКА: Сначала выберите сказку из списка слева!")
            return

        data = self.selected_fairytale_data
        
        # Обновляем поля ввода
        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, data.get("title", ""))
        
        self.update_textbox_safe(self.news_textbox, data.get("news", ""))
        self.update_textbox_safe(self.output_textbox, data.get("fairytale", ""))
        self.update_textbox_safe(self.propp_textbox, data.get("propp", ""))
        self.update_textbox_safe(self.glossary_textbox, data.get("glossary", ""))

        self.tab_view.set("Русская народная сказка")
        self.log(f"Архивная сказка '{data.get('title')}' успешно разложена по рабочим вкладкам!")

    # ================= Логика backend-генерации ИИ (OpenAI API) =================

    def start_adaptation_thread(self):
        """Запуск генерации в фоновом режиме."""
        host = self.host_entry.get().strip()
        api_key = self.key_entry.get().strip()
        llm = self.llm_entry.get().strip()
        news_text = self.news_textbox.get("1.0", "end-1c").strip()

        if not host or not llm:
            self.log("ОШИБКА: Заполните настройки эндпоинта в боковой панели!")
            return
        if not news_text:
            self.log("ОШИБКА: Пожалуйста, введите текст новости перед запуском!")
            return

        self.generate_btn.configure(state="disabled", text="Тку сказочное полотно...")
        self.reset_title_entry() # Обновляем время в заголовке по умолчанию
        threading.Thread(target=self.adapt_news_to_folklore, args=(host, api_key, llm, news_text), daemon=True).start()

    def adapt_news_to_folklore(self, host: str, api_key: str, llm: str, news_text: str):
        """Основной пайплайн трансляции новости в классическую русскую сказку по Проппу через OpenAI API."""
        try:
            # Инициализация OpenAI-совместимого клиента
            client = OpenAI(base_url=host, api_key=api_key if api_key else "dummy_key")
            
            self.log("Анализ новостной повестки...")

            # --- Шаг 1: Русская народная сказка ---
            self.log("Шаг 1/3: Генерация русской народной сказки по 5 фазам...")
            self.clear_textbox_safe(self.output_textbox)
            self.tab_view.set("Русская народная сказка")
            
            folklore_prompt = f"""
            Ты — выдающийся сказочник, мастер глубокого психологического и классического русского фольклора. 
            Твоя задача — проанализировать реальное новостное событие, извлечь его глубинное смысловое ядро (конфликт, проблему, суть решений) и написать на этой основе ПОЛНОЦЕННУЮ, длинную, высокохудожественную сказку в духе лучших сборников народных сказок Афанасьева.

            КЛЮЧЕВЫЕ ТРЕБОВАНИЯ К ХУДОЖЕСТВЕННОСТИ:
            1. НИКАКОГО ПАФОСА И КЛИШЕ: Избегай пафосных лозунгов, фальшивого героизма и прямолинейного морализаторства. Пиши спокойно, глубоко, поэтично, уделяя внимание деталям (быту, звукам природы, характерам героев).
            2. ОПОСРЕДОВАННЫЙ И НЕЗАВИСИМЫЙ СЮЖЕТ: Сказка не должна быть очевидным пересказом новости. Это должна быть самостоятельная, самодостаточная история. Новость передается через глубокие, неочевидные метафоры. Читатель не должен сразу догадаться, какая новость легла в основу, но должен прочувствовать её структуру и суть на глубинном уровне.
            3. ПОЛНОЦЕННЫЙ ОБЪЕМ И РАЗВИТИЕ (примерно пара страниц текста): Напиши развернутую историю с проработанной завязкой, неторопливым развитием сюжета, живыми диалогами персонажей, кульминацией и спокойной развязкой. Это не должен быть краткий конспект или обрывок. Сказка должна быть цельной и законченной.
            4. СЕТТИНГ И ГЕРОИ:
               - Используй сказочный анимализм (разумные, говорящие звери со своими характерами, должностями и сословиями) или людей в историческом антураже.
               - Сословия времен бояр и купцов, старые варианты должностей: бояре, купцы, воеводы, мытари, ратники, купеческие сыновья, крестьяне-пахари, царевичи.
               - Герои должны иметь мотивы, говорить напевным, но естественным народным языком без пафоса.

            СТРУКТУРА СКАЗКИ (Строго по 5 фундаментальным фазам Проппа):
            1. : Описание исходного благополучия, законов, устоявшегося порядка вещей в царстве или лесном содружестве.
            2. Фаза II: Вызов / Недостача (Появление скрытой беды, таинственной напасти или ограничения, которое медленно меняет привычный уклад жизни - метафора новости).
            3. Фаза III: Испытание / Поиск (Герой отправляется в путь. Его встречи, разговоры с другими персонажами, испытание характера на смекалку или честность).
            4. Фаза IV: Сеча / Преодоление (Кульминация. Негромкое, но мудрое и глубокое преодоление беды, нахождение решения через труд, взаимопомощь или хитрость).
            5. Фаза V: Преображение / Урок (Восстановление порядка, новые правила жизни, спокойный, глубокий вывод).

            ВЗРОСЛАЯ НОВОСТЬ-ОСНОВА (извлеки из неё только суть конфликта и структуры, но не пересказывай буквально):
            {news_text}

            Напиши полноценную сказку, чтобы она читалась на одном дыхании как старинное предание.
            """
            
            # Стандартный вызов chat.completions.create со стримингом для OpenAI SDK
            response = client.chat.completions.create(
                model=llm,
                messages=[{"role": "user", "content": folklore_prompt}],
                stream=True
            )
            
            fairytale_content = ""
            for chunk in response:
                if len(chunk.choices) > 0:
                    token = chunk.choices[0].delta.content
                    if token:
                        fairytale_content += token
                        self.append_text_safe(self.output_textbox, token)

            # --- Шаг 2: Морфологический анализ Проппа ---
            self.log("Шаг 2/3: Проведение Пропповского сопоставительного анализа по 5 фазам...")
            self.clear_textbox_safe(self.propp_textbox)
            
            propp_prompt = f"""
            Ты — ученый-фольклорист, исследователь скрытых смыслов и морфологии волшебной сказки.
            Проанализируй только что написанную сказку и сопоставь её глубокую метафорическую структуру с исходной реальной новостью, опираясь на 5 фундаментальных фаз Проппа.
            
            СТРУКТУРА РАЗБОРА:
            1. ИСХОДНЫЙ СЮЖЕТНЫЙ МОТИВ: (Какое глубинное новостное событие и конфликт лежат в основе этой сказки).
            2. ДЕКОДИРОВАНИЕ МЕТАФОР И АЛЛЕГОРИЙ: (Раскрой скрытый смысл сказки. Объясни, как реальные объекты новости зашифрованы в сказочном сюжете. Почему именно этот зверь/персонаж выбран на роль? Что символизируют ключевые сказочные образы - например, закрытые ворота, сонный туман, подземный путь или таинственная пыльца?).
            3. 5 ФУНДАМЕНТАЛЬНЫХ ФАЗ ПРОППА В СЮЖЕТЕ:
               Распиши каждую из 5 фаз по следующей схеме:
               - Название фазы:
                 * Как эта фаза сопоставляется с реальностью (событиями из новости).
                 * Цитата из сказки: [Фрагмент текста сказки, относящийся к фазе].

            СКАЗКА ДЛЯ АНАЛИЗА:
            {fairytale_content}

            ИСХОДНАЯ НОВОСТЬ:
            {news_text}
            """
            
            response_propp = client.chat.completions.create(
                model=llm,
                messages=[{"role": "user", "content": propp_prompt}],
                stream=True
            )
            
            for chunk in response_propp:
                if len(chunk.choices) > 0:
                    token = chunk.choices[0].delta.content
                    if token:
                        self.append_text_safe(self.propp_textbox, token)

            # --- Шаг 3: Словарик архаизмов и Мораль ---
            self.log("Шаг 3/3: Разработка детского толкового словарика и выявление морали...")
            self.clear_textbox_safe(self.glossary_textbox)
            
            glossary_prompt = f"""
            Проанализируй художественный текст сказки и составь для детей и исследователей:
            1. ТОЛКОВЫЙ СЛОВАРЬ (Архаизмы, сословия и должности): Выпиши старинные русские слова, сословия, варианты должностей или анималистические термины, использованные в сказке (например, мытарь, чертог, воевода, боярин, ратник, купеческий сын). Объясни их значение простым, понятным языком.
            2. ГЛУБОКАЯ МОРАЛЬ: Сформулируй поучительный смысл сказочной истории. Избегай пафоса и клише — покажи глубокий, житейский или философский урок, который несет в себе сюжет.

            СКАЗКА:
            {fairytale_content}
            """
            
            response_glossary = client.chat.completions.create(
                model=llm,
                messages=[{"role": "user", "content": glossary_prompt}],
                stream=True
            )
            
            for chunk in response_glossary:
                if len(chunk.choices) > 0:
                    token = chunk.choices[0].delta.content
                    if token:
                        self.append_text_safe(self.glossary_textbox, token)

            self.log("Трансляция новости в сказку успешно завершена!")

        except Exception as e:
            self.log(f"ОШИБКА генерации: {str(e)}")
            self.log("Убедитесь, что эндпоинт доступен и API-ключ указан верно.")
        finally:
            self.generate_btn.configure(state="normal", text="Переложить новость на сказочный мотив 🪄✨")

    # ================= Методы безопасного обновления UI из потока =================

    def update_textbox_safe(self, textbox: ctk.CTkTextbox, text: str):
        self.after(0, lambda: self._update_textbox(textbox, text))

    def _update_textbox(self, textbox: ctk.CTkTextbox, text: str):
        textbox.configure(state="normal")
        textbox.delete("1.0", "end")
        textbox.insert("1.0", text)

    def append_text_safe(self, textbox: ctk.CTkTextbox, text: str):
        self.after(0, lambda: self._append_text(textbox, text))

    def _append_text(self, textbox: ctk.CTkTextbox, text: str):
        textbox.configure(state="normal")
        textbox.insert("end", text)
        textbox.see("end")

    def clear_textbox_safe(self, textbox: ctk.CTkTextbox):
        self.after(0, lambda: self._clear_textbox(textbox))

    def _clear_textbox(self, textbox: ctk.CTkTextbox):
        textbox.configure(state="normal")
        textbox.delete("1.0", "end")


if __name__ == "__main__":
    app = ProppFairytaleApp()
    app.mainloop()
