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

st.set_page_config(page_title="BlazeX - Mega Asistan", page_icon="🔥", layout="wide")

# --- ÇEVİRİ ---
CEVIRI = {
    "tr": {
        "baslik": "BlazeX", "alt_baslik": "Oyunlar, Finans ve Mega Asistan ⚡",
        "sohbetler": "💬 Sohbetler", "yeni_sohbet": "➕ Yeni Sohbet",
        "ayarlar": "⚙️ Ayarlar", "model": "🧠 Model", "kisilik": "🎭 Kişilik",
        "gorsel_modu": "🎨 Görsel Oluşturma", "hosgeldin": "Merhaba! Ben BlazeX 🔥 Benimle sohbet edebilir, oyun oynayabilir, kod yazdırabilir ve finansal verileri takip edebilirsin!",
        "sor": "Bir şey sor...", "hata": "⚠️ Hata",
        "ozel_karakter": "Kendi Karakterini Yarat", "karakter_yaz": "Karakter talimatını yaz...",
        "disa_aktar": "📥 Sohbeti İndir", "vision_analiz": "🔍 Görseli Analiz Et",
        "sesli_dinle": "🔊 Dinle", "kopyala": "📋", "kaynaklar": "🌐 Kaynaklar:",
        "aydinlatma": "📜 Gizlilik",
        "aydinlatma_metni": "Bu uygulama KVKK kapsamında verilerinizi işlemektedir. Sohbetleriniz Groq (ABD) ve Tavily (ABD) sunucularına aktarılır. Lütfen kişisel bilgilerinizi yazmayın.",
        "hazir_sorular": "💡 Hazır Sorular", "gecmis": "📚 Geçmiş Sohbetler",
        "pdf_oku": "📄 PDF Yükle", "otomatik_ses": "🔊 Otomatik Sesli Okuma",
        "kamera": "📸 Kamera", "hafiza": "🧠 Yapay Zeka Hafızası",
        "veri_analizi": "📊 Excel/CSV Analizi", "oyun_modu": "🎮 Oyun ve Test Modu",
        "kod_calistirici": "💻 Canlı Kod Çalıştırıcı", "finans": "📈 Canlı Finans",
        "web_tasarim": "🌐 Web Sitesi Üretici", "muzik": "🎵 Şarkı Sözü Üretici"
    }
}

KISILIKLER = {
    "Normal": "Sen BlazeX adında samimi ve yardımcı bir asistansın. Türkçe cevap ver. Robotik olma.",
    "Öğretmen": "Sen sabırlı bir öğretmensin. Türkçe cevap ver.",
    "Kod Ustası": "Sen uzman bir yazılımcısın. Türkçe cevap ver. Kod bloklarını ```python ... ``` şeklinde yaz.",
    "Oyun Ustası": "Sen bir oyun sunucususun. Kullanıcıya mantık, zeka veya genel kültür soruları sorarsın. Cevabı değerlendirip puan verirsin."
}

MODELLER = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b"]
VISION_MODEL = "qwen/qwen3.8-27b"

# --- SESSION STATE ---
if "kullanici_id" not in st.session_state: st.session_state.kullanici_id = str(uuid.uuid4())[:8]
if "mesajlar" not in st.session_state: st.session_state.mesajlar = []
if "hafiza" not in st.session_state: st.session_state.hafiza = ""
if "otomatik_ses" not in st.session_state: st.session_state.otomatik_ses = False
if "onay_verildi" not in st.session_state: st.session_state.onay_verildi = False

# --- VERİTABANI ---
def db_baglantisi(): return sqlite3.connect("blazegpt.db", check_same_thread=False)
def db_olustur():
    c = db_baglantisi().cursor()
    c.execute("CREATE TABLE IF NOT EXISTS sohbetler (id INTEGER PRIMARY KEY AUTOINCREMENT, kullanici_id TEXT, baslik TEXT, mesajlar TEXT)")
    db_baglantisi().commit()
db_olustur()

def kaydet_sohbet(mesajlar):
    baslik = "Sohbet"
    for m in mesajlar:
        if m["role"] == "user" and isinstance(m["content"], str):
            baslik = m["content"][:30]
            break
    c = db_baglantisi().cursor()
    c.execute("INSERT INTO sohbetler (kullanici_id, baslik, mesajlar) VALUES (?, ?, ?)", (st.session_state.kullanici_id, baslik, json.dumps(mesajlar, ensure_ascii=False)))
    db_baglantisi().commit()

def gecmis_sohbetleri_getir():
    c = db_baglantisi().cursor()
    c.execute("SELECT id, baslik FROM sohbetler WHERE kullanici_id = ? ORDER BY id DESC LIMIT 10", (st.session_state.kullanici_id,))
    return c.fetchall()

