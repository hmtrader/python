import requests
import hashlib
import hmac
import time
from urllib.parse import urlencode


API_KEY      = 'YOUR_API_KEY'
SECRET_KEY   = b'YOUR_SECRET_KEY'
# --- CẤU HÌNH API BINANCE FUTURES ---
BASE_URL = "https://fapi.binance.com"


def _generate_signature(params: dict) -> str:
    """
    Tạo signature đúng chuẩn Binance (rất quan trọng!)
    """
    # Binance yêu cầu: query string phải được encode bằng urllib.parse.urlencode
    # và KHÔNG được có khoảng trắng, phải dùng %XX cho ký tự đặc biệt
    query_string = urlencode(params)
    signature = hmac.new(SECRET_KEY, query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    return signature

def get_server_time():
    url = f"{BASE_URL}/fapi/v1/time"
    r = requests.get(url)
    return r.json()['serverTime']

def sync_time():
    server_time = get_server_time()
    global TIMESTAMP_OFFSET
    TIMESTAMP_OFFSET = server_time - int(time.time() * 1000)
    print(f"Đã đồng bộ thời gian. Offset: {TIMESTAMP_OFFSET}ms")
    
# Đồng bộ thời gian ngay khi khởi động (rất quan trọng!)
TIMESTAMP_OFFSET = 0
sync_time()

def request(method: str, path: str, params: dict = None):
    if params is None:
        params = {}
    
    # Thêm timestamp + recvWindow
    params['timestamp'] = int(time.time() * 1000) + TIMESTAMP_OFFSET
    params['recvWindow'] = 60000
    
    # Tạo signature ĐÚNG CÁCH
    signature = _generate_signature(params)
    params['signature'] = signature
    
    headers = {
        'X-MBX-APIKEY': API_KEY
    }
    
    url = BASE_URL + path
    
    if method == 'GET':
        r = requests.get(url, headers=headers, params=params, timeout=10)
    elif method == 'POST':
        r = requests.post(url, headers=headers, params=params, timeout=10)
    elif method == 'DELETE':
        r = requests.delete(url, headers=headers, params=params, timeout=10)
    
    # In lỗi chi tiết nếu có
    if r.status_code != 200:
        print(f"Lỗi HTTP {r.status_code}: {r.text}")
        return None
    
    try:
        return r.json()
    except:
        print("Response không phải JSON:", r.text)
        return None
    
# ================== HÀM ĐẶT LỆNH LIMIT ===================
# Hàm đặt lệnh thật trên Binance
def place_order(symbol, side, type, quantity, price, timeInForce='GTC', reduceOnly=False):
    method = 'POST'
    endPoint = '/fapi/v1/order'
    
    params = {
        'symbol': symbol,
        'side': side,
        'type': type,
        'timeInForce': timeInForce,
        'quantity': quantity,    # để nguyên float
        'price': price,
        'recvWindow': 60000
    }
    if reduceOnly:
        params['reduceOnly'] = 'true'
    
    result = request(method, endPoint, params)
    if result and 'orderId' in result:
        print(f"Đặt lệnh {side} LIMIT thành công!")
        print(f"Order ID: {result['orderId']} | Giá: {price}")
    else:
        print("Đặt lệnh thất bại:", result)
    return result

# set đòn bẩy
def set_leverage(symbol, leverage):
    """Đặt đòn bẩy trước khi mở lệnh"""
    method = 'POST'
    endPoint = '/fapi/v1/leverage'
    
    params = {
        'symbol': symbol,
        'leverage': leverage
    }
    
    result = request(method, endPoint, params)
    
    if result and result.get('leverage') == leverage:
        print(f"Đã đặt đòn bẩy {leverage}x cho {symbol}")
    else:
        print("Lỗi đặt đòn bẩy:", result)
       
# Hàm lấy thông tin tài khoản futures 
def get_balance():     
    method = 'GET'
    endPoint = '/fapi/v2/balance'
    
    result = request(method, endPoint)       
    
    if not result:
        return None, None
    
    # Lọc và in ra các thông tin cần thiết
    for asset in result:
        if asset['asset'] == 'USDT':
            balance = asset['balance']
            avaliableBalance = asset['availableBalance']
            
    return balance, avaliableBalance

