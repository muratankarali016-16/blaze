import streamlit as st
from groq import Groq

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="BlazeGPT",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- ÖZEL CSS (Görünüm) ---
st.markdown("""
<style>
    /* Ana başlık - gradient */
    .ana-baslik {
        text-align: center;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3em;
        font-weight: bold;
        margin-bottom: 0;
    }
    .alt-baslik {
        text-align: center;
        color: #888;
        margin-top: 0;
        margin-bottom: 30px;
        font-size: 0.95em;
    }
    /* Sohbet balonları */
    .stChatMessage {
        border-radius: 15px;
        padding: 12px 16px;
        margin-bottom: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    /* Giriş kutusu */
    .stChatInput textarea {
        border-radius: 25px !important;
        border: 2px solid #667eea !important;
    }
    /* Kenar çubuğu koyu tema */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e1e2e 0%, #2a2a3e 100%);
    }
    section[data-testid="stSidebar"] * {
        color: #e0e0e0 !important;
    }
    /* Buton */
    .stButton button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 20px;
        font-weight: bold;
        width: 100%;
    }
    .stButton button:hover {
        opacity: 0.85;
        transform: scale(1.02);
        transition: 0.2s;
    }
</style>
""", unsafe_allow_html=True)

# --- BAŞLIK ---
st.markdown('<h1 class="ana-baslik">🤖 BlazeGPT</h1>', unsafe_allow_html=True)
st.markdown('<p class="alt-baslik">Hızlı yapay zeka asistanı ⚡</p>', unsafe_allow_html=True)

# --- API (Streamlit Cloud + Yerel uyumlu) ---
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- SESSION STATE ---
if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = []
if "isim" not in st.session_state:
    st.session_state.isim = "Kullanıcı"

# --- KENAR ÇUBUĞU ---
with st.sidebar:
    st.markdown("## ⚙️ Ayarlar")
    
    st.session_state.isim = st.text_input("👤 Adın", value=st.session_state.isim)
    
    model = st.selectbox("🧠 Model", [
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b"
    ])
    
    # Kişilik seçenekleri
    kisi_secim = st.selectbox("🎭 Kişilik", [
        "Normal Asistan",
        "Öğretmen",
        "Şair",
        "Kod Yazıcı",
        "Komedyen",
        "Özel"
    ])
    
    # Kişilik metinleri
    kisilikler = {
        "Normal Asistan": "Sen yardımcı, nazik ve zeki bir asistansın. Türkçe cevap ver.",
        "Öğretmen": "Sen sabırlı bir öğretmensin. Konuları basit örneklerle, adım adım anlatırsın. Türkçe cevap ver.",
        "Şair": "Sen duygusal bir şairsin. Cevaplarını şiirsel, edebi bir dille yazarsın. Türkçe cevap ver.",
        "Kod Yazıcı": "Sen uzman bir yazılımcısın. Kod sorularına temiz, yorumlu ve çalışan kodlarla cevap verirsin. Türkçe açıklama yap.",
        "Komedyen": "Sen esprili bir komedyensin. Cevaplarına mizah katarsın ama bilgiyi doğru verirsin. Türkçe cevap ver.",
        "Özel": ""
    }
    
    if kisi_secim == "Özel":
        kisi = st.text_area("Kişilik talimatı", value="Sen yardımcı bir asistansın.")
    else:
        kisi = kisilikler[kisi_secim]
        st.caption(f"_{kisi[:80]}..._")
    
    st.markdown("---")
    
    if st.button("🗑️ Sohbeti Temizle"):
        st.session_state.mesajlar = []
        st.rerun()
    
    st.markdown("---")
    st.caption("💡 İpucu: 120B modeli daha zeki ama daha yavaş")

# --- HOŞGELDİN MESAJI ---
if not st.session_state.mesajlar:
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown(f"""
### Merhaba {st.session_state.isim}! 👋

Ben senin kişisel yapay zekâ asistanınım. Bana şunları sorabilirsin:

- 💡 **Fikir ve öneriler**
- 📝 **Yazı yazma / düzeltme**
- 🧮 **Matematik ve kod**
- 🌍 **Genel bilgi**
- 💬 **Sohbet**

**Hadi başlayalım!** Aşağıdaki kutuya bir şey yaz. ⬇️
        """)

# --- ESKİ MESAJLAR ---
for m in st.session_state.mesajlar:
    avatar = "👤" if m["role"] == "user" else "🤖"
    with st.chat_message(m["role"], avatar=avatar):
        st.markdown(m["content"])

# --- GİRİŞ ---
if soru := st.chat_input(f"{st.session_state.isim}, bir şey sor..."):
    st.session_state.mesajlar.append({"role": "user", "content": soru})
    with st.chat_message("user", avatar="👤"):
        st.markdown(soru)
    
    with st.chat_message("assistant", avatar="🤖"):
        yer = st.empty()
        tam = ""
        
        try:
            stream = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": kisi}]
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
            tam = "Üzgünüm, bir hata oluştu."
    
    st.session_state.mesajlar.append({"role": "assistant", "content": tam})
