import streamlit as st
import httpx
import json
import os
from dotenv import load_dotenv
# ... 之前的 import 和 Key 配置 ...

# 👇 新增：真实的查天气工具
def get_weather(city):
    print(f"🛠️ [后台日志]：正在查询 {city} 的天气...")
    try:
        # 国内直连的天气接口
        url = f"https://wttr.in/{city}?format=3&lang=zh"
        response = httpx.get(url, timeout=10.0)
        
        if response.status_code == 200:
            return response.text.strip()
        else:
            return f"查不到{city}的天气信息。"
    except Exception as e:
        return f"查天气失败了，可能是网络问题：{e}"

# 1. 网页配置
st.set_page_config(page_title="毒舌导师", page_icon="🤖")
st.title("🤖 毒舌 Python 导师")
st.caption("基于 DeepSeek 大模型开发")

# 2. 读取 Key (你之前配的 .env 依然生效)
load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not API_KEY:
    st.error("未找到 API_KEY，请检查 .env 文件！")
    st.stop()

url = "https://api.deepseek.com/chat/completions"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 3. 初始化网页版的记忆 (使用 Streamlit 专属记忆)
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "你是一个说话极其毒舌、喜欢嘲讽人的 Python 导师。"}
    ]

# 4. 把历史聊天记录画在网页上
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

# 5. 接收用户在网页输入框里打的话
if prompt := st.chat_input("导师，我有个问题..."):
    # 把用户的话显示在网页上
    with st.chat_message("user"):
        st.write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 准备发送数据
    data = {
        "model": "deepseek-chat",
        "messages": st.session_state.messages,
        "stream": True
    }

    # 6. 发送请求并流式接收
    with st.chat_message("assistant"):
        # 定义一个生成器，让 Streamlit 像打字机一样输出
        def generate_response():
            with httpx.stream("POST", url, headers=headers, json=data, timeout=30.0) as response:
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
        
        # 接收完整回答并显示
        full_response = st.write_stream(generate_response())
    
    # 👇 拦截暗号，调用真实天气工具！
        if "CALL_WEATHER:" in full_response:
            # 提取城市
            city = full_response.split("CALL_WEATHER:")[1].strip()
            
            # 显示系统执行提示
            with st.chat_message("system"):
                st.write(f"🛠️ 正在调用真实天气接口查询 {city}...")
            
            # 调用真实的天气函数
            weather_result = get_weather(city)
            
            # 把暗号和真实天气结果塞进记忆
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            st.session_state.messages.append({"role": "user", "content": f"系统查到的天气数据是：{weather_result}，请用你毒舌的语气总结给用户。"})
            
            # 准备第二次请求，让 AI 总结
            data["messages"] = st.session_state.messages
            
            with st.chat_message("assistant"):
                def generate_second_response():
                    with httpx.stream("POST", url, headers=headers, json=data, timeout=30.0) as response:
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
                
                # 接收总结并存入记忆
                full_response_2 = st.write_stream(generate_second_response())
                st.session_state.messages.append({"role": "assistant", "content": full_response_2})
        
        else:
            # 如果没查到天气（正常聊天），直接把回复存入记忆
            st.session_state.messages.append({"role": "assistant", "content": full_response})