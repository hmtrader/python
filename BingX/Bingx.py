import pandas as pd
import numpy as np
import time
from ta.momentum import RSIIndicator
from ta.trend import MACD
import requests
import hmac
import hashlib
import json
from dotenv import load_dotenv
import os
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



# load symbol from env
def load_symbol_from_env():
    symbol_str = os.getenv('SYMBOLS', '')
    symbol_list = []
    for item in symbol_str.split(','):
        parts = item.strip().split(':')
        if len(parts) == 3:
            symbol = parts[0]
            amount = float(parts[1])
            leverage = float(parts[2])
            symbol_list.append({'symbol': symbol, 'amount': amount, 'leverage': leverage})
        else:
            print(f"Invalid format for {item}. Skipping.")
    return symbol_list        
    
# Tham so co dinh
# SYMBOL = os.getenv("SYMBOL")
# LEVERAGE = os.getenv("LEVERAGE")
# POSITION_AMT = os.getenv("POSITION_AMT")    # so luong usdt


def generate_signature(api_secret, payload):
    signature = hmac.new(api_secret.encode("utf-8"), payload.encode("utf-8"), digestmod=hashlib.sha256).hexdigest()
    # print("sign=" + signature)
    return signature

# Hàm gọi API
def make_request(method, path, urlpa, payload):
    url = "%s%s?%s&signature=%s" % (BASE_URL, path, urlpa, generate_signature(API_SECRET, urlpa))
    # print(url)
    headers = {
        'X-BX-APIKEY': API_KEY,
    }
    response = requests.request(method, url, headers=headers, data=payload)
    return response.text

def parseParam(paramsMap):
    sortedKeys = sorted(paramsMap)
    paramsStr = "&".join(["%s=%s" % (x, paramsMap[x]) for x in sortedKeys])
    if paramsStr != "": 
        return paramsStr+"&timestamp="+str(int(time.time() * 1000))
    else:
        return paramsStr+"timestamp="+str(int(time.time() * 1000))


# Hàm lấy dữ liệu nến từ BingX API
def get_klines_data(symbol='BTC-USDT', interval='30m', limit=1000):
    endpoint = '/openApi/swap/v2/quote/klines'
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': limit,
        'timestamp': int(time.time() * 1000)
    }
    response = requests.get(BASE_URL + endpoint, params=params)
    data = response.json()
    if data['code'] != 0:
        raise Exception(f"Lỗi lấy dữ liệu nến: {data['msg']}")
    df = pd.DataFrame(data['data'])
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

def get_balance():
    payload = {}
    endpoint = '/openApi/swap/v3/user/balance'
    method = "GET"
    params = {}
    paramsStr = parseParam(params)
    response = make_request(method, endpoint, paramsStr, payload)
    data = json.loads(response)
    # print(data)
    while data['code'] != 0:
        payload = {}
        endpoint = '/openApi/swap/v3/user/balance'
        method = "GET"
        params = {}
        paramsStr = parseParam(params)
        response = make_request(method, endpoint, paramsStr, payload)
        data = json.loads(response)
        print(f"Lỗi khi get balance. Đang reconnect mỗi 10s. Please wait......")
        time.sleep(10)
        
    for x in data['data']:
        if x['asset'] == 'USDT':
            balance = float(x['balance'])
            break
    
    return float(balance)


# Lấy giá thị trường
def get_market_price(symbol, current_time):
    payload = {}
    path = '/openApi/swap/v1/ticker/price'
    method = "GET" 
    paramsMap = {
        "symbol": symbol,
        "timestamp": current_time
    }
    paramsStr = parseParam(paramsMap)
    return make_request(method, path, paramsStr, payload) 

# Ham trả về giá trị symbol tại thời điểm
def get_current_price(symbol, current_time):
    datas = json.loads(get_market_price(symbol, current_time))
    data = datas.get("data", [])    
    return float(data['price'])

