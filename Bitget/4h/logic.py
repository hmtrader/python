# logic.py
import pandas as pd
# import pandas_ta as ta
from scipy.signal import find_peaks

CANDLES = 10    # Lấy 10 cây nến sau cùng

def get_ema9(df):
    return df['close'].ewm(span=9, adjust=False).mean()


# def add_indicators_ta(df):
#     """Thêm các chỉ báo kỹ thuật vào DataFrame."""
#     df.ta.ema(length=9, append=True)
#     df.ta.ema(length=21, append=True)
#     df.ta.rsi(length=14, append=True)
#     return df

def add_indicators(df):
    """Thêm các chỉ báo kỹ thuật vào DataFrame."""
    df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()
    
    delta = df['close'].diff(1)
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14, min_periods=14).mean()
    avg_loss = loss.rolling(window=14, min_periods=14).mean()
    rs = avg_gain / avg_loss
    df['RSI_14'] = 100 - (100 / (1 + rs))
    return df
    # df.ta.ema(length=9, append=True)
    # df.ta.ema(length=21, append=True)
    # df.ta.rsi(length=14, append=True)
    # return df


def calculate_atr(df, period=14):
    """Calculate Average True Range (ATR)."""
    df['HL'] = df['high'] - df['low']
    df['HCp'] = abs(df['high'] - df['close'].shift())
    df['LCp'] = abs(df['low'] - df['close'].shift())
    df['TR'] = df[['HL', 'HCp', 'LCp']].max(axis=1)
    df['ATR'] = df['TR'].rolling(window=period).mean()
    return df['ATR'].iloc[-1]


def analyze_trend(df):
    """
    Analyze trend based on EMA9, EMA21, and RSI(14).
    Returns 'UP', 'DOWN', or None.
    """
    # # Calculate indicators
    # df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    # df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    # delta = df['close'].diff(1)
    # gain = delta.where(delta > 0, 0)
    # loss = -delta.where(delta < 0, 0)
    # avg_gain = gain.rolling(window=14, min_periods=14).mean()
    # avg_loss = loss.rolling(window=14, min_periods=14).mean()
    # rs = avg_gain / avg_loss
    # df['RSI14'] = 100 - (100 / (1 + rs))
    
    # Get latest values
    ema9 = df['EMA_9'].iloc[-1]
    ema21 = df['EMA_21'].iloc[-1]
    rsi = df['RSI_14'].iloc[-1]
    
    if pd.isna(ema9) or pd.isna(ema21) or pd.isna(rsi):
        return None  # Not enough data
    
    if ema9 > ema21 and rsi > 50:
        return 'UP'
    elif ema9 < ema21 and rsi < 50:
        return 'DOWN'
    else:
        return 'SIDEWAY'
    
    
# def analyze_trend_ta(df):
#     """
#     Analyze trend based on EMA9, EMA21, and RSI(14).
#     Returns 'UP', 'DOWN', or None.
#     """
#     # Calculate indicators
#     df['EMA9'] = ta.ema(df['close'], length=9)
#     df['EMA21'] = ta.ema(df['close'], length=21)
#     df['RSI14'] = ta.rsi(df['close'], length=14)
    
#     # Get latest values
#     ema9 = df['EMA9'].iloc[-1]
#     ema21 = df['EMA21'].iloc[-1]
#     rsi = df['RSI14'].iloc[-1]
    
#     if pd.isna(ema9) or pd.isna(ema21) or pd.isna(rsi):
#         return None  # Not enough data
    
#     if ema9 > ema21 and rsi > 50:
#         return 'UP'
#     elif ema9 < ema21 and rsi < 50:
#         return 'DOWN'
#     else:
#         return 'SIDEWAY'

def is_hammer(df, n=CANDLES, body_multiplier=2, shadow_multiplier=0.1):
    """
    Kiểm tra mẫu nến Hammer trong khoảng n cây nến cuối cùng.
    - Trả về danh sách các tuple (vị trí i - index âm, giá trị low của nến Hammer tại i).
    - Nếu không tìm thấy, trả về danh sách rỗng [].
    """
    if len(df) < 1 or not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
        return []
    
    # Giới hạn n nếu df nhỏ hơn
    n = min(n, len(df))
    
    hammers = []
    # Lặp từ nến xa nhất trong khoảng đến nến cuối (i từ -n đến -1)
    start_i = -n
    for i in range(start_i, 0):
        o = df['open'].iloc[i]
        h = df['high'].iloc[i]
        l = df['low'].iloc[i]
        c = df['close'].iloc[i]
        
        body = abs(c - o)
        upper_shadow = h - max(o, c)
        lower_shadow = min(o, c) - l
        
        if c > o and lower_shadow >= body_multiplier * body and upper_shadow <= shadow_multiplier * body:
            hammers.append((i, l))
            # Xet nen tiep phai la nen tang
            if df['open'].iloc[i+1] < df['close'].iloc[i+1]:
                print("Hammer")
                return True
    
    return False

