import os
import logging
import threading
import json
import uvicorn
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from main import app as fastapi_app # Импортируем экземпляр FastAPI из main.py

# --- Настройка логгера ---
# Настраиваем здесь, чтобы он был доступен и для бота, и для веб-сервера
activity_logger = logging.getLogger("activity_logger")
activity_logger.setLevel(logging.INFO)
handler = logging.FileHandler("activity.log", mode='a', encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
# Избегаем двойного добавления обработчика, если модуль импортируется несколько раз
if not activity_logger.handlers:
    activity_logger.addHandler(handler)

# --- Логика Telegram-бота ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение с кнопкой для открытия Mini App."""
    web_app_url = os.environ.get("WEB_APP_URL")
    if not web_app_url:
        await update.message.reply_text("Извините, URL веб-приложения не настроен. Обратитесь к администратору.")
        return

    # Создаем кнопку, которая открывает веб-приложение
    keyboard = [
        [InlineKeyboardButton("🚀 Проверить скорость", web_app=WebAppInfo(url=web_app_url))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 Добро пожаловать в Pro Speed Test!\n\n"
        "Нажмите на кнопку ниже, чтобы открыть приложение и измерить скорость вашего интернет-соединения.",
        reply_markup=reply_markup
    )

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает данные, полученные от веб-приложения, и отправляет их пользователю."""
    data = json.loads(update.effective_message.web_app_data.data)
    
    # Логируем полученные результаты
    client_info = data.get('clientInfo', {})
    ip_address = client_info.get('ip', 'N/A')
    
    summary_log = (
        f"TEST from IP: {ip_address}, "
        f"Ping: {data.get('ping', 'N/A')}, "
        f"Download: {data.get('download', 'N/A')}, "
        f"Upload: {data.get('upload', 'N/A')}"
    )
    activity_logger.info(summary_log)

    details_log = (
        f"--- TEST DETAILS (IP: {ip_address}) ---\n"
        f"{data.get('fullLog', 'Детальный лог отсутствует.')}\n"
        f"--- END OF TEST (IP: {ip_address}) ---"
    )
    activity_logger.info(details_log)

    # Формируем и отправляем красивое сообщение пользователю
    await update.message.reply_text(
        "✅ **Тест завершен!**\n\n"
        f"**Пинг (Задержка):** {data.get('ping', '-')}\n"
        f"**Скорость загрузки (Download):** {data.get('download', '-')}\n"
        f"**Скорость отправки (Upload):** {data.get('upload', '-')}\n\n"
        "Спасибо за использование нашего сервиса!"
    )

# --- Функции для запуска серверов ---

def run_fastapi():
    """Запускает веб-сервер FastAPI."""
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)

def main() -> None:
    """Основная функция для запуска бота и веб-сервера."""
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        print("Ошибка: Токен бота (BOT_TOKEN) не найден в секретах Replit.")
        return

    # Запускаем FastAPI в отдельном потоке, чтобы не блокировать бота
    fastapi_thread = threading.Thread(target=run_fastapi)
    fastapi_thread.daemon = True
    fastapi_thread.start()
    print("Сервер FastAPI запущен в фоновом режиме.")

    # Настраиваем и запускаем Telegram-бота
    application = Application.builder().token(bot_token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))

    print("Telegram-бот запущен. Ожидание команд...")
    application.run_polling()

if __name__ == "__main__":
    main()
