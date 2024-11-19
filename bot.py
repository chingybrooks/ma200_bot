import time
import config
import telebot
from binance.client import Client
from binance.exceptions import BinanceAPIException
import numpy as np

# Инициализация клиента Binance и Telegram бота
client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET)
bot = telebot.TeleBot(config.TELEGRAM_TOKEN)

# Функция для расчета скользящей средней
def get_moving_average(symbol, interval, window):
    try:
        # Получаем исторические данные свечей (кандидельный график)
        klines = client.get_klines(symbol=symbol, interval=interval, limit=window)
        close_prices = [float(kline[4]) for kline in klines]  # Извлекаем цены закрытия
        return np.mean(close_prices)
    except BinanceAPIException as e:
        print(f"Ошибка при получении данных с Binance: {e}")
        return None

# Функция для проверки касания уровня MA
def check_touch(symbol, interval='1h'):
    ma_99 = get_moving_average(symbol, interval, 99)
    ma_200 = get_moving_average(symbol, interval, 200)

    if ma_99 is None or ma_200 is None:
        return

    try:
        # Получаем последнюю цену
        current_price = float(client.get_symbol_ticker(symbol=symbol)['price'])
        if abs(current_price - ma_99) / ma_99 <= 0.01:  # Точность до 1%
            bot.send_message(config.CHAT_ID, f"{symbol}: Цена коснулась уровня MA 99 ({ma_99}). Текущая цена: {current_price}")
        if abs(current_price - ma_200) / ma_200 <= 0.01:  # Точность до 1%
            bot.send_message(config.CHAT_ID, f"{symbol}: Цена коснулась уровня MA 200 ({ma_200}). Текущая цена: {current_price}")
    except BinanceAPIException as e:
        print(f"Ошибка при получении текущей цены: {e}")

# Основной цикл
def main():
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']  # Укажите монеты, которые хотите отслеживать
    interval = '1h'  # Интервал времени для расчета (например, '1h', '4h', '1d')

    while True:
        for symbol in symbols:
            check_touch(symbol, interval)
        time.sleep(300)  # Проверка каждые 5 минут

if __name__ == "__main__":
    main()
