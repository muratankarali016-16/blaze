import streamlit as st
from groq import Groq
import sqlite3
import json
from datetime import datetime
import requests
from io import BytesIO

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="BlazeGPT", page_icon="🔥", layout="centered")

# --- ÖZEL CSS ---
st.markdown("""
<style>
    .ana-baslik {
        text-align: center;
        background: linear-gradient(90deg, #ff6b35 0%, #f7931e 50%, #ffcc00 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3.5em;
        font-weight: bold;
        margin-bottom: 0;
    }
    .alt-baslik { text-align: center; color: #888; margin-bottom: 30px; }
    .stChatMessage { border-radius: 15px; padding: 12px 16px; margin-bottom: 10px; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #1a1a1a 0%, #2a1a0a 100%); }
    section[data-testid="stSidebar"] * { color: #e0e0e0 !important; }
    .stButton button {
        background: linear-gradient(90deg, #ff6b35 0%, #f7931e 100%);
        color: white; border: none; border-radius: 20px;
        font-weight: bold; width: 100%;
    }
    .stButton button:hover { opacity: 0.85; }
</style>
""", unsafe_allow_html=True)

# --- API ---
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- VERİTABANI ---
def db_baglantisi():
    return sqlite3.connect("blazegpt.db", check_same_thread=False)

def db_olustur():
    conn = db_baglantisi()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS sohbetler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            baslik TEXT,
            olusturma TEXT,
            guncelleme TEXT,
            mesajlar TEXT
        )
    """)
    conn.commit()
    conn.close()

db_olustur()

def yeni_sohbet(baslik="Yeni Sohbet"):
    conn = db_baglantisi()
    c = conn.cursor()
    simdi = datetime.now().isoformat()
    c.execute(
        "INSERT INTO sohbetler (baslik, olusturma, guncelleme, mesajlar) VALUES (?, ?, ?, ?)",
        (baslik, simdi, simdi, "[]")
    )
    sohbet_id = c.lastrowid
    conn.commit()
    conn.close()
    return sohbet_id

def sohbet_getir(sohbet_id):
    conn = db_baglantisi()
    c = conn.cursor()
    c.execute("SELECT mesajlar FROM sohbetler WHERE id = ?", (sohbet_id,))
    sonuc = c.fetchone()
    conn.close()
    return json.loads(sonuc[0]) if sonuc else []

def sohbet_guncelle(sohbet_id, mesajlar):
    conn = db_baglantisi()
    c = conn.cursor()
    simdi = datetime.now().isoformat()
    baslik = "Yeni Sohbet"
    for m in mesajlar:
        if m["role"] == "user" and isinstance(m["content"], str):
            baslik = m["content"][:40]
            if len(m["content"]) > 40:
                baslik += "..."
            break
    c.execute(
        "UPDATE sohbetler SET mesajlar = ?, guncelleme = ?, baslik = ? WHERE id = ?",
        (json.dumps(mesajlar, ensure_ascii=False), simdi, baslik, sohbet_id)
    )
    conn.commit()
    conn.close()

def tum_sohbetler():
    conn = db_baglantisi()
    c = conn.cursor()
    c.execute("SELECT id, baslik, guncelleme FROM sohbetler ORDER BY guncelleme DESC")
    sonuc = c.fetchall()
    conn.close()
    return sonuc

def sohbet_sil(sohbet_id):
    conn = db_baglantisi()
    c = conn.cursor()
    c.execute("DELETE FROM sohbetler WHERE id = ?", (sohbet_id,))
    conn.commit()
    conn.close()

# --- SESSION STATE ---
if "aktif_sohbet_id" not in st.session_state:
    st.session_state.aktif_sohbet_id = yeni_sohbet()

if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = sohbet_getir(st.session_state.aktif_sohbet_id)

# --- BAŞLIK (LOGO + İSİM) ---
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    st.image("logo.png", width=120)
st.markdown('<h1 class="ana-baslik">BlazeGPT</h1>', unsafe_allow_html=True)
st.markdown('<p class="alt-baslik">Groq + Pollinations ile görsel zekası ⚡</p>', unsafe_allow_html=True)

# --- KENAR ÇUBUĞU ---
with st.sidebar:
    st.markdown("## 💬 Sohbetler")
    
    if st.button("➕ Yeni Sohbet"):
        st.session_state.aktif_sohbet_id = yeni_sohbet()
        st.session_state.mesajlar = []
        st.rerun()
    
    st.markdown("---")
    
    sohbetler = tum_sohbetler()
    if sohbetler:
        for s_id, s_baslik, s_tarih in sohbetler:
            col1, col2 = st.columns([5, 1])
            with col1:
                etiket = f"💬 {s_baslik}"
                if s_id == st.session_state.aktif_sohbet_id:
                    etiket = f"✅ {s_baslik}"
                if st.button(etiket, key=f"sohbet_{s_id}"):
                    st.session_state.aktif_sohbet_id = s_id
                    st.session_state.mesajlar = sohbet_getir(s_id)
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"sil_{s_id}"):
                    sohbet_sil(s_id)
                    if s_id == st.session_state.aktif_sohbet_id:
                        st.session_state.aktif_sohbet_id = yeni_sohbet()
                        st.session_state.mesajlar = []
                    st.rerun()
    else:
        st.caption("Henüz sohbet yok")
    
    st.markdown("---")
    st.markdown("## ⚙️ Ayarlar")
    
    model = st.selectbox("🧠 Model", [
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b"
    ])
    
    kisi_secim = st.selectbox("🎭 Kişilik", [
        "Normal Asistan", "Öğretmen", "Şair", "Kod Yazıcı", "Komedyen"
    ])
    
    kisilikler = {
        "Normal Asistan": "Sen yardımcı, nazik ve zeki bir asistansın. Türkçe cevap ver.",
        "Öğretmen": "Sen sabırlı bir öğretmensin. Basit örneklerle anlatırsın. Türkçe cevap ver.",
        "Şair": "Sen duygusal bir şairsin. Şiirsel bir dille yazarsın. Türkçe cevap ver.",
        "Kod Yazıcı": "Sen uzman bir yazılımcısın. Temiz, yorumlu kod yazarsın. Türkçe açıkla.",
        "Komedyen": "Sen esprili bir komedyensin. Mizah katarsın. Türkçe cevap ver."
    }
    kisi = kisilikler[kisi_secim]
    
    st.markdown("---")
    st.markdown("### 🎨 Görsel Modu")
    gorsel_modu = st.toggle("Görsel Oluşturma", value=False)

# --- HOŞGELDİN ---
if not st.session_state.mesajlar:
    with st.chat_message("assistant", avatar="🔥"):
        st.markdown("""
