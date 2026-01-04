import time
import hmac
import hashlib
import base64
import json
import numpy as np
import pandas as pd
from dotenv import load_dotenv
import os
import requests
import multiprocessing


#load từ file .env
load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
BASE_URL = os.getenv("BASE_URL")
MARGIN_USDT = os.getenv("MARGIN_USDT")
INTERVAL = os.getenv("INTERVAL")
CHECK_INTERVAL = os.getenv("CHECK_INTERVAL")    #5 phut
LOGFILE = os.getenv("LOGFILE")
API_PASS = os.getenv("API_PASS")
PRODUCT_TYPE = "USDT-FUTURES"       # Hien tai chi test cho tai khoan future thôi



# Your API key and secret key (though not required for this public endpoint, included for completeness)
API_KEY = API_KEY
SECRET_KEY = API_SECRET



# Function to generate signature
def generate_signature(method, endpoint, query_string, body, timestamp):
    if query_string:
        message = timestamp + method.upper() + endpoint + '?' + query_string + body
    else:
        message = str(timestamp) + method.upper() + endpoint + body
    signature = hmac.new(SECRET_KEY.encode('utf-8'), message.encode('utf-8'), digestmod=hashlib.sha256).digest()
    return base64.b64encode(signature).decode('utf-8')

# # Hàm gọi API
# def make_request1(method, path, urlpa, payload):
#     url = "%s%s?%s&signature=%s" % (BASE_URL, path, urlpa, generate_signature(API_SECRET, urlpa))
#     # print(url)
#     headers = {
#         'X-BX-APIKEY': API_KEY,
#     }
#     response = requests.request(method, url, headers=headers, data=payload)
#     return response.text

def parseParam(paramsMap):
    sortedKeys = sorted(paramsMap)
    paramsStr = "&".join(["%s=%s" % (x, paramsMap[x]) for x in sortedKeys])
    if paramsStr != "": 
        return paramsStr+"&timestamp="+str(int(time.time() * 1000))
    else:
        return paramsStr+"timestamp="+str(int(time.time() * 1000))

def make_request(url, method, endpoint, timestamp, payload):
    
    query_string = f"productType={PRODUCT_TYPE}&symbol=TRXUSDT"
    
    body = payload
    
    if method == "GET":
        body = ""
        
    if method == "POST":
        query_string = ""
        
    sign = generate_signature(method, endpoint, query_string, body, timestamp)
    
    headers = {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": timestamp,
        "Content-Type": "application/json",
        "ACCESS-PASSPHRASE": API_PASS
    }
    
    full_url = url + (f"?{query_string}" if query_string else "")
    # print("full_url:", full_url)
    # print("payload:", payload)
    response = requests.request(method, full_url, headers=headers, data=payload)
    return response.text

    # sign = generate_signature(method, endpoint, query_string, body, timestamp)
    
    # headers = {
    #     "ACCESS-KEY": API_KEY,
    #     "ACCESS-SIGN": sign,
    #     "ACCESS-TIMESTAMP": timestamp,
    #     "Content-Type": "application/json",
    #     "ACCESS-PASSPHRASE": API_PASS
    # }
    
    # response = requests.post(url, headers=headers, data=body)
    # data = response.json()


# Function to get spot account assets
def get_futures_account_assets():
    method = "GET"
    payload = {}
    endpoint = "/api/v2/mix/account/accounts"
    url = BASE_URL + endpoint
    # print("url:" ,url)
    
    timestamp = str(int(time.time() * 1000))
    
    response = make_request(url, method, endpoint, timestamp, payload)
    
    data = json.loads(response)
    # print(data)
    # if data:
    if data['code'] == '00000':
        return data['data']  # List of assets
    else:
        print("API Error:", data['msg'])
    # else:
    #     print("HTTP Error:", response.status_code, response.text)
    return None

def get_all_position():
    method = "GET"
    payload = {}
    endpoint = "/api/v2/mix/position/all-position"
    url = BASE_URL + endpoint
    # print("url:" ,url)
    timestamp = str(int(time.time() * 1000))
    
    response = make_request(url, method, endpoint, timestamp, payload)
    data = json.loads(response)
    # print(data)
    
    if data['code'] == '00000':
        return data['data']  # List of assets
    else:
        print("API Error:", data['msg'])
    # else:
    #     print("HTTP Error:", response.status_code, response.text)
    return None

