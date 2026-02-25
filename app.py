"""
ИсторияДруг — Инклюзивный помощник по истории
Разработан по принципам Universal Design for Learning (UDL)
"""

import streamlit as st
import openai
import base64
import io
import tempfile
import os
from PIL import Image

# ─────────────────────────────────────────────
# КОНФИГУРАЦИЯ СТРАНИЦЫ
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="ИсторияДруг",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# СИСТЕМНЫЙ ПРОМПТ (UDL / Plain Language)
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """
Ты — добрый и терпеливый учитель истории по имени «ИсторяДруг».
Ты помогаешь детям с особыми образовательными потребностями.

Правила общения:
1. Используй ПРОСТЫЕ и КОРОТКИЕ предложения. Не более 15 слов в предложении.
2. Избегай абстрактных метафор и сложных слов.
3. Если используешь незнакомое слово — сразу объясни его в скобках.
4. Структурируй ответ: сначала главная мысль, потом детали.
5. Используй конкретные примеры из жизни.
6. Всегда заканчивай ответ одним простым вопросом или предложением подумать вместе.
7. Отвечай на том же языке, на котором спрашивают.
8. Будь очень доброжелательным. Хвали за любой вопрос.
9. Максимальная длина ответа — 150 слов.
"""

# ─────────────────────────────────────────────
# ДИНАМИЧЕСКИЙ CSS (размер шрифта + тема)
# ─────────────────────────────────────────────
def apply_styles(font_size: int, high_contrast: bool):
    bg_color = "#1a1a2e" if high_contrast else "#f8f9fa"
    text_color = "#ffffff" if high_contrast else "#212529"
    chat_bg = "#16213e" if high_contrast else "#ffffff"
    user_bubble = "#e8f4fd" if not high_contrast else "#0f3460"
    bot_bubble = "#fff3cd" if not high_contrast else "#533483"
    border_color = "#ffdd57" if high_contrast else "#dee2e6"

    st.markdown(f"""
    <style>
        /* Основной контейнер */
        .stApp {{
            background-color: {bg_color};
            color: {text_color};
            font-size: {font_size}px !important;
        }}

        /* Все тексты */
        p, div, span, label, .stMarkdown {{
            font-size: {font_size}px !important;
            color: {text_color} !important;
            line-height: 1.7 !important;
        }}

        h1 {{ font-size: {font_size + 14}px !important; }}
        h2 {{ font-size: {font_size + 8}px !important; }}
        h3 {{ font-size: {font_size + 4}px !important; }}

        /* Боковая панель */
        [data-testid="stSidebar"] {{
            background-color: {"#16213e" if high_contrast else "#e9ecef"} !important;
        }}

        /* Пузыри чата */
        .user-bubble {{
            background: {user_bubble};
            border-radius: 18px 18px 4px 18px;
            padding: 14px 20px;
            margin: 10px 0 10px 15%;
            border: 2px solid {border_color};
            font-size: {font_size}px;
            color: {text_color};
        }}
        .bot-bubble {{
            background: {bot_bubble};
            border-radius: 18px 18px 18px 4px;
            padding: 14px 20px;
            margin: 10px 15% 10px 0;
            border: 2px solid {border_color};
            font-size: {font_size}px;
            color: {text_color};
        }}
        .bubble-label {{
            font-size: {font_size - 4}px !important;
            opacity: 0.7;
            margin-bottom: 4px;
            font-weight: bold;
        }}

        /* Кнопки — крупные и заметные */
        .stButton > button {{
            font-size: {font_size}px !important;
            padding: 12px 28px !important;
            border-radius: 12px !important;
            border: 2px solid {border_color} !important;
            font-weight: bold !important;
            min-height: 52px !important;
            transition: transform 0.1s ease;
        }}
        .stButton > button:hover {{
            transform: scale(1.03);
        }}

        /* Поле ввода текста */
        .stChatInput textarea {{
            font-size: {font_size}px !important;
            border-radius: 12px !important;
        }}

        /* Слайдер */
        [data-testid="stSlider"] label {{
            font-size: {font_size}px !important;
        }}

        /* Загрузчик файлов */
        [data-testid="stFileUploader"] {{
            font-size: {font_size}px !important;
        }}

        /* Аудио плеер */
        audio {{
            width: 100%;
            border-radius: 12px;
        }}

        /* Скрыть лишние элементы Streamlit */
        #MainMenu, footer {{ visibility: hidden; }}
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# ФУНКЦИЯ: Анализ изображения (GPT-4o Vision)
# ─────────────────────────────────────────────
def analyze_image(client: openai.OpenAI, image_file) -> str:
    """
    Принимает файл изображения, кодирует в base64,
    отправляет в GPT-4o Vision и возвращает описание
    в стиле Plain Language для ребёнка.
    """
    try:
        # Открываем и оптимизируем изображение через Pillow
        img = Image.open(image_file)

        # Конвертируем в RGB (на случай RGBA или других режимов)
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Уменьшаем, если слишком большое (экономия токенов)
        max_size = (1024, 1024)
        img.thumbnail(max_size, Image.LANCZOS)

        # Кодируем в base64
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)
        image_data = base64.b64encode(buffer.read()).decode("utf-8")

        prompt_vision = (
            "Посмотри на это изображение. "
            "Объясни ребёнку 8-12 лет, что на нём изображено. "
            "Расскажи про исторический контекст, если он есть. "
            "Используй очень простые слова. Короткие предложения. "
            "Максимум 100 слов."
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_vision},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}",
                                "detail": "low",
                            },
                        },
                    ],
                }
            ],
            max_tokens=300,
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"⚠️ Не удалось проанализировать изображение: {e}"


# ─────────────────────────────────────────────
# ФУНКЦИЯ: Транскрибация голоса (Whisper)
# ─────────────────────────────────────────────
def transcribe_audio(client: openai.OpenAI, audio_bytes: bytes) -> str:
    """
    Принимает байты аудио, сохраняет во временный файл,
    отправляет в Whisper API и возвращает текст.
    """
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ru",
            )

        os.unlink(tmp_path)
        return transcript.text

    except Exception as e:
        return f"⚠️ Ошибка транскрибации: {e}"


# ─────────────────────────────────────────────
# ФУНКЦИЯ: Генерация речи (TTS)
# ─────────────────────────────────────────────
def generate_speech(client: openai.OpenAI, text: str) -> bytes | None:
    """
    Принимает текст, возвращает байты MP3-аудио через TTS.
    Голос 'nova' — мягкий и дружелюбный.
    """
    try:
        # Ограничиваем длину текста для TTS (лимит API — 4096 символов)
        text_for_tts = text[:4096]

        response = client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=text_for_tts,
            response_format="mp3",
        )
        return response.content

    except Exception as e:
        st.error(f"⚠️ Ошибка генерации речи: {e}")
        return None


# ─────────────────────────────────────────────
# ФУНКЦИЯ: Отправка сообщения в GPT-4o
# ─────────────────────────────────────────────
def get_ai_response(client: openai.OpenAI, messages: list) -> str:
    """
    Отправляет историю диалога в GPT-4o и возвращает ответ.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=500,
            temperature=0.7,
        )
        return response.choices[0].message.content

    except openai.AuthenticationError:
        return "⚠️ Неверный API-ключ. Проверь ключ в боковой панели."
    except openai.RateLimitError:
        return "⚠️ Превышен лимит запросов. Попробуй через минуту."
    except Exception as e:
        return f"⚠️ Ошибка: {e}"


