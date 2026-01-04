import time

import api
import find_sr as src
import config
import logic
import function as fc
import notifier as nt

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

def set_tp_sl(symbol, holdSide, tp_price, sl_price):
    api.place_tpsl_order(symbol, "pos_profit", 0, holdSide, tp_price)
    api.place_tpsl_order(symbol, "pos_loss", 0, holdSide, sl_price)
    

def manage_open_positions(symbol='BTCUSDT'):
    """Kiểm tra và quản lý các vị thế đang mở."""
    try:
        positions = api.get_all_position()
        # fc.write_log("positions:", positions)
        for pos in positions:
            if pos['symbol'] == symbol and float(pos['total']) != 0:
                # fc.write_log("Vi the mo: ", pos)
                margin_size = float(pos.get('marginSize', 0))
                unrealized_pl = float(pos.get('unrealizedPL', 0))
                lev = float(pos.get('leverage', 0))
                entry_price = float(pos.get('openPriceAvg', 0))
                # fc.write_log(f"margin_size: {margin_size} and unrealized_pl: {unrealized_pl}")
                pnl_ratio = (unrealized_pl / margin_size)*100 if margin_size > 0 else 0
                # fc.write_log(f"pnl_ratio: {pnl_ratio} ")
                stopLossId = pos['stopLossId']
                stopLostPrice = float(pos.get('stopLoss', 0)) if pos.get('stopLoss', 0) not in (None, "", '0') else 0.0 
                pnl_sl = float(config.SL_TARGET_RATE / lev) 
                pnl_tp = float(config.TP_TARGET_RATE / lev) 
                if stopLostPrice == 0.0:
                    tp_price, sl_price = cal_tp_sl(entry_price, pnl_tp, pnl_sl, pos['holdSide'], 2)
                            
                    fc.write_log(f"Chưa có TP và SL nên update lại thông tin: TP {tp_price} và SL {sl_price}")
                    set_tp_sl(symbol, pos['holdSide'], tp_price, sl_price)
                    # planType: Take profit and stop loss type
                    # pos_profit: position take profit;
                    # pos_loss: position stop loss
                    
                                    
                # fc.write_log(f"entry_price: {entry_price} ")
                fc.write_log(f"Đang có vị thế {pos['holdSide']}: PnL = {pnl_ratio:.2f}% - Stop loss: {stopLostPrice:.3f}")
                
                # Sắp xếp các quy tắc trailing stop từ cao đến thấp
                sorted_rules = sorted(config.TRAILING_STOP_RULES.items(), key=lambda item: item[0], reverse=True)
                # fc.write_log("sorted_rules:" , sorted_rules)
                new_sl_price = 0.0
                for target_pnl, sl_pnl in sorted_rules:
                    if pnl_ratio > target_pnl*100:
                        new_sl_price =  round(entry_price * ((1 + sl_pnl/lev) if pos['holdSide'] == 'long' else (1 - sl_pnl/lev)), 2)
                        fc.write_log(f"new_sl_price: {new_sl_price}")
                        if (new_sl_price > stopLostPrice and pos['holdSide'] == 'long') or (new_sl_price < stopLostPrice and pos['holdSide'] == 'short'):
                            fc.write_log(f"PnL > {target_pnl*100}%. Cập nhật SL lên: {new_sl_price}")
                            # ===> Thêm logic gọi API để cập nhật SL tại đây <===
                            api.place_tpsl_order(symbol, "pos_loss", 0, pos['holdSide'], new_sl_price)
                            # api.modify_tpsl_order(symbol=symbol, order_id=stopLossId, trigger_price=new_sl_price, trigger_type="mark_price", amount=0)
                            return True # Đã xử lý, thoát hàm
                        
                        break
                    
                fc.write_log("Không update lại stoploss")
                return True    
        
        return False # Không có vị thế
    except Exception as e:
        fc.write_log(f"Lỗi khi quản lý vị thế: {e}")
        return True