# Function to check if there are open futures positions and get info or place order
def check_open_futures_positions():
    positions = get_all_position()
    if positions and len(positions) > 0:
        position_infos = []
        for pos in positions:
            # Calculate unrealizedPL_rate as (unrealizedPL / marginSize) * 100 if marginSize > 0
            margin_size = float(pos.get('marginSize', 0))
            unrealized_pl = float(pos.get('unrealizedPL', 0))
            unrealized_pl_rate = (unrealized_pl / margin_size * 100) if margin_size > 0 else 0
            
            info = {
                "symbol": pos.get('symbol'),
                "holdSide": pos.get('holdSide'),
                "marginSize": pos.get('marginSize'),
                "leverage": pos.get('leverage'),
                "openPriceAvg": pos.get('openPriceAvg'),
                "unrealizedPL": pos.get('unrealizedPL'),
                "unrealizedPL_rate": unrealized_pl_rate,
                "takeProfit": pos.get('takeProfit'),
                "stopLoss": pos.get('stopLoss'),
                "takeProfitId": pos.get('takeProfitId'),
                "stopLossId": pos.get('stopLossId')
            }
            position_infos.append(info)
        return position_infos  # Return list of dicts with position info
    else:
        print("No open positions found. Considering placing a new order...")
        # Example: Place a sample order (customize as needed)
        # order_result = place_futures_order(
        #     symbol="BTCUSDT_UMCBL",  # Example symbol for USDT perpetual
        #     margin_coin="USDT",
        #     side="open_long",  # Or "open_short", etc.
        #     order_type="market",  # "limit" or "market"
        #     size="0.001",  # Quantity in base coin
        #     price=None  # For limit orders
        # )
        return None  # Return the order result or None

def get_cross_balance():
    method = "GET"
    payload = {}
    endpoint = "/api/v2/mix/account/accounts"
    url = BASE_URL + endpoint
    
    timestamp = str(int(time.time() * 1000))
    
    response = make_request(url, method, endpoint, timestamp, payload)
    data = json.loads(response)
    # print(data)
    # return None
    while data['code'] != "00000":
        timestamp = str(int(time.time() * 1000))
        response = make_request(url, method, endpoint, timestamp, payload)
        data = json.loads(response)
        print(f"Lỗi khi get balance. Đang reconnect mỗi 10s. Please wait......")
        time.sleep(10)
        
    for x in data['data']:
        if x['marginCoin'] == 'USDT':
            balance = float(x['crossedMaxAvailable'])
            break
    
    return float(balance)

    
# Hàm lấy dữ liệu nến từ Bitget API
def get_klines_data(symbol='BTCUSDT', interval='1H', limit=200):
    # method = "GET"
    # payload = {}
    endpoint = '/api/v2/mix/market/candles'
    params = {
        'symbol': symbol,
        'granularity': interval,
        'limit': limit,
        'productType': PRODUCT_TYPE
    }
    response = requests.get(BASE_URL + endpoint, params=params)
    data = response.json()
    # print(data)
    if data['code'] != '00000':
        raise Exception(f"Lỗi lấy dữ liệu nến: {data['msg']}")
    df = pd.DataFrame(data['data'])
    df['timestamp_ms'] = pd.to_numeric(df[0])
    df['open'] = df[1].astype(float)
    df['high'] = df[2].astype(float)
    df['low'] = df[3].astype(float)
    df['close'] = df[4].astype(float)
    df['volume'] = df[6].astype(float)
    df['timestamp'] = pd.to_datetime(df['timestamp_ms'], unit='ms')
    df = df.drop(columns=['timestamp_ms'])
    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]


def get_order_detail():
    method = "GET"
    payload = {}
    endpoint = "/api/v2/mix/order/detail"
    url = BASE_URL + endpoint
    
    timestamp = str(int(time.time() * 1000))
    
    response = make_request(url, method, endpoint, timestamp, payload)
    data = json.loads(response)
    # print(data)
    # return None
    while data['code'] != "00000":
        timestamp = str(int(time.time() * 1000))
        response = make_request(url, method, endpoint, timestamp, payload)
        data = json.loads(response)
        print(f"Lỗi khi get balance. Đang reconnect mỗi 10s. Please wait......")
        time.sleep(10)
        
    for x in data['data']:
        if x['marginCoin'] == 'USDT':
            balance = float(x['available'])
            break
    
    return float(balance)  
    