def is_inverted_hammer(df, n=CANDLES, body_multiplier=2, shadow_multiplier=0.1):
    """
    Kiểm tra mẫu nến Inverted Hammer (bullish reversal).
    - Thân nến nhỏ, bóng trên dài (ít nhất body_multiplier lần thân), bóng dưới nhỏ.
    - Close > open (nến tăng).
    """
    if len(df) < 1 or not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
        return []
    
    # Giới hạn n nếu df nhỏ hơn
    n = min(n, len(df))
    
    start_i = -n
    for i in range(start_i, 0):
        o = df['open'].iloc[i]
        h = df['high'].iloc[i]
        l = df['low'].iloc[i]
        c = df['close'].iloc[i]
    
        body = abs(c - o)
        upper_shadow = h - max(o, c)
        lower_shadow = min(o, c) - l
        
        if c > o and upper_shadow >= body_multiplier * body and lower_shadow <= shadow_multiplier * body:
            # Xet nen tiếp theo phải là nến tăng
            if df['open'].iloc[i+1] > df['close'].iloc[i+1]:
                print("Inverted Hammer")
                return True
    
    return False

def is_shooting_star(df, n=CANDLES, body_multiplier=2, shadow_multiplier=0.1):
    """
    Kiểm tra mẫu nến Shooting Star (bearish reversal).
    - Thân nến nhỏ, bóng trên dài, bóng dưới nhỏ.
    - Close < open (nến giảm).
    """
    if len(df) < 1 or not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
        return []
    
    # Giới hạn n nếu df nhỏ hơn
    n = min(n, len(df))
    
    start_i = -n
    for i in range(start_i, 0):
        o = df['open'].iloc[i]
        h = df['high'].iloc[i]
        l = df['low'].iloc[i]
        c = df['close'].iloc[i]
        
        body = abs(c - o)
        upper_shadow = h - max(o, c)
        lower_shadow = min(o, c) - l
        
        if c < o and upper_shadow >= body_multiplier * body and lower_shadow <= shadow_multiplier * body:
            # Xet nen tiếp theo phải là nến giảm
            if df['open'].iloc[i+1] > df['close'].iloc[i+1]:
                print("shooting_star")
                return True
        
    return False

def is_hanging_man(df, n=CANDLES, body_multiplier=2, shadow_multiplier=0.1):
    """
    Kiểm tra mẫu nến Hanging Man (bearish reversal).
    - Thân nến nhỏ, bóng dưới dài, bóng trên nhỏ.
    - Close < open (nến giảm).
    """
    
    if len(df) < 1 or not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
        return []
    
    # Giới hạn n nếu df nhỏ hơn
    n = min(n, len(df))
    
    start_i = -n
    for i in range(start_i, 0):
        o = df['open'].iloc[i]
        h = df['high'].iloc[i]
        l = df['low'].iloc[i]
        c = df['close'].iloc[i]
        
        body = abs(c - o)
        upper_shadow = h - max(o, c)
        lower_shadow = min(o, c) - l
        
        if c < o and lower_shadow >= body_multiplier * body and upper_shadow <= shadow_multiplier * body:
            print("Hanging Man")
            return True
        
    return False

def is_bullish_engulfing(df, n=CANDLES, min_count=2):
    """
    Tìm các cặp nến Bullish Engulfing trong khoảng n cây nến cuối cùng.
    - Trả về danh sách các vị trí i (index âm) nơi có Bullish Engulfing.
    - Mỗi cặp là nến tại (i-1) và i.
    """
    if len(df) < 2:
        return []  # Không đủ nến để kiểm tra bất kỳ cặp nào
    
    positions = []
    # Bắt đầu từ vị trí sớm nhất có thể trong n nến cuối (cần i-1 hợp lệ)
    start_i = max(-len(df) + 1, -n)
    for i in range(start_i, 0):  # Lặp từ start_i đến -1 (i < 0)
        o1 = df['open'].iloc[i-1]
        c1 = df['close'].iloc[i-1]
        o2 = df['open'].iloc[i]
        c2 = df['close'].iloc[i]
        
        if c1 < o1 and c2 > o2 and o2 < c1 and c2 > o1:
            positions.append(i)
    
    if len(positions) >= min_count:
        print("Bullish Engulfing")
        return True
    
    return False

