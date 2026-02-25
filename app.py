import streamlit as st
from openai import OpenAI
import base64
from io import BytesIO
from PIL import Image

# ==========================================
# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ И UDL НАСТРОЙКИ
# ==========================================
st.set_page_config(
    page_title="Доступная История", 
    page_icon="🏛️", 
    layout="centered"
)

# Боковая панель: Настройки доступности
st.sidebar.title("Настройки")
st.sidebar.markdown("Здесь можно настроить приложение так, как тебе удобно.")

# UDL: Слайдер для изменения размера шрифта (поддержка слабовидящих и дислексии)
font_size = st.sidebar.slider("Размер текста", min_value=18, max_value=32, value=22)

# UDL: CSS-стилизация для крупных шрифтов и высокой контрастности
st.markdown(f"""
    <style>
    html, body, [class*="st-"] {{
        font-size: {font_size}px !important;
    }}
    /* Высококонтрастные цвета для читаемости */
    .stChatMessage {{
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
    }}
    .stButton button {{
        background-color: #0056b3;
        color: white;
        border-radius: 8px;
        font-weight: bold;
    }}
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 2. ИНИЦИАЛИЗАЦИЯ И БЕЗОПАСНОСТЬ (API KEYS)
# ==========================================
# Безопасное получение ключа (сначала из secrets, затем из интерфейса)
api_key = st.secrets.get("OPENAI_API_KEY", "")
if not api_key:
    api_key = st.sidebar.text_input("🔑 Введи OpenAI API Key (для родителей/учителей)", type="password")

if not api_key:
    st.info("Пожалуйста, попроси взрослого ввести ключ доступа (API Key) слева, чтобы мы могли начать!")
    st.stop()

client = OpenAI(api_key=api_key)


# ==========================================
# 3. ОСНОВНЫЕ ФУНКЦИИ (ИИ И МУЛЬТИМОДАЛЬНОСТЬ)
# ==========================================
def encode_image(uploaded_file):
    """Кодирует загруженное изображение в base64 для Vision API."""
    bytes_data = uploaded_file.getvalue()
    return base64.b64encode(bytes_data).decode('utf-8')

def transcribe_audio(audio_bytes):
    """Транскрибирует голос ребенка в текст с помощью Whisper."""
    audio_file = BytesIO(audio_bytes)
    audio_file.name = "audio.wav"
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    )
    return transcript.text

def generate_speech(text):
    """Превращает текст ответа в понятную аудио-речь (TTS)."""
    response = client.audio.speech.create(
        model="tts-1",
        voice="nova", # Голос Nova звучит мягко и дружелюбно
        input=text
    )
    return response.content

def get_assistant_response(messages):
    """Отправляет контекст диалога в GPT-4o."""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.7 # Немного креативности, но без ухода от фактов
    )
    return response.choices[0].message.content


# ==========================================
# 4. УПРАВЛЕНИЕ СОСТОЯНИЕМ (SESSION STATE)
# ==========================================
# UDL Промпт: Жесткие правила для ИИ, чтобы ответы были инклюзивными
SYSTEM_PROMPT = """
Ты — добрый, эмпатичный и терпеливый учитель истории. Твои ученики — дети с особыми образовательными потребностями.
Твои правила общения (Universal Design for Learning):
1. Plain Language: Используй очень простой язык.
2. Короткие предложения: Максимум 10-12 слов в предложении.
3. Никаких абстракций: Избегай метафор, сарказма и сложных дат, если о них не спрашивают. Объясняй через осязаемые примеры (например, "размером с автобус", "как твоя школа").
4. Если тебе показывают картинку, сначала прямо скажи, что на ней, а потом расскажи один интересный исторический факт.
5. Форматирование: Разделяй текст на короткие абзацы.
"""

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

if "processed_images" not in st.session_state:
    st.session_state.processed_images = [] # Запоминаем отправленные фото
if "last_audio" not in st.session_state:
    st.session_state.last_audio = None


# ==========================================
# 5. ИНТЕРФЕЙС ПРИЛОЖЕНИЯ
# ==========================================
st.title("🏛️ Машина Времени")
st.write("Привет! Я твой помощник. Мы можем изучать историю вместе. Напиши мне, скажи голосом или покажи картинку!")

# Отображение истории переписки
for i, msg in enumerate(st.session_state.messages):
    if msg["role"] == "system":
        continue
    
    with st.chat_message(msg["role"]):
        # Обработка мультимодальных сообщений (где есть картинки и текст)
        if isinstance(msg["content"], list):
            for item in msg["content"]:
                if item["type"] == "text":
                    st.write(item["text"])
                elif item["type"] == "image_url":
                    # Показываем отправленное изображение
                    st.image(item["image_url"]["url"])
        else:
            # Обычный текст
            st.write(msg["content"])
        
        # UDL: Кнопка озвучки для каждого ответа ИИ
        if msg["role"] == "assistant":
            # Используем уникальный ключ для каждой кнопки
            if st.button("🔊 Озвучить ответ", key=f"tts_{i}"):
                with st.spinner("Создаю звук..."):
                    audio_data = generate_speech(msg["content"])
                    # autoplay=True автоматически запустит аудио (работает в новых версиях Streamlit)
                    st.audio(audio_data, format="audio/mp3", autoplay=True)


# ==========================================
# 6. ВВОД ДАННЫХ (ТЕКСТ, ГОЛОС, ФОТО)
# ==========================================
st.markdown("---")

# Панель мультисенсорного ввода
col1, col2 = st.columns([1, 1])
with col1:
    uploaded_image = st.file_uploader("🖼️ Покажи фото (положи в Машину Времени)", type=["png", "jpg", "jpeg"])
with col2:
    audio_value = st.audio_input("🎤 Задай вопрос голосом")

user_text = st.chat_input("⌨️ Или напиши свой вопрос здесь...")

# Логика обработки триггеров (когда пользователь отправляет запрос)
trigger_text = None
is_triggered = False

if user_text:
    trigger_text = user_text
    is_triggered = True
elif audio_value and audio_value != st.session_state.last_audio:
    st.session_state.last_audio = audio_value
    with st.spinner("Слушаю тебя..."):
        trigger_text = transcribe_audio(audio_value.getvalue())
        is_triggered = True

# Если сработал триггер ввода (текст или голос)
if is_triggered:
    user_message_content = []
    
    # Добавляем текст/транскрипцию
    if trigger_text:
        user_message_content.append({"type": "text", "text": trigger_text})
    
    # Проверяем, есть ли новое изображение
    if uploaded_image and uploaded_image.file_id not in st.session_state.processed_images:
        b64_img = encode_image(uploaded_image)
        mime_type = uploaded_image.type
        img_url = f"data:{mime_type};base64,{b64_img}"
        
        user_message_content.append({
            "type": "image_url",
            "image_url": {"url": img_url}
        })
        st.session_state.processed_images.append(uploaded_image.file_id)
        
        # Если ребенок загрузил фото, но ничего не написал/сказал
        if not trigger_text:
            user_message_content.append({"type": "text", "text": "Расскажи, что изображено на этой картинке?"})

    # 1. Сохраняем и показываем запрос ученика
    st.session_state.messages.append({"role": "user", "content": user_message_content})
    with st.chat_message("user"):
        if trigger_text: 
            st.write(trigger_text)
        if uploaded_image and uploaded_image.file_id in st.session_state.processed_images:
            st.image(uploaded_image)

    # 2. Получаем и показываем ответ ИИ
    with st.chat_message("assistant"):
        with st.spinner("Думаю..."):
            ai_reply = get_assistant_response(st.session_state.messages)
            st.write(ai_reply)
            # Сохраняем ответ как обычный текст
            st.session_state.messages.append({"role": "assistant", "content": ai_reply})
            
            # Перезагружаем интерфейс, чтобы появилась кнопка "Озвучить"
            st.rerun()
