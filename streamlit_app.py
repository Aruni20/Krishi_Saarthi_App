import streamlit as st
import pandas as pd
import time
from gtts import gTTS
import tempfile
import altair as alt
import json
from deep_translator import GoogleTranslator  

# -------------------------------
# Define Language Options
# -------------------------------
LANG_OPTIONS = {
    "Hindi": "hi",
    "Bengali": "bn",
    "Tamil": "ta",
    "Telugu": "te",
    "Malayalam": "ml",
    "Gujarati": "gu",
    "Kannada": "kn",
    "Marathi": "mr"
}

# -------------------------------
# Load Best Crop CSV
# -------------------------------
@st.cache_data
def load_crop_data():
    return pd.read_csv("best_crops_india.csv")

crop_df = load_crop_data()

# -------------------------------
# gTTS Audio Function
# -------------------------------
def generate_audio(text, lang='en'):
    tts = gTTS(text=text, lang=lang)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        tts.save(fp.name)
        with open(fp.name, "rb") as audio_file:
            audio_bytes = audio_file.read()
        return audio_bytes

# -------------------------------
# Translation using deep-translator
# -------------------------------
def translate_text(text, dest_lang):
    try:
        translated = GoogleTranslator(source='auto', target=dest_lang).translate(text)
        return translated
    except Exception as e:
        return f"[Translation Error] {text}"

# -------------------------------
# Load Crop Farming Advice JSON
# -------------------------------
@st.cache_data
def load_crop_advice():
    with open("crop_farming_advice.json", "r", encoding="utf-8") as f:
        return json.load(f)

crop_advice = load_crop_advice()

# -------------------------------
# Sidebar: Location Input + Language Selection + Recommendation
# -------------------------------
with st.sidebar:
    st.header("🌱 KrishiSaarthi-: Smart Advisor")

    states = sorted(crop_df["State"].unique())
    selected_state = st.selectbox("State", states)

    districts = sorted(crop_df[crop_df["State"] == selected_state]["District"].unique())
    selected_district = st.selectbox("District", districts)

    selected_lang_label = st.selectbox(
        "🌐 Select Preferred Language for Audio",
        list(LANG_OPTIONS.keys())
    )
    lang_code = LANG_OPTIONS[selected_lang_label]

    if "recommended_crop" not in st.session_state:
        st.session_state.recommended_crop = None
    if "recommendation_audio" not in st.session_state:
        st.session_state.recommendation_audio = None

    if st.button("🔘 Get Recommendation"):
        with st.spinner("Fetching recommendation... ⏳"):
            time.sleep(2)
        result = crop_df[
            (crop_df["State"] == selected_state) &
            (crop_df["District"] == selected_district)
        ]
        if not result.empty:
            recommended_crop = result.iloc[0]["Best Crop"]
            st.session_state.recommended_crop = recommended_crop

            audio_text = f"The recommended crop for {selected_district}, {selected_state} is {recommended_crop}."
            translated_text = translate_text(audio_text, dest_lang=lang_code)
            audio_bytes = generate_audio(translated_text, lang=lang_code)
            st.session_state.recommendation_audio = audio_bytes
        else:
            st.session_state.recommended_crop = None
            st.session_state.recommendation_audio = None
            st.warning("No recommendation found for this district.")

    # ✅ Display Recommendation & Description in Sidebar
    if st.session_state.recommended_crop:
        recommended_crop = st.session_state.recommended_crop
        recommendation_audio = st.session_state.recommendation_audio

        crop_key = recommended_crop.lower()
        st.success("✅ RECOMMENDED CROP")
        st.markdown(f"You should grow: 🌾 **{recommended_crop}**")

        if recommendation_audio:
            st.audio(recommendation_audio, format="audio/mp3")

        crop_desc_en = crop_advice.get(crop_key, {}).get("crop_description", "")
        if crop_desc_en:
            st.markdown("🎯 **Crop Description:**")
            st.markdown(f"*{crop_desc_en}*")
            if st.button("▶️ 🔊 फ़सल विवरण सुनें (Selected Language Audio)", key="crop_audio_sidebar"):
                translated_desc = translate_text(crop_desc_en, dest_lang=lang_code)
                audio_bytes = generate_audio(translated_desc, lang=lang_code)
                st.audio(audio_bytes, format="audio/mp3")

