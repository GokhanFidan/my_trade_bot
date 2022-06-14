import pandas as pd
import pandas_ta as pta
import numpy as np
from datetime import datetime, time, timedelta
import binance
import math
import requests
import talib as ta
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
import os

api_key = ''
api_secret = ''
client = Client(api_key, api_secret)

orderId_long = 0
orderId_short = 0
orderId_longtakeprofit = 0
orderId_shorttakeprofit = 0
orderId_longexit = 0
orderId_shortexit = 0


def decide_run(signalPmax, close, vwma, iftr, ma, precise_order_amount, quantityUsdt,
               symbol, inverse, last_posit):
    if (ma > close or inverse == "longexit") and last_posit == "longtrigggered":
        long_exit(precise_order_amount, symbol, quantityUsdt)

    if (ma < close or inverse == "shortexit") and last_posit == "shorttriggered":
        short_exit(precise_order_amount, symbol, quantityUsdt)

    if signalPmax == "BUY" and close > vwma and iftr > 0 and close > ma:
        open_long(precise_order_amount, quantityUsdt, symbol)

    if signalPmax == "SELL" and close < vwma and iftr < 0 and close < ma:
        open_short(precise_order_amount, quantityUsdt, symbol)


def last_position(symbol):
    a = []
    try:
        for i in reversed(client.futures_get_all_orders()):
            if i['symbol'] == symbol:
                a.append(i)
    except binance.exceptions.BinanceAPIException as e:
        print(f"tüm emirleri çekerken problem oldu {e.message}")
        substring = 'Timestamp for this request was 1000ms ahead of the server'
        if substring in e.message:
            os.system('w32tm/resync')
            for i in reversed(client.futures_get_all_orders()):
                if i['symbol'] == symbol:
                    a.append(i)
    if len(a) == 0:
        return False  # daha önce hiç ticaret yapılmadı last_posit=false
    else:
        if a[0]['orderId'] == orderId_long and a[0]['status'] == 'FILLED':
            return "longtrigggered"
        elif a[0]['orderId'] == orderId_short and a[0]['status'] == 'FILLED':
            return "shorttriggered"
        elif a[0]['orderId'] == orderId_longexit and a[0]['status'] == 'FILLED':
            return "longexittriggered"
        elif a[0]['orderId'] == orderId_shortexit and a[0]['status'] == 'FILLED':
            return "shortexittriggered"
        else:
            return False


"""        elif a[0]['orderId'] == orderId_longtakeprofit and a[0]['status']=='NEW':
            return "longtakeprofitopenednottriggered"
        elif a[0]['orderId'] == orderId_longtakeprofit and a[0]['status']=='FILLED':
            return "longtakeprofittriggered"

        elif a[0]['orderId'] == orderId_shorttakeprofit and a[0]['status']=='NEW':
            return "shorttakeprofitopenednottriggered"
        elif a[0]['orderId'] == orderId_shorttakeprofit and a[0]['status']=='FILLED':
            return "shorttakeprofittriggered"
        
        elif a[0]['orderId'] == orderId_shortexit and a[0]['status']=='NEW':
            return "shortexitopenednottriggered"
        
        elif a[0]['orderId'] == orderId_longexit and a[0]['status']=='NEW':
            return "longexitopenednottriggered"
"""


def generatevar(data, moving_average_length=11):
    var_arr = (pta.vidya(((data.High + data.Low) / 2), moving_average_length)).tolist()
    return var_arr


def generatePMax(var_array, close_array, high_array, low_array, atr_period, atr_multiplier):
    try:
        tr = pta.true_range(high_array, low_array, close_array)
        atr = pta.sma(tr, atr_period)
    except Exception as exp:
        print('exception in atr:', str(exp), flush=True)
        return []

    previous_final_upperband = 0
    previous_final_lowerband = 0
    final_upperband = 0
    final_lowerband = 0
    previous_var = 0
    previous_pmax = 0
    pmax = []
    pmaxc = 0

    for i in range(0, len(close_array)):
        if np.isnan(close_array[i]):
            pass
        else:
            atrc = atr[i]
            varc = var_array[i]

            if math.isnan(atrc):
                atrc = 0

            basic_upperband = varc + atr_multiplier * atrc
            basic_lowerband = varc - atr_multiplier * atrc

            if basic_upperband < previous_final_upperband or previous_var > previous_final_upperband:
                final_upperband = basic_upperband
            else:
                final_upperband = previous_final_upperband

            if basic_lowerband > previous_final_lowerband or previous_var < previous_final_lowerband:
                final_lowerband = basic_lowerband
            else:
                final_lowerband = previous_final_lowerband

            if previous_pmax == previous_final_upperband and varc <= final_upperband:
                pmaxc = final_upperband
            else:
                if previous_pmax == previous_final_upperband and varc >= final_upperband:
                    pmaxc = final_lowerband
                else:
                    if previous_pmax == previous_final_lowerband and varc >= final_lowerband:
                        pmaxc = final_lowerband
                    elif previous_pmax == previous_final_lowerband and varc <= final_lowerband:
                        pmaxc = final_upperband

            pmax.append(pmaxc)

            previous_var = varc

            previous_final_upperband = final_upperband

            previous_final_lowerband = final_lowerband

            previous_pmax = pmaxc

    return pmax


