import os
import time
import hmac
import hashlib
import base64
import json
import requests
import pandas as pd
from dotenv import load_dotenv
# from bitget.v2.mix import MixApi
# from bitget.v2.mix_enums import MarginMode, OrderSide, ProductType

import config

# Tải biến môi trường từ file .env
load_dotenv()

# Khởi tạo API
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
BASE_URL = os.getenv("BASE_URL")
MARGIN_USDT = os.getenv("MARGIN_USDT")
INTERVAL = os.getenv("INTERVAL")
CHECK_INTERVAL = os.getenv("CHECK_INTERVAL")    #5 phut
LOGFILE = os.getenv("LOGFILE")
API_PASS = os.getenv("API_PASS")
PRODUCT_TYPE = "usdt-futures"       # Hien tai chi test cho tai khoan future thôi

# Your API key and secret key (though not required for this public endpoint, included for completeness)
API_KEY = API_KEY
SECRET_KEY = API_SECRET



# Function to generate signature
def generate_signature(method, endpoint, query_string, body, timestamp):
    if query_string:
        message = timestamp + method.upper() + endpoint + '?' + query_string + body
    else:
        message = str(timestamp) + method.upper() + endpoint + body
    # print("message:",message)    
    signature = hmac.new(SECRET_KEY.encode('utf-8'), message.encode('utf-8'), digestmod=hashlib.sha256).digest()
    return base64.b64encode(signature).decode('utf-8')

def parseParam(paramsMap):
    sortedKeys = sorted(paramsMap)
    paramsStr = "&".join(["%s=%s" % (x, paramsMap[x]) for x in sortedKeys])
    if paramsStr != "": 
        return paramsStr    #+"&timestamp="+str(int(time.time() * 1000))
    else:
        return "" #paramsStr+"timestamp="+str(int(time.time() * 1000))


def make_request(url, method, endpoint, timestamp, payload):
    
    # parse_params_to_str(payload)
    # query_string = endpoint + payload #f"productType={PRODUCT_TYPE}"
    query_string = ""
    # print("query_string:",query_string)
    body = payload
    
    if method == "GET":
        body = ""
        if payload:
            query_string = f"{parseParam(payload)}&productType={PRODUCT_TYPE}"
        else:
            query_string = f"productType={PRODUCT_TYPE}"
        # print("query_string:",query_string)
        
            
    if method == "POST":
        query_string = ""
        
    sign = generate_signature(method, endpoint, query_string, body, timestamp)
    # print("sign:",sign)
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

# Hàm lấy dữ liệu nến từ Bitget API
def get_klines_data(symbol='BTCUSDT', interval='1H', limit=200):
    """Lấy dữ liệu nến và chuyển thành DataFrame của Pandas."""
    try:
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
        # print(df)
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    
    except Exception as e:
        print(f"Lỗi khi lấy dữ liệu nến {interval}: {e}")
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
    
    
def place_future_order(symbol, amount, side, orderType, tradeSide):
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
        "tradeSide": tradeSide
        # "presetStopSurplusPrice": takeProfit,
        # "presetStopLossPrice": stopLoss
        
    }
    
    payload = json.dumps(payload)
    
    response = json.loads(make_request(url, method, endpoint, timestamp, payload))
    
    if response['code'] != "00000":
        return None, response['msg']
    
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
    print(f"Set leverage {symbol}  leverage=x{leverage} for side={holdSide}.")
    payload = {
        "symbol": symbol,
        'productType': PRODUCT_TYPE,
        "marginCoin": "USDT",
        "leverage": leverage,
        "holdSide": holdSide
        
    }
    
    payload = json.dumps(payload)
    return make_request(url, method, endpoint, timestamp, payload)
    
    
def modify_tpsl_order(symbol, order_id, trigger_price, trigger_type="mark_price", amount=0 ):
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
        "size": amount
        
    }
    
    payload = json.dumps(payload)
    response = json.loads(make_request(url, method, endpoint, timestamp, payload))
    # print(response)
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
    
#Modify Trigger Order 
def modify_plan_order(orderId, clientOid, symbol, tp_price, sl_price, trigger_type="mark_price"):
    method = "POST"
    endpoint = "/api/v2/mix/order/modify-plan-order"
    payload = {}
    url = BASE_URL + endpoint
    
    timestamp = str(int(time.time() * 1000))
    
    payload = {
        "orderId": orderId,
        "symbol": symbol,
        "productType": PRODUCT_TYPE,
        "planType":"normal_plan",
        "newStopSurplusTriggerPrice": str(tp_price),
        "newStopSurplusTriggerType": trigger_type,
        "newStopLossTriggerPrice": str(sl_price),
        "newStopLossTriggerType": trigger_type
        
    }
    
    payload = json.dumps(payload)
    response = json.loads(make_request(url, method, endpoint, timestamp, payload))
    print(response)
    if response['code'] == '00000':
        return response['data']  # Order ID, etc.
    
    return response    

#Place a stop-profit and stop-loss plan order
def place_tpsl_order(symbol, planType, amount, holdSide, triggerPrice):
    method = "POST"
    endpoint = "/api/v2/mix/order/place-tpsl-order"
    payload = {}
    url = BASE_URL + endpoint
    
    timestamp = str(int(time.time() * 1000))
    
    payload = {
        "symbol": symbol,
        "marginCoin": "USDT",
        "productType": PRODUCT_TYPE,
        "planType": planType,
        "size": amount,
        "holdSide": holdSide,
        "triggerType": "mark_price",
        "triggerPrice": triggerPrice 
        
    }
    # planType: Take profit and stop loss type
        # profit_plan: take profit plan;
        # loss_plan: stop loss plan;
        # moving_plan: trailing stop;
        # pos_profit: position take profit;
        # pos_loss: position stop loss
    payload = json.dumps(payload)
    response = json.loads(make_request(url, method, endpoint, timestamp, payload))
    print(response)
    if response['code'] == '00000':
        return response['data']  # Order ID, etc.
    
    return response
