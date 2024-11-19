import logging
import time
import numpy as np
from pycoingecko import CoinGeckoAPI
from telebot import TeleBot
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# Инициализация клиента CoinGecko и Telegram
cg = CoinGeckoAPI()
bot = TeleBot(Config.TELEGRAM_TOKEN)

# Логирование с ротацией логов
log_handler = logging.handlers.RotatingFileHandler('crypto_bot.log', maxBytes=5*1024*1024, backupCount=3)
log_handler.setLevel(logging.INFO)
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger()
logger.addHandler(log_handler)

# Настройки
INTERVAL = '4h'  # Используемый интервал
TOUCH_PRECISION = 0.01  # Порог приближения к MA (по умолчанию 1%)

# Получение MA с CoinGecko
def get_moving_average(symbol_id, days='30', interval='4h', window=99):
    try:
        # Получаем данные о ценах за последние дни с указанным интервалом
        market_data = cg.get_coin_market_chart_by_id(id=symbol_id, vs_currency='usd', days=days, interval=interval)
        close_prices = [price[1] for price in market_data['prices']]
        
        if len(close_prices) < window:
            return None  # Недостаточно данных для расчета MA
        
        return np.mean(close_prices[-window:])
    except Exception as e:
        logging.error(f"Ошибка при получении данных с CoinGecko для {symbol_id}: {e}")
        return None

# Функция для логирования уведомлений
def log_alert(message):
    logging.info(f"Отправлено уведомление: {message}")
    bot.send_message(config.CHAT_ID, message)

# Функция проверки касания MA
def check_touch(symbol_id):
    ma_99 = get_moving_average(symbol_id, window=99)
    ma_200 = get_moving_average(symbol_id, window=200)
    
    if not ma_99 or not ma_200:
        logging.error(f"Не удалось получить MA для {symbol_id}")
        return

    current_price = cg.get_price(ids=symbol_id, vs_currencies='usd')[symbol_id]['usd']
    
    if abs((current_price - ma_99) / ma_99) <= TOUCH_PRECISION:
        message = f"Цена {symbol_id} коснулась MA 99: {current_price} (MA 99 = {ma_99})"
        log_alert(message)
    if abs((current_price - ma_200) / ma_200) <= TOUCH_PRECISION:
        message = f"Цена {symbol_id} коснулась MA 200: {current_price} (MA 200 = {ma_200})"
        log_alert(message)

# Команда для настройки порога
@bot.message_handler(commands=['set_alert_threshold'])
def set_alert_threshold(message):
    global TOUCH_PRECISION
    try:
        threshold = float(message.text.split()[1])  # Например, '/set_alert_threshold 0.05' для 5%
        if 0 < threshold < 0.2:  # Ограничение от 0.1% до 20%
            TOUCH_PRECISION = threshold
            response = f"Порог приближения к MA установлен на {threshold * 100}%"
            bot.send_message(config.CHAT_ID, response)
            logging.info(response)
        else:
            bot.send_message(config.CHAT_ID, "Порог должен быть между 0.1% и 20%.")
    except ValueError:
        bot.send_message(config.CHAT_ID, "Введите корректное число для порога (например, 0.05 для 5%).")

# Получение списка топ-200 монет (исключая stablecoins)
def get_top_200_symbols():
    try:
        # Получаем топ-200 монет с CoinGecko, исключая stablecoins
        coins = cg.get_coins_markets(vs_currency='usd')
        filtered_coins = [coin['id'] for coin in coins if not coin['id'].endswith('usd') and not 'usd' in coin['id']]
        return filtered_coins[:200]  # Ограничиваем до топ-200
    except Exception as e:
        logging.error(f"Ошибка при получении списка монет с CoinGecko: {e}")
        return []

# Основной цикл с многопоточностью
def main():
    symbols = get_top_200_symbols()  # Получаем топ-200 монет
    while True:
        try:
            with ThreadPoolExecutor(max_workers=5) as executor:
                executor.map(check_touch, symbols)
            time.sleep(1800)  # Задержка на 30 минут перед повторной проверкой
        except Exception as e:
            logging.error(f"Неожиданная ошибка в основном цикле: {e}")
            bot.send_message(config.CHAT_ID, f"Ошибка в работе бота: {e}")
            time.sleep(60)

if __name__ == '__main__':
    main()
