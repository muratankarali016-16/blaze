import streamlit as st
from groq import Groq
import sqlite3
import json
from datetime import datetime
import requests
from io import BytesIO
import PyPDF2
import io

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="BlazeGPT", page_icon="🔥", layout="centered")

# --- ÇEVİRİ SÖZLÜĞÜ ---
CEVIRI = {
    "tr": {
        "dil_adi": "🇹🇷 Türkçe", "baslik": "BlazeGPT",
        "alt_baslik": "Groq + Pollinations ile görsel zekası ⚡",
        "sohbetler": "💬 Sohbetler", "yeni_sohbet": "➕ Yeni Sohbet",
        "sohbet_yok": "Henüz sohbet yok", "ayarlar": "⚙️ Ayarlar",
        "model": "🧠 Model", "kisilik": "🎭 Kişilik",
        "gorsel_modu": "🎨 Görsel Oluşturma",
        "gorsel_olusturuluyor": "🎨 Görsel oluşturuluyor...",
        "pdf_analiz": "📄 PDF Analiz",
        "pdf_yukle": "PDF dosyanı yükle",
        "pdf_ozetle": "📝 Özet Çıkar",
        "pdf_sor": "PDF hakkında bir şey sor...",
        "pdf_isle": "PDF İşleniyor...",
        "hosgeldin": "### Merhaba! Ben BlazeGPT 🔥\n\n- 💬 Sohbet edebilirsin\n- 🎨 Görsel modunu açıp görsel oluşturabilirsin\n- 📄 PDF yükleyip analiz ettirebilirsin\n- 💾 Sohbetlerin **otomatik kaydedilir**\n\n**Hadi başlayalım!** ⬇️",
        "sor": "Bir şey sor...",
        "kisilikler": {
            "Normal Asistan": "Sen yardımcı, nazik ve zeki bir asistansın. Türkçe cevap ver.",
            "Öğretmen": "Sen sabırlı bir öğretmensin. Basit örneklerle anlatırsın. Türkçe cevap ver.",
            "Şair": "Sen duygusal bir şairsin. Şiirsel bir dille yazarsın. Türkçe cevap ver.",
            "Kod Yazıcı": "Sen uzman bir yazılımcısın. Temiz, yorumlu kod yazarsın. Türkçe açıkla.",
            "Komedyen": "Sen esprili bir komedyensin. Mizah katarsın. Türkçe cevap ver."
        },
        "kisilik_isimleri": ["Normal Asistan", "Öğretmen", "Şair", "Kod Yazıcı", "Komedyen"],
        "hata": "⚠️ Hata", "gorsel_hata": "Görsel oluşturulamadı.",
        "gorsel_ayarlari": "🖼️ Görsel Ayarları",
        "gorsel_sayisi": "Görsel Sayısı",
        "gorsel_boyut": "Boyut",
        "kare": "⬛ Kare (1024x1024)",
        "yatay": "▬ Yatay (1280x720)",
        "dikey": "▮ Dikey (720x1280)",
        "indir": "💾 İndir",
        "pdf_hata": "PDF işlenirken hata oluştu."
    },
    "en": {
        "dil_adi": "🇬🇧 English", "baslik": "BlazeGPT",
        "alt_baslik": "Visual intelligence with Groq + Pollinations ⚡",
        "sohbetler": "💬 Chats", "yeni_sohbet": "➕ New Chat",
        "sohbet_yok": "No chats yet", "ayarlar": "⚙️ Settings",
        "model": "🧠 Model", "kisilik": "🎭 Personality",
        "gorsel_modu": "🎨 Image Generation",
        "gorsel_olusturuluyor": "🎨 Generating image...",
        "pdf_analiz": "📄 PDF Analysis",
        "pdf_yukle": "Upload your PDF",
        "pdf_ozetle": "📝 Summarize",
        "pdf_sor": "Ask something about the PDF...",
        "pdf_isle": "Processing PDF...",
        "hosgeldin": "### Hello! I'm BlazeGPT 🔥\n\n- 💬 You can chat\n- 🎨 Turn on image mode\n- 📄 Upload PDF and analyze it\n- 💾 Your chats are **auto-saved**\n\n**Let's start!** ⬇️",
        "sor": "Ask something...",
        "kisilikler": {
            "Normal Assistant": "You are a helpful, kind, and smart assistant. Answer in English.",
            "Teacher": "You are a patient teacher. Explain with simple examples. Answer in English.",
            "Poet": "You are an emotional poet. Write poetically. Answer in English.",
            "Coder": "You are an expert programmer. Write clean, commented code. Explain in English.",
            "Comedian": "You are a funny comedian. Add humor. Answer in English."
        },
        "kisilik_isimleri": ["Normal Assistant", "Teacher", "Poet", "Coder", "Comedian"],
        "hata": "⚠️ Error", "gorsel_hata": "Could not generate image.",
        "gorsel_ayarlari": "🖼️ Image Settings",
        "gorsel_sayisi": "Number of Images",
        "gorsel_boyut": "Size",
        "kare": "⬛ Square (1024x1024)",
        "yatay": "▬ Landscape (1280x720)",
        "dikey": "▮ Portrait (720x1280)",
        "indir": "💾 Download",
        "pdf_hata": "Error processing PDF."
    }
}

