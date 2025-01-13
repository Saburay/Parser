# ----------------------
#   Code by Radimich   
#   Date: 2025
#   Land:Larnevsk     
# ----------------------
'''Создание приложения на Python, которое парсит медиафайлы с сайта,
требует авторизации, запоминает данные пользователя и структурирует файлы
Что исправлено:
Добавление протокола к URL:
Если URL начинается с //, добавляется https:.
Обработка недопустимых символов в именах файлов:
Удаляются символы, которые не могут быть частью имени файла.
Логирование ошибок:
Все ошибки записываются в файл parser.log.
Улучшенная обработка ошибок при скачивании файлов:
Если файл недоступен, программа продолжает скачивать остальные файлы.
Как использовать:
Запусти приложение.
Введи URL сайта.
Если сайт требует авторизации, введи логин и пароль.
Нажми "Начать парсинг" и выбери папку для сохранения.
Нажми "Открыть папку с данными" — откроется папка с сохранёнными файлами.
'''
import os
import json
import requests
from bs4 import BeautifulSoup
from tkinter import Tk, Label, Entry, Button, messagebox, filedialog, simpledialog
import subprocess  # Для открытия папки
import logging  # Для логирования ошибок
from urllib.parse import urljoin  # Для корректного объединения URL

# Настройка логирования
logging.basicConfig(filename="parser.log", level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

# Файл для хранения данных пользователя
CONFIG_FILE = "user_config.json"

# Загрузка конфигурации
def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as file:
                return json.load(file)
        return {"url": "", "username": "", "password": ""}
    except Exception as e:
        logging.error(f"Ошибка при загрузке конфигурации: {e}")
        return {"url": "", "username": "", "password": ""}

# Сохранение конфигурации
def save_config(url, username, password):
    try:
        config = {"url": url, "username": username, "password": password}
        with open(CONFIG_FILE, "w") as file:
            json.dump(config, file)
    except Exception as e:
        logging.error(f"Ошибка при сохранении конфигурации: {e}")

# Проверка необходимости авторизации
def check_auth_required(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            login_form = soup.find("form", {"action": lambda x: x and "login" in x.lower()})
            return login_form is not None
        else:
            logging.error(f"Ошибка при проверке авторизации: статус {response.status_code}")
            return False
    except Exception as e:
        logging.error(f"Ошибка при проверке авторизации: {e}")
        return False

# Авторизация на сайте
def login(url, username, password):
    session = requests.Session()
    login_data = {
        "username": username,
        "password": password
    }
    try:
        response = session.post(f"{url}/login", data=login_data, timeout=10)
        if response.status_code == 200:
            return session
        else:
            logging.error(f"Ошибка авторизации: статус {response.status_code}")
            messagebox.showerror("Ошибка", "Не удалось авторизоваться")
            return None
    except Exception as e:
        logging.error(f"Ошибка авторизации: {e}")
        messagebox.showerror("Ошибка", f"Ошибка подключения: {e}")
        return None

# Парсинг медиафайлов
def parse_media(session, url):
    media_files = []
    try:
        response = session.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            # Поиск всех тегов <img>, <video>, <audio>
            for img in soup.find_all("img"):
                try:
                    src = img.get("src")
                    if src:
                        # Добавляем протокол, если URL начинается с //
                        if src.startswith("//"):
                            src = "https:" + src
                        media_files.append({"type": "image", "url": src})
                except Exception as e:
                    logging.error(f"Ошибка при обработке изображения: {e}")

            for video in soup.find_all("video"):
                try:
                    src = video.get("src")
                    if src:
                        if src.startswith("//"):
                            src = "https:" + src
                        media_files.append({"type": "video", "url": src})
                except Exception as e:
                    logging.error(f"Ошибка при обработке видео: {e}")

            for audio in soup.find_all("audio"):
                try:
                    src = audio.get("src")
                    if src:
                        if src.startswith("//"):
                            src = "https:" + src
                        media_files.append({"type": "audio", "url": src})
                except Exception as e:
                    logging.error(f"Ошибка при обработке аудио: {e}")
        else:
            logging.error(f"Ошибка при парсинге: статус {response.status_code}")
            messagebox.showerror("Ошибка", f"Ошибка при парсинге: статус {response.status_code}")
    except Exception as e:
        logging.error(f"Ошибка при парсинге: {e}")
        messagebox.showerror("Ошибка", f"Ошибка парсинга: {e}")

    return media_files

# Графический интерфейс
class ParserApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Парсер медиафайлов")

        # Загрузка конфигурации
        self.config = load_config()

        # Переменная для хранения пути к последней папке с данными
        self.last_save_path = None

        # Поля ввода
        Label(root, text="URL сайта:").grid(row=0, column=0, padx=10, pady=10)
        self.url_entry = Entry(root, width=50)
        self.url_entry.insert(0, self.config.get("url", ""))
        self.url_entry.grid(row=0, column=1, padx=10, pady=10)

        # Кнопка "Начать парсинг"
        Button(root, text="Начать парсинг", command=self.start_parsing).grid(row=1, column=1, pady=10)

        # Кнопка "Открыть папку с данными"
        Button(root, text="Открыть папку с данными", command=self.open_data_folder).grid(row=2, column=1, pady=10)

        # Кнопка "Сохранить данные"
        Button(root, text="Сохранить данные", command=self.save_data).grid(row=3, column=1, pady=10)

    def start_parsing(self):
        url = self.url_entry.get()
        if not url:
            messagebox.showerror("Ошибка", "Введите URL сайта")
            return

        # Проверка необходимости авторизации
        auth_required = check_auth_required(url)
        if auth_required:
            username = simpledialog.askstring("Логин", "Введите логин:", parent=self.root)
            password = simpledialog.askstring("Пароль", "Введите пароль:", parent=self.root, show="*")
            if not username or not password:
                messagebox.showerror("Ошибка", "Логин и пароль обязательны")
                return

            # Сохранение данных
            save_config(url, username, password)

            # Авторизация
            session = login(url, username, password)
            if not session:
                return
        else:
            session = requests.Session()  # Сессия без авторизации

        # Парсинг медиафайлов
        media_files = parse_media(session, url)
        if media_files:
            self.last_save_path = self.save_media(media_files)
            messagebox.showinfo("Успех", f"Медиафайлы успешно сохранены в {self.last_save_path}")
        else:
            messagebox.showinfo("Информация", "Медиафайлы не найдены")

    def save_media(self, media_files):
        save_path = filedialog.askdirectory(title="Выберите папку для сохранения")
        if not save_path:
            return None

        for media in media_files:
            file_type = media["type"]
            file_url = media["url"]
            file_name = os.path.basename(file_url)

            # Убираем недопустимые символы из имени файла
            file_name = "".join(c for c in file_name if c.isalnum() or c in ('.', '_', '-'))

            # Создание папки по типу файла
            type_folder = os.path.join(save_path, file_type)
            if not os.path.exists(type_folder):
                os.makedirs(type_folder)

            # Скачивание файла с обработкой ошибок
            try:
                response = requests.get(file_url, timeout=10)  # Таймаут 10 секунд
                if response.status_code == 200:
                    with open(os.path.join(type_folder, file_name), "wb") as file:
                        file.write(response.content)
                    print(f"Сохранено: {file_name} в папку {type_folder}")
                else:
                    logging.error(f"Ошибка при скачивании {file_name}: статус {response.status_code}")
            except Exception as e:
                logging.error(f"Ошибка при скачивании {file_name}: {e}")

        return save_path

    def open_data_folder(self):
        if self.last_save_path and os.path.exists(self.last_save_path):
            try:
                # Открываем папку в проводнике (Windows) или Finder (macOS)
                if os.name == "nt":  # Windows
                    os.startfile(self.last_save_path)
                elif os.name == "posix":  # macOS или Linux
                    subprocess.run(["open", self.last_save_path] if os.uname().sysname == "Darwin" else ["xdg-open", self.last_save_path])
            except Exception as e:
                logging.error(f"Ошибка при открытии папки: {e}")
                messagebox.showerror("Ошибка", f"Не удалось открыть папку: {e}")
        else:
            messagebox.showinfo("Информация", "Папка с данными не найдена или парсинг ещё не выполнен.")

    def save_data(self):
        # Сохраняем данные (например, конфигурацию или лог ошибок)
        save_path = filedialog.asksaveasfilename(
            title="Сохранить данные",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if save_path:
            try:
                # Пример: сохраняем текущую конфигурацию
                with open(save_path, "w") as file:
                    json.dump(self.config, file)
                messagebox.showinfo("Успех", f"Данные сохранены в {save_path}")
            except Exception as e:
                logging.error(f"Ошибка при сохранении данных: {e}")
                messagebox.showerror("Ошибка", f"Не удалось сохранить данные: {e}")

# Запуск приложения
if __name__ == "__main__":
    root = Tk()
    app = ParserApp(root)
    root.mainloop()

#----------------------------------