def cancel_order(symbol):
    endpoint = '/api/v2/mix/order/cancel-order'
    method = "POST"
    payload = {}
    url = BASE_URL + endpoint
    timestamp = str(int(time.time() * 1000))
    payload = {
        "symbol": symbol,
        'productType': PRODUCT_TYPE
    }
    payload = json.dumps(payload)
    return make_request(url, method, endpoint, timestamp, payload)   

def close_position(symbol):
    endpoint = '/api/v2/mix/order/close-positions'
    method = "POST"
    payload = {}
    url = BASE_URL + endpoint
    timestamp = str(int(time.time() * 1000))
    payload = {
        "symbol": symbol,
        'productType': PRODUCT_TYPE
    }
    payload = json.dumps(payload)
    return make_request(url, method, endpoint, timestamp, payload)   
    
    
def place_future_order(symbol, amount, side, orderType, tradeSide, takeProfit, stopLoss):
    method = "POST"
    endpoint = "/api/v2/mix/order/place-order"
    payload = {}
    url = BASE_URL + endpoint
    
    timestamp = str(int(time.time() * 1000))
    
    payload = {
        "symbol": symbol,
        'productType': PRODUCT_TYPE,
        "marginMode": "crossed",
        "marginCoin": "USDT",
        "size": amount,
        "side": side,
        "orderType": orderType,
        "tradeSide": tradeSide,
        "presetStopSurplusPrice": takeProfit,
        "presetStopLossPrice": stopLoss
        
    }
    
    payload = json.dumps(payload)
    
    response = json.loads(make_request(url, method, endpoint, timestamp, payload))
    
    if response['code'] != "00000":
        return response['code'], response['msg']
    
    data = response["data"]
    if data:
        clientOid = data['clientOid']
        orderId = data['orderId']
        return clientOid, orderId
    else:
        return None, None    


def change_leverage(symbol, leverage, holdSide):
    method = "POST"
    endpoint = "/api/v2/mix/account/set-leverage"
    payload = {}
    url = BASE_URL + endpoint
    
    timestamp = str(int(time.time() * 1000))
    
    payload = {
        "symbol": symbol,
        'productType': PRODUCT_TYPE,
        "marginCoin": "USDT",
        "leverage": leverage,
        "holdSide": holdSide
        
    }
    
    payload = json.dumps(payload)
    return make_request(url, method, endpoint, timestamp, payload)
    
    
def modify_tpsl_order(symbol, order_id, trigger_price, trigger_type="market_price", amount=0):
    method = "POST"
    endpoint = "/api/v2/mix/order/modify-tpsl-order"
    payload = {}
    url = BASE_URL + endpoint
    
    timestamp = str(int(time.time() * 1000))
    
    payload = {
        "symbol": symbol,
        "marginCoin": "USDT",
        "orderId": order_id,
        "triggerPrice": str(trigger_price),
        "triggerType": trigger_type,
        "productType": PRODUCT_TYPE,
        "size": float(amount)
        
    }
    
    payload = json.dumps(payload)
    print("payload:", payload)
    response = json.loads(make_request(url, method, endpoint, timestamp, payload))
    print(response)
    if response['code'] == '00000':
        return response['data']  # Order ID, etc.
    
    return response


def get_ticker(symbol='BNBUSDT'):
    # method = "GET"
    # payload = {}
    endpoint = '/api/v2/mix/market/ticker'
    params = {
        'symbol': symbol,
        'productType': PRODUCT_TYPE
    }
    response = requests.get(BASE_URL + endpoint, params=params)
    data = response.json()
    # print(data)
    if data['code'] != '00000':
        raise Exception(f"Lỗi lấy dữ liệu nến: {data['msg']}")
     
    data = response.json()
    # print(data)
    result = data['data']
    for x in data['data']:
        curPrice = float(x['lastPr'])
    
    return curPrice