# ─────────────────────────────────────────────
# ИНИЦИАЛИЗАЦИЯ SESSION STATE
# ─────────────────────────────────────────────
def init_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
    if "chat_history" not in st.session_state:
        # Отображаемая история (без system)
        st.session_state.chat_history = []
    if "last_bot_message" not in st.session_state:
        st.session_state.last_bot_message = ""
    if "tts_audio" not in st.session_state:
        st.session_state.tts_audio = None
    if "api_key" not in st.session_state:
        st.session_state.api_key = ""


# ─────────────────────────────────────────────
# БОКОВАЯ ПАНЕЛЬ
# ─────────────────────────────────────────────
def render_sidebar() -> tuple[int, bool, str]:
    with st.sidebar:
        st.markdown("## ⚙️ Настройки")
        st.divider()

        # API ключ
        st.markdown("### 🔑 API-ключ OpenAI")
        # Пробуем получить из secrets (для деплоя)
        default_key = ""
        try:
            default_key = st.secrets["OPENAI_API_KEY"]
        except Exception:
            pass

        api_key = st.text_input(
            "Вставь свой ключ:",
            value=default_key or st.session_state.get("api_key", ""),
            type="password",
            help="Ключ начинается с 'sk-'. Получи его на platform.openai.com",
            placeholder="sk-...",
        )
        st.session_state.api_key = api_key

        st.divider()

        # Размер шрифта
        st.markdown("### 🔤 Размер текста")
        font_size = st.slider(
            "Выбери размер:",
            min_value=18,
            max_value=32,
            value=22,
            step=2,
            help="Сдвинь вправо для более крупного текста",
        )

        # Примеры размеров
        st.markdown(
            f'<p style="font-size:{font_size}px; color: gray;">Пример текста</p>',
            unsafe_allow_html=True,
        )

        st.divider()

        # Тема
        st.markdown("### 🎨 Тема оформления")
        high_contrast = st.toggle(
            "Высокий контраст",
            value=False,
            help="Тёмный фон с яркими цветами — легче читать",
        )

        st.divider()

        # Очистка истории
        st.markdown("### 🗑️ История чата")
        if st.button("Начать заново", use_container_width=True):
            st.session_state.messages = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ]
            st.session_state.chat_history = []
            st.session_state.last_bot_message = ""
            st.session_state.tts_audio = None
            st.rerun()

        st.divider()
        st.markdown(
            "<small>🏛️ ИсторияДруг v1.0<br>Сделан с ❤️ для инклюзивного обучения</small>",
            unsafe_allow_html=True,
        )

    return font_size, high_contrast, api_key


