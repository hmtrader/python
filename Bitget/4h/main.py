# main.py
import time

import config
import trade
import api




# load symbol from env
def load_symbol_from_env():
    symbol_str = config.SYMBOLS
    symbol_list = []
    for item in symbol_str.split(','):
        parts = item.strip().split(':')
        if len(parts) == 3:
            symbol = parts[0]
            amount = float(parts[1])
            leverage = float(parts[2])
            symbol_list.append({'symbol': symbol, 'amount': amount, 'leverage': leverage})
        else:
            print(f"Invalid format for {item}. Skipping.")
    return symbol_list     



def main():
    # Lay danh sach coin
    symbols_list = load_symbol_from_env()
    
    if not symbols_list:
        print(f"No valid coins found.")
        return
    
    # print(f"Get list coins success.")
    # print(symbols_list)
    print(f"------------Program start--------------------")
    cross_balance = float(api.get_cross_balance())  # Change product_type as needed
    print("Cross_balance:", cross_balance)
    while True:
        try:
            for item in symbols_list:
                trade.execute_trade_logic(item['symbol'], item['amount'], item['leverage'])
                
            # Chờ 15 phút cho chu kỳ tiếp theo
            print("Wait 15 min....")
            time.sleep(15 * 60)
        except KeyboardInterrupt:
            print("Dừng bot.")
            break
        except Exception as e:
            print(f"Lỗi không mong muốn: {e}")
            time.sleep(60)

if __name__ == '__main__':
    
    print("Bắt đầu bot giao dịch...")
    main()
    print("Kết thúc giao dịch.")

    