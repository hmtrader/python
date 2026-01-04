import pandas as pd
import numpy as np
import time
from ta.momentum import RSIIndicator
import requests
import hmac
import hashlib
import json
from dotenv import load_dotenv
import os

#load từ file .env
load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
BASE_URL = os.getenv("BASE_URL")

# Tham so co dinh
SYMBOL = os.getenv("SYMBOL")
LEVERAGE = os.getenv("LEVERAGE")
POSITION_AMT = os.getenv("POSITION_AMT")    # so luong usdt
MARGIN_USDT = os.getenv("MARGIN_USDT")
INTERVAL = os.getenv("INTERVAL")
CHECK_INTERVAL = os.getenv("CHECK_INTERVAL")    #5 phut
LOGFILE = os.getenv("LOGFILE")

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
        print(f"Lỗi khi get balance.")
        time.sleep(20)
        
    for x in data['data']:
        if x['asset'] == 'USDT':
            balance = float(x['balance'])
            break
    
    return balance

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
def place_order(side, price, quantity, stop_loss, take_profit):
    payload = {}
    path = '/openApi/swap/v2/trade/order'
    method = "POST"
    
    paramsMap = {
        "symbol": SYMBOL,
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

# Hàm đóng lệnh thật trên BingX
def close_order(order_id, side, quantity):
    endpoint = '/openApi/swap/v2/trade/close'
    params = {
        'symbol': SYMBOL,
        'orderId': order_id,
        'side': 'SELL' if side == 'buy' else 'BUY',
        'type': 'MARKET',
        'quantity': quantity,
        'timestamp': int(time.time() * 1000)
    }
    params['sign'] = generate_signature(params, API_SECRET)
    headers = {'X-BX-APIKEY': API_KEY}
    response = requests.post(BASE_URL + endpoint, headers=headers, params=params)
    data = response.json()
    if data['code'] != 0:
        raise Exception(f"Lỗi đóng lệnh: {data['msg']}")
    return data

def get_position(symbol):
    payload = {}
    path = '/openApi/swap/v2/user/positions'
    method = "GET"
    paramsMap = {
        "symbol": symbol
    }
    paramsStr = parseParam(paramsMap)
    response = json.loads(make_request(method, path, paramsStr, payload))
    if response['code'] != 0:
        raise Exception(f"Lỗi lấy position id: {response['msg']}")
    
    data = response.get("data",[])
    print("get_position data: " , data)
    # print("Get position: " , data[0]['positionId'], data[0]['positionSide'], data[0]['pnlRatio'])
    
    if data:
        item = data[0]
        posId = item.get('positionId')
        side = item.get('positionSide')
        pnl = item.get('pnlRatio')
        # print("Get position: " , data[0]['positionId'], data[0]['positionSide'], data[0]['pnlRatio'])
        return posId, side, pnl
    else:
        return None, None, None


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
        "side": "LONG" if side == 'BUY' else "SHORT",
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

# Lớp quản lý lệnh
class Order:
    def __init__(self, side, entry_price, quantity, stop_loss, take_profit, timestamp, order_id):
        self.side = side
        self.entry_price = entry_price
        self.quantity = quantity
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.timestamp = timestamp
        self.order_id = order_id
        self.active = True
        self.profit = 0
        self.close_price = None
        self.close_reason = None
        self.close_time = None

    def update(self, current_price, current_time, balance):
        if self.active:
            if self.side == 'buy':
                self.profit = (current_price - self.entry_price) / self.entry_price * 100
                profit_usdt = (current_price - self.entry_price) * self.quantity
                write_log(f"Lệnh {self.side.upper()} đang mở: Giá hiện tại: {current_price:.5f}, Lợi nhuận tạm tính: {profit_usdt:.2f} USDT ({self.profit:.2f}%)")
                if current_price <= self.stop_loss:
                    return self.close(current_price, current_time, "Stop-loss triggered", balance)
                elif current_price >= self.take_profit:
                    return self.close(current_price, current_time, "Take-profit triggered", balance)
                elif self.profit > 1:
                    new_stop_loss = self.entry_price + self.entry_price * (self.profit - self.profit*0.2)
                    if new_stop_loss > self.stop_loss:
                        write_log(f"Điều chỉnh stop-loss từ {self.stop_loss:.5f} lên {new_stop_loss:.5f}")
                        self.stop_loss = new_stop_loss
            elif self.side == 'sell':
                self.profit = (self.entry_price - current_price) / self.entry_price * 100
                profit_usdt = (self.entry_price - current_price) * self.quantity
                write_log(f"Lệnh {self.side.upper()} đang mở: Giá hiện tại: {current_price:.5f}, Lợi nhuận tạm tính: {profit_usdt:.2f} USDT ({self.profit:.2f}%)")
                if current_price >= self.stop_loss:
                    return self.close(current_price, current_time, "Stop-loss triggered", balance)
                elif current_price <= self.take_profit:
                    return self.close(current_price, current_time, "Take-profit triggered", balance)
                elif self.profit > 1:
                    new_stop_loss = self.entry_price  - self.entry_price * (self.profit - self.profit*0.2)
                    if new_stop_loss < self.stop_loss:
                        write_log(f"Điều chỉnh stop-loss từ {self.stop_loss:.5f} xuống {new_stop_loss:.5f}")
                        self.stop_loss = new_stop_loss
            # write_log(f"Pnl hiện tại: {self.profit:.5f}%, Balance: {balance:.5f} USDT.")
        return 0, balance

    def close(self, current_price, current_time, reason, balance):
        if self.active:
            self.active = False
            self.close_price = current_price
            self.close_time = current_time
            self.close_reason = reason
            if self.side == 'buy':
                profit = (current_price - self.entry_price) * self.quantity
            else:
                profit = (self.entry_price - current_price) * self.quantity
            new_balance = balance + profit
            profit_pct = (profit / (self.entry_price * self.quantity)) * 100 if self.entry_price > 0 else 0
            write_log(f"Lệnh {self.side.upper()} đóng tại giá {current_price:.5f}. Lý do: {reason}")
            write_log(f"Lợi nhuận: {profit:.2f} USDT (Tỷ lệ: {profit_pct:.2f}%)")
            write_log(f"Số dư USDT mới: {new_balance:.2f} USDT")
            close_order(self.order_id, self.side, self.quantity)  # Đóng lệnh thật
            
            return profit, new_balance
        return 0, balance

    def to_dict(self):
        return {
            'timestamp': self.timestamp,
            'side': self.side,
            'entry_price': self.entry_price,
            'quantity': self.quantity,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'close_price': self.close_price,
            'close_time': self.close_time,
            'close_reason': self.close_reason,
            'profit': self.profit,
            'profit_usdt': (self.close_price - self.entry_price) * self.quantity if self.side == 'buy' else (self.entry_price - self.close_price) * self.quantity if self.close_price else 0
        }

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

# Hàm chính
def main():
    symbol = SYMBOL
    interval = INTERVAL
    current_order = None
    balance = get_balance()  # Lấy số dư từ API
    first_time = True
    position_amt = float(POSITION_AMT)
    lev = float(LEVERAGE)
    
    write_log(f"Khởi động chương trình. Số dư USDT ban đầu: {balance:.2f} USDT")
    print("----Check position--------")
    position_id, side, pnl = get_position(symbol=symbol)
    # print("posi id:", position_id)
    # if position_id:
    #     close_position(position_id)
    if position_id:
        write_log(f"Vị thế {side} {symbol} đang mở, với lợi nhuận {pnl} thành công.\n")
    else:
        print("Không có vị thế nào đang mở")
        
    # while True:
    #     try:
    #         current_time = pd.Timestamp.now()
    #         df = get_klines_data(symbol=symbol, interval=interval, limit=1000)
    #         result = analyze_trend(df)
    #         current_price = get_current_price(symbol=symbol, current_time=current_time)
    #         trend = result['trend']
            
            
    #         # Ghi log thong tin xu huong va so du
    #         if first_time:
    #             log_message = (f"------------Bắt đầu chương trình--------------\n"
    #                         f"Phân tích xu hướng thị trường {SYMBOL} ({INTERVAL}):\n"
    #                         f"Xu hướng: {trend}\n"
    #                         f"Giá hiện tại: {current_price:.5f} USDT\n"
    #                         f"Thay đổi giá (%): {result['latest_price_change_pct']:.2f}%\n"
    #                         f"RSI: {result['latest_rsi']:.2f}\n"
    #                         f"ATR (%): {result['latest_atr_pct']:.2f}%\n"
    #                         f"Số dư USDT hiện tại: {balance:.5f} USDT")
    #             first_time = False
    #         else:
    #             log_message = (f"Giá hiện tại: {current_price:.5f} USDT "
    #                         f"Thay đổi giá (%): {result['latest_price_change_pct']:.2f}%\n"
    #                         )
    #         write_log(log_message)
            
            
    #         # print(f"------Check current order----- {current_order}")
    #         if current_order and current_order.active:
    #             # print(f"------show current order-----", current_order)
    #             profit, balance = current_order.update(current_price, current_time, balance)
    #             if not current_order.active:
    #                 save_order_history(current_order)
    #                 current_order = None
    #         else:
    #             # print(f"------show current order else-----")
    #             quantity = position_amt / current_price*lev
    #             # print(f"------show current order else 1-----")
    #             order_value = quantity*lev
    #             # print(f"------show current order else 2-----")
    #             order_value = round(order_value, 4)
    #             # print("------Check balance-----")
    #             if position_amt > balance:
    #                 write_log(f"Số dư không đủ ({balance:.2f} USDT) để đặt lệnh với giá trị {quantity:.2f} USDT")
    #             else:
                    
                    
    #                 if 'Sideway' in trend:
    #                     write_log("Thị trường đi ngang, không đặt lệnh mới.")
    #                 else:
    #                     if 'Bullish' in trend:
    #                         if set_leverage(symbol=symbol, leverage=LEVERAGE, side="LONG"):
    #                             write_log(f"Thiết lập đòn bẩy {LEVERAGE} cho {symbol} thành công.")
    #                         else:
    #                             write_log(f"Không thể thiết lập đòn bẩy.")
    #                             return
                            
    #                         stop_loss = current_price - current_price * 0.050
    #                         take_profit = current_price + current_price * 0.1
    #                         # balance -= order_value
    #                         order_id = place_order('BUY', current_price, quantity, stop_loss, take_profit)
    #                         current_order = Order('BUY', current_price, quantity, stop_loss, take_profit, current_time, order_id)
    #                         write_log(f"Đặt lệnh MUA tại giá {current_price:.5f}, SL: {stop_loss:.5f}, TP: {take_profit:.5f}, Order ID: {order_id}")
    #                         write_log(f"Số dư USDT còn lại sau khi đặt lệnh: {balance:.2f} USDT")
    #                     elif 'Bearish' in trend:
    #                         if set_leverage(symbol=symbol, leverage=LEVERAGE, side="SHORT"):
    #                             write_log(f"Thiết lập đòn bẩy {LEVERAGE} cho {symbol} thành công.")
    #                         else:
    #                             write_log(f"Không thể thiết lập đòn bẩy.")
    #                             return
                            
    #                         stop_loss = current_price + current_price * 0.050
    #                         take_profit = current_price - current_price * 0.1
    #                         # balance -= order_value
    #                         order_id = place_order('SELL', current_price, quantity, stop_loss, take_profit)
    #                         current_order = Order('SELL', current_price, quantity, stop_loss, take_profit, current_time, order_id)
    #                         write_log(f"Đặt lệnh BÁN tại giá {current_price:.5f}, SL: {stop_loss:.5f}, TP: {take_profit:.5f}, Order ID: {order_id}")
    #                         write_log(f"Số dư USDT còn lại sau khi đặt lệnh: {balance:.2f} USDT")
                    
                        

    #         time.sleep(5*60)

    #     except Exception as e:
    #         write_log(f"Lỗi: {e}")
    #         time.sleep(60)
    #     except KeyboardInterrupt:
    #         write_log("Dừng chương trình.")
    #         if current_order and current_order.active:
    #             try:
    #                 current_price = get_current_price(symbol=symbol, current_time=current_time)
    #                 current_time = pd.Timestamp.now()
    #                 position_id = get_position(symbol=symbol)
    #                 close_position(position_id)
    #                 save_order_history(current_order)
    #                 balance = get_balance()
    #                 write_log(f"Lệnh {current_order.side.upper()} đã được đóng do dừng chương trình. Số dư USDT cuối cùng: {balance:.2f} USDT")
    #             except Exception as e:
    #                 write_log(f"Lỗi khi đóng lệnh: {e}")
    #         else:
    #             write_log(f"Không có lệnh đang mở. Số dư USDT cuối cùng: {balance:.2f} USDT")
    #         break

if __name__ == "__main__":
    main()