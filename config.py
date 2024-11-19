import os
from dotenv import load_dotenv

# Загрузка переменных из .env файла
load_dotenv()

class Config:
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    CHAT_ID = os.getenv('CHAT_ID')