# Hàm đặt lệnh thật trên BingX
def place_order(symbol, side, quantity, stop_loss, take_profit):
    payload = {}
    path = '/openApi/swap/v2/trade/order'
    method = "POST"
    
    paramsMap = {
        "symbol": symbol,
        "side": side,
        "positionSide": "LONG" if side == 'BUY' else "SHORT",
        "type": "MARKET",
        "quantity": quantity,
        "takeProfit": f"""{{
            "type": "TAKE_PROFIT_MARKET",
            "stopPrice": {take_profit},
            "price": {take_profit},
            "workingType": "MARK_PRICE"
        }}""",
        "stopLoss": f"""{{
            "type": "STOP_MARKET",
            "stopPrice": {stop_loss},
            "price": {stop_loss},
            "workingType": "MARK_PRICE"
        }}"""
    }
    # print("place_order response: {paramsStr}")
    paramsStr = parseParam(paramsMap)
    response = json.loads(make_request(method, path, paramsStr, payload)) 
    # write_log(f"place_order response: {response}")    
    data = response.get('data', [])
    # write_log(f"place_order data: {data}")
    return data['order']['orderId']

def replace_order(symbol, side, positionSide, type, quantity, stop_loss):
    payload = {}
    path = '/openApi/swap/v2/trade/order'
    method = "POST"
    timestamp = int(time.time() * 1000)
    paramsMap = {
        "symbol": symbol,
        "side": side,
        "positionSide": positionSide,
        "type": type, # "STOP_MARKET",
        "quantity": quantity,
        "stopPrice": stop_loss,
        "price": stop_loss,  # Giá kích hoạt, có thể là 0 hoặc = stopPrice
        "workingType": "MARK_PRICE",
        "timestamp": str(timestamp)
    }
    paramsStr = parseParam(paramsMap)
    return make_request(method, path, paramsStr, payload)

def cancel_order(symbol, orderID):
    payload = {}
    path = '/openApi/swap/v2/trade/order'
    method = "DELETE"
    timestamp = int(time.time() * 1000)
    paramsMap = {
        "orderId": orderID,
        "symbol": symbol,
        "timestamp": str(timestamp)
    }
    paramsStr = parseParam(paramsMap)
    return make_request(method, path, paramsStr, payload)

# Hàm đóng lệnh thật trên BingX
def close_order(symbol, order_id, side, quantity):
    payload = {}
    path = '/openApi/swap/v2/trade/close'
    method = "POST" 
    paramsMap = {
        'symbol': symbol,
        'orderId': order_id,
        'side': 'SELL' if side == 'buy' else 'BUY',
        'type': 'MARKET',
        'quantity': quantity,
        'timestamp': int(time.time() * 1000)
    }
    paramsStr = parseParam(paramsMap)
    response = json.loads(make_request(method, path, paramsStr, payload)) 
    data = response.get('data', [])
    if data['code'] != 0:
        raise Exception(f"Lỗi đóng lệnh: {data['msg']}")
    return data

def get_position(symbol):
    payload = {}
    path = '/openApi/swap/v2/user/positions'
    method = "GET"
    timestamp = int(time.time() * 1000)
    paramsMap = {
        "symbol": symbol,
        'timestamp': str(timestamp)
    }
    paramsStr = parseParam(paramsMap)
    response = json.loads(make_request(method, path, paramsStr, payload))
    while response['code'] != 0:
        payload = {}
        path = '/openApi/swap/v2/user/positions'
        method = "GET"
        timestamp = int(time.time() * 1000)
        paramsMap = {
            "symbol": symbol,
            'timestamp': str(timestamp)
        }
        paramsStr = parseParam(paramsMap)
        response = json.loads(make_request(method, path, paramsStr, payload))
        # data = response.get('data', [])
        print(f"Lỗi khi get position id. Đang reconnect mỗi 10s. Please wait......")
        time.sleep(10)
   
    data = response.get("data",[])
    # print(data)
    if data:
        item = data[0]
        posId = item.get('positionId')
        positionSide = item.get('positionSide')
        avgPrice = item.get('avgPrice')
        pnl = float(item.get('pnlRatio'))
        return posId, positionSide, avgPrice, pnl
    else:
        return None, None, None, None


# Close position
def close_position(pos_id):
    payload = {}
    path = '/openApi/swap/v1/trade/closePosition'
    method = "POST"
    paramsMap = {
        "timestamp": int(time.time() * 1000),
        "positionId": pos_id
    }
    paramsStr = parseParam(paramsMap)
    response = json.loads(make_request(method, path, paramsStr, payload))
    if response['code'] != 0:
        raise Exception(f"Lỗi đóng position: {response['msg']}")
    return True
    
