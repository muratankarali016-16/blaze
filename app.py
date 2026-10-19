import streamlit as st
from groq import Groq
from tavily import TavilyClient
import sqlite3
import json
from datetime import datetime
import requests
from io import BytesIO
import uuid
import base64
from pypdf import PdfReader
import pandas as pd
import yfinance as yf
import hashlib

st.set_page_config(page_title="BlazeX - Ultimate Asistan", page_icon="🔥", layout="wide")

# --- ÇEVİRİ ---
CEVIRI = {
    "tr": {
        "baslik": "BlazeX", "alt_baslik": "Düşünen, Sesli ve Akıllı Asistan ⚡",
        "ayarlar": "⚙️ Ayarlar", "model": "🧠 Model", "kisilik": "🎭 Kişilik",
        "hosgeldin": "Merhaba! Ben BlazeX 🔥 Benimle sohbet edebilir, oyun oynayabilir, kod yazdırabilirsin!",
        "sor": "Bir şey sor...", "hata": "⚠️ Hata",
        "disa_aktar": "📥 Sohbeti İndir", "vision_analiz": "🔍 Görseli Analiz Et",
        "sesli_dinle": "🔊 Dinle", "kopyala": "📋", "kaynaklar": "🌐 Kaynaklar:",
        "aydinlatma": "📜 Gizlilik", "aydinlatma_metni": "Bu uygulama KVKK kapsamında verilerinizi işlemektedir. Sohbetleriniz Groq (ABD) ve Tavily (ABD) sunucularına aktarılır. Lütfen kişisel bilgilerinizi yazmayın.",
        "gecmis": "📚 Geçmiş Sohbetler", "pdf_oku": "📄 PDF Yükle", "otomatik_ses": "🔊 Otomatik Ses",
        "kamera": "📸 Kamera", "hafiza": "🧠 Yapay Zeka Hafızası", "veri_analizi": "📊 Excel/CSV",
        "oyun_modu": "🎮 Oyun Modu", "kod_calistirici": "💻 Kod Çalıştırıcı", "finans": "📈 Canlı Finans",
        "dedektif": "🕵️ Dedektif", "mimar": "🎨 Mimar", "rutin": "⚡ Rutin Planlayıcı",
        "pdf_ses": "📚 PDF Seslendirici"
    }
}

KISILIKLER = {
    "Normal": "Sen BlazeX adında samimi ve yardımcı bir asistansın. Türkçe cevap ver. Robotik olma.",
    "Dedektif": "Sen Sherlock Holmes gibi zeki bir dedektifsin. Gizli anlamları bulursun.",
    "Mimar": "Sen uzman bir iç mimarsın. Tasarım planı ve eşya listesi çıkarırsın.",
    "Oyun Ustası": "Sen bir RPG oyun yöneticisisin. Kullanıcıya seçenekler sunarak hikaye yazarsın."
}

MODELLER = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b"]
VISION_MODEL = "qwen/qwen3.8-27b"

# --- SESSION STATE ---
if "kullanici_id" not in st.session_state: st.session_state.kullanici_id = str(uuid.uuid4())[:8]
if "mesajlar" not in st.session_state: st.session_state.mesajlar = []
if "hafiza" not in st.session_state: st.session_state.hafiza = ""
if "otomatik_ses" not in st.session_state: st.session_state.otomatik_ses = False
if "onay_verildi" not in st.session_state: st.session_state.onay_verildi = False
if "pdf_metin" not in st.session_state: st.session_state.pdf_metin = ""
if "sayfa" not in st.session_state: st.session_state.sayfa = "anasayfa"

# --- VERİTABANI ---
def db_baglantisi(): return sqlite3.connect("blazegpt.db", check_same_thread=False)
def db_olustur():
    c = db_baglantisi().cursor()
    c.execute("CREATE TABLE IF NOT EXISTS sohbetler (id INTEGER PRIMARY KEY AUTOINCREMENT, kullanici_id TEXT, baslik TEXT, mesajlar TEXT)")
    db_baglantisi().commit()
