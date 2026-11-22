import streamlit as st
import httpx
import json
import os
from dotenv import load_dotenv

# 1. 网页配置
st.set_page_config(page_title="毒舌导师", page_icon="🤖")
st.title("🤖 毒舌 Python 导师")
st.caption("基于 DeepSeek 大模型开发")

# 2. 读取 Key
try:
    API_KEY = st.secrets["DEEPSEEK_API_KEY"]
except Exception:
    load_dotenv()
    API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not API_KEY:
    st.error("未找到 API_KEY，请检查云端 Secrets 或本地 .env 文件！")
    st.stop()

url = "https://api.deepseek.com/chat/completions"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 3. 查天气工具
def get_weather(city):
    try:
        url_weather = f"https://wttr.in/{city}?format=3&lang=zh"
        response = httpx.get(url_weather, timeout=10.0)
        if response.status_code == 200:
            return response.text.strip()
        else:
            return f"查不到{city}的天气信息。"
    except Exception as e:
        return f"查天气失败，网络问题：{e}"

# 4. 初始化记忆
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "你是一个说话极其毒舌的 Python 导师，但你拥有一个超能力：你可以查天气。当用户问你天气时，你必须直接输出：CALL_WEATHER:城市名（比如：CALL_WEATHER:北京），不要带其他废话。"}
    ]

# 5. 渲染历史记录
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

# 6. 聊天主循环
if prompt := st.chat_input("导师，我有个问题..."):
    with st.chat_message("user"):
        st.write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    data = {
        "model": "deepseek-chat",
        "messages": st.session_state.messages,
        "stream": True
    }

    # ================= 第一次请求：正常聊天 =================
    with st.chat_message("assistant"):
        def generate_response():
            try:
                with httpx.stream("POST", url, headers=headers, json=data, timeout=30.0) as response:
                    if response.status_code != 200:
                        response.read()
                        yield f"\n\n⚠️ 请求失败，状态码：{response.status_code}，详情：{response.text}"
                        return
                    for line in response.iter_lines():
                        if line and line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                content = chunk["choices"][0]["delta"].get("content", "")
                                if content:
                                    yield content
                            except Exception:
                                pass
            except Exception as e:
                yield f"\n\n⚠️ 网络报错：{str(e)}"
        
        full_response = st.write_stream(generate_response())
    
    # 保存第一次的回复
    st.session_state.messages.append({"role": "assistant", "content": full_response})

    # ================= 拦截暗号：调用天气工具 =================
    if "CALL_WEATHER:" in full_response:
        city = full_response.split("CALL_WEATHER:")[1].strip()
        
        with st.chat_message("system"):
            st.write(f"🛠️ 正在调用真实天气接口查询 {city}...")
        
        weather_result = get_weather(city)
        
        st.session_state.messages.append({"role": "user", "content": f"系统查到的天气数据是：{weather_result}，请用你毒舌的语气总结给用户。"})
        data["messages"] = st.session_state.messages
        
        # ================= 第二次请求：总结天气 =================
        with st.chat_message("assistant"):
            def generate_second_response():
                try:
                    with httpx.stream("POST", url, headers=headers, json=data, timeout=30.0) as response:
                        if response.status_code != 200:
                            response.read()
                            yield f"\n\n⚠️ 请求失败，状态码：{response.status_code}，详情：{response.text}"
                            return
                        for line in response.iter_lines():
                            if line and line.startswith("data: "):
                                data_str = line[6:]
                                if data_str == "[DONE]": break
                                try:
                                    chunk = json.loads(data_str)
                                    content = chunk["choices"][0]["delta"].get("content", "")
                                    if content:
                                        yield content
                                except Exception:
                                    pass
                except Exception as e:
                    yield f"\n\n⚠️ 网络报错：{str(e)}"
            
            full_response_2 = st.write_stream(generate_second_response())
            st.session_state.messages.append({"role": "assistant", "content": full_response_2})