def sohbet_yukle(sid):
    c = db_baglantisi().cursor()
    c.execute("SELECT mesajlar FROM sohbetler WHERE id = ?", (sid,))
    res = c.fetchone()
    if res: st.session_state.mesajlar = json.loads(res[0])

client = Groq(api_key=st.secrets["GROQ_API_KEY"])
tavily = TavilyClient(api_key=st.secrets.get("TAVILY_API_KEY", ""))

# --- CSS ---
st.markdown("""
<style>
    .stApp { background-color: #1e1e2e; }
    .stChatMessage { border-radius: 15px; padding: 10px; margin-bottom: 10px; }
    .stButton button { background: #4d6bfe; color: white; border-radius: 10px; border: none; transition: 0.3s; }
    .stButton button:hover { background: #3b55d9; transform: scale(1.02); }
</style>
""", unsafe_allow_html=True)

def sesli_oku(metin):
    safe_metin = metin.replace('"', '\\"').replace('\n', ' ')
    js = f"<script>var msg = new SpeechSynthesisUtterance(\"{safe_metin}\"); msg.lang = 'tr-TR'; window.speechSynthesis.speak(msg);</script>"
    st.components.v1.html(js, height=0)

# --- BAŞLIK ---
col1, col2, col3 = st.columns([1, 1, 1])
with col2: st.image("logo.png", width=100)
st.markdown(f'<h1 style="text-align: center; color: #4d6bfe; font-size: 2.5em; margin-bottom: 0;">🔥 {CEVIRI["tr"]["baslik"]}</h1>', unsafe_allow_html=True)
st.markdown(f'<p style="text-align: center; color: #a0a0b0;">{CEVIRI["tr"]["alt_baslik"]}</p>', unsafe_allow_html=True)

# --- KVKK ONAY EKRANI ---
if not st.session_state.onay_verildi:
    st.warning("⚠️ **Devam etmek için lütfen aydınlatma metnini kabul edin.**")
    with st.container(border=True):
        st.write(CEVIRI["tr"]["aydinlatma_metni"])
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Kabul Ediyorum", use_container_width=True, type="primary"):
            st.session_state.onay_verildi = True
            st.rerun()
    with col2:
        if st.button("❌ Reddediyorum", use_container_width=True):
            st.error("Kabul etmeniz gerekmektedir.")
    st.stop()

# --- KENAR ÇUBUĞU (MEGA MENÜ) ---
with st.sidebar:
    st.markdown(f"## {CEVIRI['tr']['ayarlar']}")
    model = st.selectbox(CEVIRI["tr"]["model"], MODELLER, index=0) 
    kisi_secim = st.selectbox(CEVIRI["tr"]["kisilik"], list(KISILIKLER.keys()) + ["Özel Karakter"])
    
    if kisi_secim == "Özel Karakter":
        kisi = st.text_area("Karakter talimatı", "Sen yardımcı bir asistansın.")
    else:
        kisi = KISILIKLER[kisi_secim]
        
    st.markdown("---")
    
    # 1. CANLI FİNANS
    with st.expander(CEVIRI["tr"]["finans"]):
        sembol = st.text_input("Sembol Girin (Örn: THYAO.IS, BTC-USD, AAPL)")
        if st.button("Fiyatı Getir"):
            try:
                hisse = yf.Ticker(sembol)
                veri = hisse.history(period="1d")
                if not veri.empty:
                    fiyat = veri['Close'].iloc[-1]
                    st.success(f"**{sembol}** Güncel Fiyat: **{fiyat:.2f}**")
                else:
                    st.error("Veri bulunamadı.")
            except Exception as e:
                st.error(f"Hata: {e}")

    # 2. CANLI KOD ÇALIŞTIRICI
    with st.expander(CEVIRI["tr"]["kod_calistirici"]):
        kod = st.text_area("Python Kodu:")
        if st.button("Kodu Çalıştır"):
            try:
                # Güvenli olması için exec kullanıyoruz, gerçek üretimde sandbox gerekir
                local_vars = {}
                exec(kod, {}, local_vars)
                st.success("Kod başarıyla çalıştı!")
                if local_vars:
                    st.write(local_vars)
            except Exception as e:
                st.error(f"Hata: {e}")

    # 3. OYUN VE IQ TESTİ MODU
    with st.expander(CEVIRI["tr"]["oyun_modu"]):
        if st.button("🧩 IQ Testine Başla"):
            st.session_state.mesajlar.append({"role": "user", "content": "Bana zor bir mantık sorusu sor ve cevabımı bekle."})
            st.rerun()

    # 4. WEB SİTESİ VE MÜZİK ÜRETİCİ
    with st.expander(CEVIRI["tr"]["web_tasarim"]):
        if st.button("🌐 Bana Kişisel Portfolyo Sitesi Yaz"):
            st.session_state.mesajlar.append({"role": "user", "content": "Bana çok şık, modern bir kişisel portfolyo HTML/CSS kodu yaz."})
            st.rerun()
    with st.expander(CEVIRI["tr"]["muzik"]):
        if st.button("🎵 Bana Hüzünlü Bir Şarkı Sözü Yaz"):
            st.session_state.mesajlar.append({"role": "user", "content": "Bana hüzünlü, duygusal bir şarkı sözü yaz."})
            st.rerun()

    # DİĞER ARAÇLAR
    with st.expander(CEVIRI["tr"]["hafiza"]):
        hafiza_input = st.text_area("Hafıza:", value=st.session_state.hafiza)
        if st.button("🧠 Kaydet"): st.session_state.hafiza = hafiza_input

    with st.expander(CEVIRI["tr"]["gecmis"]):
        for sid, baslik in gecmis_sohbetleri_getir():
            if st.button(f"💬 {baslik}", key=f"gecmis_{sid}"):
                sohbet_yukle(sid)
                st.rerun()

    st.markdown("---")
    st.session_state.otomatik_ses = st.toggle(CEVIRI["tr"]["otomatik_ses"], value=st.session_state.otomatik_ses)
    gorsel_modu = st.toggle(CEVIRI["tr"]["gorsel_modu"], value=False)
    web_arama_modu = st.toggle("🌐 İnternette Ara", value=False)

