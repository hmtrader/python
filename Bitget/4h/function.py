import time, datetime

# Hàm ghi log vào file
def write_log(message, filename="trading_bot"):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    dateLog = time.strftime('%Y-%m-%d')
    log_entry = f"[{timestamp}] {message}\n"
    filename = f"log\{filename}_{dateLog}.txt"
    print(log_entry.strip())
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(log_entry)
        
        
# Hàm lưu lịch sử lệnh vào CSV
def save_order_history(pd, order, filename='order_history.csv'):
    order_data = order.to_dict()
    df = pd.DataFrame([order_data])
    try:
        existing_df = pd.read_csv(filename)
        df = pd.concat([existing_df, df], ignore_index=True)
    except FileNotFoundError:
        pass
    df.to_csv(filename, index=False)
    write_log(f"Lưu lịch sử lệnh vào {filename}")        