#Thiet lap don bay
def set_leverage(symbol, leverage, side):
    payload = {}
    path = '/openApi/swap/v2/trade/leverage'
    method = 'POST'
    paramsMap = {
        "leverage": leverage,
        "side": side,
        "symbol": symbol
    }
    paramsStr = parseParam(paramsMap) 
    return make_request(method, path, paramsStr, payload)     

# Hàm ghi log vào file
def write_log(message, filename=LOGFILE):
    timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}\n"
    print(log_entry.strip())
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(log_entry)

# Hàm phân tích xu hướng thị trường
def analyze_trend(df, rsi_period=14, atr_period=14, threshold=0.5):
    df['price_change_pct'] = df['close'].pct_change() * 100
    rsi = RSIIndicator(df['close'], window=rsi_period)
    df['rsi'] = rsi.rsi()
    df['tr'] = np.maximum(df['high'] - df['low'], 
                          np.maximum(abs(df['high'] - df['close'].shift()), 
                                     abs(df['low'] - df['close'].shift())))
    df['atr'] = df['tr'].rolling(window=atr_period).mean()
    
    latest_data = df.iloc[-1]
    latest_price_change = df['price_change_pct'].iloc[-1]
    latest_rsi = df['rsi'].iloc[-1]
    latest_atr_pct = (df['atr'].iloc[-1] / df['close'].iloc[-1]) * 100

    if latest_rsi > 70 and latest_price_change > threshold:
        trend = "Bullish (Tăng mạnh)"
    elif latest_rsi < 30 and latest_price_change < -threshold:
        trend = "Bearish (Giảm mạnh)"
    elif abs(latest_price_change) < threshold and latest_atr_pct < 0.5:
        trend = "Sideway (Đi ngang)"
    elif latest_rsi > 50 and latest_price_change > 0:
        trend = "Bullish (Tăng nhẹ)"
    elif latest_rsi < 50 and latest_price_change < 0:
        trend = "Bearish (Giảm nhẹ)"
    else:
        trend = "Sideway (Đi ngang)"

    return {
        'trend': trend,
        'latest_price_change_pct': latest_price_change,
        'latest_rsi': latest_rsi,
        'latest_atr_pct': latest_atr_pct,
        'latest_price': latest_data['close']
    }

def get_orders(symbol):
    payload = {}
    path = '/openApi/swap/v2/trade/openOrders'
    method = "GET"
    timestamp = int(time.time() * 1000)
    paramsMap = {
        "symbol": symbol,
        "timestamp": str(timestamp)
    }
    paramsStr = parseParam(paramsMap)
    return make_request(method, path, paramsStr, payload)

def get_order_stoploss_data(symbol):
    response = json.loads(get_orders(symbol))
    data = response.get('data', [])
    # print(data)
    while response['code'] != 0:
        response = json.loads(get_orders(symbol))
        data = response.get('data', [])
        print(f"Lỗi khi get order id. Đang reconnect mỗi 10s. Please wait......")
        time.sleep(10)
        
    # order_id = None    
    # origQty = None
    for x in data.get('orders', []):
        # print("Type hien tai:", x.get('type' ))  
        if x.get('type') == 'STOP_MARKET':
            order_id = x.get('orderId')
            origQty = float(x.get('origQty'))
            stopPrice = float(x.get('stopPrice'))
            side = x.get('side')
            positionSide = x.get('positionSide')
            type = x.get('type')
            break
    # print("data hien tai", order_id)    
    return order_id, origQty, stopPrice, side, positionSide, type

# Hàm tính Fibonacci Retracement
def calculate_fibonacci_levels(df):
    high = df['high'].max()
    low = df['low'].min()
    diff = high - low
    fib_levels = {
        '0.0%': high,
        '23.6%': high - 0.236 * diff,
        '38.2%': high - 0.382 * diff,
        '50.0%': high - 0.5 * diff,
        '61.8%': high - 0.618 * diff,
        '78.6%': high - 0.786 * diff,
        '100.0%': low
    }
    return fib_levels