# --- ÖZEL CSS ---
st.markdown("""
<style>
    .ana-baslik { text-align: center; background: linear-gradient(90deg, #ff6b35 0%, #f7931e 50%, #ffcc00 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 3.5em; font-weight: bold; margin-bottom: 0; }
    .alt-baslik { text-align: center; color: #888; margin-bottom: 30px; }
    .stChatMessage { border-radius: 15px; padding: 12px 16px; margin-bottom: 10px; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #1a1a1a 0%, #2a1a0a 100%); }
    section[data-testid="stSidebar"] * { color: #e0e0e0 !important; }
    .stButton button { background: linear-gradient(90deg, #ff6b35 0%, #f7931e 100%); color: white; border: none; border-radius: 20px; font-weight: bold; width: 100%; }
    .stDownloadButton button { background: linear-gradient(90deg, #ff6b35 0%, #f7931e 100%); color: white; border: none; border-radius: 15px; font-size: 0.85em; padding: 5px 10px; }
</style>
""", unsafe_allow_html=True)

# --- API ---
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- DİL ---
if "dil" not in st.session_state:
    st.session_state.dil = "tr"

# --- PDF METİN ÇIKARMA ---
def pdf_metin_cikar(uploaded_file):
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.getvalue()))
        metin = ""
        for sayfa in reader.pages:
            extracted = sayfa.extract_text()
            if extracted:
                metin += extracted + "\n"
        return metin[:15000]  # İlk 15000 karakter
    except Exception as e:
        return None

# --- VERİTABANI ---
def db_baglantisi():
    return sqlite3.connect("blazegpt.db", check_same_thread=False)

def db_olustur():
    conn = db_baglantisi()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS sohbetler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            baslik TEXT, olusturma TEXT, guncelleme TEXT, mesajlar TEXT
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
    sid = c.lastrowid
    conn.commit()
    conn.close()
    return sid

def sohbet_getir(sid):
    conn = db_baglantisi()
    c = conn.cursor()
    c.execute("SELECT mesajlar FROM sohbetler WHERE id = ?", (sid,))
    r = c.fetchone()
    conn.close()
    return json.loads(r[0]) if r else []

def sohbet_guncelle(sid, mesajlar):
    conn = db_baglantisi()
    c = conn.cursor()
    simdi = datetime.now().isoformat()
    baslik = "Yeni Sohbet"
    for m in mesajlar:
        if m["role"] == "user" and isinstance(m["content"], str):
            baslik = m["content"][:40] + ("..." if len(m["content"]) > 40 else "")
            break
    c.execute(
        "UPDATE sohbetler SET mesajlar = ?, guncelleme = ?, baslik = ? WHERE id = ?",
        (json.dumps(mesajlar, ensure_ascii=False), simdi, baslik, sid)
    )
    conn.commit()
    conn.close()

def tum_sohbetler():
    conn = db_baglantisi()
    c = conn.cursor()
    c.execute("SELECT id, baslik, guncelleme FROM sohbetler ORDER BY guncelleme DESC")
    r = c.fetchall()
    conn.close()
    return r

def sohbet_sil(sid):
    conn = db_baglantisi()
    c = conn.cursor()
    c.execute("DELETE FROM sohbetler WHERE id = ?", (sid,))
    conn.commit()
    conn.close()

# --- GÖRSEL OLUŞTURMA ---
def gorsel_olustur(prompt, genislik, yukseklik, seed=0):
    try:
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
        params = {"width": genislik, "height": yukseklik, "nologo": "true", "seed": seed}
        r = requests.get(url, params=params, timeout=90)
        if r.status_code == 200:
            return r.content
        return None
    except Exception:
        return None

# --- SESSION STATE ---
if "aktif_sohbet_id" not in st.session_state:
    st.session_state.aktif_sohbet_id = yeni_sohbet()

