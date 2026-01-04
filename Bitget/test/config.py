# config.py

# === CÀI ĐẶT GIAO DỊCH ===
SYMBOL = 'UNIUSDT'  # Cặp giao dịch (sử dụng symbol cho hợp đồng tương lai)
# SYMBOLS = "BNBUSDT:1:30,BGBUSDT:1:15,NEARUSDT:0.5:20,RAYUSDT:0.5:15" #symbol:amount:leverage
SYMBOLS = "ADAUSDT:0.5:20,MUSDT:0.5:20" #symbol:amount:leverage
LEVERAGE = 10             # Đòn bẩy
ORDER_SIZE = 0.01        # Khối lượng mỗi lệnh (ví dụ: 0.001 bnb)

# === CÀI ĐẶT PHÂN TÍCH KỸ THUẬT ===
TIMEFRAME_TREND = '4H'    # Khung thời gian chính để xác định xu hướng
TIMEFRAME_CONFIRM = '1H'  # Khung thời gian để xác nhận xu hướng và tìm tín hiệu đảo chiều
TIMEFRAME_ENTRY = '15m'   # Khung thời gian để tìm điểm vào lệnh thuận xu hướng
TIMEFRAME_EMA = '30m'   # Khung thời gian để xác nhận đường EMA9

EMA_SHORT = 9
EMA_LONG = 21
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# === CÀI ĐẶT QUẢN LÝ RỦI RO ===
# SL/TP cho lệnh thuận xu hướng
SL_TARGET_RATE = 1       # 100%
TP_TARGET_RATE = 2     # 550%
PROFIT_TARGET_RATIO = 550  # Tỷ lệ R:R (ví dụ: TP = 5.5 * SL)
STOP_LOSS_PERCENTAGE_FROM_ZONE = 0.05 # 5% so với vùng Hỗ trợ/Kháng cự

# SL cho lệnh ngược xu hướng
COUNTER_TREND_SL_PERCENTAGE = 0.05 # 5% so với nến tín hiệu

# Trailing Stop
TRAILING_STOP_RULES = {
    9.0: 8.5,
    8.0: 7.5,
    7.0: 6.5,
    6.0: 5.5,
    5.0: 4.5,
    4.0: 3.5,  # Nếu PnL > 400%, SL = Entry + 350%
    3.0: 2.5,  # Nếu PnL > 300%, SL = Entry + 250%
    2.0: 1.5,  # Nếu PnL > 200%, SL = Entry + 150%
    1.5: 1.0,  # Nếu PnL > 150%, SL = Entry + 100%
    1.0: 0.5,  # Nếu PnL > 100%, SL = Entry + 50%
    0.5: 0.25, # Nếu PnL > 50%, SL = Entry + 25%
    0.2: 0.1, # Nếu PnL > 20%, SL = Entry + 10%
}