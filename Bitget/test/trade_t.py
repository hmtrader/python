import time

# import api
import find_sr_chatgpt as src
import config
import logic
import pandas as pd

def cal_tp_sl(price, pnl_tp, pnl_sl, side, multi):
    tp = 0.0
    sl = 0.0
    if side == 'long':
        sl = round(float(price * (1 - pnl_sl)), multi) 
        tp = round(float(price * (1 + pnl_tp)), multi) 
    else:
        sl = round(float(price * (1 + pnl_sl)), multi) 
        tp = round(float(price * (1 - pnl_tp)), multi)     
        
    return tp, sl    

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Function to get trend
def get_trend(ema9, ema21, rsi):
    if ema9 > ema21 and rsi > 50:
        return 'UP'
    elif ema9 < ema21 and rsi < 50:
        return 'DOWN'
    else:
        return 'SIDEWAY'

# def set_tp_sl(symbol, holdSide, tp_price, sl_price):
#     api.place_tpsl_order(symbol, "pos_profit", 0, holdSide, tp_price)
#     api.place_tpsl_order(symbol, "pos_loss", 0, holdSide, sl_price)
    

# def manage_open_positions(symbol='BTCUSDT'):
#     """Kiểm tra và quản lý các vị thế đang mở."""
#     try:
#         positions = api.get_all_position()
#         # print("positions:", positions)
#         for pos in positions:
#             if pos['symbol'] == symbol and float(pos['total']) != 0:
#                 # print("Vi the mo: ", pos)
#                 margin_size = float(pos.get('marginSize', 0))
#                 unrealized_pl = float(pos.get('unrealizedPL', 0))
#                 lev = float(pos.get('leverage', 0))
#                 entry_price = float(pos.get('openPriceAvg', 0))
#                 # print(f"margin_size: {margin_size} and unrealized_pl: {unrealized_pl}")
#                 pnl_ratio = (unrealized_pl / margin_size)*100 if margin_size > 0 else 0
#                 # print(f"pnl_ratio: {pnl_ratio} ")
#                 stopLossId = pos['stopLossId']
#                 stopLostPrice = float(pos.get('stopLoss', 0)) if pos.get('stopLoss', 0) not in (None, "", '0') else 0.0 
#                 pnl_sl = float(config.SL_TARGET_RATE / lev) 
#                 pnl_tp = float(config.TP_TARGET_RATE / lev) 
#                 if stopLostPrice == 0.0:
#                     tp_price, sl_price = cal_tp_sl(entry_price, pnl_tp, pnl_sl, pos['holdSide'], 2)
                            
#                     print(f"Chưa có TP và SL nên update lại thông tin: TP {tp_price} và SL {sl_price}")
#                     set_tp_sl(symbol, pos['holdSide'], tp_price, sl_price)
#                     # planType: Take profit and stop loss type
#                     # pos_profit: position take profit;
#                     # pos_loss: position stop loss
                    
                                    
#                 # print(f"entry_price: {entry_price} ")
#                 print(f"Đang có vị thế {pos['holdSide']}: PnL = {pnl_ratio:.2f}% - Stop loss: {stopLostPrice:.3f}")
                
#                 # Sắp xếp các quy tắc trailing stop từ cao đến thấp
#                 sorted_rules = sorted(config.TRAILING_STOP_RULES.items(), key=lambda item: item[0], reverse=True)
#                 # print("sorted_rules:" , sorted_rules)
#                 new_sl_price = None
#                 for target_pnl, sl_pnl in sorted_rules:
#                     if pnl_ratio > target_pnl*100:
#                         new_sl_price =  round(entry_price * ((1 + sl_pnl/lev) if pos['holdSide'] == 'long' else (1 - sl_pnl/lev)), 2)
#                         print("new_sl_price:" , new_sl_price)
#                         if (new_sl_price > stopLostPrice and pos['holdSide'] == 'long') or (new_sl_price < stopLostPrice and pos['holdSide'] == 'short'):
#                             print(f"PnL > {target_pnl*100}%. Cập nhật SL lên: {new_sl_price}")
#                             # ===> Thêm logic gọi API để cập nhật SL tại đây <===
#                             api.place_tpsl_order(symbol, "pos_loss", 0, pos['holdSide'], new_sl_price)
#                             # api.modify_tpsl_order(symbol=symbol, order_id=stopLossId, trigger_price=new_sl_price, trigger_type="mark_price", amount=0)
#                             return True # Đã xử lý, thoát hàm
                        