db_olustur()

def kaydet_sohbet(mesajlar, k_id):
    baslik = "Sohbet"
    for m in mesajlar:
        if m["role"] == "user" and isinstance(m["content"], str):
            baslik = m["content"][:30]; break
    c = db_baglantisi().cursor()
    c.execute("INSERT INTO sohbetler (kullanici_id, baslik, mesajlar) VALUES (?, ?, ?)", (k_id, baslik, json.dumps(mesajlar, ensure_ascii=False)))
    db_baglantisi().commit()

def pdf_metin_cikar(dosya):
    try:
        reader = PdfReader(BytesIO(dosya.getvalue()))
        metin = ""
        for sayfa in reader.pages:
            metin += sayfa.extract_text() + "\n"
        return metin[:5000]
    except: return None

client = Groq(api_key=st.secrets["GROQ_API_KEY"])
tavily = TavilyClient(api_key=st.secrets.get("TAVILY_API_KEY", ""))

def sesli_oku(metin):
    safe_metin = metin.replace('"', '\\"').replace('\n', ' ')
    js = f"<script>var msg = new SpeechSynthesisUtterance(\"{safe_metin}\"); msg.lang = 'tr-TR'; window.speechSynthesis.speak(msg);</script>"
    st.components.v1.html(js, height=0)

# --- SAYFA YÖNLENDİRME ---
if not st.session_state.onay_verildi:
    st.warning("⚠️ Devam etmek için lütfen aydınlatma metnini kabul edin.")
    with st.container(border=True): st.write(CEVIRI["tr"]["aydinlatma_metni"])
    if st.button("✅ Kabul Ediyorum", type="primary"): st.session_state.onay_verildi = True; st.rerun()
    st.stop()

if st.session_state.sayfa == "anasayfa":
    st.markdown("<h1 style='text-align: center; color: #4d6bfe; font-size: 4em;'>🔥 BlazeX</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 1.2em;'>Geleceğin Yapay Zeka Asistanı</p>", unsafe_allow_html=True)
    if st.button("🚀 Hemen Başla", use_container_width=True, type="primary"):
        st.session_state.sayfa = "uygulama"; st.rerun()
    st.stop()