def is_bearish_engulfing(df, n=CANDLES, min_count=2):
    """
    Kiểm tra mẫu nến Bearish Engulfing (bearish reversal).
    - Nến trước: tăng (Close > open).
    - Nến hiện tại: giảm (Close < open), và thân engulf thân nến trước (open hiện tại > Close trước, Close hiện tại < open trước).
    """
    if len(df) < 2:
        return []  # Không đủ nến để kiểm tra bất kỳ cặp nào
    
    positions = []
    # Bắt đầu từ vị trí sớm nhất có thể trong n nến cuối (cần i-1 hợp lệ)
    start_i = max(-len(df) + 1, -n)
    for i in range(start_i, 0):  # Lặp từ start_i đến -1 (i < 0)
        o1 = df['open'].iloc[i-1]
        c1 = df['close'].iloc[i-1]
        o2 = df['open'].iloc[i]
        c2 = df['close'].iloc[i]
   
        if c1 > o1 and c2 < o2 and o2 > c1 and c2 < o1:
            positions.append(i)
        
    if len(positions) >= min_count:
        print("Bearish Engulfing")
        return True
    
    return False

def is_morning_star(df, n=CANDLES, gap_threshold=0.01):
    """
    Kiểm tra mẫu nến Morning Star (bullish reversal, 3 nến).
    - Nến 1: giảm mạnh.
    - Nến 2: thân nhỏ (doji hoặc spinning top), gap xuống dưới nến 1.
    - Nến 3: tăng mạnh, close trên midpoint của nến 1.
    """
    if len(df) < 1 or not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
        return []
    
    # Giới hạn n nếu df nhỏ hơn
    n = min(n, len(df))
    
    start_i = -n
    for i in range(start_i, 0):
        o1, c1 = df['open'].iloc[i-2], df['close'].iloc[i-2]
        o2, c2 = df['open'].iloc[i-1], df['close'].iloc[i-1]
        o3, c3 = df['open'].iloc[i], df['close'].iloc[i]
        
        body1 = abs(c1 - o1)
        body2 = abs(c2 - o2)
        body3 = abs(c3 - o3)
        
        midpoint1 = (o1 + c1) / 2
        
        if (c1 < o1) and (body2 < 0.5 * body1) and (o2 < c1) and (c3 > o3) and (c3 > midpoint1):
            print("Morning Star")
            return True

    return False

def is_evening_star(df, n=CANDLES, gap_threshold=0.01):
    """
    Kiểm tra mẫu nến Evening Star (bearish reversal, 3 nến).
    - Nến 1: tăng mạnh.
    - Nến 2: thân nhỏ, gap lên trên nến 1.
    - Nến 3: giảm mạnh, close dưới midpoint của nến 1.
    """
    if len(df) < 1 or not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
        return []
    
    # Giới hạn n nếu df nhỏ hơn
    n = min(n, len(df))
    
    start_i = -n
    for i in range(start_i, 0):
        o1, c1 = df['open'].iloc[i-2], df['close'].iloc[i-2]
        o2, c2 = df['open'].iloc[i-1], df['close'].iloc[i-1]
        o3, c3 = df['open'].iloc[i], df['close'].iloc[i]
        
        body1 = abs(c1 - o1)
        body2 = abs(c2 - o2)
        body3 = abs(c3 - o3)
        
        midpoint1 = (o1 + c1) / 2
        
        if (c1 > o1) and (body2 < 0.5 * body1) and (o2 > c1) and (c3 < o3) and (c3 < midpoint1):
            print("Evening star")
            return True
        
    return False

# Hàm mới: Kiểm tra có tạo đáy (trough) trên khung 15M (nến cuối là local min trên low)
def is_trough(df, i=-1, distance=1):
    series = df['low'].values
    troughs, _ = find_peaks(-series, distance=distance)
    return (len(series) + i) in troughs  # Kiểm tra index cuối có phải trough

# Hàm kiểm tra tạo đỉnh (peak) trên high
def is_peak(df, i=-1, distance=1):
    series = df['high'].values
    peaks, _ = find_peaks(series, distance=distance)
    return (len(series) + i) in peaks

def find_peak(df, distance=1, recent_candles=5):
    series = df['high'].values
    peaks, _ = find_peaks(series, distance=distance)
    # Lấy chỉ số của recent_candles cuối cùng (từ len(series) - recent_candles đến len(series)-1)
    start_idx = len(series) - recent_candles
    recent_peaks = peaks[peaks >= start_idx]
    if len(recent_peaks) == 0:
        return None
    
    # Lấy đỉnh gần nhất (chỉ số lớn nhất trong recent_peaks, tức mới nhất)
    nearest_peak_index = recent_peaks[-1]  # -1 để lấy đỉnh mới nhất trong khoảng
    
    high_value = series[nearest_peak_index]
    
    return high_value

