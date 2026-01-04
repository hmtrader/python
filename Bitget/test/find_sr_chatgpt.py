import pandas as pd
import numpy as np
from scipy.signal import find_peaks

volume_factor = 1.5     # Hệ số xác định volume cao
min_gap_percent = 3.0   # khoảng cách tối thiểu giữa hai vùng (theo %)

# ====== TÍNH ATR (Average True Range) ======
def calculate_atr(df, period=14):
    high = df['high']
    low = df['low']
    close = df['close']
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

# ====== PHÁT HIỆN NẾN ĐẶC BIỆT ======
def detect_bullish_reversal(candle, avg_body, avg_vol):
    """Nến tăng mạnh hoặc rút râu bật lên với volume cao"""
    body = abs(candle['close'] - candle['open'])
    rng = candle['high'] - candle['low']
    lower_shadow = min(candle['open'], candle['close']) - candle['low']
    cond_volume = candle['volume'] > volume_factor * avg_vol
    # nến tăng mạnh
    cond_strong = (candle['close'] > candle['open']) and (body > 1.5 * avg_body)
    # nến rút râu bật mạnh
    cond_wick = (lower_shadow > body * 1.5) and (candle['close'] > candle['open'])
    return cond_volume and (cond_strong or cond_wick)

def detect_bearish_reversal(candle, avg_body, avg_vol):
    """Nến giảm mạnh hoặc rút râu phía trên với volume cao"""
    body = abs(candle['close'] - candle['open'])
    rng = candle['high'] - candle['low']
    upper_shadow = candle['high'] - max(candle['open'], candle['close'])
    cond_volume = candle['volume'] > volume_factor * avg_vol
    # nến giảm mạnh
    cond_strong = (candle['close'] < candle['open']) and (body > 1.5 * avg_body)
    # nến rút râu giảm
    cond_wick = (upper_shadow > body * 1.5) and (candle['close'] < candle['open'])
    return cond_volume and (cond_strong or cond_wick)

def find_local_extrema(df, window=3):
    """Tìm các đỉnh và đáy cục bộ."""
    if 'high' not in df.columns or 'low' not in df.columns:
        raise KeyError("DataFrame phải có cột 'high' và 'low'")
    high_series = df['high']
    low_series = df['low']
    peak_idx, _ = find_peaks(high_series, distance=window)
    trough_idx, _ = find_peaks(-low_series, distance=window)
    return high_series.iloc[peak_idx], low_series.iloc[trough_idx]

    # highs = df['high']
    # lows = df['low']
    # local_highs, local_lows = [], []
    # try:
    #     for i in range(window, len(df)-window):
    #         if highs.iloc[i] == max(highs[i-window:i+window+1]):
    #             local_highs.append((df['timestamp'][i], highs.iloc[i]))
    #         if lows.iloc[i] == min(lows[i-window:i+window+1]):
    #             local_lows.append((df['timestamp'][i], lows.iloc[i]))
    # except Exception as e:
    #     return e, None
                
    # return local_highs, local_lows

# ====== NHÓM MỨC GIÁ GẦN NHAU THÀNH VÙNG ======
def cluster_levels(levels: pd.Series, tol_percent: float = 0.5) -> list:
    if levels.empty:
        return []
    prices = np.sort(levels.values)
    clusters = []
    cur = [prices[0]]
    for p in prices[1:]:
        if (p - cur[-1]) / cur[-1] * 100 <= tol_percent:
            cur.append(p)
        else:
            clusters.append(np.mean(cur))
            cur = [p]
    clusters.append(np.mean(cur))
    return clusters


# ====== HÀM XÁC ĐỊNH KHOẢNG GẦN GIÁ (ADAPTIVE) ======
def adaptive_tolerance(lvl, atr_percent):
    """
    Tự động điều chỉnh vùng "gần giá" tùy theo loại coin:
    - Coin lớn: vùng hẹp (0.3% - 0.75%)
    - Coin nhỏ: vùng rộng hơn hoặc tối thiểu giá trị tuyệt đối
    """
    if lvl > 1000:
        tol = lvl * max(0.003, atr_percent)           # BTC, ETH
    elif lvl > 10:
        tol = lvl * max(0.0075, atr_percent * 1.2)    # mid-cap
    elif lvl > 1:
        tol = max(lvl * max(0.015, atr_percent * 1.5), 0.02)  # low-cap
    else:
        tol = max(lvl * max(0.03, atr_percent * 2), 0.01)     # penny coin
    return tol


# ==================== PHÂN TÍCH HỖ TRỢ / KHÁNG CỰ ====================
def find_support_resistance(df):
    avg_body = abs(df['close'] - df['open']).mean()
    avg_vol = df['volume'].mean()
    current_price = df['close'].iloc[-1]

    # === TÍNH ATR & xác định khoảng cách tối thiểu động ===
    atr = calculate_atr(df, 14).iloc[-1]
    atr_percent = (atr / current_price) * 100
    min_gap_percent = max(3.0, atr_percent * 1.2)

    # print(f"\n[ATR biến động] ATR% = {atr_percent:.2f} → min_gap_percent = {min_gap_percent:.2f}%")

    highs, lows = find_local_extrema(df, window=3)
    res_levels = cluster_levels(highs)
    # print("")
    sup_levels = cluster_levels(lows)
    # print("sup_levels:" , sup_levels)
     
    valid_supports = []
    for lvl in sup_levels:
        tol = adaptive_tolerance(lvl, atr_percent)
        near = df[(df['low'] >= lvl - tol) & (df['low'] <= lvl + tol)]
        if len(near) >= 2:
            valid_supports.append(lvl)
        elif len(near) > 0:
            idx = near.index[-1]
            candle = df.iloc[idx]
            if detect_bullish_reversal(candle, avg_body, avg_vol):
                valid_supports.append(lvl)

    valid_resists = []
    for lvl in res_levels:
        tol = adaptive_tolerance(lvl, atr_percent)
        near = df[(df['high'] >= lvl - tol) & (df['high'] <= lvl + tol)]
        if len(near) >= 2:
            valid_resists.append(lvl)
        elif len(near) > 0:
            idx = near.index[-1]
            candle = df.iloc[idx]
            if detect_bearish_reversal(candle, avg_body, avg_vol):
                valid_resists.append(lvl)
                 

    # Sắp xếp
    supports = sorted([s for s in valid_supports if s < current_price], reverse=True)
    resistances = sorted([r for r in valid_resists if r > current_price])
    # print("supports:" , supports)
    # === Hàm phụ: tìm vùng thứ hai bằng cách mở rộng dần khoảng cách ===
    def find_second_zone(zones, first, base_gap):
        if len(zones) < 2:
            return None
        gap = base_gap
        for attempt in range(3):  # tối đa mở rộng 3 lần
            for z in zones[1:]:
                if percent_diff(first, z) >= gap:
                    return z
            gap *= 1.5  # nới thêm 50% mỗi vòng
        return None

    # === Tìm hỗ trợ/kháng cự với auto-extend ===
    S1 = supports[0] if len(supports) > 0 else None
    S2 = find_second_zone(supports, S1, min_gap_percent) if S1 else None

    R1 = resistances[0] if len(resistances) > 0 else None
    R2 = find_second_zone(resistances, R1, min_gap_percent) if R1 else None

    return S1, S2, R1, R2, current_price, min_gap_percent

# ====== HÀM TÍNH TỈ LỆ % GIỮA CÁC VÙNG ======
def percent_diff(a, b):
    """Tính % chênh lệch giữa hai mức giá"""
    if not a or not b:
        return None
    return abs(a - b) / ((a + b) / 2) * 100