if st.session_state.sayfa == "uygulama":
    with st.sidebar:
        st.markdown(f"### 👤 Oturum: {st.session_state.kullanici_id}")
        if st.button("🚪 Ana Sayfa"): st.session_state.sayfa = "anasayfa"; st.rerun()
        st.markdown("---")
        
        model = st.selectbox(CEVIRI["tr"]["model"], MODELLER, index=0) 
        kisi_secim = st.selectbox(CEVIRI["tr"]["kisilik"], list(KISILIKLER.keys()))
        kisi = KISILIKLER[kisi_secim]
            
        st.markdown("---")
        
        with st.expander(CEVIRI["tr"]["hafiza"]):
            hafiza_input = st.text_area("Hafıza:", value=st.session_state.hafiza)
            if st.button("🧠 Kaydet"): st.session_state.hafiza = hafiza_input

        with st.expander(CEVIRI["tr"]["finans"]):
            sembol = st.text_input("Sembol (Örn: BTC-USD, THYAO.IS)")
            if st.button("Fiyat Getir"):
                try:
                    hisse = yf.Ticker(sembol); veri = hisse.history(period="1d")
                    if not veri.empty: st.success(f"**{sembol}**: {veri['Close'].iloc[-1]:.2f}")
                except: st.error("Bulunamadı.")

        with st.expander(CEVIRI["tr"]["kod_calistirici"]):
            kod = st.text_area("Python:")
            if st.button("Çalıştır"):
                try:
                    local_vars = {}
                    exec(kod, {}, local_vars)
                    st.success("Çalıştı!"); st.write(local_vars)
                except Exception as e: st.error(f"Hata: {e}")

        with st.expander(CEVIRI["tr"]["pdf_ses"]):
            pdf_file = st.file_uploader("PDF Yükle", type=["pdf"])
            if pdf_file:
                if st.button("📚 PDF'i Oku"):
                    metin = pdf_metin_cikar(pdf_file)
                    if metin:
                        st.session_state.pdf_metin = metin
                        st.success("Hazır!")
            if st.session_state.pdf_metin:
                if st.button("🔊 Dinlemeye Başla"):
                    sesli_oku(st.session_state.pdf_metin)

        st.markdown("---")
        st.session_state.otomatik_ses = st.toggle(CEVIRI["tr"]["otomatik_ses"], value=st.session_state.otomatik_ses)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2: st.image("logo.png", width=80)
    st.markdown(f'<h1 style="text-align: center; color: #4d6bfe;">🔥 {CEVIRI["tr"]["baslik"]}</h1>', unsafe_allow_html=True)
    
    if not st.session_state.mesajlar: st.info(CEVIRI["tr"]["hosgeldin"])

    # --- ESKİ MESAJLARI GÖSTER ---
    for i, m in enumerate(st.session_state.mesajlar):
        if not isinstance(m["content"], str): continue
        
        avatar = "👤" if m["role"] == "user" else "🔥"
        with st.chat_message(m["role"], avatar=avatar):
            st.markdown(m["content"])
            
            if m["role"] == "assistant":
                c1, c2, c3 = st.columns([1, 1, 8])
                with c1:
                    if st.button(CEVIRI["tr"]["sesli_dinle"], key=f"tts_{i}"): sesli_oku(m["content"])
                with c2:
                    if st.button(CEVIRI["tr"]["kopyala"], key=f"cpy_{i}"): st.code(m["content"])

    # --- GİRİŞ KUTUSU VE ANİMASYON ---
    if soru := st.chat_input(CEVIRI["tr"]["sor"]):
        st.session_state.mesajlar.append({"role": "user", "content": soru})
        with st.chat_message("user", avatar="👤"):
            st.markdown(soru)
            
        with st.chat_message("assistant", avatar="🔥"):
            yer = st.empty()
            
            try:
                niyet = "NORMAL"
                if "çiz" in soru.lower() or "resim" in soru.lower() or "görsel" in soru.lower(): niyet = "GORSEL"
                
                if niyet == "GORSEL":
                    with yer.container():
                        st.write("🎨 *Görsel oluşturuluyor...*")
                        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(soru)}?width=1024&height=1024&nologo=true"
                        r = requests.get(url, timeout=90)
                        if r.status_code == 200:
                            st.image(BytesIO(r.content), use_container_width=True)
                            cevap = f"🖼️ İstediğin görseli oluşturdum: {soru}"
                            st.session_state.mesajlar.append({"role": "assistant", "content": cevap})
                        else:
                            st.error("Görsel oluşturulamadı.")
                            cevap = "Hata."
                else:
                    yer.markdown("🤔 *BlazeX düşünüyor...*")
                    
                    mesajlar_gonder = [{"role": "system", "content": kisi}]
                    if st.session_state.hafiza:
                        mesajlar_gonder.append({"role": "system", "content": f"Kullanıcı Bilgisi: {st.session_state.hafiza}"})
                    mesajlar_gonder += st.session_state.mesajlar
                    
                    stream = client.chat.completions.create(
                        model=model, 
                        messages=mesajlar_gonder, 
                        stream=True, 
                        temperature=0.6
                    )
                    
                    tam_metin = ""
                    def stream_uretici():
                        nonlocal tam_metin
                        for parca in stream:
                            icerik = parca.choices[0].delta.content or ""
                            tam_metin += icerik
                            yield icerik
                    
                    yer.write_stream(stream_uretici())
                    
                    if tam_metin:
                        st.session_state.mesajlar.append({"role": "assistant", "content": tam_metin})
                        cevap = tam_metin
            
            except Exception as e:
                st.error(f"⚠️ Hata: {e}")
                cevap = "Bir hata oluştu."
        
        if st.session_state.otomatik_ses and cevap and cevap != "Bir hata oluştu.":
            sesli_oku(cevap)
            
        st.rerun()