if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = sohbet_getir(st.session_state.aktif_sohbet_id)

if "pdf_metin" not in st.session_state:
    st.session_state.pdf_metin = ""

if "pdf_mesajlar" not in st.session_state:
    st.session_state.pdf_mesajlar = []

T = CEVIRI[st.session_state.dil]

# --- BAŞLIK ---
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    st.image("logo.png", width=120)
st.markdown(f'<h1 class="ana-baslik">{T["baslik"]}</h1>', unsafe_allow_html=True)
st.markdown(f'<p class="alt-baslik">{T["alt_baslik"]}</p>', unsafe_allow_html=True)

# --- SEKMELER ---
tab1, tab2 = st.tabs(["💬 Sohbet", T["pdf_analiz"]])

# ============ SEKME 1: SOHBET ============
with tab1:
    with st.sidebar:
        st.markdown("## 🌐 Dil / Language")
        secili_dil = st.selectbox(
            "Dil", options=list(CEVIRI.keys()),
            format_func=lambda x: CEVIRI[x]["dil_adi"],
            index=list(CEVIRI.keys()).index(st.session_state.dil),
            label_visibility="collapsed"
        )
        if secili_dil != st.session_state.dil:
            st.session_state.dil = secili_dil
            st.rerun()

        st.markdown("---")
        st.markdown(f"## {T['sohbetler']}")
        if st.button(T["yeni_sohbet"]):
            st.session_state.aktif_sohbet_id = yeni_sohbet()
            st.session_state.mesajlar = []
            st.rerun()
        st.markdown("---")

        sohbetler = tum_sohbetler()
        if sohbetler:
            for s_id, s_baslik, s_tarih in sohbetler:
                c1, c2 = st.columns([5, 1])
                with c1:
                    etiket = f"💬 {s_baslik}"
                    if s_id == st.session_state.aktif_sohbet_id:
                        etiket = f"✅ {s_baslik}"
                    if st.button(etiket, key=f"sohbet_{s_id}"):
                        st.session_state.aktif_sohbet_id = s_id
                        st.session_state.mesajlar = sohbet_getir(s_id)
                        st.rerun()
                with c2:
                    if st.button("🗑️", key=f"sil_{s_id}"):
                        sohbet_sil(s_id)
                        if s_id == st.session_state.aktif_sohbet_id:
                            st.session_state.aktif_sohbet_id = yeni_sohbet()
                            st.session_state.mesajlar = []
                        st.rerun()
        else:
            st.caption(T["sohbet_yok"])

        st.markdown("---")
        st.markdown(f"## {T['ayarlar']}")
        model = st.selectbox(T["model"], ["openai/gpt-oss-20b", "openai/gpt-oss-120b"])
        kisi_secim = st.selectbox(T["kisilik"], T["kisilik_isimleri"])
        kisi = T["kisilikler"][kisi_secim]

        st.markdown("---")
        gorsel_modu = st.toggle(T["gorsel_modu"], value=False)

        if gorsel_modu:
            st.markdown(f"### {T['gorsel_ayarlari']}")
            gorsel_sayisi = st.slider(T["gorsel_sayisi"], min_value=1, max_value=4, value=4)
            boyut_secim = st.radio(T["gorsel_boyut"], [T["kare"], T["yatay"], T["dikey"]])
            if boyut_secim == T["kare"]:
                genislik, yukseklik = 1024, 1024
            elif boyut_secim == T["yatay"]:
                genislik, yukseklik = 1280, 720
            else:
                genislik, yukseklik = 720, 1280

    if not st.session_state.mesajlar:
        with st.chat_message("assistant", avatar="🔥"):
            st.markdown(T["hosgeldin"])

    for m in st.session_state.mesajlar:
        avatar = "👤" if m["role"] == "user" else "🔥"
        with st.chat_message(m["role"], avatar=avatar):
            if isinstance(m["content"], str):
                st.markdown(m["content"])

    if soru := st.chat_input(T["sor"]):
        st.session_state.mesajlar.append({"role": "user", "content": soru})
        with st.chat_message("user", avatar="👤"):
            st.markdown(soru)

        with st.chat_message("assistant", avatar="🔥"):
            if gorsel_modu:
                with st.spinner(T["gorsel_olusturuluyor"]):
                    st.markdown(f"**{soru}**")
                    gorseller = []
                    for i in range(gorsel_sayisi):
                        veri = gorsel_olustur(soru, genislik, yukseklik, seed=i*1000)
                        if veri:
                            gorseller.append(veri)
                    if gorseller:
                        if len(gorseller) == 1:
                            st.image(BytesIO(gorseller[0]), use_container_width=True)
                            st.download_button(label=T["indir"], data=gorseller[0], file_name="blazegpt_1.png", mime="image/png")
                        else:
                            for i in range(0, len(gorseller), 2):
                                cols = st.columns(2)
                                for j, col in enumerate(cols):
                                    idx = i + j
                                    if idx < len(gorseller):
                                        with col:
                                            st.image(BytesIO(gorseller[idx]), use_container_width=True)
                                            st.download_button(label=T["indir"], data=gorseller[idx], file_name=f"blazegpt_{idx+1}.png", mime="image/png", key=f"indir_{idx}")
                        cevap = f"🖼️ {len(gorseller)} görsel oluşturuldu: {soru}"
                    else:
                        st.error(T["gorsel_hata"])
                        cevap = T["gorsel_hata"]
            else:
                yer = st.empty()
                tam = ""
                try:
                    stream = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "system", "content": kisi}] + st.session_state.mesajlar,
                        stream=True
                    )
                    for parca in stream:
                        icerik = parca.choices[0].delta.content or ""
                        tam += icerik
                        yer.markdown(tam + "▌")
                    yer.markdown(tam)
                    cevap = tam
                except Exception as e:
                    yer.error(f"{T['hata']}: {e}")
                    cevap = "Hata"

        st.session_state.mesajlar.append({"role": "assistant", "content": cevap})
        sohbet_guncelle(st.session_state.aktif_sohbet_id, st.session_state.mesajlar)