# Hàm xác định dáy
def find_trough(df, distance=1, recent_candles=5):
    series = df['low'].values
    # Để tìm đáy, sử dụng find_peaks trên series âm (-series)
    troughs, _ = find_peaks(-series, distance=distance)
    # Lấy chỉ số của recent_candles cuối cùng (từ len(series) - recent_candles đến len(series)-1)
    start_idx = len(series) - recent_candles
    recent_troughs = troughs[troughs >= start_idx]
    if len(recent_troughs) == 0:
        return None
    
    # Lấy đáy gần nhất (chỉ số lớn nhất trong recent_troughs, tức mới nhất)
    nearest_troughs_index = recent_troughs[-1]  # -1 để lấy đáy mới nhất trong khoảng
    
    low_value = series[nearest_troughs_index]
    
    return low_value


def is_reversal_pattern(df, direction):
    """
    Kiểm tra mô hình nến đảo chiều đơn giản trên khung 1H.
    direction: 'UP' (thị trường tăng nên tìm đảo chiều giảm)
            , 'DOWN' (thị trường giảm nên tìm đảo chiều tăng)
    LƯU Ý: Đây là logic nhận dạng mẫu nến rất đơn giản.
    """
    if len(df) < 2:
        return False, None

    last_candle = df.iloc[-1]
    prev_candle = df.iloc[-2]

    # Bearish Engulfing (Đảo chiều giảm)
    if direction == 'UP':
        if (is_shooting_star(df) or is_bearish_engulfing(df) or is_hanging_man(df) or is_evening_star(df)):
             return True, last_candle['high'] # Trả về đỉnh nến để đặt SL

    # Bullish Engulfing (Đảo chiều tăng)
    if direction == 'DOWN':
        if (is_hammer(df) or is_inverted_hammer(df) or is_bullish_engulfing(df) or is_morning_star(df)):
            return True, last_candle['low'] # Trả về đáy nến để đặt SL

    return False, None

def check_volume_trough_peak(df, n=100, value=""):
    """
    Tìm đáy thấp nhất (giá trị low thấp nhất) trong n cây nến cuối cùng của DataFrame df.
    Trả về giá trị đáy, số lượng nến tăng (close > open), và số lượng nến giảm (close < open)
    từ đầu khoảng n nến đến vị trí của đáy thấp nhất (bao gồm vị trí đó).
    
    Args:
    df (pd.DataFrame): DataFrame với cột 'open', 'close', 'low'.
    n (int): Số lượng nến cuối cùng để xem xét (mặc định 10).
    
    Returns:
    tuple: (lowest_low, num_up, num_down) hoặc (None, 0, 0) nếu không đủ dữ liệu.
    """
    if len(df) < 1 or 'low' not in df.columns or 'open' not in df.columns or 'close' not in df.columns:
        return None, 0, 0
    
    # Giới hạn n nếu df nhỏ hơn
    n = min(n, len(df))
    
    # Lấy n nến cuối cùng
    recent_df = df.iloc[-n:-2]
    if value == "peak": 
        recent_value = recent_df['high']
        # Tìm giá trị cao nhất
        best_value = recent_value.max()
        # Tìm vị trí tương đối trong slice (0 là nến xa nhất, n-1 là mới nhất)
        pos_value = recent_value.argmax()
    elif value == "trough":    
        recent_value = recent_df['low']
        # Tìm giá trị low thấp nhất
        best_value = recent_value.min()
        # Tìm vị trí tương đối trong slice (0 là nến xa nhất, n-1 là mới nhất)
        pos_value = recent_value.argmin()
    else:
        return None, None, None
    
    
    # print("Pos_value:", pos_value)
    
    # Slice từ vị trí của đáy thấp nhất đến nến cuối cùng (bao gồm đáy)
    slice_value = recent_df.iloc[pos_value:]
    
    if len(slice_value) < 4:
        print(f"check_volume_trough_peak slice_value {len(slice_value)}: chưa đủ dữ liệu để xác định đỉnh đáy.")
        return None, None, None 
    
    # Tính khối lượng mua/bán nếu có cột 'volume'
    if 'volume' in slice_value.columns:
        buy_volume = slice_value[slice_value['close'] > slice_value['open']]['volume'].sum()
        sell_volume = slice_value[slice_value['close'] < slice_value['open']]['volume'].sum()
    # else:
    #     buy_volume = 0
    #     sell_volume = 0
    
    if buy_volume == 0:
        buy_volume = 1
        
    if sell_volume == 0:
        sell_volume = 1    
    
    return best_value, buy_volume, sell_volume


