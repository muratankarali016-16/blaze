import streamlit as st
from groq import Groq

st.set_page_config(page_title="Benim ChatGPT'm", page_icon="🤖")
st.title("🤖 Benim ChatGPT'm")

# ⚠️ BURAYA KENDİ API KEY'İNİ YAPIŞTIR
client = Groq(api_key=st.secrets["GROQ_API_KEY"])
if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = []

with st.sidebar:
    st.header("⚙️ Ayarlar")
    model = st.selectbox("Model", [
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b"
    ])
    if st.button("🗑️ Sohbeti Temizle"):
        st.session_state.mesajlar = []
        st.rerun()

for m in st.session_state.mesajlar:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if soru := st.chat_input("Bir şey sor..."):
    st.session_state.mesajlar.append({"role": "user", "content": soru})
    with st.chat_message("user"):
        st.markdown(soru)

    with st.chat_message("assistant"):
        yer = st.empty()
        tam = ""
        try:
            stream = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": "Sen yardımcı bir asistansın. Türkçe cevap ver."}]
                         + st.session_state.mesajlar,
                stream=True
            )
            for parca in stream:
                icerik = parca.choices[0].delta.content or ""
                tam += icerik
                yer.markdown(tam + "▌")
            yer.markdown(tam)
        except Exception as e:
            yer.error(f"⚠️ Hata: {e}")
            tam = "Hata oluştu."
    st.session_state.mesajlar.append({"role": "assistant", "content": tam})