def get_account_info():
    method = "GET"
    payload = {}
    endpoint = "/api/v2/spot/account/info"
    url = BASE_URL + endpoint
    
    timestamp = str(int(time.time() * 1000))
    
    response = make_request(url, method, endpoint, timestamp, payload)
    data = json.loads(response)
    print(data)


def get_copy_trader_list():
    method = "GET"
    payload = {}
    endpoint = "/api/v2/copy/mix-follower/query-traders"
    url = BASE_URL + endpoint
    
    timestamp = str(int(time.time() * 1000))
    
    response = make_request(url, method, endpoint, timestamp, payload)
    data = json.loads(response)
    
    # endpoint = '/api/v2/copy/mix-follower/query-current-orders'
    # params = {
    #     'symbol': 'ETHUSDT',
    #     'productType': PRODUCT_TYPE
    # }
    # response = requests.get(BASE_URL + endpoint, params=params)
    # data = response.json()
    print(data)
    

# Hàm tinh toan lai giá căn cu tren pnl hien tai va pnl_target
def cal_price_pnl(current_price, target_pnl, positionSide, lev):
    # print(f"DEBUG: current_price={current_price} ({type(current_price)})")
    # print(f"DEBUG: target_pnl={target_pnl} ({type(target_pnl)})")
    # print(f"DEBUG: lev={lev} ({type(lev)})")
    
    current_price = float(current_price)
    target_pnl = float(target_pnl)
    lev = float(lev)
    target_price = 0.0
    if positionSide == "LONG":
        target_price = float(current_price * (1 + target_pnl / lev)) 
    else:
        target_price = float(current_price * (1 - target_pnl / lev)) 
        
    return float(target_price)

def cal_tp_sl(price, pnl_tp, pnl_sl, side, multi):
    tp = 0.0
    sl = 0.0
    if side == 'long':
        sl = round(float(price * (1 - pnl_sl)), multi) 
        tp = round(float(price * (1 + pnl_tp)), multi) 
    else:
        sl = round(float(price * (1 + pnl_sl)), multi) 
        tp = round(float(price * (1 - pnl_tp)), multi)     
        
    return tp, sl   


# Ham process chinh
def symbol_process(position_info, timeframe=INTERVAL, limit=100, lookback=24):
    first_time = True
    
    current_time = pd.Timestamp.now()
    symbol = position_info['symbol']
    amount = position_info['marginSize']
    lev = position_info['leverage']
    pnl = float(position_info['unrealizedPL_rate'])             
    side = position_info['holdSide']  
    entry_price = float(position_info['openPriceAvg'])  
    stopPrice = float(position_info['stopLoss'])  
    stopLossId = position_info['stopLossId']
    
    
    last_milestone_achieved = 0
    if pnl > 50:          #loi nhuan tren 50%
        print(f"Lợi nhuận > {pnl:.2f} % nên sẽ update lại stop-loss")
        
        # order_id, quantity, stopPrice, side, positionSide, type = get_order_stoploss_data(symbol=symbol)
        update_sl = True
        # print(f"order_id: {order_id}, quantity: {quantity}, stopPrice: {stopPrice}, side: {side}, positionSide: {positionSide}, type: {type}")
        pnl_milestones = int(pnl /50)*50    # = [100, 150, 200, 250, 300]
        if pnl >= 100 and pnl_milestones > last_milestone_achieved and pnl_milestones in [100, 150, 200, 250, 300, 350, 400]:
            target_pnl = float((pnl - 50)/100)
            last_milestone_achieved = pnl_milestones
        else:
            target_pnl = float((pnl / 2) / 100)
        print(f"target_pnl: {target_pnl:.2f}")    
        # print(f"side: {side}")    
        if side == "long":
            new_stop_loss = cal_price_pnl(entry_price, target_pnl, side, lev) 
            print(f"Vị thế {side}: Stop-loss mới {new_stop_loss:.5f}.")
            if new_stop_loss <= stopPrice:
                update_sl = False
            # print(f"{side} New stop-loss {new_stop_loss:.5f}")
        else:
            new_stop_loss = cal_price_pnl(entry_price, target_pnl, side, lev) 
            print(f"Vị thế {side}: Stop-loss mới {new_stop_loss:.5f}.")
            if new_stop_loss >= stopPrice:
                update_sl = False
            # print(f"{side} New stop-loss {new_stop_loss:.5f}")
        # print(f"Pnl đang là {pnl} % nên điều chỉnh stop-loss {stopPrice:.5f} thành {new_stop_loss:.5f}")
        
        print(f"Update stop-loss flag: {update_sl} ")
        if update_sl:
            modify_tpsl_order(symbol=symbol, order_id=stopLossId, trigger_price=new_stop_loss, trigger_type="market_price", amount=0)
            print(f"Điều chỉnh stop-loss mới {new_stop_loss:.5f} thành công.")
        else:
            print(f"Không Xóa stop-loss cũ {stopPrice:.5f}.")
    else:
        print(f"Lợi nhuận {pnl:.2f} % nên không update lại stop-loss")  
                
            
               
            
        

