import os
import requests
import pandas as pd
import yfinance as yf
from fredapi import Fred
from datetime import datetime, timedelta

# 从环境变量获取 Key (不要硬编码在代码里)
FRED_API_KEY = os.environ.get("FRED_API_KEY")
FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK")

def get_data_and_analyze():
    fred = Fred(api_key=FRED_API_KEY)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # 1. 获取 SOFR 和 IORB
    try:
        sofr = fred.get_series('SOFR', observation_start=start_date).dropna().iloc[-1]
        iorb = fred.get_series('IORB', observation_start=start_date).dropna().iloc[-1]
        spread = sofr - iorb
    except:
        return None, "数据获取失败"

    # 2. 获取 DXY (美元指数)
    try:
        dxy = yf.Ticker("DX-Y.NYB").history(period="5d")['Close'].iloc[-1]
    except:
        dxy = 0

    # 3. 逻辑判断
    alert_level = "info" # info, warning, danger
    title = "🟢 宏观流动性正常"
    
    if spread > 0.05: # 5个基点
        alert_level = "danger"
        title = "🔴 严重警报：在岸流动性枯竭"
    elif spread > 0:
        alert_level = "warning"
        title = "🟡 预警：回购利率倒挂"
    elif dxy > 106:
        alert_level = "warning"
        title = "🟡 预警：美元极度强势"

    return alert_level, title, spread, dxy

def send_feishu_card(level, title, spread, dxy):
    # 根据级别设置颜色
    color_map = {
        "info": "green",    # 绿色
        "warning": "yellow",# 黄色
        "danger": "red"     # 红色
    }
    
    # 构造飞书富文本卡片
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 必须包含你在飞书设置的关键词“监控”
    card_content = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": color_map.get(level, "blue"),
                "title": {
                    "content": f"{title} | 每日监控",
                    "tag": "plain_text"
                }
            },
            "elements": [
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**SOFR-IORB 利差:**\n{spread:.4f}%"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**美元指数 (DXY):**\n{dxy:.2f}"
                            }
                        }
                    ]
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"更新时间: {current_time} (UTC)"
                        }
                    ]
                }
            ]
        }
    }

    headers = {'Content-Type': 'application/json'}
    response = requests.post(FEISHU_WEBHOOK, json=card_content, headers=headers)
    print(f"Feishu Response: {response.text}")

if __name__ == "__main__":
    if not FRED_API_KEY or not FEISHU_WEBHOOK:
        print("Error: Missing Environment Variables")
    else:
        level, title, spread, dxy = get_data_and_analyze()
        if level:
            send_feishu_card(level, title, spread, dxy)
