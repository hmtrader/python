#ChatGPT

import ccxt
import pandas as pd
import numpy as np

# ==================== CẤU HÌNH ====================
symbol = "BTC/USDT"     # Cặp giao dịch
timeframe = "4h"        # Khung 4 giờ
limit = 500             # Số nến lấy về
volume_factor = 1.5     # Hệ số xác định volume cao
exchange = ccxt.bitget()

# ==================== HÀM TIỆN ÍCH ====================
def fetch_ohlcv(symbol, timeframe="4h", limit=500):
    """Lấy dữ liệu OHLCV từ sàn."""
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp','open','high','low','close','volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def detect_strong_bullish(df):
    """Phát hiện nến tăng mạnh kèm volume cao."""
    df = df.copy()
    df['body'] = abs(df['close'] - df['open'])
    df['range'] = df['high'] - df['low']
    avg_body = df['body'].mean()
    avg_vol = df['volume'].mean()
    c = df.iloc[-1]
    cond_body = c['body'] > 1.5 * avg_body
    cond_pos = c['close'] > c['low'] + 0.7 * c['range']
    cond_vol = c['volume'] > volume_factor * avg_vol
    return (c['close'] > c['open']) and cond_body and cond_pos and cond_vol

def detect_strong_bearish(df):
    """Phát hiện nến giảm mạnh kèm volume cao."""
    df = df.copy()
    df['body'] = abs(df['close'] - df['open'])
    df['range'] = df['high'] - df['low']
    avg_body = df['body'].mean()
    avg_vol = df['volume'].mean()
    c = df.iloc[-1]
    cond_body = c['body'] > 1.5 * avg_body
    cond_pos = c['close'] < c['high'] - 0.7 * c['range']
    cond_vol = c['volume'] > volume_factor * avg_vol
    return (c['close'] < c['open']) and cond_body and cond_pos and cond_vol

def find_local_extrema(df, window=3):
    """Tìm các đỉnh và đáy cục bộ."""
    highs = df['high']
    lows = df['low']
    local_highs, local_lows = [], []
    for i in range(window, len(df)-window):
        if highs[i] == max(highs[i-window:i+window+1]):
            local_highs.append((df['timestamp'][i], highs[i]))
        if lows[i] == min(lows[i-window:i+window+1]):
            local_lows.append((df['timestamp'][i], lows[i]))
    return local_highs, local_lows

def cluster_levels(levels, threshold_percent=1.0):
    """Nhóm các mức giá gần nhau thành vùng."""
    if not levels:
        return []
    levels = sorted([p for t, p in levels])
    clusters = [[levels[0]]]
    for price in levels[1:]:
        if abs(price - np.mean(clusters[-1])) / price * 100 < threshold_percent:
            clusters[-1].append(price)
        else:
            clusters.append([price])
    return [np.mean(c) for c in clusters]

# ==================== PHÂN TÍCH HỖ TRỢ / KHÁNG CỰ ====================
def find_support_resistance(df):
    highs, lows = find_local_extrema(df, window=3)
    res_levels = cluster_levels(highs)
    sup_levels = cluster_levels(lows)

    current_price = df['close'].iloc[-1]
    avg_vol = df['volume'].mean()

    valid_supports = []
    for lvl in sup_levels:
        near = df[(df['low'] < lvl * 1.005) & (df['low'] > lvl * 0.995)]
        # Điều kiện: ít nhất 2 đáy rõ ràng hoặc nến bật mạnh với volume cao
        if len(near) >= 2:
            valid_supports.append(lvl)
        elif len(near) > 0:
            idx = near.index[-1]
            sub_df = df.loc[max(0, idx-3):idx]
            if detect_strong_bullish(sub_df):
                valid_supports.append(lvl)

    valid_resists = []
    for lvl in res_levels:
        near = df[(df['high'] > lvl * 0.995) & (df['high'] < lvl * 1.005)]
        if len(near) >= 2:
            valid_resists.append(lvl)
        elif len(near) > 0:
            idx = near.index[-1]
            sub_df = df.loc[max(0, idx-3):idx]
            if detect_strong_bearish(sub_df):
                valid_resists.append(lvl)

    supports = sorted([s for s in valid_supports if s < current_price], reverse=True)[:2]
    resistances = sorted([r for r in valid_resists if r > current_price])[:2]

    S1 = supports[0] if len(supports) > 0 else None
    S2 = supports[1] if len(supports) > 1 else None
    R1 = resistances[0] if len(resistances) > 0 else None
    R2 = resistances[1] if len(resistances) > 1 else None

    return S1, S2, R1, R2

# ==================== CHẠY CHƯƠNG TRÌNH ====================
if __name__ == "__main__":
    df = fetch_ohlcv(symbol, timeframe, limit)
    S1, S2, R1, R2 = find_support_resistance(df)
    last_price = df['close'].iloc[-1]

    print(f"\n=== KẾT QUẢ PHÂN TÍCH 4H ({symbol}) ===")
    print(f"Giá hiện tại: {last_price:.2f}")
    print(f"Hỗ trợ 1 (gần nhất): {S1}")
    print(f"Hỗ trợ 2 (sâu hơn): {S2}")
    print(f"Kháng cự 1 (gần nhất): {R1}")
    print(f"Kháng cự 2 (xa hơn): {R2}")