# chay tien trinh cho tung position 
def run_symbol_process(position_info):
    symbol = position_info['symbol'] 
    amount = position_info['marginSize']
    lev = position_info['leverage']
    # pnl = position_info['unrealizedPL_rate']
    print(f"Starting process for {symbol} with amount={amount}, leverage={lev} ...")
    symbol_process(position_info)    
    
# Hàm chính
def main():
    
    # print(f"Get list coins success.")
    print(f"------------Program start--------------------")
    
    cross_balance = get_cross_balance()  # Change product_type as needed
    print(f"Số dư USDT khả dụng: {cross_balance:.2f} USDT")
    symbol = 'OPENUSDT'
    # Kiem tra 
    # while True:
    #     try:
    #         print("--------------Kiểm tra có vị thế đang mở không?----------------")
    #         positions = check_open_futures_positions()
    #         if positions:
    #             print("Các vị thế đang mở:")
    #             for pos in positions:
    #                 print("Symbol: ", pos["symbol"], " -Hold side: ", pos["holdSide"], " -Pnl Rate: ", pos["unrealizedPL_rate"], "-Amount: ", pos["marginSize"])
    #                 print("Thực hiện tiến trình kiểm tra pnl rate để update lại stop loss.")
    #                 symbol_process(pos, timeframe=INTERVAL, limit=100, lookback=24)
                    
                
    #             # tam thoi chua can chay process
    #             # processes = []
            
    #             # for item in positions:
    #             #     process = multiprocessing.Process(
    #             #         target=run_symbol_process,
    #             #         args=(item)
    #             #     )
    #             #     processes.append(process)
    #             #     process.start()
                
    #             # # Doi tất cả tiến trình hoàn thành. 
    #             # for process in processes:
    #             #     process.join()    
                    
    #         else:
    #             print("Chưa có vị thế nào đang mở")
    #             print("Kiểm tra, xác nhận giao dịch")        
    
    #         print("*********Sẽ kiểm tra lại sau 5 phút************") 
    #         time.sleep(5*60)    # 5 phut
            
    
    #     except Exception as e:
    #         print(f"Lỗi: {e}")
    #         time.sleep(5*60)
        
    #     except KeyboardInterrupt:
    #         print("Dừng chương trình.")
    #         balance = get_cross_balance()
    #         print(f"Số dư USDT cuối cùng: {balance:.2f} USDT")
    # print("Close position")
    # close_position(symbol='OPENUSDT')
    # get_account_info()
    # get_copy_trader_list()
    # current_price = get_ticker(symbol)
    # leverage=15
    print("set leverage")
    change_leverage(symbol='BGBUSDT', leverage=5, holdSide='long')
    # pnl_sl = float(1 / leverage) 
    # pnl_tp = float(2 / leverage) 
    # marginAmount = round(float(0.5 * leverage /current_price), 3)
    # tp, sl = cal_tp_sl(current_price, pnl_tp, pnl_sl, 'long', 3)
    # print("Đặt lệnh")
    # clientOid, orderId = place_future_order(symbol=symbol, amount=marginAmount, side='buy', orderType='market', tradeSide='open', takeProfit=tp, stopLoss=sl)
    # print("clientOid:", clientOid, "  orderId: ", orderId) 
    
    # print("Set lai sl")
    # modify_tpsl_order(symbol='OPENUSDT', order_id=orderId, trigger_price=0.45, trigger_type="mark_price", amount=0)
    

    print(f"--------------END PROGRAM----------------------")

if __name__ == "__main__":
    main()
    
    
    