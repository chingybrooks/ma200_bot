import time
import config
import telebot
from binance.client import Client
from binance.exceptions import BinanceAPIException
import numpy as np
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, filename='bot.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Инициализация клиента Binance и Telegram бота
client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET)
bot = telebot.TeleBot(config.TELEGRAM_TOKEN)

# Глобальные настройки
INTERVAL = '4h'  # Начальный интервал
TOUCH_PRECISION = 0.01  # Порог чувствительности для касания MA (1%)
EXCLUDED_SYMBOLS = ['USDT', 'BUSD', 'USDC', 'DAI', 'TUSD', 'PAX', 'GUSD', 'USDP', 'SUSD', 'UST']  # Исключаем стейблкоины

# Функция для получения топ-200 монет без стейблкоинов
def get_top_200_symbols():
    try:
        # Получение списка всех торговых пар
        tickers = client.get_ticker()
        symbols = []

        # Фильтрация топ-200 пар и исключение стейблкоинов
        for ticker in tickers:
            symbol = ticker['symbol']

            # Проверка на стейблкоин (исключаем пары, содержащие стейблкоины)
            if any(stable in symbol for stable in EXCLUDED_SYMBOLS):
                continue

            # Проверяем, что пара торгуется к USDT (или другим крупным рынкам)
            if symbol.endswith('USDT'):
                symbols.append(symbol)

        # Ограничиваем список топ-200
        return sorted(symbols, key=lambda s: float(client.get_symbol_ticker(symbol=s)['price']), reverse=True)[:200]

    except BinanceAPIException as e:
        logging.error(f"Ошибка при получении топ-200 монет: {e}")
        return []

# Функция для расчета скользящей средней
def get_moving_average(symbol, interval, window):
    try:
        klines = client.get_klines(symbol=symbol, interval=interval, limit=window)
        close_prices = [float(kline[4]) for kline in klines]  # Извлекаем цены закрытия
        return np.mean(close_prices)
    except BinanceAPIException as e:
        logging.error(f"Ошибка при получении данных с Binance: {e}")
        return None

# Функция для проверки касания уровня MA
def check_touch(symbol):
    ma_99 = get_moving_average(symbol, INTERVAL, 99)
    ma_200 = get_moving_average(symbol, INTERVAL, 200)

    if ma_99 is None or ma_200 is None:
        return

    try:
        current_price = float(client.get_symbol_ticker(symbol=symbol)['price'])
        if abs(current_price - ma_99) / ma_99 <= TOUCH_PRECISION:
            message = f"{symbol}: Цена коснулась уровня MA 99 ({ma_99}). Текущая цена: {current_price}"
            bot.send_message(config.CHAT_ID, message)
            logging.info(message)
        if abs(current_price - ma_200) / ma_200 <= TOUCH_PRECISION:
            message = f"{symbol}: Цена коснулась уровня MA 200 ({ma_200}). Текущая цена: {current_price}"
            bot.send_message(config.CHAT_ID, message)
            logging.info(message)
    except BinanceAPIException as e:
        logging.error(f"Ошибка при получении текущей цены: {e}")

# Обработчик команды для изменения интервала
@bot.message_handler(commands=['set_interval'])
def set_interval(message):
    global INTERVAL
    interval = message.text.split()[1]  # Например, '/set_interval 4h'
    if interval in ['1h', '4h', '1d', '1w']:
        INTERVAL = interval
        response = f"Интервал изменен на {interval}"
        bot.send_message(config.CHAT_ID, response)
        logging.info(response)
    else:
        bot.send_message(config.CHAT_ID, "Некорректный интервал. Используйте '1h', '4h', '1d', '1w'.")

# Обработчик команды для изменения порога касания MA
@bot.message_handler(commands=['set_precision'])
def set_precision(message):
    global TOUCH_PRECISION
    try:
        precision = float(message.text.split()[1])  # Например, '/set_precision 0.02' для 2%
        if 0 < precision < 0.1:  # Устанавливаем допустимые пределы от 0.1% до 10%
            TOUCH_PRECISION = precision
            response = f"Порог точности изменен на {precision * 100}%"
            bot.send_message(config.CHAT_ID, response)
            logging.info(response)
        else:
            bot.send_message(config.CHAT_ID, "Порог должен быть между 0.1% и 10%.")
    except ValueError:
        bot.send_message(config.CHAT_ID, "Введите корректное число для порога точности (например, 0.02 для 2%).")

# Основной цикл
def main():
    symbols = get_top_200_symbols()  # Получаем топ-200 монет без стейблкоинов

    while True:
        try:
            for symbol in symbols:
                check_touch(symbol)
            time.sleep(1800)  # Проверка каждые 30 минут (1800 секунд)
        except Exception as e:
            logging.error(f"Неожиданная ошибка в основном цикле: {e}")
            bot.send_message(config.CHAT_ID, f"Ошибка в работе бота: {e}")
            time.sleep(60)  # Задержка в случае ошибки, чтобы избежать частых повторений

if __name__ == "__main__":
    bot.polling(none_stop=True)  # Запуск бота для обработки команд
    main()