# ─────────────────────────────────────────────
# ОТРИСОВКА ИСТОРИИ ЧАТА
# ─────────────────────────────────────────────
def render_chat_history(font_size: int):
    for item in st.session_state.chat_history:
        if item["role"] == "user":
            icon = "🧒" if not item.get("from_voice") else "🎤"
            label = "Ты написал:" if not item.get("from_voice") else "Ты сказал:"
            st.markdown(
                f'<div class="user-bubble">'
                f'<div class="bubble-label">{icon} {label}</div>'
                f'{item["content"]}'
                f"</div>",
                unsafe_allow_html=True,
            )
        elif item["role"] == "assistant":
            st.markdown(
                f'<div class="bot-bubble">'
                f'<div class="bubble-label">🏛️ ИсторяДруг:</div>'
                f'{item["content"]}'
                f"</div>",
                unsafe_allow_html=True,
            )
        elif item["role"] == "image":
            st.markdown(
                f'<div class="bot-bubble">'
                f'<div class="bubble-label">🖼️ Анализ изображения:</div>'
                f'{item["content"]}'
                f"</div>",
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────
# ГЛАВНАЯ ФУНКЦИЯ
# ─────────────────────────────────────────────
def main():
    init_session_state()

    # Боковая панель
    font_size, high_contrast, api_key = render_sidebar()

    # Применяем стили
    apply_styles(font_size, high_contrast)

    # Заголовок
    col1, col2 = st.columns([1, 8])
    with col1:
        st.markdown(
            '<div style="font-size: 60px; line-height: 1;">🏛️</div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.title("ИсторяДруг")
        st.markdown("**Твой добрый помощник по истории**")

    st.divider()

    # Проверка API ключа
    if not api_key:
        st.warning(
            "👋 Привет! Чтобы начать, вставь API-ключ OpenAI в **боковую панель** слева.",
            icon="🔑",
        )
        st.info(
            "💡 Ключ можно получить на сайте **platform.openai.com**. "
            "Он выглядит так: `sk-...`"
        )
        st.stop()

    # Инициализация клиента
    client = openai.OpenAI(api_key=api_key)

    # ── ОБЛАСТЬ ЗАГРУЗКИ ИЗОБРАЖЕНИЯ ────────────────────────
    with st.expander("🖼️ Загрузить историческое фото или картину", expanded=False):
        st.markdown(
            "Загрузи фотографию, картину или рисунок. "
            "Я расскажу, что на ней изображено!"
        )
        uploaded_file = st.file_uploader(
            "Выбери файл:",
            type=["jpg", "jpeg", "png", "webp", "bmp"],
            help="Поддерживаются форматы: JPG, PNG, WEBP, BMP",
            label_visibility="collapsed",
        )

        if uploaded_file is not None:
            col_img, col_desc = st.columns([1, 1])
            with col_img:
                st.image(uploaded_file, use_container_width=True, caption="Твоё изображение")

            with col_desc:
                if st.button("🔍 Что это такое?", use_container_width=True, key="analyze_img"):
                    with st.spinner("Смотрю на изображение... 🧐"):
                        uploaded_file.seek(0)
                        description = analyze_image(client, uploaded_file)

                    # Добавляем в историю чата
                    st.session_state.chat_history.append(
                        {"role": "image", "content": description}
                    )

                    # Добавляем контекст в диалог для памяти
                    st.session_state.messages.append(
                        {
                            "role": "user",
                            "content": f"[Ученик загрузил изображение. Вот его описание: {description}] "
                                       f"Расскажи мне об этом подробнее простыми словами.",
                        }
                    )
                    follow_up = get_ai_response(client, st.session_state.messages)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": follow_up}
                    )
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": follow_up}
                    )
                    st.session_state.last_bot_message = follow_up
                    st.session_state.tts_audio = None
                    st.rerun()

    # ── ОБЛАСТЬ ГОЛОСОВОГО ВВОДА ──────────────────────────
    with st.expander("🎤 Задать вопрос голосом", expanded=False):
        st.markdown("Нажми на микрофон, задай вопрос голосом!")
        audio_input = st.audio_input(
            "Запись голоса:",
            key="voice_input",
            label_visibility="collapsed",
        )

        if audio_input is not None:
            if st.button("📝 Распознать и отправить", use_container_width=True, key="transcribe_btn"):
                with st.spinner("Слушаю тебя... 👂"):
                    audio_bytes = audio_input.read()
                    transcribed_text = transcribe_audio(client, audio_bytes)

                if transcribed_text and not transcribed_text.startswith("⚠️"):
                    st.success(f"Я услышал: **{transcribed_text}**")

                    # Добавляем в историю
                    st.session_state.chat_history.append(
                        {"role": "user", "content": transcribed_text, "from_voice": True}
                    )
                    st.session_state.messages.append(
                        {"role": "user", "content": transcribed_text}
                    )

                    with st.spinner("Думаю над ответом... 🤔"):
                        response = get_ai_response(client, st.session_state.messages)

                    st.session_state.messages.append(
                        {"role": "assistant", "content": response}
                    )
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": response}
                    )
                    st.session_state.last_bot_message = response
                    st.session_state.tts_audio = None
                    st.rerun()
                else:
                    st.error(transcribed_text)

    st.divider()

    # ── ИСТОРИЯ ЧАТА ───────────────────────────────────────
    if not st.session_state.chat_history:
        st.markdown(
            """
            <div style="text-align: center; padding: 40px; opacity: 0.6;">
                <div style="font-size: 64px;">🏛️</div>
                <br>
                <b>Привет! Я ИсторяДруг.</b><br>
                Спроси меня про любое историческое событие.<br>
                Можешь написать, сказать голосом или загрузить картинку!
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        render_chat_history(font_size)

    # ── КНОПКА ОЗВУЧИТЬ ПОСЛЕДНИЙ ОТВЕТ ───────────────────
    if st.session_state.last_bot_message:
        st.divider()
        col_tts1, col_tts2, col_tts3 = st.columns([1, 2, 1])
        with col_tts2:
            if st.button(
                "🔊 Озвучить последний ответ",
                use_container_width=True,
                key="tts_button",
                help="Нажми, чтобы услышать ответ вслух",
            ):
                with st.spinner("Готовлю озвучку... 🔊"):
                    audio_data = generate_speech(
                        client, st.session_state.last_bot_message
                    )
                    if audio_data:
                        st.session_state.tts_audio = audio_data

        # Показываем аудиоплеер если есть аудио
        if st.session_state.tts_audio:
            with col_tts2:
                st.audio(st.session_state.tts_audio, format="audio/mp3", autoplay=True)

    # ── ТЕКСТОВЫЙ ВВОД (CHAT INPUT) ─────────────────────────
    user_input = st.chat_input(
        "✏️ Напиши свой вопрос по истории...",
        key="text_input",
    )

    if user_input:
        # Добавляем сообщение пользователя
        st.session_state.chat_history.append(
            {"role": "user", "content": user_input}
        )
        st.session_state.messages.append(
            {"role": "user", "content": user_input}
        )

        # Получаем ответ от ИИ
        with st.spinner("Думаю... 🤔"):
            response = get_ai_response(client, st.session_state.messages)

        # Сохраняем ответ
        st.session_state.messages.append(
            {"role": "assistant", "content": response}
        )
        st.session_state.chat_history.append(
            {"role": "assistant", "content": response}
        )
        st.session_state.last_bot_message = response
        st.session_state.tts_audio = None

        st.rerun()


# ─────────────────────────────────────────────
# ТОЧКА ВХОДА
# ─────────────────────────────────────────────
if __name__ == "__main__":
    main()