def generateSignalPmax(data):
    var_arr = generatevar(data, moving_average_length=11)
    pmax = generatePMax(var_arr, data.Close, data.High, data.Low, 10, 1.4)
    previous_var = var_arr[-2]
    previous_pmax = pmax[-2]
    last_var = var_arr[-1]
    last_pmax = pmax[-1]
    if last_var > last_pmax and previous_pmax > previous_var:
        return "BUY"

    if last_var < last_pmax and previous_pmax < previous_var:
        return "SELL"


def calculate_vwma(high, low, close, volume):
    a = pta.vwma(((high + low + close) / 3), volume, 200)
    return a[-1:]


def calculate_ma(close):
    b = pta.sma(close, 100)
    return b[-1:]


def Inverse(all_close):
    v12 = 0.1 * (ta.RSI(all_close, 116) - 50)
    v22 = ta.WMA(v12, 26)
    iftr = (np.exp(2 * v22) - 1) / (np.exp(2 * v22) + 1)
    iftr_now = iftr[iftr.index[-1]]
    iftr_previous = iftr[iftr.index[-2:-1]]
    if (float(iftr_previous > 0.25)) and (float(iftr_now) < 0.25):
        return "longexit"
    if (float(iftr_previous) < -0.25) and (float(iftr_now) > -0.25):
        return "shortexit"


def calculate_iftransformrsi(all_close):
    v12 = 0.1 * (ta.RSI(all_close, 116) - 50)
    v22 = ta.WMA(v12, 26)
    iftr = (np.exp(2 * v22) - 1) / (np.exp(2 * v22) + 1)
    return iftr[-1:]


def get_data(symbol):
    try:
        source = client.futures_historical_klines(symbol=symbol, interval="3m",
                                                  start_str=(datetime.now() - timedelta(days=1)).strftime(
                                                      '%Y-%m-%d %H:%M:%S'))
        data = pd.DataFrame(source,
                            columns=['Open time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close time', 'Qav', 'Not',
                                     'Tbbav', 'Tbqav', 'Ignore'])
        data.drop(['Open time', 'Qav', 'Not', 'Tbbav', 'Tbqav', 'Ignore', 'Close time'], axis=1, inplace=True)
        data.Open = data.Open.astype("float")
        data.Low = data.Low.astype("float")
        data.High = data.High.astype("float")
        data.Close = data.Close.astype("float")
        data.Volume = data.Volume.astype("float")
        return data
    except binance.exceptions.BinanceAPIException as e:
        print(f"tüm emirleri çekerken problem oldu {e.message}")
        substring = 'Timestamp for this request was 1000ms ahead of the server'
        if substring in e.message:
            os.system('w32tm/resync')


def calculate_amount(amount, leverage, symbol):
    global info_o, current_price, precision, price_precise
    quantityUsdt = float(amount * leverage)
    try:
        info_1 = client.futures_mark_price(symbol=symbol, recvWindow=5000)
        current_price = info_1['markPrice']
    except binance.exceptions.BinanceAPIException as e:
        print(f"markprice symbol  çekerken calculateamountta problem oldu {e.message}")
        substring = 'Timestamp for this request was 1000ms ahead of the server'
        if substring in e.message:
            os.system('w32tm/resync')
    try:

        info_o = client.futures_exchange_info()['symbols']
    except binance.exceptions.BinanceAPIException as e:
        print(f"exchange info çekerken calculateamountta problem oldu {e.message}")
        substring = 'Timestamp for this request was 1000ms ahead of the server'
        if substring in e.message:
            os.system('w32tm/resync')
    for i in range(len(info_o)):
        if info_o[i]['symbol'] == symbol:
            precision = info_o[i]['quantityPrecision']
            price_precise = info_o[i]['pricePrecision']
    order_amount = quantityUsdt / float(current_price)
    precise_order_amount = "{:0.0{}f}".format(order_amount, precision)
    return precise_order_amount, quantityUsdt, int(price_precise)