# Hàm xác định vùng hỗ trợ/kháng cự dựa trên Volume
def find_support_resistance(df, fib_levels):
    # Tìm vùng có khối lượng cao (High Volume Nodes)
    volume_threshold = df['volume'].quantile(0.75)  # Top 25% khối lượng
    high_volume_zones = df[df['volume'] >= volume_threshold][['high', 'low']]
    
    # Tìm vùng hỗ trợ/kháng cự gần các mức Fibonacci
    support = None
    resistance = None
    for level_name, level_price in fib_levels.items():
        # Vùng hỗ trợ: gần mức Fib 61.8% hoặc 78.6% và có khối lượng cao
        if level_name in ['61.8%', '78.6%']:
            if any(abs(high_volume_zones['low'] - level_price) < level_price * 0.01):  # Trong 1% giá
                support = level_price
        # Vùng kháng cự: gần mức Fib 23.6% hoặc 38.2% và có khối lượng cao
        if level_name in ['23.6%', '38.2%']:
            if any(abs(high_volume_zones['high'] - level_price) < level_price * 0.01):
                resistance = level_price
    
    return support, resistance

# Hàm xác định xu hướng bằng MACD
def determine_trend_macd(df):
    macd = MACD(close=df['close'], window_slow=26, window_fast=12, window_sign=9)
    df['macd'] = macd.macd()
    df['signal'] = macd.macd_signal()
    
    latest_macd = df['macd'].iloc[-1]
    # print("latest_macd: ", latest_macd)
    latest_signal = df['signal'].iloc[-1]
    # print("latest_signal: ", latest_signal)
    
    if latest_macd > latest_signal:
        return "Bullish"
    elif latest_macd < latest_signal:
        return "Bearish"
    else:
        return "Sideway"
    
# Ham xac dinh xu huong bang EMA9 và EMA21
def determine_trend_ema(df, ema_short=9, ema_long=21, lookback=24):
    """
    Xác định xu hướng trong 24 nến cuối: 
    - Uptrend nếu tất cả EMA9 > EMA21 VÀ EMA21 đang hướng lên (EMA21[-1] > EMA21[-2])
    - Downtrend nếu tất cả EMA9 < EMA21 VÀ EMA21 đang hướng xuống (EMA21[-1] < EMA21[-2])
    - Neutral nếu có sự lẫn lộn hoặc không thỏa mãn hướng
    """
    df['EMA9'] = df['close'].ewm(span=ema_short, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=ema_long, adjust=False).mean()
    
    if len(df) < lookback + 1:  # Cần ít nhất lookback + 1 để kiểm tra hướng
        return 'Insufficient data'
    
    recent_df = df.tail(lookback)
    ema9_above = (recent_df['EMA9'] > recent_df['EMA21']).all()
    ema9_below = (recent_df['EMA9'] < recent_df['EMA21']).all()
    ema21_upward = recent_df['EMA21'].iloc[-1] > recent_df['EMA21'].iloc[-2]
    ema21_downward = recent_df['EMA21'].iloc[-1] < recent_df['EMA21'].iloc[-2]
    
    if ema9_above and ema21_upward:
        return 'Up'
    elif ema9_below and ema21_downward:
        return 'Down'
    else:
        return 'Neutral'

# Hàm kiểm tra Bullish Hammer (trong downtrend)
def is_hammer(open_, high, low, close, body_ratio=0.3, shadow_ratio=2):
    """
    Nến Hammer: Thân nhỏ ở trên, bóng dưới dài ít nhất 2x thân, bóng trên nhỏ.
    Ưu tiên bullish (close >= open)
    """
    body = abs(close - open_)
    total_range = high - low
    lower_shadow = min(open_, close) - low
    upper_shadow = high - max(open_, close)
    
    if body > body_ratio * total_range:
        return False
    
    if lower_shadow < shadow_ratio * body:
        return False
    
    if upper_shadow > body:
        return False
    
    return close >= open_

# Hàm kiểm tra Bullish Engulfing (hai nến, trong downtrend)
def is_bullish_engulfing(df, i):
    """
    Bullish Engulfing:
    - Nến 1: Đỏ (Close < Open)
    - Nến 2: Xanh (Close > Open), Open2 < Close1, Close2 > Open1
    """
    if i < 1:
        return False
    open1, close1 = df['Open'].iloc[i-1], df['Close'].iloc[i-1]
    open2, close2 = df['Open'].iloc[i], df['Close'].iloc[i]
    
    if close1 >= open1:  # Nến 1 đỏ
        return False
    if close2 <= open2:  # Nến 2 xanh
        return False
    if open2 >= close1:
        return False
    if close2 <= open1:
        return False
    return True

