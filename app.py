import streamlit as st
from openai import OpenAI
import base64
from io import BytesIO

# ==========================================
# 1. КОНФИГУРАЦИЯ И UDL СТИЛИ
# ==========================================
st.set_page_config(page_title="Доступная История (Grok Edition)", page_icon="🏛️")

st.sidebar.title("⚙️ Настройки системы")
font_size = st.sidebar.slider("Размер текста", 18, 32, 22)

st.markdown(f"""
    <style>
    html, body, [class*="st-"] {{ font-size: {font_size}px !important; }}
    .stChatMessage {{ background-color: #f0f2f6; border-radius: 15px; padding: 15px; }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. ИНИЦИАЛИЗАЦИЯ КЛИЕНТОВ (ГИБРИД)
# ==========================================
# Получаем ключи из secrets или интерфейса
openai_key = st.sidebar.text_input("🔑 OpenAI API Key (для голоса)", type="password", value=st.secrets.get("OPENAI_API_KEY", ""))
grok_key = st.sidebar.text_input("🔑 Grok API Key (для ума)", type="password", value=st.secrets.get("GROK_API_KEY", ""))

if not openai_key or not grok_key:
    st.warning("Для работы нужны оба ключа: OpenAI (голос) и Grok (текст/фото).")
    st.stop()

# Клиент OpenAI для звука
client_audio = OpenAI(api_key=openai_key)

# Клиент Grok для текста и зрения (используем совместимый с OpenAI SDK)
client_grok = OpenAI(
    api_key=grok_key,
    base_url="https://api.x.ai/v1",
)

# ==========================================
# 3. ФУНКЦИИ-ПОМОЩНИКИ
# ==========================================

def encode_image(uploaded_file):
    return base64.b64encode(uploaded_file.getvalue()).decode('utf-8')

def transcribe_audio(audio_bytes):
    """Используем OpenAI Whisper"""
    audio_file = BytesIO(audio_bytes)
    audio_file.name = "audio.wav"
    transcript = client_audio.audio.transcriptions.create(model="whisper-1", file=audio_file)
    return transcript.text

def generate_speech(text):
    """Используем OpenAI TTS"""
    response = client_audio.audio.speech.create(model="tts-1", voice="nova", input=text)
    return response.content

def get_grok_response(messages):
    """Запрос к Grok-2-vision-latest"""
    response = client_grok.chat.completions.create(
        model="grok-2-vision-latest", # Или grok-vision-beta в зависимости от доступа
        messages=messages,
        temperature=0.6
    )
    return response.choices[0].message.content

# ==========================================
# 4. ЛОГИКА ДИАЛОГА
# ==========================================

SYSTEM_PROMPT = """
Ты — добрый учитель истории. Твои ученики — дети.
Пиши короткими предложениями. Используй простые слова.
Если видишь картинку — объясни её просто и добавь один факт.
"""

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

# Отображение чата
for i, msg in enumerate(st.session_state.messages):
    if msg["role"] == "system": continue
    with st.chat_message(msg["role"]):
        if isinstance(msg["content"], list):
            for item in msg["content"]:
                if item["type"] == "text": st.write(item["text"])
                elif item["type"] == "image_url": st.image(item["image_url"]["url"])
        else:
            st.write(msg["content"])
        
        if msg["role"] == "assistant":
            if st.button("🔊 Послушать ответ", key=f"audio_{i}"):
                audio = generate_speech(msg["content"])
                st.audio(audio, autoplay=True)

# ==========================================
# 5. ВВОД (МУЛЬТИМОДАЛЬНОСТЬ)
# ==========================================

img_file = st.file_uploader("🖼️ Загрузи фото", type=["jpg", "png"])
voice_file = st.audio_input("🎤 Скажи что-нибудь")
text_input = st.chat_input("⌨️ Напиши здесь...")

input_text = None
if text_input:
    input_text = text_input
elif voice_file:
    with st.spinner("Распознаю голос..."):
        input_text = transcribe_audio(voice_file.getvalue())

if input_text or img_file:
    new_content = []
    
    if input_text:
        new_content.append({"type": "text", "text": input_text})
    
    if img_file:
        b64_img = encode_image(img_file)
        new_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
        })
        if not input_text:
            new_content.append({"type": "text", "text": "Что на этой картинке?"})

    st.session_state.messages.append({"role": "user", "content": new_content})
    
    with st.chat_message("assistant"):
        with st.spinner("Grok изучает историю..."):
            reply = get_grok_response(st.session_state.messages)
            st.write(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.rerun()