# ============ SEKME 2: PDF ANALİZ ============
with tab2:
    st.markdown(f"### {T['pdf_yukle']}")
    uploaded_pdf = st.file_uploader("PDF", type=["pdf"], label_visibility="collapsed")

    if uploaded_pdf:
        if st.session_state.pdf_metin == "":
            with st.spinner(T["pdf_isle"]):
                metin = pdf_metin_cikar(uploaded_pdf)
                if metin:
                    st.session_state.pdf_metin = metin
                    st.session_state.pdf_mesajlar = []
                    st.success("✅ PDF yüklendi! Artık soru sorabilirsin.")
                else:
                    st.error(T["pdf_hata"])

        if st.session_state.pdf_metin:
            # Özet butonu
            if st.button(T["pdf_ozetle"]):
                with st.spinner("Özet çıkarılıyor..."):
                    try:
                        cevap = client.chat.completions.create(
                            model="openai/gpt-oss-20b",
                            messages=[
                                {"role": "system", "content": "Sen yardımcı bir asistansın. Verilen metni Türkçe olarak kısa ve öz bir şekilde özetle."},
                                {"role": "user", "content": f"Şu metni özetle:\n\n{st.session_state.pdf_metin[:8000]}"}
                            ]
                        )
                        ozet = cevap.choices[0].message.content
                        st.session_state.pdf_mesajlar.append({"role": "assistant", "content": f"📝 **Özet:**\n\n{ozet}"})
                        st.rerun()
                    except Exception as e:
                        st.error(f"Hata: {e}")

            # PDF sohbet geçmişi
            for m in st.session_state.pdf_mesajlar:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])

            # PDF soru sorma
            pdf_soru = st.chat_input(T["pdf_sor"])
            if pdf_soru:
                st.session_state.pdf_mesajlar.append({"role": "user", "content": pdf_soru})
                with st.chat_message("user"):
                    st.markdown(pdf_soru)

                with st.chat_message("assistant"):
                    yer = st.empty()
                    tam = ""
                    try:
                        stream = client.chat.completions.create(
                            model="openai/gpt-oss-20b",
                            messages=[
                                {"role": "system", "content": "Sen yardımcı bir asistansın. Sadece verilen PDF metnine dayanarak soruları Türkçe cevapla. Bilmiyorsan 'Bu bilgi PDF'te yok' de."},
                                {"role": "user", "content": f"PDF Metni:\n\n{st.session_state.pdf_metin[:8000]}\n\nSoru: {pdf_soru}"}
                            ],
                            stream=True
                        )
                        for parca in stream:
                            icerik = parca.choices[0].delta.content or ""
                            tam += icerik
                            yer.markdown(tam + "▌")
                        yer.markdown(tam)
                    except Exception as e:
                        yer.error(f"{T['hata']}: {e}")
                        tam = "Hata"

                st.session_state.pdf_mesajlar.append({"role": "assistant", "content": tam})