# Hàm kiểm tra Morning Star (ba nến, trong downtrend)
def is_morning_star(df, i):
    """
    Morning Star:
    - Nến 1: Đỏ dài
    - Nến 2: Thân nhỏ (doji-like), gap xuống
    - Nến 3: Xanh dài, close trên giữa nến 1
    """
    if i < 2:
        return False
    open1, close1 = df['Open'].iloc[i-2], df['Close'].iloc[i-2]
    open2, close2 = df['Open'].iloc[i-1], df['Close'].iloc[i-1]
    open3, close3 = df['Open'].iloc[i], df['Close'].iloc[i]
    
    body1 = abs(open1 - close1)
    body2 = abs(open2 - close2)
    body3 = abs(open3 - close3)
    
    # Nến 1 đỏ dài
    if close1 >= open1 or body1 < 0.5 * (df['High'].iloc[i-2] - df['Low'].iloc[i-2]):
        return False
    
    # Nến 2 thân nhỏ
    if body2 > 0.1 * (df['High'].iloc[i-1] - df['Low'].iloc[i-1]):
        return False
    
    # Gap xuống
    if open2 >= close1:
        return False
    
    # Nến 3 xanh dài, close3 > midpoint1
    midpoint1 = (open1 + close1) / 2
    if close3 <= open3 or body3 < 0.5 * (df['High'].iloc[i] - df['Low'].iloc[i]) or close3 <= midpoint1:
        return False
    
    return True

# Bearish Engulfing (hai nến, trong uptrend)
def is_bearish_engulfing(df, i):
    """
    Bearish Engulfing:
    - Nến 1: Xanh (Close > Open)
    - Nến 2: Đỏ (Close < Open), Open2 > Close1, Close2 < Open1
    """
    if i < 1:
        return False
    open1, close1 = df['Open'].iloc[i-1], df['Close'].iloc[i-1]
    open2, close2 = df['Open'].iloc[i], df['Close'].iloc[i]
    
    if close1 <= open1:  # Nến 1 xanh
        return False
    if close2 >= open2:  # Nến 2 đỏ
        return False
    if open2 <= close1:
        return False
    if close2 >= open1:
        return False
    return True

# Shooting Star (bearish hammer, trong uptrend)
def is_shooting_star(open_, high, low, close, body_ratio=0.3, shadow_ratio=2):
    """
    Shooting Star: Thân nhỏ ở dưới, bóng trên dài ít nhất 2x thân, bóng dưới nhỏ.
    Ưu tiên bearish (close <= open)
    """
    body = abs(close - open_)
    total_range = high - low
    lower_shadow = min(open_, close) - low
    upper_shadow = high - max(open_, close)
    
    if body > body_ratio * total_range:
        return False
    
    if upper_shadow < shadow_ratio * body:
        return False
    
    if lower_shadow > body:
        return False
    
    return close <= open_

# Evening Star (ba nến, trong uptrend)
def is_evening_star(df, i):
    """
    Evening Star:
    - Nến 1: Xanh dài
    - Nến 2: Thân nhỏ (doji-like), gap lên
    - Nến 3: Đỏ dài, close dưới giữa nến 1
    """
    if i < 2:
        return False
    open1, close1 = df['Open'].iloc[i-2], df['Close'].iloc[i-2]
    open2, close2 = df['Open'].iloc[i-1], df['Close'].iloc[i-1]
    open3, close3 = df['Open'].iloc[i], df['Close'].iloc[i]
    
    body1 = abs(open1 - close1)
    body2 = abs(open2 - close2)
    body3 = abs(open3 - close3)
    
    # Nến 1 xanh dài
    if close1 <= open1 or body1 < 0.5 * (df['High'].iloc[i-2] - df['Low'].iloc[i-2]):
        return False
    
    # Nến 2 thân nhỏ
    if body2 > 0.1 * (df['High'].iloc[i-1] - df['Low'].iloc[i-1]):
        return False
    
    # Gap lên
    if open2 <= close1:
        return False
    
    # Nến 3 đỏ dài, close3 < midpoint1
    midpoint1 = (open1 + close1) / 2
    if close3 >= open3 or body3 < 0.5 * (df['High'].iloc[i] - df['Low'].iloc[i]) or close3 >= midpoint1:
        return False
    
    return True