def execute_trade_logic(symbol, amount, leverage):
    """Thực thi logic giao dịch chính."""
    fc.write_log("\n" + "="*50)
    fc.write_log(f"Bắt đầu chu kỳ kiểm tra {symbol} lúc {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. Kiểm tra vị thế đang mở
    is_position_open = manage_open_positions(symbol)
    if is_position_open:
        # print("Đã có vị thế đang mở. Bỏ qua tìm lệnh mới.")
        return

    # 2. Phân tích xu hướng đa khung
    df_4h = api.get_klines_data(symbol, config.TIMEFRAME_TREND)
    df_1h = api.get_klines_data(symbol, config.TIMEFRAME_CONFIRM)
    df_15m = api.get_klines_data(symbol, config.TIMEFRAME_ENTRY)
    df_30m = api.get_klines_data(symbol, config.TIMEFRAME_EMA)
    
    if df_4h is None or df_1h is None or df_15m is None or df_30m is None:
        print("Không thể lấy dữ liệu, bỏ qua chu kỳ này.")
        return

    df_4h = logic.add_indicators(df_4h)
    df_1h = logic.add_indicators(df_1h)
    df_15m = logic.add_indicators(df_15m) 
    df_30m = logic.add_indicators(df_30m) 
    # print(df_15m.tail())
    
    trend_4h = logic.analyze_trend(df_4h)
    trend_1h = logic.analyze_trend(df_1h)
    trend_30m = logic.analyze_trend(df_30m)
    overall_trend = None
    fc.write_log(f"Xu hướng 4H: {trend_4h} | Xu hướng 1H: {trend_1h} | Xu hướng 30M: {trend_30m}")
    if trend_4h == 'UP' and trend_1h == 'UP' and trend_30m == 'UP':
        overall_trend = 'UP'
        fc.write_log("Xu hướng: TĂNG - Ưu tiên LONG")
    elif trend_4h == 'DOWN' and trend_1h == 'DOWN' and trend_30m == 'DOWN':
        overall_trend = 'DOWN'
        fc.write_log("Xu hướng: GIẢM - Ưu tiên SHORT")
    else:
        fc.write_log("Xu hướng không rõ - CHỜ ĐỢI")
        return

    # 3. Xác định vùng Hỗ trợ/Kháng cự trên khung 4H
    fc.write_log("----Xác định vùng hỗ trợ và kháng cự trên khung 4h--------")
    s1, s2, r1, r2, _, _ = src.find_support_resistance(df_4h)
    
    fc.write_log(f"Hỗ trợ 1 (gần nhất): {s1}")
    # fc.write_log(f"Hỗ trợ 2 (sâu hơn): {s2}")
    fc.write_log(f"Kháng cự 1 (gần nhất): {r1}")
    # fc.write_log(f"Kháng cự 2 (xa hơn): {r2}")
    
       
    # current_price = df_1h.iloc[-1]['close']
    current_price = api.get_ticker(symbol)
    # fc.write_log(f"Giá hiện tại: {current_price:.2f}")
    
    atr_4h = logic.calculate_atr(df_4h)
    
    # Chinh lai atr doi với những đồng có biên độ quá lớn
    if current_price > 10000:
        atr_4h = atr_4h/4
    elif current_price > 2000:    
        atr_4h = atr_4h/2
        
    fc.write_log(f"atr_4h: {atr_4h}")    
    near_threshold = atr_4h * 0.5  # "Gần" là trong 0.5 ATR
    
    
    # Tính EMA9 trên 15M
    ema9_1h = df_1h.iloc[-1]["EMA_9"]
    
    # 4. Tìm điểm vào lệnh
    # Kịch bản 1: Xu hướng TĂNG được xác nhận
    # % Biến động giá = % Lời/Lỗ mong muốn / Đòn bẩy
    pnl_sl = float(config.SL_TARGET_RATE / leverage) 
    pnl_tp = float(config.TP_TARGET_RATE / leverage) 
    marginAmount = round(float(amount * leverage /current_price), 3)
    if overall_trend == "UP":
        fc.write_log("=> Xu hướng TĂNG được xác nhận. Ưu tiên LONG.")
        fc.write_log("Kiểm tra tín hiệu đảo chiều....")
        is_reversal_down, high_price = logic.is_reversal_pattern(df_1h, direction=overall_trend)
        if is_reversal_down:        #Kiem tra co tin hiệu đảo chiều trong giai đoạn giảm hay không?
            fc.write_log("Reversal down signal on 1H detected.")
            # Xác nhận ở 30m: tạo đỉnh, và nến giảm lớn hơn nến tăng
            # Cách đơn giản: kiểm tra 30m có nến giảm lớn hơn nến tăng liền trước và tạo lower low then higher close
            try:
                last_30 = df_30m.iloc[-1]
                prev_30 = df_30m.iloc[-2]
                cond_30 = (last_30["close"] < last_30["open"]) and ((last_30["open"] - last_30["close"]) > abs(prev_30["close"] - prev_30["open"]))
            except Exception:
                cond_30 = False
            
            if cond_30:
                fc.write_log("30m confirmation OK -> prepare SHORT (counter-trend).")
                # SL = đáy cây nến/cụm nến 1H thấp hơn 5%
                tp, sl = cal_tp_sl(current_price, pnl_tp, pnl_sl, 'short', 3)
                fc.write_log(f"Vào lệnh SHORT tại {current_price:.2f} (ngược xu hướng), size: {marginAmount} usdt; Stop-loss: {sl:.5f}; Take-profit: {tp:.5f}")
                # fc.write_log(f"SL: {sl:.2f}")
                # fc.write_log(f"TP: {tp:.2f}")
                
                api.change_leverage(symbol=symbol, leverage=leverage, holdSide='short')
                fc.write_log(f"Set leverage {symbol} leverage= x{leverage} for side=SHORT.")
                clientOid, orderId = api.place_future_order(symbol=symbol, amount=marginAmount, side='sell', orderType='market', tradeSide='open')
                if clientOid:
                    fc.write_log(f"Place order successful. ClientOid: {clientOid} and order Id: {orderId}") 
                    fc.write_log(f"Setup TP và SL tại: TP {tp} và SL {sl}")
                    set_tp_sl(symbol, 'short', tp, sl)
                    # api.modify_plan_order(orderId=orderId, clientOid=clientOid,symbol=symbol, tp_price=tp, sl_price=sl, trigger_type="mark_price")
                else:
                    fc.write_log(f"Place order fail. {orderId}")     
                return
            else:
                fc.write_log("30m confirmation failed; skip LONG.")
                return
            
        else:
            fc.write_log("Chưa có tín hiệu đảo chiều.")    
            
         
        # =======================================================================================================
        # Kiểm tra volume giao dich co thể tìm ra sự đảo chiều sớm của xu hướng
        # Đang là xu hướng tăng nên sẽ tìm tín hiệu volume để SHORT
        fc.write_log("Kiểm tra tín hiệu volume giao dịch.")
        peak, buy_volume, sell_volume = logic.check_volume_trough_peak(df_1h, 12, "peak")  #kiểm tra tại 12 cây nến gần nhất
        if peak and sell_volume / buy_volume > 2:      # Tổng lượng volume bán lớn gấp 1.5 lần volume mua nên lực bán đang mạnh xem xét tín hiệu SHORT
            fc.write_log("Lực bán đang chiếm ưu thế nên tìm điểm vào lệnh SHORT.")
            # Kiểm tra và xác nhận tạo đỉnh < đỉnh cao nhất
            # Kiểm tra và xác nhận tạo đáy > đáy thấp nhất
            local_trough = logic.find_trough(df_30m, 1, 10)     #Tim đáy cục bộ để xác định tín hiệu SHORT
            local_peak = logic.find_peak(df_30m, 1, 10)         
            fc.write_log(f"Đỉnh cao nhất: {peak}, đỉnh cục bộ: {local_peak}, và giá hiện tại là: {current_price}")
            if local_peak < peak and current_price < local_trough:
                tp, sl = cal_tp_sl(current_price, pnl_tp, pnl_sl, 'short', 2)
                fc.write_log(f"Vào lệnh SHORT Market tại {current_price:.2f} (ngược xu hướng), size: {marginAmount} usdt; Stop-loss: {sl:.5f}; Take-profit: {tp:.5f}")
                
                api.change_leverage(symbol=symbol, leverage=leverage, holdSide='short')
                fc.write_log(f"Set leverage {symbol}  leverage=x{leverage} for side=SHORT.")
                clientOid, orderId = api.place_future_order(symbol=symbol, amount=marginAmount, side='sell', orderType='market', tradeSide='open')
                if clientOid:
                    fc.write_log(f"Place order successful. ClientOid: {clientOid} and order Id: {orderId}") 
                    # fc.write_log(f"Setup TP và SL tại: TP {tp} và SL {sl}")
                    set_tp_sl(symbol, 'short', tp, sl)
                    # api.modify_plan_order(orderId=orderId, clientOid=clientOid,symbol=symbol, tp_price=tp, sl_price=sl, trigger_type="mark_price")
                else:
                    fc.write_log(f"Place order fail. {orderId}")     
                return
            else:
                fc.write_log(f"Chưa thể SHORT. Chờ giá break qua đáy cục bộ {local_trough}")
                return
        else:
            fc.write_log("Lực mua vẫn chiếm ưu thế nên chờ.")
            
        # =======================================================================================================        
        # Điều kiện 1: Gần S1 hoặc S2     
        fc.write_log(f"Kiểm tra giá hồi về vùng hỗ trợ {s1} và {s2}:")   
        if s1 or s2:
            for support in [s1, s2]:
                if support and abs(current_price - support) <= near_threshold:
                    fc.write_log(f"Giá gần S{'1' if support == s1 else '2'} ({support:.2f})")
                    # Phân tích 15M
                    rsi_30m = df_30m.iloc[-1]['RSI_14']
                    if rsi_30m > 70:
                        fc.write_log("RSI 30M >70 - CHỜ ĐỢI điều chỉnh")
                        continue
                    # Kiểm tra có tạo đáy trên 30M thay vì tín hiệu bullish
                    fc.write_log("Kiểm tra khung 30m xem có tạo đáy cục bộ chưa." )
                    if logic.is_trough(df_30m):
                        entry = df_15m['close'].iloc[-1]  # Hoặc dùng exchange.fetch_ticker(symbol)['last'] cho market
                        # sl = round(float(current_price * (1 - pnl_sl)), 3) 
                        # tp = round(float(current_price * (1 + pnl_tp)), 3) 
                        tp, sl = cal_tp_sl(current_price, pnl_tp, pnl_sl, 'long', 3)
                        fc.write_log(f"VÀO LONG MARKET tại {current_price:.2f} (tại EMA9 30m), size: {marginAmount} usdt; Stop-loss: {sl:.5f}; Take-profit: {tp:.5f}")
                        # fc.write_log(f"SL: {sl:.5f}")
                        # fc.write_log(f"TP: {tp:.5f}")
                        api.change_leverage(symbol=symbol, leverage=leverage, holdSide='long')
                        fc.write_log(f"Set leverage {symbol} leverage= x{leverage} for side=LONG.")
                        clientOid, orderId = api.place_future_order(symbol=symbol, amount=marginAmount, side='buy', orderType='market', tradeSide='open')
                        if clientOid:
                            fc.write_log(f"Place order successful. ClientOid: {clientOid} and order Id: {orderId}") 
                            # fc.write_log(f"Setup TP và SL tại: TP {tp} và SL {sl}")
                            set_tp_sl(symbol, 'long', tp, sl)
                            # api.modify_plan_order(orderId=orderId, clientOid=clientOid,symbol=symbol, tp_price=tp, sl_price=sl, trigger_type="mark_price")
                        else:
                            fc.write_log(f"Place order fail. {orderId}")     
                        return
                    else:
                        fc.write_log("Khung 30m chưa tạo đáy cục bộ. Waiting...." )
                        
                    if current_price < s2:
                        fc.write_log("Giá phá S2 - CHỜ ĐỢI, đánh giá lại xu hướng")
                else:
                    fc.write_log(f"Giá hiện tại {current_price} với near_threshold {near_threshold} chưa gần với vùng support {support}")        
                        
        # =======================================================================================================
        # # Tạm thời không xet điều kiện này nữa vì risk quá nhiều
        # # Điều kiện 2: HOẶC gần EMA9 1h và nến tăng xác nhận
        # # fc.write_log("Kiểm tra giá có gần EMA9 khung 1h hay không?")
        # fc.write_log("Kiểm tra giá có tạo đáy giữa đỉnh và EMA9 khung 1h hay không?")
        # local_trough = logic.find_trough(df_1h, 1, 5)
        # fc.write_log("Đáy cục bộ: ", local_trough)
        # if local_trough:
        #     fc.write_log("Kiểm tra giá có nằm trong vùng EMA9 khung 1h hay không?")
        #     if abs(current_price - ema9_1h) <= near_threshold:
        #         fc.write_log(f"Giá hiện tại {current_price:.2f} gần EMA9 1h ({ema9_1h:.2f}) với biên độ {near_threshold}")
        #         rsi_1h = df_1h.iloc[-1]['RSI_14']
        #         if rsi_1h > 70:
        #             fc.write_log("RSI 1h > 70 - Đang vào vùng quá mua - CHỜ ĐỢI điều chỉnh")
        #             return
                
        #         if df_1h['close'].iloc[-1] > df_1h['open'].iloc[-1] and df_1h['close'].iloc[-1] > ema9_1h and current_price > local_trough:  # Nến tăng xác nhận và giá hiện tại phải lớn hơn đáy
                    
        #             tp, sl = cal_tp_sl(current_price, pnl_tp, pnl_sl, 'long', 2)
        #             fc.write_log(f"VÀO LONG MARKET tại {current_price:.2f} (tại EMA9 1h), size: {marginAmount} usdt; Stop-loss: {sl:.5f}; Take-profit: {tp:.5f}")
        #             # fc.write_log(f"SL: {sl:.5f}")
        #             # fc.write_log(f"TP: {tp:.5f}")
        #             api.change_leverage(symbol=symbol, leverage=leverage, holdSide='long')
        #             fc.write_log(f"Set leverage {symbol}  leverage=x{leverage} for side=LONG.")
        #             clientOid, orderId = api.place_future_order(symbol=symbol, amount=marginAmount, side='buy', orderType='market', tradeSide='open')
        #             if clientOid:
        #                 fc.write_log(f"Place order successful. ClientOid: {clientOid} and order Id: {orderId}") 
        #                 # fc.write_log(f"Setup TP và SL tại: TP {tp} và SL {sl}")
        #                 set_tp_sl(symbol, 'long', tp, sl)
        #                 # api.modify_plan_order(orderId=orderId, clientOid=clientOid,symbol=symbol, tp_price=tp, sl_price=sl, trigger_type="mark_price")
        #             else:
        #                 fc.write_log(f"Place order fail. {orderId}")     
        #             return
        #         else:
        #             fc.write_log(f"Chờ xác nhận nến tăng")
        #     else:
        #         fc.write_log(f"Giá chưa nằm trong vùng EMA9 nên chờ. ")
        # else:
        #     fc.write_log(f"Chưa tạo đáy cục bộ nên chờ. ")   
            
    # Xet down trend
    elif overall_trend == 'DOWN':
        fc.write_log("=> Xu hướng GIẢM được xác nhận. Ưu tiên SHORT. Tìm thời điểm để vào lệnh.")
        # =======================================================================================================
        fc.write_log("Kiểm tra tín hiệu đảo chiều....")
        is_reversal_up, low_price = logic.is_reversal_pattern(df_1h, direction=overall_trend)
        if is_reversal_up:        #Kiem tra co tin hiệu đảo chiều trong giai đoạn giảm hay không?
            fc.write_log("Reversal signal on 1H detected.")
            # Xác nhận ở 30m: tạo đáy, và nến tăng lớn hơn nến giảm
            # Cách đơn giản: kiểm tra 30m có nến tăng lớn hơn nến giảm liền trước và tạo lower low then higher close
            try:
                last_30 = df_30m.iloc[-1]
                prev_30 = df_30m.iloc[-2]
                cond_30 = (last_30["close"] > last_30["open"]) and ((last_30["close"] - last_30["open"]) > abs(prev_30["close"] - prev_30["open"]))
            except Exception:
                cond_30 = False
            
            if cond_30:
                fc.write_log("30m confirmation OK -> prepare LONG (counter-trend).")
                # SL = đáy cây nến/cụm nến 1H thấp hơn 5%
                # sl = round(float(current_price * (1 - pnl_sl)), 3) 
                # tp = round(float(current_price * (1 + pnl_tp)), 3) 
                tp, sl = cal_tp_sl(current_price, pnl_tp, pnl_sl, 'long', 2)
                fc.write_log(f"Vào lệnh LONG Market tại {current_price:.2f} (ngược xu hướng), size: {marginAmount} usdt; Stop-loss: {sl:.5f}; Take-profit: {tp:.5f}")
                # fc.write_log(f"SL: {sl:.2f}")
                # fc.write_log(f"TP: {tp:.2f}")
                api.change_leverage(symbol=symbol, leverage=leverage, holdSide='long')
                fc.write_log(f"Set leverage {symbol}  leverage=x{leverage} for side=LONG.")
                clientOid, orderId = api.place_future_order(symbol=symbol, amount=marginAmount, side='buy', orderType='market', tradeSide='open')
                if clientOid:
                    fc.write_log(f"Place order successful. ClientOid: {clientOid} and order Id: {orderId}") 
                    # fc.write_log(f"Setup TP và SL tại: TP {tp} và SL {sl}")
                    set_tp_sl(symbol, 'long', tp, sl)
                    # api.modify_plan_order(orderId=orderId, clientOid=clientOid,symbol=symbol, tp_price=tp, sl_price=sl, trigger_type="mark_price")
                else:
                    fc.write_log(f"Place order fail. {orderId}")     
                return
            else:
                fc.write_log("30m confirmation failed; skip LONG.")
            
        else:
            fc.write_log("Chưa có tín hiệu đảo chiều.")    
        
        # =======================================================================================================
        # Kiểm tra volume giao dich co thể tìm ra sự đảo chiều sớm của xu hướng
        # Đang là xu hướng giảm nên sẽ tìm tín hiệu volume để LONG
        fc.write_log("Kiểm tra tín hiệu volume giao dịch.")
        trough, buy_volume, sell_volume = logic.check_volume_trough_peak(df_1h, 12, "trough")  #kiểm tra tại 12 cây nến gần nhất
        if trough and buy_volume / sell_volume > 2:      # Tổng lượng volume mua lớn gấp 1.5 lần volume bán nên lực mua đang mạnh xem xét tín hiệu LONG
            fc.write_log("Lực mua đang chiếm ưu thế nên tìm điểm vào lệnh LONG.")
            # Kiểm tra và xác nhận tạo đáy > đáy thấp nhất
            local_trough = logic.find_trough(df_30m, 1, 10)
            local_peak = logic.find_peak(df_30m, 1, 10)         #Tim đỉnh cục bộ để xác định tín hiệu LONG
            fc.write_log(f"Đáy thấp nhất: {trough}, đáy cục bộ: {local_trough}, và giá hiện tại là: {current_price}, Đỉnh cục bộ: {local_peak}")
            if local_trough > trough and current_price > local_peak:        # Break up qua đỉnh cục bộ sẽ vào lệnh long
                tp, sl = cal_tp_sl(current_price, pnl_tp, pnl_sl, 'long', 2)
                fc.write_log(f"Vào lệnh LONG Market tại {current_price:.2f} (ngược xu hướng), size: {marginAmount} usdt; Stop-loss: {sl:.5f}; Take-profit: {tp:.5f}")
                
                api.change_leverage(symbol=symbol, leverage=leverage, holdSide='long')
                fc.write_log(f"Set leverage {symbol}  leverage=x{leverage} for side=LONG.")
                clientOid, orderId = api.place_future_order(symbol=symbol, amount=marginAmount, side='buy', orderType='market', tradeSide='open')
                if clientOid:
                    fc.write_log(f"Place order successful. ClientOid: {clientOid} and order Id: {orderId}") 
                    # fc.write_log(f"Setup TP và SL tại: TP {tp} và SL {sl}")
                    set_tp_sl(symbol, 'long', tp, sl)
                    # api.modify_plan_order(orderId=orderId, clientOid=clientOid,symbol=symbol, tp_price=tp, sl_price=sl, trigger_type="mark_price")
                else:
                    fc.write_log(f"Place order fail. {orderId}")     
                return
            else:
                fc.write_log(f"Chưa thể LONG. Chờ giá break qua đỉnh cục bộ {local_peak}")
                return
        else:
            fc.write_log("Lực bán vẫn chiếm ưu thế nên chờ.")
        
        
         # =======================================================================================================
        # Kiểm tra SHORT thuận (tại resistance trên 15M)
        # Điều kiện 1: Gần S1 hoặc S2     
        fc.write_log("Kiểm tra giá hồi về vùng kháng cự {r1} và {r2}:")
        if r1 or r2:
            for resistance in [r1, r2]:
                if resistance and abs(current_price - resistance) <= near_threshold:
                    fc.write_log(f"Giá gần R{'1' if resistance == r1 else '2'} ({resistance:.2f})")
                    rsi_30m = df_30m.iloc[-1]['RSI_14']
                    # fc.write_log("rsi_15m:" , rsi_15m )
                    if rsi_30m < 30:
                        fc.write_log("RSI 30M <30 - CHỜ ĐỢI điều chỉnh")
                        return
                    
                    fc.write_log("Kiểm tra khung 30m xem có tạo đỉnh cục bộ chưa." )
                    if logic.is_peak(df_30m):
                        fc.write_log("Đã tạo đỉnh nên sẽ vào lệnh." )
                        
                        tp, sl = cal_tp_sl(current_price, pnl_tp, pnl_sl, 'short', 2)
                        fc.write_log(f"VÀO SHORT MARKET tại {current_price:.2f}, size: {marginAmount} usdt; Stop-loss: {sl:.5f}; Take-profit: {tp:.5f}")
                        
                        api.change_leverage(symbol=symbol, leverage=leverage, holdSide='short')
                        fc.write_log(f"Set leverage {symbol}  leverage=x{leverage} for side=SHORT.")
                        clientOid, orderId = api.place_future_order(symbol=symbol, amount=marginAmount, side='sell', orderType='market', tradeSide='open')
                        if clientOid:
                            fc.write_log(f"Place order successful. ClientOid: {clientOid} and order Id: {orderId}") 
                            # fc.write_log(f"Setup TP và SL tại: TP {tp} và SL {sl}")
                            set_tp_sl(symbol, 'short', tp, sl)
                            # api.modify_plan_order(orderId=orderId, clientOid=clientOid,symbol=symbol, tp_price=tp, sl_price=sl, trigger_type="mark_price")
                        else:
                            fc.write_log(f"Place order fail. {orderId}")     
                        return
                    else:
                        fc.write_log("Khung 30m chưa tạo đỉnh cục bộ. Waiting...." )
                        
                    if current_price > r2:
                        fc.write_log("Giá phá R2 - CHỜ ĐỢI, đánh giá lại xu hướng")
                
                else:
                    fc.write_log(f"Giá hiện tại {current_price} với near_threshold {near_threshold} chưa nằm trong vùng R{'1' if resistance == r1 else '2'} nên tiếp tục đợi")
       
        # =======================================================================================================
        # # Điều kiện 2: HOẶC gần EMA9 1h và nến giảm xác nhận
        # # fc.write_log("Kiểm tra giá có gần EMA9 khung 1h hay không?")
        # fc.write_log(f"Kiểm tra giá có tạo đỉnh giữa đáy và EMA9 khung 1h hay không?")
        # local_peak = logic.find_peak(df_1h, 1, 5)
        # fc.write_log(f"Đỉnh cục bộ: {local_peak}")
        # if local_peak:
        #     fc.write_log(f"Kiểm tra giá có gần EMA9 khung 1h hay không?")
            
        #     if abs(current_price - ema9_1h) <= near_threshold:
        #         fc.write_log(f"Giá hiện tại {current_price:.2f} gần EMA9 30m ({ema9_1h:.2f}) với biên độ {near_threshold}")
        #         rsi_1h = df_1h.iloc[-1]['RSI_14']
        #         if rsi_1h < 30:
        #             fc.write_log(f"RSI 30M < 30 - Đang vào vùng quá bán - CHỜ ĐỢI điều chỉnh")
        #             return
        #         # fc.write_log("Close:", df_30m['close'].iloc[-1])
        #         # fc.write_log("open:", df_30m['open'].iloc[-1])
                
        #         if df_1h['close'].iloc[-1] < df_1h['open'].iloc[-1] and df_1h['close'].iloc[-1] < ema9_1h and current_price < local_peak:  # Nến giảm xác nhận
        #             # entry = df_15m['Close'].iloc[-1]
        #             # sl = round(r1 if r1 else float(current_price * (1 + pnl_sl)), 3)
        #             # tp = round(float(current_price * (1 - pnl_tp)), 3) 
        #             tp, sl = cal_tp_sl(current_price, pnl_tp, pnl_sl, 'short', 2)
        #             fc.write_log(f"VÀO SHORT MARKET tại {current_price:.2f} (tại EMA9 30m), size: {marginAmount} usdt; Stop-loss: {sl:.5f}; Take-profit: {tp:.5f}")
        #             # fc.write_log(f"SL: {sl:.2f}")
        #             # fc.write_log(f"TP: {tp:.2f}")
        #             api.change_leverage(symbol=symbol, leverage=leverage, holdSide='short')
        #             fc.write_log(f"Set leverage {symbol} leverage=x{leverage} for side=SHORT.")
        #             clientOid, orderId = api.place_future_order(symbol=symbol, amount=marginAmount, side='sell', orderType='market', tradeSide='open')
        #             if clientOid:
        #                 fc.write_log(f"Place order successful. ClientOid: {clientOid} and order Id: {orderId}") 
        #                 # fc.write_log(f"Setup TP và SL tại: TP {tp} và SL {sl}")
        #                 set_tp_sl(symbol, 'short', tp, sl)
        #                 # api.modify_plan_order(orderId=orderId, clientOid=clientOid, symbol=symbol, tp_price=tp, sl_price=sl, trigger_type="mark_price")
        #             else:
        #                 fc.write_log(f"Place order fail. {orderId}")     
        #             return
        #         else:
        #             fc.write_log(f"Chờ xác nhận nến giảm")
        #     else:
        #         fc.write_log(f"Không gần EMA9 nên chờ tiếp")
        # else:
        #     fc.write_log(f"Chưa tạo đỉnh tại EMA9 1h nên CHỜ.")        
                
    else:
        fc.write_log("Xu hướng không đồng thuận hoặc không rõ ràng. CHỜ ĐỢI.")