# --- SOHBET ALANI ---
if not st.session_state.mesajlar: st.info(CEVIRI["tr"]["hosgeldin"])

for i, m in enumerate(st.session_state.mesajlar):
    if not isinstance(m["content"], str): continue
    if m["role"] == "user":
        st.markdown(f'<div style="text-align: right; margin-bottom: 10px;"><span style="background: #005c4b; padding: 12px; border-radius: 15px; color: white; display: inline-block; max-width: 80%;">{m["content"]}</span></div>', unsafe_allow_html=True)
    else:
        with st.chat_message("assistant", avatar="🔥"): st.markdown(m["content"])
        c1, c2, c3 = st.columns([1, 1, 8])
        with c1:
            if st.button(CEVIRI["tr"]["sesli_dinle"], key=f"tts_{i}"): sesli_oku(m["content"])
        with c2:
            if st.button(CEVIRI["tr"]["kopyala"], key=f"cpy_{i}"): st.code(m["content"])

# --- GİRİŞ KUTUSU ---
if soru := st.chat_input(CEVIRI["tr"]["sor"]):
    st.session_state.mesajlar.append({"role": "user", "content": soru})
    cevap = ""
    
    if gorsel_modu:
        with st.spinner("🎨 Görsel oluşturuluyor..."):
            try:
                url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(soru)}?width=1024&height=1024&nologo=true"
                r = requests.get(url, timeout=90)
                if r.status_code == 200:
                    st.image(BytesIO(r.content), use_container_width=True)
                    cevap = f"🖼️ Görsel oluşturuldu: {soru}"
                else: cevap = "Görsel oluşturulamadı."
            except Exception as e: cevap = f"Görsel hatası: {e}"
    else:
        tam = ""
        try:
            arama_sonucu = ""
            if web_arama_modu and tavily:
                with st.spinner("🌐 İnternette araştırıyorum..."):
                    try:
                        res = tavily.search(query=soru, max_results=2)
                        for r in res.get("results", []):
                            arama_sonucu += f"Kaynak: {r['url']}\nÖzet: {r['content']}\n\n"
                    except: pass

            mesajlar_gonder = [{"role": "system", "content": kisi}]
            if st.session_state.hafiza:
                mesajlar_gonder.append({"role": "system", "content": f"Kullanıcı hakkında bilgi: {st.session_state.hafiza}"})
            if arama_sonucu:
                mesajlar_gonder.append({"role": "system", "content": f"Güncel Bilgiler:\n{arama_sonucu}"})
            mesajlar_gonder += st.session_state.mesajlar
            
            stream = client.chat.completions.create(model=model, messages=mesajlar_gonder, stream=True, temperature=0.6)
            for parca in stream: tam += parca.choices[0].delta.content or ""
            cevap = tam
            
            if arama_sonucu:
                cevap += f"\n\n{CEVIRI['tr']['kaynaklar']}\n"
                for r in res.get("results", []): cevap += f"- [{r['title']}]({r['url']})\n"
                    
        except Exception as e:
            if "429" in str(e): st.error("⏳ API Limitine Takıldık! Lütfen 1 dakika bekleyin.")
            else: st.error(f"⚠️ Hata: {e}")
            cevap = "Bir hata oluştu."
    
    st.session_state.mesajlar.append({"role": "assistant", "content": cevap})
    kaydet_sohbet(st.session_state.mesajlar)
    
    if st.session_state.otomatik_ses and cevap != "Bir hata oluştu.": sesli_oku(cevap)
    st.rerun()