# Hàm chính để tìm các mô hình đảo chiều (sử dụng trend mới)
def find_reversal_patterns(df, lookback=24):
    df = df.copy()
    current_trend = determine_trend_ema(df, lookback=lookback)
    reversals = []
    
    # Chỉ tìm patterns ở 24 nến cuối để phù hợp với trend
    start_idx = max(0, len(df) - lookback)
    for i in range(start_idx, len(df)):
        trend = determine_trend_ema(df.iloc[:i+1], lookback=min(lookback, i+1))  # Trend tại thời điểm i
        
        if trend == 'Down':  # Tìm bullish reversals trong downtrend
            if is_hammer(df['Open'].iloc[i], df['High'].iloc[i], df['Low'].iloc[i], df['Close'].iloc[i]):
                reversals.append((i, 'Hammer (Bullish Reversal)'))
            if is_bullish_engulfing(df, i):
                reversals.append((i, 'Bullish Engulfing'))
            if is_morning_star(df, i):
                reversals.append((i, 'Morning Star'))
        
        elif trend == 'Up':  # Tìm bearish reversals trong uptrend
            if is_shooting_star(df['Open'].iloc[i], df['High'].iloc[i], df['Low'].iloc[i], df['Close'].iloc[i]):
                reversals.append((i, 'Shooting Star (Bearish Reversal)'))
            if is_bearish_engulfing(df, i):
                reversals.append((i, 'Bearish Engulfing'))
            if is_evening_star(df, i):
                reversals.append((i, 'Evening Star'))
    
    return reversals, current_trend  # Trả về patterns và trend hiện tại

# Hàm đưa ra quyết định giao dịch
def trading_decision(support, resistance, trend, current_price, lev):
    # current_price = df['close'].iloc[-1]
    new_support = support
    new_resistance = resistance
    
    
    
    if trend == "Down" and new_support is not None:      
        # Dang xu huong giam nen se xem xet vung ho tro vung khang cu
        if resistance < current_price:
            new_support = resistance       # lay la vung khang cu la vung ho tro moi
                
        print(f"Vùng hỗ trợ mới: {new_support:.5f} ")
        # Tính khoảng cách từ đáy (support) đến giá hiện tại
        pnl_cur_support = (current_price - new_support) / new_support * 100 * lev  
        print(f"Pnl cach vung hỗ trợ mới: {pnl_cur_support:.2f} %")
        if pnl_cur_support > 50:
            return "SHORT"
        else:
            print(f"Đang là xu hướng giảm nhưng giá đang gần vùng hỗ trợ có thể thay đổi xu hướng, nên không vào lệnh.")
            return "WAITING"
    elif trend == "Up" and new_resistance is not None:
        # Dang xu huong giam nen se xem xet vung ho tro vung khang cu
        if support > current_price:
            new_resistance = support       # lay la vung support la vung khang cu moi
            
        print(f"Vùng kháng cự mới: {new_resistance:.5f} ")
        # Tính khoảng cách từ đỉnh (resistance) đến giá hiện tại
        pnl_cur_resistance = abs((current_price - new_resistance) / new_resistance * 100 * lev)  
        print(f"Pnl cach vung kháng cự mới: {pnl_cur_resistance:.2f} %")
        if pnl_cur_resistance > 50:
            return "LONG"
        else:
            print(f"Đang là xu hướng tăng nhưng giá đang gần vùng kháng cự có thể thay đổi xu hướng, nên không vào lệnh.")
            return "WAITING"
    else:
        return "No clear signal (sideways trend)"

# Hàm lưu lịch sử lệnh vào CSV
def save_order_history(order, filename='order_history.csv'):
    order_data = order.to_dict()
    df = pd.DataFrame([order_data])
    try:
        existing_df = pd.read_csv(filename)
        df = pd.concat([existing_df, df], ignore_index=True)
    except FileNotFoundError:
        pass
    df.to_csv(filename, index=False)
    write_log(f"Lưu lịch sử lệnh vào {filename}")

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