# -------------------------------
# Main Area: Farming Style Visualization
# -------------------------------
@st.cache_data
def load_farming_json():
    with open("corrected_crops.json", "r") as f:
        return json.load(f)

style_data_json = load_farming_json()

recommended_crop = st.session_state.recommended_crop
if recommended_crop:
    crop_key = recommended_crop.lower()
    if crop_key in style_data_json:
        crop_info = style_data_json[crop_key]
        chart_data = crop_info["chart"]["data"]
        labels = chart_data["labels"]

        rows = []
        for dataset in chart_data["datasets"]:
            metric = dataset["label"]
            for cluster, value in zip(labels, dataset["data"]):
                rows.append({"Cluster": cluster, "Metric": metric, "Value": value})
        df_long = pd.DataFrame(rows)

        st.title("📊 FARMING STYLE VISUALIZATION")
        st.markdown("---")
        st.subheader(f"📈 {recommended_crop} Farming Style Insights")

        style_desc_en = crop_advice.get(crop_key, {}).get("visualization_description", "")
        if style_desc_en:
            st.markdown(f"🔍 *{style_desc_en}*")
            if st.button("▶️ 🔊 शैली विवरण सुनें (Selected Language Audio)"):
                translated_desc = translate_text(style_desc_en, dest_lang=lang_code)
                audio_bytes = generate_audio(translated_desc, lang=lang_code)
                st.audio(audio_bytes, format="audio/mp3")

        chart = alt.Chart(df_long).mark_bar().encode(
            x=alt.X("Cluster:N", title="Cluster (Region, Soil)"),
            y=alt.Y("Value:Q"),
            color=alt.Color("Metric:N", title="Metric"),
            tooltip=["Metric", "Cluster", "Value"]
        ).properties(height=350).configure_axis(
            labelFontSize=12, titleFontSize=14
        ).configure_legend(
            titleFontSize=12, labelFontSize=11
        )
        st.altair_chart(chart, use_container_width=True)

        # Common Practices
        common_intro = crop_advice.get(crop_key, {}).get("common_practices_introduction", "")
        practices_list = crop_advice.get(crop_key, {}).get("farming_practices", [])

        if common_intro and practices_list:
            st.markdown("📌 **Common Farming Practices:**")
            st.markdown(f"*{common_intro}*")

            full_text = common_intro + " "
            for practice in practices_list:
                practice_text = f"Cluster {practice['Cluster']}: {practice['Explanation']}"
                st.markdown(f"🔹 **{practice_text}**")
                full_text += practice_text + " "

            if st.button("▶️ 🔊 Translate & Speak Common Practices"):
                translated_text = translate_text(full_text, dest_lang=lang_code)
                st.markdown(f"📝 *{translated_text}*")
                audio_bytes = generate_audio(translated_text, lang=lang_code)
                st.audio(audio_bytes, format="audio/mp3")

        # Best Practice Recommendation
        best_dict = crop_advice.get(crop_key, {}).get("best_practice_recommendation", {})
        if best_dict:
            st.subheader("🧠 BEST Practice Recommendation")
            st.markdown("🌟 **Best Practice Recommendation:**")
            english_advice = best_dict.get("Advice", "")
            st.markdown(f"✅ *{english_advice}*")

            if st.button("▶️ 🔊 Translate & Speak Best Practice"):
                translated_best = translate_text(english_advice, dest_lang=lang_code)
                st.markdown(f"✨ *\"{translated_best}\"*")
                audio_bytes = generate_audio(translated_best, lang=lang_code)
                st.audio(audio_bytes, format="audio/mp3")

# -------------------------------
# Local Crop News
# -------------------------------
st.markdown("---")
st.subheader("📰 LOCAL CROP NEWS")

news_hi = "14 जुलाई को बिहार में मक्का किसानों के लिए 2000 रुपये की सब्सिडी की घोषणा की गई।"
st.markdown("📅 **July 14**: *\"₹2000 subsidy announced for maize farmers in Bihar.\"*")
st.markdown(f"📝 *\"{news_hi}\"*")

if st.button("▶️ 🔊 Listen to News in Hindi"):
    audio_bytes = generate_audio(news_hi, lang="hi")
    st.audio(audio_bytes, format="audio/mp3")
