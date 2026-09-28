import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 設定網頁標題與外觀（手機、平板友善）
st.set_page_config(page_title="自選股多日漲跌幅統計", layout="wide")
st.title("📈 自選股即時監控與多日漲跌幅統計")

# 1. 側邊欄設定
st.sidebar.header("⚙️ 設定自選股與天數")

# 股票輸入框
default_tickers = "2330.TW, 2317.TW, 2454.TW, AAPL"
user_input = st.sidebar.text_area(
    "請輸入股票代號（多檔請用逗號隔開）\n台股請加 .TW (例如: 2330.TW)", 
    value=default_tickers
)

# 需求 2：自訂往前 N 天的拉桿（可選 1 到 60 天，預設為 20 天）
custom_days = st.sidebar.slider(
    "請選擇自訂統計天數 (往前 N 天)", 
    min_value=1, 
    max_value=60, 
    value=20,
    step=1
)

# 整理輸入的代號清單
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

# 2. 核心抓取與計算邏輯
def get_stock_data(tickers, n_days):
    data_list = []
    
    for ticker_to_search in tickers:
        try:
            # 為了防範放假、休市等非交易日，抓取 N + 20 天的歷史資料最安全
            fetch_days = max(30, n_days + 20)
            stock = yf.Ticker(ticker_to_search)
            hist = stock.history(period=f"{fetch_days}d")
            
            if hist.empty:
                continue
                
            # 取得股票名稱（若抓不到則顯示代號）
            stock_info = stock.info
            stock_name = stock_info.get('shortName', ticker_to_search)
            
            # 處理即時/最新價格（開盤中為即時價，收盤後為收盤價）
            latest_row = hist.iloc[-1]
            current_price = latest_row['Close']
            prev_close = hist.iloc[-2]['Close'] if len(hist) > 1 else current_price
            
            # 1. 當日漲跌幅
            daily_change_pct = ((current_price - prev_close) / prev_close) * 100
            
            # 固定天數的累計漲跌幅計算（-1 是最新，-4 是往前 3 個交易日，依此類推）
            change_3d = ((current_price - hist.iloc[-4]['Close']) / hist.iloc[-4]['Close']) * 100 if len(hist) >= 4 else 0
            change_5d = ((current_price - hist.iloc[-6]['Close']) / hist.iloc[-6]['Close']) * 100 if len(hist) >= 6 else 0
            change_10d = ((current_price - hist.iloc[-11]['Close']) / hist.iloc[-11]['Close']) * 100 if len(hist) >= 11 else 0
            
            # 2. 需求二：動態計算往前 N 天的漲跌幅
            # 在 pandas iloc 中，最新是 -1，往前 N 天的收盤價位置就是 -(n_days + 1)
            target_index = -(n_days + 1)
            if len(hist) >= abs(target_index):
                past_price = hist.iloc[target_index]['Close']
                custom_change = ((current_price - past_price) / past_price) * 100
            else:
                custom_change = 0.0
            
            data_list.append({
                "代號": ticker_to_search,
                "股票名稱": stock_name,
                "目前市價/收盤價": f"{current_price:.2f}",
                # 需求 1：所有百分比數字皆透過 round(val, 2) 限制在小數點後兩位
                "當日漲跌幅 (%)": round(daily_change_pct, 2),
                "近 3 日漲跌 (%)": round(change_3d, 2),
                "近 5 日漲跌 (%)": round(change_5d, 2),
                "近 10 日漲跌 (%)": round(change_10d, 2),
                f"自訂近 {n_days} 日漲跌 (%)": round(custom_change, 2), # 新增的動態欄位
            })
        except Exception as e:
            st.error(f"無法抓取 {ticker_to_search} 的資料，請檢查代號是否正確。")
            
    return pd.DataFrame(data_list)

# 3. 畫面渲染
if ticker_list:
    with st.spinner('正在抓取最新股價與統計多日漲跌幅...'):
        df = get_stock_data(ticker_list, custom_days)
        
    if not df.empty:
        # 定義顏色標示函數：正數變紅（台股習慣），負數變綠
        def color_change(val):
            if isinstance(val, (int, float)):
                if val > 0:
                    return 'color: #ff4b4b; font-weight: bold;'
                elif val < 0:
                    return 'color: #00b050; font-weight: bold;'
            return ''

        # 針對所有漲跌幅欄位套用顏色標記
        target_columns = ["當日漲跌幅 (%)", "近 3 日漲跌 (%)", "近 5 日漲跌 (%)", "近 10 日漲跌 (%)", f"自訂近 {custom_days} 日漲跌 (%)"]
        styled_df = df.style.map(color_change, subset=target_columns)
        
        # 顯示最後更新時間
        st.caption(f"最後更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (延遲約15分鐘)")
        
        # 用漂亮的表格顯示出來
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        # 提供重新整理按鈕
        if st.button("🔄 重新整理最新股價"):
            st.rerun()
    else:
        st.warning("查無任何股票資料，請確認側邊欄輸入的代號。")