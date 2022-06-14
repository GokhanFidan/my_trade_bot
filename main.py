from binance.exceptions import BinanceAPIException, BinanceOrderException
from functions import *
api_key=''
api_secret=''
client = Client(api_key, api_secret)

global amount
global signalPmax
symbol='SOLUSDT'
leverage = 20

try:
    amount = float(client.futures_account()['totalMarginBalance'])-1
except binance.exceptions.BinanceAPIException as e:
    print(f"miktarı girerken problem oldu {e.message}")
    substring = 'Timestamp for this request was 1000ms ahead of the server'
    if substring in e.message:
       os.system('w32tm/resync')


try:
    client.futures_change_leverage(symbol=symbol, leverage=leverage, recvWindow=5000)
except binance.exceptions.BinanceAPIException as e:
    print(f"kaldıracı ayarlarken problem oldu {e.message}")
    substring = 'Timestamp for this request was 1000ms ahead of the server'
    if substring in e.message:
       os.system('w32tm/resync')
try:
    client.futures_change_margin_type(symbol=symbol, marginType='ISOLATED', recvWindow=5000)
except binance.exceptions.BinanceAPIException as e:
    print(f"margini değiştirmeye gerek yoktu {e.message}")
    substring = 'Timestamp for this request was 1000ms ahead of the server'
    if substring in e.message:
       os.system('w32tm/resync')
last_transaction_date=""

while True:
    if datetime.now().minute % 3 == 0 and last_transaction_date != datetime.now().strftime("%m/%d/%Y, %H:%M"):
        last_transaction_date=datetime.now().strftime("%m/%d/%Y, %H:%M")
        try:
            amount = float(client.futures_account()['totalMarginBalance']) - 1
        except binance.exceptions.BinanceAPIException as e:
            print(f"miktarı girerken problem oldu {e.message}")
            substring = 'Timestamp for this request was 1000ms ahead of the server'
            if substring in e.message:
                os.system('w32tm/resync')
        data = get_data(symbol)
        signalPmax = generateSignalPmax(data)
        close = float(data.Close[-1:][data.Close[-1:].index[0]])
        vwma = float(calculate_vwma(data.High,data.Low,data.Close,data.Volume)[calculate_vwma(data.High,data.Low,data.Close,data.Volume).index[0]])
        iftr = float(calculate_iftransformrsi(data.Close)[calculate_iftransformrsi(data.Close).index[0]])
        ma = float(calculate_ma(data.Close)[calculate_ma(data.Close).index[0]])
        last_pmax=generatePMax(generatevar(data, moving_average_length=11),data.Close,data.High,data.Low,10, 1.4)[-1]
        calculate_amount_arr = calculate_amount(amount,leverage,symbol)
        precise_order_amount = calculate_amount_arr[0]
        quantityUsdt = calculate_amount_arr[1]
        price_precision = calculate_amount_arr[2]
        inverse=Inverse(data.Close)
        last_posit=last_position(symbol)
        decide_run(signalPmax,close,vwma,iftr,ma,precise_order_amount, quantityUsdt,symbol,inverse,last_posit)

    else:
        continue