### Merhaba! Ben BlazeGPT 🔥

- 💬 Sohbet edebilirsin
- 🎨 Görsel modunu açıp görsel oluşturabilirsin
- 💾 Sohbetlerin **otomatik kaydedilir**

**Hadi başlayalım!** ⬇️
        """)

# --- ESKİ MESAJLAR ---
for m in st.session_state.mesajlar:
    avatar = "👤" if m["role"] == "user" else "🔥"
    with st.chat_message(m["role"], avatar=avatar):
        if isinstance(m["content"], str):
            st.markdown(m["content"])

# --- GİRİŞ ---
if soru := st.chat_input("Bir şey sor..."):
    st.session_state.mesajlar.append({"role": "user", "content": soru})
    with st.chat_message("user", avatar="👤"):
        st.markdown(soru)
    
    with st.chat_message("assistant", avatar="🔥"):
        if gorsel_modu:
            with st.spinner("🎨 Görsel oluşturuluyor..."):
                try:
                    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(soru)}?width=1024&height=1024&nologo=true"
                    r = requests.get(url, timeout=60)
                    if r.status_code == 200:
                        st.image(BytesIO(r.content), caption=soru, use_container_width=True)
                        cevap = f"🖼️ Oluşturulan görsel: {soru}"
                    else:
                        st.error("Görsel oluşturulamadı.")
                        cevap = "Görsel oluşturulamadı."
                except Exception as e:
                    st.error(f"Hata: {e}")
                    cevap = "Hata oluştu."
        else:
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
                cevap = tam
            except Exception as e:
                yer.error(f"⚠️ Hata: {e}")
                cevap = "Hata oluştu."
    
    st.session_state.mesajlar.append({"role": "assistant", "content": cevap})
    sohbet_guncelle(st.session_state.aktif_sohbet_id, st.session_state.mesajlar)
