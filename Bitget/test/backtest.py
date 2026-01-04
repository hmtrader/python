import trade_t as trade



def main():
    # Lay danh sach coin
    trade.execute_trade_logic('BTCUSDT', '2', '50')

if __name__ == '__main__':
    
    print("Bắt đầu backtest...")
    main()
    print("Kết thúc backtest.")

    