import api
import time

def open_order(symbol, entry_price, risk_usdt, leverage, side='BUY'):
    # Tính khối lượng vị thế
    capital = float(risk_usdt * leverage)
    quantity = float(capital / entry_price)
    
    quantity = round(quantity, 3)
    
    print(f"Chuẩn bị mở {side} {quantity} {symbol} tại giá {entry_price}")
    print(f"Đòn bẩy {leverage}x | Rủi ro ~{risk_usdt} USDT")
    
    # Set đòn bẩy cho vị thế trước khi đặt lệnh
    api.set_leverage(symbol, leverage)
    # Delay lại 1 chút phòng trường hợp chưa kịp thực hiện lệnh
    time.sleep(1)
    
    # Đặt lệnh
    api.place_order(symbol=symbol, side=side, type = 'LIMIT', quantity=quantity, price=entry_price, reduceOnly=False)
    

def get_balance():
    balance, avaliableBalance = api.get_balance()
    
    if not balance:
        print("Không lay được balance.")
        return None
    
    print("Kết nối thành công!")
    print("-"*30)
    print("Thông tin balance:")
    
    print(f"Tổng số dư: {balance} USDT")
    print(f"Số dư khả dụng: {avaliableBalance} USDT")

# Ham chinh cua chuong trinh
def main():
    print("---------------Programe start-------------------")
    get_balance()
    open_order('ETHUSDT', 2400, 2, 25, 'BUY')   #đặt lệnh LIMIT ETH với giá 2400 khối lượng 2 USDT đòn bẫy x25
    print("---------------End program----------------------")
    
    
if __name__ == "__main__":
    main()    