def open_long(precise_order_amount, quantityUsdt, symbol):
    try:
        my_order = client.futures_create_order(symbol=symbol, side="BUY", type='MARKET',
                                               quantity=precise_order_amount, recvWindow=5000)
        telegram_bot_sendtext(bot_mesaj=f"open long gerçekleşti size : long {quantityUsdt} saat :{datetime.now()}",
                              bot_token='',
                              id=)
        print(f"open long gerçekleşti size : long {quantityUsdt} saat :{datetime.now()}")
        global orderId_long
        orderId_long = my_order['orderId']

    except binance.exceptions.BinanceAPIException as e:
        telegram_bot_sendtext(bot_mesaj=f"timestamp long emir gönderirken open_longta problem oldu {e.message}",
                              bot_token='',
                              id=)
        print(f"long emir gönderirken open_longta problem oldu {e.message}")
        substring = 'Timestamp for this request was 1000ms ahead of the server'
        if substring in e.message:
            os.system('w32tm/resync')
    except binance.exceptions.BinanceOrderMinAmountException as e:
        telegram_bot_sendtext(bot_mesaj=f"open long emir gönderemedim {e.message}",
                              bot_token='',
                              id=)
        print(f"open long emir gönderemedim {e.message}")
    except binance.exceptions.BinanceOrderException as e:
        telegram_bot_sendtext(bot_mesaj=f"open long emir gönderemedim {e.message}",
                              bot_token='',
                              id=)
        print(f"open long emir gönderemedim {e.message}")
    except binance.exceptions.BinanceRequestException as e:
        telegram_bot_sendtext(bot_mesaj=f"open long emir gönderemedim {e.message}",
                              bot_token='',
                              id=)
        print(f"open long emir gönderemedim {e.message}")



def open_short(precise_order_amount, quantityUsdt, symbol):
    global orderId_short
    try:
        my_order = client.futures_create_order(symbol=symbol, side="SELL", type='MARKET',
                                               quantity=precise_order_amount, recvWindow=5000)
        telegram_bot_sendtext(
            bot_mesaj=f"open short emir gerçekleşti size : short {quantityUsdt} saat :{datetime.now()}",
            bot_token='',
            id=)
        print(f"open short emir gerçekleşti size : short {quantityUsdt} saat :{datetime.now()}")
        orderId_short = my_order['orderId']
    except binance.exceptions.BinanceAPIException as e:
        telegram_bot_sendtext(
            bot_mesaj=f"timestamp short emir gönderirken open_shortta problem oldu {e.message}",
            bot_token='',
            id=)
        print(f"short emir gönderirken open_shortta problem oldu {e.message}")
        substring = 'Timestamp for this request was 1000ms ahead of the server'
        if substring in e.message:
            os.system('w32tm/resync')
    except binance.exceptions.BinanceOrderMinAmountException as e:
        telegram_bot_sendtext(
            bot_mesaj=f"open short emir gönderemedim {e.message}",
            bot_token='',
            id=)
        print(f"open short emir gönderemedim {e.message}")
    except binance.exceptions.BinanceOrderException as e:
        telegram_bot_sendtext(
            bot_mesaj=f"open short emir gönderemedim {e.message}",
            bot_token='',
            id=)
        print(f"open short emir gönderemedim {e.message}")
    except binance.exceptions.BinanceRequestException as e:
        telegram_bot_sendtext(
            bot_mesaj=f"open short emir gönderemedim {e.message}",
            bot_token='',
            id=)
        print(f"open short emir gönderemedim {e.message}")



def long_exit(precise_order_amount, symbol, quantityUsdt):
    global orderId_longexit
    try:
        my_order = client.futures_create_order(symbol=symbol, side="SELL", type='MARKET', quantity=precise_order_amount,
                                               reduceOnly=True,
                                               recvWindow=5000)
        orderId_longexit = my_order['orderId']
        telegram_bot_sendtext(
            bot_mesaj=f"long exit emir açıldı : {quantityUsdt} saat : {datetime.now()}",
            bot_token='',
            id=)
        print(f"long exit emir açıldı : {quantityUsdt} saat : {datetime.now()}")
    except binance.exceptions.BinanceAPIException as e:
        telegram_bot_sendtext(
            bot_mesaj=f"timestamp longexit gönderirken long_exitte problem oldu {e.message}",
            bot_token='',
            id=)
        print(f"longexit gönderirken long_exitte problem oldu {e.message}")
        substring = 'Timestamp for this request was 1000ms ahead of the server'
        if substring in e.message:
            os.system('w32tm/resync')


def short_exit(precise_order_amount, symbol, quantityUsdt):
    global orderId_shortexit
    try:
        my_order = client.futures_create_order(symbol=symbol, side="BUY", type='MARKET', quantity=precise_order_amount,
                                               reduceOnly=True,
                                               recvWindow=5000)
        orderId_shortexit = my_order['orderId']
        telegram_bot_sendtext(
            bot_mesaj=f"short exit emir açıldı : {quantityUsdt} saat : {datetime.now()}",
            bot_token='',
            id=)
        print(f"short exit emir açıldı : {quantityUsdt} saat : {datetime.now()}")
    except binance.exceptions.BinanceAPIException as e:
        telegram_bot_sendtext(
            bot_mesaj=f" timestamp shortexit gönderirken short_exitte problem oldu {e.message}",
            bot_token='',
            id=)
        print(f"shortexit gönderirken short_exitte problem oldu {e.message}")
        substring = 'Timestamp for this request was 1000ms ahead of the server'
        if substring in e.message:
            os.system('w32tm/resync')


def telegram_bot_sendtext(bot_token, bot_mesaj, id: str):
    bot_token = '-'
    bot_chatID = id
    url = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + str(
        bot_chatID) + '&parse_mode=Markdown&text=' + bot_mesaj

    response = requests.get(url)
