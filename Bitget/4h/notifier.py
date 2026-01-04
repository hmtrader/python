import os
import requests
from dotenv import load_dotenv

# Tải biến môi trường từ file .env
load_dotenv()



# Khởi tạo API
TELE_API_HTTP = os.getenv("TELE_API_HTTP")
TELE_CHAT_ID = os.getenv("TELE_CHAT_ID")

BOT_TOKEN = TELE_API_HTTP
CHAT_ID = TELE_CHAT_ID
# ---------------------------------------------

def gui_tin_nhan_telegram(message):
    """
    Hàm này gửi một tin nhắn văn bản đến một Chat ID cụ thể qua Bot Telegram.
    """
    # Xây dựng URL của API Telegram
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # Dữ liệu gửi đi (payload)
    # 'parse_mode': 'MarkdownV2' cho phép bạn dùng định dạng như *đậm*, _nghiêng_
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown" # Dùng Markdown đơn giản cho dễ
    }
    
    try:
        # Gửi yêu cầu POST
        response = requests.post(url, data=payload)
        response.raise_for_status() # Kiểm tra nếu có lỗi HTTP
        
        print(f"Tin nhắn đã được gửi: {message}")
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi gửi tin nhắn: {e}")
        return None

# --- Ví dụ thử nghiệm ---
if __name__ == "__main__":
    # Gửi tin nhắn thử nghiệm khi chạy file này
    gui_tin_nhan_telegram("Đây là tin nhắn thử nghiệm từ Bot Python!")