def symbol_process(api_key, secret, symbol, position_amt, lev, timeframe=INTERVAL, limit=100, lookback=24):
    first_time = True
    balance = get_balance()
    position_id, positionSide, entry_price, pnl = get_position(symbol=symbol)
    # print("posi id:", position_id)
    if position_id:
        close_position(position_id)
        write_log(f"Đã đóng vị thế {symbol} thành công.\n")
        position_id = None
        
        
    while True:
        try:
            current_time = pd.Timestamp.now()
            df = get_klines_data(symbol=symbol, interval=timeframe, limit=limit)
            # result = analyze_trend(df)
            current_price = get_current_price(symbol=symbol, current_time=current_time)
            # trend = result['trend']
            # trend = determine_trend_macd(df)
            # Tìm patterns với lookback mới
            trend = determine_trend_ema(df, lookback=lookback)
            
            position_id, positionSide, entry_price, pnl = get_position(symbol=symbol)
            if position_id:
                pnl = float(pnl * 100) 
            # Ghi log thong tin xu huong va so du
            if first_time:
                log_message = (f"------------Bắt đầu chương trình--------------\n"
                            f"Phân tích xu hướng thị trường {symbol} ({timeframe}): thị trường đang {trend}\n"
                            f"Giá hiện tại: {current_price:.5f} USDT\n")
                first_time = False
            else:
                if position_id:
                    log_message = (f"Đang có lệnh {positionSide} {symbol} giá entry {entry_price} và giá hiện tại: {current_price:.5f} USDT, với pnl: {pnl:.2f} % ")
                else:
                    log_message = (f"Giá {symbol} hiện tại: {current_price:.5f} USDT, chưa mở vị thế. ")
                    
            write_log(log_message)
            
            
            if position_id:
                last_milestone_achieved = 0
                if pnl > 75:          #loi nhuan tren 50%
                    write_log(f"Lợi nhuận > 75% nên sẽ update lại stop-loss")
                    order_id, quantity, stopPrice, side, positionSide, type = get_order_stoploss_data(symbol=symbol)
                    update_sl = True
                    # write_log(f"order_id: {order_id}, quantity: {quantity}, stopPrice: {stopPrice}, side: {side}, positionSide: {positionSide}, type: {type}")
                    pnl_milestones = int(pnl /50)*50    # = [100, 150, 200, 250, 300]
                    if pnl >= 100 and pnl_milestones > last_milestone_achieved and pnl_milestones in [100, 150, 200, 250, 300]:
                        target_pnl = float((pnl - 25)/100)
                        last_milestone_achieved = pnl_milestones
                    else:
                        target_pnl = float((pnl / 2) / 100)
                    write_log(f"target_pnl: {target_pnl}")    
                    if positionSide == "LONG":
                        new_stop_loss = cal_price_pnl(entry_price, target_pnl, positionSide, lev) 
                        write_log(f"Vị thế {positionSide}: Stop-loss mới {new_stop_loss:.5f}, stop-loss cũ {stopPrice:.5f}.")
                        if new_stop_loss <= stopPrice:
                            update_sl = False
                        # write_log(f"{side} New stop-loss {new_stop_loss:.5f}")
                    else:
                        new_stop_loss = cal_price_pnl(entry_price, target_pnl, positionSide, lev) 
                        write_log(f"Vị thế {positionSide}: Stop-loss mới {new_stop_loss:.5f}, stop-loss cũ {stopPrice:.5f}.")
                        if new_stop_loss >= stopPrice:
                            update_sl = False
                        # write_log(f"{side} New stop-loss {new_stop_loss:.5f}")
                    # write_log(f"Pnl đang là {pnl} % nên điều chỉnh stop-loss {stopPrice:.5f} thành {new_stop_loss:.5f}")
                    
                    write_log(f"Update stop-loss flag: {update_sl} ")
                    if update_sl:
                        cancel_order(symbol, order_id)
                        write_log(f"Xóa stop-loss cũ {stopPrice:.5f} thành công.")
                        replace_order(symbol, side, positionSide, type, quantity, new_stop_loss)
                        write_log(f"Điều chỉnh stop-loss mới {new_stop_loss:.5f} thành công.")
                    else:
                        write_log(f"Không Xóa stop-loss cũ {stopPrice:.5f}.")
                
            else:
                quantity = position_amt / current_price*lev
                order_value = quantity*lev
                order_value = round(order_value, 4)
                # print("------Check balance-----")
                if position_amt > balance:
                    write_log(f"Số dư không đủ ({balance:.2f} USDT) để đặt lệnh với giá trị {quantity:.2f} USDT")
                else:
                    # Tính Fibonacci Retracement
                    fib_levels = calculate_fibonacci_levels(df)
                    
                    # Xác định vùng hỗ trợ/kháng cự
                    support, resistance = find_support_resistance(df, fib_levels)
                    # print(f"\nVùng hỗ trợ: ", support)
                    # print(f"\nVùng kháng cự:", resistance)
                    
                    
                    
                    signal = trading_decision(support, resistance, trend, current_price, lev)
                    
                    if 'sideway' in signal:
                        write_log("Thị trường đi ngang, không đặt lệnh mới.")
                    else:
                        # % Biến động giá = % Lời/Lỗ mong muốn / Đòn bẩy
                        pnl_sl = float(1 / lev) # mong muon la 100%
                        pnl_tp = float(3 / lev) # mong muon la 300%
                        
                        
                        
                        if signal == 'LONG':
                            if set_leverage(symbol=symbol, leverage=lev, side=signal):
                                write_log(f"Thiết lập đòn bẩy x{lev} cho lệnh {signal} {symbol} thành công.")
                            else:
                                write_log(f"Không thể thiết lập đòn bẩy.")
                                return
                        
                            stop_loss = float(current_price * (1 - pnl_sl)) 
                            take_profit = float(current_price * (1 + pnl_tp)) 
                            # balance -= order_value
                            place_order(symbol, 'BUY', quantity, stop_loss, take_profit)
                            
                            write_log(f"Xu hướng {trend}. Đặt lệnh LONG {quantity} {symbol} tại giá {current_price:.5f}, SL: {stop_loss:.5f}, TP: {take_profit:.5f}")
                            # write_log(f"Số dư USDT còn lại sau khi đặt lệnh: {balance:.2f} USDT")
                        elif signal == 'SHORT':
                            if set_leverage(symbol=symbol, leverage=lev, side=signal):
                                write_log(f"Thiết lập đòn bẩy x{lev} cho lệnh {signal} {symbol} thành công.")
                            else:
                                write_log(f"Không thể thiết lập đòn bẩy.")
                                return
                            
                            stop_loss = float(current_price * (1 + pnl_sl)) 
                            take_profit = float(current_price * (1 - pnl_tp)) 
                            # balance -= order_value
                            place_order(symbol, 'SELL', quantity, stop_loss, take_profit)
                            
                            write_log(f"Xu hướng {trend}. Đặt lệnh SHORT {quantity} {symbol} tại giá {current_price:.5f}, SL: {stop_loss:.5f}, TP: {take_profit:.5f}")
                
               
            time.sleep(5*60)    # 5 phut
            
    
        except Exception as e:
            write_log(f"Lỗi: {e}")
            time.sleep(5*60)
        
        except KeyboardInterrupt:
            write_log("Dừng chương trình.")
            balance = get_balance()
            if position_id:
                try:
                    current_price = get_current_price(symbol=symbol, current_time=current_time)
                    current_time = pd.Timestamp.now()
                    close_position(position_id)
                    write_log(f"Lệnh {positionSide} đã được đóng do dừng chương trình. Với lợi nhuận {pnl:.2f} % và số dư USDT cuối cùng: {balance:.2f} USDT")
                except Exception as e:
                    write_log(f"Lỗi khi đóng lệnh: {e}")
            else:
                write_log(f"Không có lệnh đang mở. Số dư USDT cuối cùng: {balance:.2f} USDT")
            break
        
        
 
