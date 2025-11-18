import requests
import hashlib
import hmac
import time
import urllib.parse

API_KEY      = 'YOUR_API_KEY'
SECRET_KEY   = 'YOUR_SECRET_KEY'

# --- CẤU HÌNH API BINANCE FUTURES ---
BASE_URL = "https://fapi.binance.com"
ENDPOINT = "/fapi/v3/balance"

def hmac_hashing(api_secret: str, payload: str) -> str:
    m = hmac.new(api_secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256)
    return m.hexdigest()

def get_binance_futures_balance():
    """
    Kết nối API Binance Futures bằng HMAC SHA256 để lấy thông tin số dư (balance).
    """
    
    # 1. Tạo Timestamp
    # Binance yêu cầu timestamp tính bằng mili giây
    timestamp = int(time.time() * 1000)
    
    # 2. Xây dựng Chuỗi Tham số (Payload)
    # Endpoint này yêu cầu tham số tối thiểu là timestamp
    params = {
        'timestamp': timestamp,
        'recvWindow': 15000 # Thời gian chờ request (15 giây)
    }
    
    # 3. Chuyển tham số thành Query String
    query_string = urllib.parse.urlencode(params)
    
    # 4. Tạo Signature (Chữ ký HMAC SHA256)
    signature = hmac_hashing(SECRET_KEY, query_string)
    
    # 5. Hoàn thiện URL Request
    # Thêm signature vào cuối query string
    full_url = f"{BASE_URL}{ENDPOINT}?{query_string}&signature={signature}"
    
    # 6. Thiết lập Header và Gửi Request
    headers = {
        'X-MBX-APIKEY': API_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(full_url, headers=headers)
        response.raise_for_status() # Báo lỗi nếu status code là 4xx hoặc 5xx
        
        data = response.json()
        # print(data)
        
        print("✅ Kết nối thành công!")
        print("-" * 30)
        print("💰 Thông tin Futures Balance:")
        
        # Lọc và in ra các thông tin cần thiết
        for asset in data:
            if asset['asset'] == 'USDT':
                print(f"  Tổng số dư: {asset['balance']} USDT")
                print(f"  Số dư khả dụng: {asset['availableBalance']} USDT")
                
    except requests.exceptions.HTTPError as errh:
        print(f"❌ Lỗi HTTP (Kiểm tra Key/Secret/Permissions): {errh}")
        print(f"Response Body: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Lỗi kết nối (Mạng/URL): {e}")


# Hàm chính
def main():
    
    # print(f"Get list coins success.")
    print(f"------------Program start--------------------")
    
    print("Đang kết nối với Binance...")

    get_binance_futures_balance()
    
    print(f"--------------END PROGRAM----------------------")

if __name__ == "__main__":
    main()
    
    
    