#                         break
                    
#                 print("Không update lại stoploss")
#                 return True    
        
#         return False # Không có vị thế
#     except Exception as e:
#         print(f"Lỗi khi quản lý vị thế: {e}")
#         return True


def execute_trade_logic(symbol="BTCUSDT", amount=0, leverage=20):
    """Thực thi logic giao dịch chính."""
    print("\n" + "="*50)
    print(f"Bắt đầu chu kỳ kiểm tra {symbol} lúc {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Load data from Excel
    file_path = 'btc_usdt_5m.csv'  # Change to your Excel file path
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])  # Assuming column 'datetime'
    df.set_index('timestamp', inplace=True)
    df = df[~df.index.duplicated(keep='first')]  # Remove duplicates if any

    # Filter from 1/1/2020 to current (assuming data up to now)
    start_date = pd.to_datetime('2024-05-01')
    end_date = pd.to_datetime('now')  # Or set to specific if needed
    df = df.loc[start_date:end_date]

    # Resample to 1h and 4h
    df_1h = df.resample('1h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    })
    df_1h['rsi'] = calculate_rsi(df_1h['close'])
    df_1h['ema9'] = df_1h['close'].ewm(span=9, adjust=False).mean()
    df_1h['ema21'] = df_1h['close'].ewm(span=21, adjust=False).mean()

    df_4h = df.resample('4h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    })
    df_4h['rsi'] = calculate_rsi(df_4h['close'])
    df_4h['ema9'] = df_4h['close'].ewm(span=9, adjust=False).mean()
    df_4h['ema21'] = df_4h['close'].ewm(span=21, adjust=False).mean()
    
    df_30m = df.resample('30min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    })
    df_30m['rsi'] = calculate_rsi(df_30m['close'])
    df_30m['ema9'] = df_30m['close'].ewm(span=9, adjust=False).mean()
    df_30m['ema21'] = df_30m['close'].ewm(span=21, adjust=False).mean()
    
    df_15m = df.resample('15min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    })
    df_15m['rsi'] = calculate_rsi(df_30m['close'])
    df_15m['ema9'] = df_30m['close'].ewm(span=9, adjust=False).mean()
    df_15m['ema21'] = df_30m['close'].ewm(span=21, adjust=False).mean()
    
    # print("4h")
    # print(df_4h.tail())
    # print("1h")
    # print(df_1h.tail())
    # print("30m")
    # print(df_30m.tail())
    
    # Backtest parameters
    initial_capital = 1000.0
    margin_per_trade = float(amount)
    leverage = float(leverage)
    position_size = (margin_per_trade) * (leverage)  # 100 USDT
    # take_profit_pnl = config.  # 200%
    # stop_loss_pnl = -1.0  # -100%
    # price_change_tp = take_profit_pnl / leverage  # 0.04
    # price_change_sl = stop_loss_pnl / leverage   # -0.02

    # Backtest
    capital = initial_capital
    trades = []
    position = None
    

    # 1. Kiểm tra vị thế đang mở
    # position = manage_open_positions(symbol)
    # if position:
    #     # print("Đã có vị thế đang mở. Bỏ qua tìm lệnh mới.")
    #     return

    # 2. Phân tích xu hướng đa khung
    # df_4h = api.get_klines_data(symbol, config.TIMEFRAME_TREND)
    # df_1h = api.get_klines_data(symbol, config.TIMEFRAME_CONFIRM)
    # df_15m = api.get_klines_data(symbol, config.TIMEFRAME_ENTRY)
    # df_30m = api.get_klines_data(symbol, config.TIMEFRAME_EMA)
    
    if df_4h is None or df_1h is None or df_15m is None or df_30m is None:
        print("Không thể lấy dữ liệu, bỏ qua chu kỳ này.")
        return
    df_e = df_30m
    for i in range(len(df_e)):
        current_time = df_e.index[i]
        current_open = df_e['open'].iloc[i]
        current_high = df_e['high'].iloc[i]
        current_low = df_e['low'].iloc[i]
        current_close = df_e['close'].iloc[i]
        
        current_price = df_e['close'].iloc[i]
        marginAmount = round(float(amount) * float(leverage) /float(current_price), 3)
        
        print(f"current_time: {current_time}")
        
        # print(df_15m.tail())
        
        
        if position is not None:
            # Check for exit
            # First, calculate current PNL based on close (for trailing decision)
            if position['direction'] == 'LONG':
                profit = (current_close - position['entry']) * (position_size / position['entry'])
            else:
                profit = (position['entry'] - current_close) * (position_size / position['entry'])
            # pnl_percent = (profit / margin_per_trade) * 100 / 100  # pnl in decimal, e.g., 1.0 for 100%

            # Sắp xếp các quy tắc trailing stop từ cao đến thấp
            # sorted_rules = sorted(config.TRAILING_STOP_RULES.items(), key=lambda item: item[0], reverse=True)
            # new_sl_price = None
            # for target_pnl, sl_pnl in sorted_rules:
            #     if pnl_percent > target_pnl*100:
            #         new_sl_price =  round(entry_price * ((1 + sl_pnl/leverage) if position['direction'] == 'LONG' else (1 - sl_pnl/leverage)), 2)
            #         print("new_sl_price:" , new_sl_price)
            #         if (new_sl_price > position['sl'] and position['direction'] == 'LONG') or (new_sl_price < position['sl'] and position['direction'] == 'SHORT'):
            #             position['sl'] = new_sl_price
                                            
            #         break
                    
            # # Update SL if conditions met
            # if position['direction'] == 'LONG':
            #     if pnl_percent > 2.0:
            #         new_sl = round(entry_price * ((1 + pnl_sl)), 2)
            #         position['sl'] = max(position['sl'], new_sl)  # Trail up
            #     elif pnl_percent > 1.0:
            #         new_sl = position['entry'] * (1 + trail_100_to_50 / leverage)
            #         position['sl'] = max(position['sl'], new_sl)
            # elif position['direction'] == 'SHORT':
            #     if pnl_percent > 2.0:
            #         new_sl = position['entry'] * (1 - trail_200_to_150 / leverage)  # For short, SL is above, trail down
            #         position['sl'] = min(position['sl'], new_sl)
            #     elif pnl_percent > 1.0:
            #         new_sl = position['entry'] * (1 - trail_100_to_50 / leverage)
            #         position['sl'] = min(position['sl'], new_sl)

            # Now, check for exit using high/low (assuming worst case within candle)
            # For simplicity, check if low <= sl or high >= tp for long, etc.
            if position['direction'] == 'LONG':
                if current_low <= position['sl']:
                    exit_price = max(current_open, position['sl'])  # Approximate hit at sl if low <= sl
                    if exit_price < position['sl']: exit_price = position['sl']
                    profit = (exit_price - position['entry']) * (position_size / position['entry'])
                    capital += profit
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': current_time,
                        'direction': 'LONG',
                        'entry_price': position['entry'],
                        'exit_price': exit_price,
                        'profit': profit,
                        'pnl_percent': (profit / margin_per_trade) * 100
                    })
                    position = None
                    continue  # Skip to next
                elif current_high >= position['tp']:
                    exit_price = min(current_open, position['tp']) if current_open > position['tp'] else position['tp']
                    profit = (exit_price - position['entry']) * (position_size / position['entry'])
                    capital += profit
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': current_time,
                        'direction': 'LONG',
                        'entry_price': position['entry'],
                        'exit_price': exit_price,
                        'profit': profit,
                        'pnl_percent': (profit / margin_per_trade) * 100
                    })
                    position = None
                    continue
            elif position['direction'] == 'SHORT':
                if current_high >= position['sl']:
                    exit_price = min(current_open, position['sl']) if current_open > position['sl'] else position['sl']
                    profit = (position['entry'] - exit_price) * (position_size / position['entry'])
                    capital += profit
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': current_time,
                        'direction': 'SHORT',
                        'entry_price': position['entry'],
                        'exit_price': exit_price,
                        'profit': profit,
                        'pnl_percent': (profit / margin_per_trade) * 100
                    })
                    position = None
                    continue
                elif current_low <= position['tp']:
                    exit_price = max(current_open, position['tp']) if current_open < position['tp'] else position['tp']
                    profit = (position['entry'] - exit_price) * (position_size / position['entry'])
                    capital += profit
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': current_time,
                        'direction': 'SHORT',
                        'entry_price': position['entry'],
                        'exit_price': exit_price,
                        'profit': profit,
                        'pnl_percent': (profit / margin_per_trade) * 100
                    })
                    position = None
                    continue

        if position is None and capital >= margin_per_trade:
            
            df_4h_up = df_4h.loc[:current_time]
            df_1h_up = df_1h.loc[:current_time]
            df_15m_up = df_15m.loc[:current_time]
            df_30m_up = df_30m.loc[:current_time]
            
            # # Thêm các chỉ báo kỹ thuật vào df
            # df_4h = logic.add_indicators(df_4h_up)
            # df_1h = logic.add_indicators(df_1h_up)
            # df_15m = logic.add_indicators(df_15m_up) 
            # df_30m = logic.add_indicators(df_30m_up) 
            # Xác định xu hướng
            trend_4h = get_trend(df_4h_up['ema9'].iloc[-1], df_4h_up['ema21'].iloc[-1], df_4h_up['rsi'].iloc[-1])
            trend_1h = get_trend(df_1h_up['ema9'].iloc[-1], df_1h_up['ema21'].iloc[-1], df_1h_up['rsi'].iloc[-1])
            trend_30m = get_trend(df_30m_up['ema9'].iloc[-1], df_30m_up['ema21'].iloc[-1], df_30m_up['rsi'].iloc[-1])
            overall_trend = None
            # print(f"Xu hướng 4H: {trend_4h} | Xu hướng 1H: {trend_1h} | Xu hướng 30M: {trend_30m}")
            if trend_4h == 'UP' and trend_1h == 'UP' and trend_30m == 'UP':
                overall_trend = 'UP'
                # print("Xu hướng: TĂNG - Ưu tiên LONG")
            elif trend_4h == 'DOWN' and trend_1h == 'DOWN' and trend_30m == 'DOWN':
                overall_trend = 'DOWN'
                # print("Xu hướng: GIẢM - Ưu tiên SHORT")
            else:
                # print("Xu hướng không rõ - CHỜ ĐỢI")
                continue
            
            # print("----Xác định vùng hỗ trợ và kháng cự trên khung 4h--------")
            s1, s2, r1, r2, _, _ = src.find_support_resistance(df_4h_up)
            
            
            atr_4h = 350 # logic.calculate_atr(df_4h_up)
            # print("atr_4h:", atr_4h)
            near_threshold = atr_4h * 0.75  # "Gần" là trong 0.5 ATR
            
            # Tính EMA9 trên 15M
            ema9_30m = df_30m_up.iloc[-1]["ema9"]
            
            # 4. Tìm điểm vào lệnh
            # Kịch bản 1: Xu hướng TĂNG được xác nhận
            # % Biến động giá = % Lời/Lỗ mong muốn / Đòn bẩy
            pnl_sl = float(config.SL_TARGET_RATE / leverage) 
            pnl_tp = float(config.TP_TARGET_RATE / leverage) 
        
            # Check signal
            try:
                
                entry_price = current_close
                
                if overall_trend == "UP":
                    print("=> Xu hướng TĂNG được xác nhận. Ưu tiên LONG.")
                    # print("Kiểm tra tín hiệu đảo chiều....")
                    is_reversal_down, high_price = logic.is_reversal_pattern(df_1h, direction=overall_trend)
                    if is_reversal_down:        #Kiem tra co tin hiệu đảo chiều trong giai đoạn giảm hay không?
                        # print("Reversal down signal on 1H detected.")
                        # Xác nhận ở 30m: tạo đỉnh, và nến giảm lớn hơn nến tăng
                        # Cách đơn giản: kiểm tra 30m có nến giảm lớn hơn nến tăng liền trước và tạo lower low then higher close
                        try:
                            last_30 = df_30m.iloc[-1]
                            prev_30 = df_30m.iloc[-2]
                            cond_30 = (last_30["close"] < last_30["open"]) and ((last_30["open"] - last_30["close"]) > abs(prev_30["close"] - prev_30["open"]))
                        except Exception:
                            cond_30 = False
                        
                        if cond_30:
                            # print("30m confirmation OK -> prepare SHORT (counter-trend).")
                            # SL = đáy cây nến/cụm nến 1H thấp hơn 5%
                            tp, sl = cal_tp_sl(current_price, pnl_tp, pnl_sl, 'short', 3)
                            print(f"Vào lệnh SHORT tại {current_price:.2f} (ngược xu hướng), size: {marginAmount} usdt; Stop-loss: {sl:.5f}; Take-profit: {tp:.5f}")
                            direction = 'SHORT'
                            # tp = entry_price * (1 + price_change_tp)
                            # sl = entry_price * (1 + price_change_sl)
                            position = {
                                'direction': direction,
                                'entry': entry_price,
                                'tp': tp,
                                'sl': sl,
                                'entry_time': current_time
                            }
                            continue
                        else:
                            print("Chờ xác nhận lại điểm vào lệnh SHORT.")
                            continue
                        
                    else:
                        print("Chưa có tín hiệu đảo chiều.")    
                        
                        
                    # =======================================================================================================
                    # Kiểm tra volume giao dich co thể tìm ra sự đảo chiều sớm của xu hướng
                    # Đang là xu hướng tăng nên sẽ tìm tín hiệu volume để SHORT
                    print("Kiểm tra tín hiệu volume giao dịch.")
                    peak, buy_volume, sell_volume = logic.check_volume_trough_peak(df_1h, 12, "peak")  #kiểm tra tại 12 cây nến gần nhất
                    if sell_volume / buy_volume > 1.5:      # Tổng lượng volume bán lớn gấp 1.5 lần volume mua nên lực bán đang mạnh xem xét tín hiệu SHORT
                        # print("Lực bán đang chiếm ưu thế nên tìm điểm vào lệnh SHORT.")
                        # Kiểm tra và xác nhận tạo đỉnh < đỉnh cao nhất
                        local_peak = logic.find_peak(df_30m, 1, 10)
                        # print(f"Đỉnh cao nhất: {peak}, đỉnh cục bộ: {local_peak}, và giá hiện tại là: {current_price}")
                        if local_peak < peak and current_price < local_trough:
                            tp, sl = cal_tp_sl(current_price, pnl_tp, pnl_sl, 'short', 2)
                            print(f"Vào lệnh SHORT Market tại {current_price:.2f} (ngược xu hướng), size: {marginAmount} usdt; Stop-loss: {sl:.5f}; Take-profit: {tp:.5f}")
                            
                            
                            direction = 'SHORT'
                            # tp = entry_price * (1 + price_change_tp)
                            # sl = entry_price * (1 + price_change_sl)
                            position = {
                                'direction': direction,
                                'entry': entry_price,
                                'tp': tp,
                                'sl': sl,
                                'entry_time': current_time
                            }
                            continue
                        else:
                            # print("Chưa thể SHORT. Chờ giá break qua đáy cục bộ")
                            continue
                    else:
                        print("Lực bán vẫn chiếm ưu thế nên chờ.")
                        
                    # =======================================================================================================        
                    # Điều kiện 1: Gần S1 hoặc S2     
                    print("Kiểm tra giá hồi về vùng kháng cự:")   
                    if s1 or s2:
                        for support in [s1, s2]:
                            if support and abs(current_price - support) <= near_threshold:
                                # print(f"Giá gần S{'1' if support == s1 else '2'} ({support:.2f})")
                                # Phân tích 15M
                                rsi_15m = df_15m.iloc[-1]['rsi']
                                if rsi_15m > 70:
                                    # print("RSI 15M >70 - CHỜ ĐỢI điều chỉnh")
                                    continue
                                # Kiểm tra có tạo đáy trên 15M thay vì tín hiệu bullish
                                # print("Kiểm tra khung 15m xem có tạo đỉnh chưa." )
                                if logic.is_trough(df_15m):
                                    entry = df_15m['close'].iloc[-1]  # Hoặc dùng exchange.fetch_ticker(symbol)['last'] cho market
                                    # sl = round(float(current_price * (1 - pnl_sl)), 3) 
                                    # tp = round(float(current_price * (1 + pnl_tp)), 3) 
                                    tp, sl = cal_tp_sl(current_price, pnl_tp, pnl_sl, 'long', 3)
                                    print(f"VÀO LONG MARKET tại {current_price:.2f} (tại EMA9 30m), size: {marginAmount} usdt; Stop-loss: {sl:.5f}; Take-profit: {tp:.5f}")
                                    direction = 'LONG'
                                    # tp = entry_price * (1 + price_change_tp)
                                    # sl = entry_price * (1 + price_change_sl)
                                    position = {
                                        'direction': direction,
                                        'entry': entry_price,
                                        'tp': tp,
                                        'sl': sl,
                                        'entry_time': current_time
                                    }
                                    continue
                                
                                if current_price < s2:
                                    continue
                                    # print("Giá phá S2 - CHỜ ĐỢI, đánh giá lại xu hướng")
                    
                    # Điều kiện 2: HOẶC gần EMA9 30M và nến tăng xác nhận
                    # print("Kiểm tra giá có gần EMA9 khung 30 phút hay không?")
                    # print("Kiểm tra giá có tạo đáy giữa đỉnh và EMA9 khung 30 phút hay không?")
                    local_trough = logic.find_trough(df_30m, 1, 5)
                    # print("Đáy cục bộ: ", local_trough)
                    if local_trough:
                        # print("Kiểm tra giá có nằm trong vùng EMA9 khung 30 phút hay không?")
                        if abs(current_price - ema9_30m) <= near_threshold:
                            # print(f"Giá hiện tại {current_price:.2f} gần EMA9 30m ({ema9_30m:.2f}) với biên độ {near_threshold}")
                            rsi_30m = df_30m.iloc[-1]['rsi']
                            if rsi_30m > 70:
                                # print("RSI 30M > 70 - Đang vào vùng quá mua - CHỜ ĐỢI điều chỉnh")
                                continue
                            
                            if df_30m['close'].iloc[-1] > df_30m['open'].iloc[-1] and current_price > local_trough:  # Nến tăng xác nhận và giá hiện tại phải lớn hơn đáy
                                
                                tp, sl = cal_tp_sl(current_price, pnl_tp, pnl_sl, 'long', 2)
                                print(f"VÀO LONG MARKET tại {current_price:.2f} (tại EMA9 30m), size: {marginAmount} usdt; Stop-loss: {sl:.5f}; Take-profit: {tp:.5f}")
                                
                                direction = 'LONG'
                                # tp = entry_price * (1 + price_change_tp)
                                # sl = entry_price * (1 + price_change_sl)
                                position = {
                                    'direction': direction,
                                    'entry': entry_price,
                                    'tp': tp,
                                    'sl': sl,
                                    'entry_time': current_time
                                }
                                continue
                            else:
                                # print(f"Chờ xác nhận nến tăng")
                                continue
                        else:
                            # print(f"Giá chưa nằm trong vùng EMA9 nên chờ. ")
                            continue
                    # else:
                    #     print(f"Chưa tạo đáy cục bộ nên chờ. ")   
                
                
                # Xet down trend
                elif overall_trend == 'DOWN':
                    # print("=> Xu hướng GIẢM được xác nhận. Ưu tiên SHORT. Tìm thời điểm để vào lệnh.")
                    # =======================================================================================================
                    # print("Kiểm tra tín hiệu đảo chiều....")
                    is_reversal_up, low_price = logic.is_reversal_pattern(df_1h, direction=overall_trend)
                    if is_reversal_up:        #Kiem tra co tin hiệu đảo chiều trong giai đoạn giảm hay không?
                        # print("Reversal signal on 1H detected.")
                        # Xác nhận ở 30m: tạo đáy, và nến tăng lớn hơn nến giảm
                        # Cách đơn giản: kiểm tra 30m có nến tăng lớn hơn nến giảm liền trước và tạo lower low then higher close
                        try:
                            last_30 = df_30m.iloc[-1]
                            prev_30 = df_30m.iloc[-2]
                            cond_30 = (last_30["close"] > last_30["open"]) and ((last_30["close"] - last_30["open"]) > abs(prev_30["close"] - prev_30["open"]))
                        except Exception:
                            cond_30 = False
                        
                        if cond_30:
                            # print("Tín hiệu 30m được xác nhận.")
                           
                            tp, sl = cal_tp_sl(current_price, pnl_tp, pnl_sl, 'long', 2)
                            print(f"Vào lệnh LONG Market tại {current_price:.2f} (ngược xu hướng), size: {marginAmount} usdt; Stop-loss: {sl:.5f}; Take-profit: {tp:.5f}")
                            direction = 'LONG'
                            # tp = entry_price * (1 + price_change_tp)
                            # sl = entry_price * (1 + price_change_sl)
                            position = {
                                'direction': direction,
                                'entry': entry_price,
                                'tp': tp,
                                'sl': sl,
                                'entry_time': current_time
                            }
                            continue
                        else:
                            # print("Chờ xác nhận lại điểm vào lệnh LONG.")
                            continue
                        
                    # else:
                    #     print("Chưa có tín hiệu đảo chiều.")    
                    
                    # =======================================================================================================
                    # Kiểm tra volume giao dich co thể tìm ra sự đảo chiều sớm của xu hướng
                    # Đang là xu hướng giảm nên sẽ tìm tín hiệu volume để LONG
                    # print("Kiểm tra tín hiệu volume giao dịch.")
                    trough, buy_volume, sell_volume = logic.check_volume_trough_peak(df_1h, 12, "trough")  #kiểm tra tại 10 cây nến gần nhất
                    if buy_volume / sell_volume > 1.5:      # Tổng lượng volume mua lớn gấp 1.5 lần volume bán nên lực mua đang mạnh xem xét tín hiệu LONG
                        # print("Lực mua đang chiếm ưu thế nên tìm điểm vào lệnh LONG.")
                        # Kiểm tra và xác nhận tạo đáy > đáy thấp nhất
                        local_trough = logic.find_trough(df_30m, 1, 10)
                        local_peak = logic.find_peak(df_30m, 1, 10)         #Tim đỉnh cục bộ để xác định tín hiệu LONG
                        # print(f"Đáy thấp nhất: {trough}, đáy cục bộ: {local_trough}, và giá hiện tại là: {current_price}, Đỉnh cục bộ: {local_peak}")
                        if local_trough > trough and current_price > local_peak:        # Break up qua đỉnh cục bộ sẽ vào lệnh long
                            tp, sl = cal_tp_sl(current_price, pnl_tp, pnl_sl, 'long', 2)
                            print(f"Vào lệnh LONG Market tại {current_price:.2f} (ngược xu hướng), size: {marginAmount} usdt; Stop-loss: {sl:.5f}; Take-profit: {tp:.5f}")
                            
                            direction = 'LONG'
                            # tp = entry_price * (1 + price_change_tp)
                            # sl = entry_price * (1 + price_change_sl)
                            position = {
                                'direction': direction,
                                'entry': entry_price,
                                'tp': tp,
                                'sl': sl,
                                'entry_time': current_time
                            }
                            continue
                        else:
                            # print(f"Chưa thể LONG. Chờ giá break qua đỉnh cục bộ {local_peak}")
                            continue
                    # else:
                    #     print("Lực bán vẫn chiếm ưu thế nên chờ.")
                    
                    
                    # =======================================================================================================
                    # Kiểm tra SHORT thuận (tại resistance trên 15M)
                    # Điều kiện 1: Gần S1 hoặc S2     
                    # print("Kiểm tra giá hồi về vùng kháng cự:")
                    if r1 or r2:
                        for resistance in [r1, r2]:
                            if resistance and abs(current_price - resistance) <= near_threshold:
                                # print(f"Giá gần R{'1' if resistance == r1 else '2'} ({resistance:.2f})")
                                rsi_15m = df_15m.iloc[-1]['rsi']
                                # print("rsi_15m:" , rsi_15m )
                                if rsi_15m < 30:
                                    # print("RSI 15M <30 - CHỜ ĐỢI điều chỉnh")
                                    continue
                                
                                # print("Kiểm tra khung 15m xem có tạo đỉnh chưa." )
                                if logic.is_peak(df_15m):
                                    # print("Đã tạo đỉnh nên sẽ vào lệnh." )
                                    
                                    tp, sl = cal_tp_sl(current_price, pnl_tp, pnl_sl, 'short', 2)
                                    print(f"VÀO SHORT MARKET tại {current_price:.2f}, size: {marginAmount} usdt; Stop-loss: {sl:.5f}; Take-profit: {tp:.5f}")
                                    
                                    direction = 'SHORT'
                                    # tp = entry_price * (1 + price_change_tp)
                                    # sl = entry_price * (1 + price_change_sl)
                                    position = {
                                        'direction': direction,
                                        'entry': entry_price,
                                        'tp': tp,
                                        'sl': sl,
                                        'entry_time': current_time
                                    } 
                                    continue
                                # else:
                                #     # print("Khung 15m chưa tạo đỉnh. Waiting...." )
                                #     continue
                                    

                                if current_price > r2:
                                    # print("Giá phá R2 - CHỜ ĐỢI, đánh giá lại xu hướng")
                                    continue
                            
                            # else:
                            #     print(f"Giá chưa nằm trong vùng R{'1' if resistance == r1 else '2'} nên tiếp tục đợi")
                    
                    
                    # =======================================================================================================
                    # Điều kiện 2: HOẶC gần EMA9 15M và nến giảm xác nhận
                    # print("Kiểm tra giá có gần EMA9 khung 30 phút hay không?")
                    # print("Kiểm tra giá có tạo đỉnh giữa đáy và EMA9 khung 30 phút hay không?")
                    local_peak = logic.find_peak(df_30m, 1, 5)
                    # print(f"Đỉnh cục bộ: {local_peak}, Đáy thấp nhất: {trough}")
                    if local_peak:
                        # print("Kiểm tra giá có gần EMA9 khung 30 phút hay không?")
                        if abs(current_price - ema9_30m) <= near_threshold:
                            # print(f"Giá hiện tại {current_price:.2f} gần EMA9 30m ({ema9_30m:.2f}) với biên độ {near_threshold}")
                            rsi_30m = df_30m.iloc[-1]['rsi']
                            if rsi_30m < 30:
                                # print("RSI 30M < 30 - Đang vào vùng quá bán - CHỜ ĐỢI điều chỉnh")
                                continue
                            # print("Close:", df_30m['close'].iloc[-1])
                            # print("open:", df_30m['open'].iloc[-1])
                            
                            if df_30m['close'].iloc[-1] < df_30m['open'].iloc[-1] and current_price < trough:  # Nến giảm xác nhận, giá phải break xuống đáy thấp nhất
                                # entry = df_15m['Close'].iloc[-1]
                                # sl = round(r1 if r1 else float(current_price * (1 + pnl_sl)), 3)
                                # tp = round(float(current_price * (1 - pnl_tp)), 3) 
                                tp, sl = cal_tp_sl(current_price, pnl_tp, pnl_sl, 'short', 2)
                                print(f"VÀO SHORT MARKET tại {current_price:.2f} (tại EMA9 30m), size: {marginAmount} usdt; Stop-loss: {sl:.5f}; Take-profit: {tp:.5f}")
                                # print(f"SL: {sl:.2f}")
                                # print(f"TP: {tp:.2f}")
                                direction = 'SHORT'
                                # tp = entry_price * (1 + price_change_tp)
                                # sl = entry_price * (1 + price_change_sl)
                                position = {
                                    'direction': direction,
                                    'entry': entry_price,
                                    'tp': tp,
                                    'sl': sl,
                                    'entry_time': current_time
                                }     
                                continue
                            else:
                                # print(f"Chờ xác nhận nến giảm hoặc break qua đáy thấp nhất {trough}.")
                                continue
                        else:
                            print(f"Không gần EMA9 nên chờ tiếp")
                    else:
                        print(f"Chưa tạo đỉnh tại EMA9 30m nên CHỜ.")        
                            
                # else:
                #     print("Xu hướng không đồng thuận hoặc không rõ ràng. CHỜ ĐỢI.")
                
            except IndexError:
                pass

    # If still in position at end, close at last close
    # Ngày cuối cùng
    if position is not None:
        exit_price = df['close'].iloc[-1]
        if position['direction'] == 'LONG':
            profit = (exit_price - position['entry']) * (position_size / position['entry'])
        else:
            profit = (position['entry'] - exit_price) * (position_size / position['entry'])
        capital += profit
        trades.append({
            'entry_time': position['entry_time'],
            'exit_time': df.index[-1],
            'direction': position['direction'],
            'entry_price': position['entry'],
            'exit_price': exit_price,
            'profit': profit,
            'pnl_percent': (profit / margin_per_trade) * 100
        })

    # Summary
    print("Trades Summary:")
    for trade in trades:
        print(f"Entry: {trade['entry_time']}, Direction: {trade['direction']}, Entry Price: {trade['entry_price']}, Exit: {trade['exit_time']}, Exit Price: {trade['exit_price']}, Profit: {trade['profit']:.2f} USDT, PNL: {trade['pnl_percent']:.2f}%")

    total_profit = capital - initial_capital
    print(f"\nTotal Trades: {len(trades)}")
    print(f"Final Capital: {capital:.2f} USDT")
    print(f"Total Profit/Loss: {total_profit:.2f} USDT")
    
    
    
    
    
            
    