# chay tien trinh cho tung symbol 
def run_symbol_process(api_key, secret, symbol_info):
    symbol = symbol_info['symbol'] + '-USDT' if not symbol_info['symbol'].endswith('-USDT') else symbol_info['symbol']
    amount = symbol_info['amount']
    lev = symbol_info['leverage']
    write_log(f"Starting process for {symbol} with amount={amount}, leverage={lev}...")
    symbol_process(api_key, secret, symbol, amount, lev)
    



# Hàm chính
def main():
    
    # Lay danh sach coin
    symbols_list = load_symbol_from_env()
    # print(symbols_list)
    if not symbols_list:
        write_log(f"No valid coins found.")
        return
    
    write_log(f"Get list coins success.")
    write_log(f"------------Program start--------------------")
    
    balance = get_balance()
    write_log(f"Khởi động chương trình. Số dư USDT ban đầu: {balance:.2f} USDT")
    
    processes = []
        
    for item in symbols_list:
        process = multiprocessing.Process(
            target=run_symbol_process,
            args=(API_KEY, API_SECRET, item)
        )
        processes.append(process)
        process.start()
        
    # Doi tất cả tiến trình hoàn thành. 
    for process in processes:
        process.join()    

    write_log(f"--------------END PROGRAM----------------------")

if __name__ == "__main__":
    main()