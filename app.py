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

st.set_page_config(page_title="BlazeX - Akıllı Asistan", page_icon="🔥", layout="wide")

# --- ÇEVİRİ ---
CEVIRI = {
    "tr": {
        "baslik": "BlazeX", "alt_baslik": "Sohbet, Oyun, Finans ve Daha Fazlası ⚡",
        "sohbetler": "💬 Sohbetler", "yeni_sohbet": "➕ Yeni Sohbet",
        "ayarlar": "⚙️ Ayarlar", "model": "🧠 Model", "kisilik": "🎭 Kişilik",
        "gorsel_modu": "🎨 Görsel Oluşturma", "hosgeldin": "Merhaba! Ben BlazeX 🔥 Artık bir dedektif, bir yazar, bir mimar ve bir finans uzmanıyım. Benimle neler yapabileceğini hayal bile edemezsin!",
        "sor": "Bir şey sor...", "hata": "⚠️ Hata",
        "ozel_karakter": "Kendi Karakterini Yarat", "karakter_yaz": "Karakter talimatını yaz...",
        "disa_aktar": "📥 Sohbeti İndir", "vision_analiz": "🔍 Görseli Analiz Et",
        "sesli_dinle": "🔊 Dinle", "kopyala": "📋", "kaynaklar": "🌐 Kaynaklar:",
        "aydinlatma": "📜 Gizlilik",
        "aydinlatma_metni": "Bu uygulama KVKK kapsamında verilerinizi işlemektedir. Sohbetleriniz Groq (ABD) ve Tavily (ABD) sunucularına aktarılır. Lütfen kişisel bilgilerinizi yazmayın.",
        "hazir_sorular": "💡 Hazır Sorular", "gecmis": "📚 Geçmiş Sohbetler",
        "pdf_oku": "📄 PDF Yükle", "otomatik_ses": "🔊 Otomatik Sesli Okuma",
        "kamera": "📸 Kamera", "hafiza": "🧠 Yapay Zeka Hafızası",
        "veri_analizi": "📊 Excel/CSV Analizi", "oyun_modu": "🎮 Oyun Modu",
        "kod_calistirici": "💻 Kod Çalıştırıcı", "finans": "📈 Canlı Finans",
        "dedektif": "🕵️ Dedektif Modu", "mimar": "🎨 Yapay Zeka Mimarı",
        "rutin": "⚡ Rutin Planlayıcı", "pdf_ses": "📚 PDF Seslendirici",
        "web_tasarim": "🌐 Web Sitesi Üretici", "muzik": "🎵 Şarkı Sözü Üretici"
    }
}

KISILIKLER = {
    "Normal": "Sen BlazeX adında samimi ve yardımcı bir asistansın. Türkçe cevap ver. Robotik olma.",
    "Öğretmen": "Sen sabırlı bir öğretmensin. Türkçe cevap ver.",
    "Kod Ustası": "Sen uzman bir yazılımcısın. Türkçe cevap ver. Kod bloklarını ```python ... ``` şeklinde yaz.",
    "Dedektif": "Sen Sherlock Holmes gibi zeki bir dedektifsin. Kullanıcının verdiği metinlerdeki gizli anlamları, şifreleri ve ipuçlarını bulursun. Türkçe cevap ver.",
    "Mimar": "Sen uzman bir iç mimarsın. Kullanıcının isteklerine göre hayalindeki odayı tasarlarsın ve gerekli eşyaların listesini çıkarırsın. Türkçe cevap ver.",
    "Oyun Ustası": "Sen bir RPG oyun yöneticisisin. Kullanıcıya seçenekler sunarak bir macera hikayesi yazarsın. Türkçe cevap ver.",
    "Mülakatçı": "Sen bir İK uzmanısın. Kullanıcıya iş mülakatı soruları soruyorsun. Cevaplarını değerlendir ve geri bildirim ver.",
    "İngilizce Öğretmeni": "You are an English teacher. You must talk to the user in English to help them practice. Correct their mistakes politely."
}

MODELLER = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b"]
VISION_MODEL = "qwen/qwen3.8-27b"

# --- SESSION STATE & HAFIZA ---
if "kullanici_id" not in st.session_state:
    st.session_state.kullanici_id = str(uuid.uuid4())[:8]
if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = []
if "hafiza" not in st.session_state:
    st.session_state.hafiza = ""
if "otomatik_ses" not in st.session_state:
    st.session_state.otomatik_ses = False
if "onay_verildi" not in st.session_state:
    st.session_state.onay_verildi = False
if "pdf_metin" not in st.session_state:
    st.session_state.pdf_metin = ""

# --- VERİTABANI ---
def db_baglantisi():
    return sqlite3.connect("blazegpt.db", check_same_thread=False)

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
    c.execute("INSERT INTO sohbetler (kullanici_id, baslik, mesajlar) VALUES (?, ?, ?)", 
              (st.session_state.kullanici_id, baslik, json.dumps(mesajlar, ensure_ascii=False)))
    db_baglantisi().commit()

def gecmis_sohbetleri_getir():
    conn = db_baglantisi()
    c = conn.cursor()
    c.execute("SELECT id, baslik FROM sohbetler WHERE kullanici_id = ? ORDER BY id DESC LIMIT 10", (st.session_state.kullanici_id,))
    res = c.fetchall()
    conn.close()
    return res

def sohbet_yukle(sid):
    conn = db_baglantisi()
    c = conn.cursor()
    c.execute("SELECT mesajlar FROM sohbetler WHERE id = ?", (sid,))
    res = c.fetchone()
    conn.close()
    if res:
        st.session_state.mesajlar = json.loads(res[0])

def pdf_metin_cikar(dosya):
    try:
        reader = PdfReader(BytesIO(dosya.getvalue()))
        metin = ""
        for sayfa in reader.pages:
            metin += sayfa.extract_text() + "\n"
        return metin[:5000]
    except Exception:
        return None

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
with col2:
    st.image("logo.png", width=100)
st.markdown(f'<h1 style="text-align: center; color: #4d6bfe; font-size: 2.5em; margin-bottom: 0; text-shadow: 0 0 20px #4d6bfe;">🔥 {CEVIRI["tr"]["baslik"]}</h1>', unsafe_allow_html=True)
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
    kisi_secim = st.selectbox(CEVIRI["tr"]["kisilik"], list(KISILIKLER.keys()))
    kisi = KISILIKLER[kisi_secim]
        
    st.markdown("---")
    
    # DEDEKTİF MODU
    with st.expander(CEVIRI["tr"]["dedektif"]):
        metin = st.text_area("Analiz edilecek metni girin:")
        if st.button("🕵️ Gizli Anlamı Çöz"):
            st.session_state.mesajlar.append({"role": "user", "content": f"Bu metni bir dedektif gibi analiz et ve gizli anlamları bul:\n{metin}"})
            st.rerun()

    # MİMAR
    with st.expander(CEVIRI["tr"]["mimar"]):
        oda = st.text_input("Nasıl bir oda istiyorsun?")
        if st.button("🎨 Odayı Tasarla"):
            st.session_state.mesajlar.append({"role": "user", "content": f"Bana şu oda için bir tasarım planı ve eşya listesi çıkar: {oda}"})
            st.rerun()

    # RUTİN PLANLAYICI
    with st.expander(CEVIRI["tr"]["rutin"]):
        isler = st.text_area("Bugün neler yapmalısın?")
        if st.button("⚡ Plan Oluştur"):
            st.session_state.mesajlar.append({"role": "user", "content": f"Şu işlerimi saat saat planla:\n{isler}"})
            st.rerun()

    # PDF SESLENDİRİCİ
    with st.expander(CEVIRI["tr"]["pdf_ses"]):
        pdf_file = st.file_uploader("Seslendirilecek PDF", type=["pdf"])
        if pdf_file:
            if st.button("📚 PDF'i Sesli Oku"):
                metin = pdf_metin_cikar(pdf_file)
                if metin:
                    st.session_state.pdf_metin = metin
                    st.success("PDF Hazır! Okumak için butona basın.")
                else:
                    st.error("PDF okunamadı.")
        if st.session_state.pdf_metin:
            if st.button("🔊 Dinlemeye Başla"):
                sesli_oku(st.session_state.pdf_metin)

    # FİNANS
    with st.expander(CEVIRI["tr"]["finans"]):
        sembol = st.text_input("Sembol (Örn: BTC-USD, THYAO.IS)")
        if st.button("Fiyat Getir"):
            try:
                hisse = yf.Ticker(sembol)
                veri = hisse.history(period="1d")
                if not veri.empty: st.success(f"**{sembol}**: {veri['Close'].iloc[-1]:.2f}")
                else: st.error("Veri yok.")
            except: st.error("Bulunamadı.")

    # KOD ÇALIŞTIRICI
    with st.expander(CEVIRI["tr"]["kod_calistirici"]):
        kod = st.text_area("Python Kodu:")
        if st.button("Çalıştır"):
            try:
                local_vars = {}
                exec(kod, {}, local_vars)
                st.success("Çalıştı!"); st.write(local_vars)
            except Exception as e: st.error(f"Hata: {e}")

    # OYUN MODU (RPG)
    with st.expander(CEVIRI["tr"]["oyun_modu"]):
        if st.button("🎮 Maceraya Başla"):
            st.session_state.mesajlar.append({"role": "user", "content": "Beni karanlık bir ormanın girişinde başlatan, seçimlerime göre ilerleyen bir macera oyunu başlat. Bana seçenekler sun."})
            st.rerun()
            
    # WEB TASARIM
    with st.expander(CEVIRI["tr"]["web_tasarim"]):
        if st.button("🌐 Portfolyo Sitesi Kodu"):
            st.session_state.mesajlar.append({"role": "user", "content": "Bana çok şık, modern bir kişisel portfolyo HTML/CSS kodu yaz."})
            st.rerun()
            
    # MÜZİK
    with st.expander(CEVIRI["tr"]["muzik"]):
        if st.button("🎵 Şarkı Sözü Yaz"):
            st.session_state.mesajlar.append({"role": "user", "content": "Bana hüzünlü, duygusal bir şarkı sözü yaz."})
            st.rerun()

    # HAFIZA & GEÇMİŞ
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
if not st.session_state.mesajlar:
    st.info(CEVIRI["tr"]["hosgeldin"])

for i, m in enumerate(st.session_state.mesajlar):
    if not isinstance(m["content"], str): continue
    
    if m["role"] == "user":
        st.markdown(f'<div style="text-align: right; margin-bottom: 10px;"><span style="background: #005c4b; padding: 12px; border-radius: 15px; color: white; display: inline-block; max-width: 80%;">{m["content"]}</span></div>', unsafe_allow_html=True)
    else:
        with st.chat_message("assistant", avatar="🔥"):
            st.markdown(m["content"])
            
        c1, c2, c3 = st.columns([1, 1, 8])
        with c1:
            if st.button(CEVIRI["tr"]["sesli_dinle"], key=f"tts_{i}"):
                sesli_oku(m["content"])
        with c2:
            if st.button(CEVIRI["tr"]["kopyala"], key=f"cpy_{i}"):
                st.code(m["content"])

# --- KAMERA ---
with st.expander(CEVIRI["tr"]["kamera"]):
    foto = st.camera_input("Fotoğraf Çek")
    if foto and st.button("📸 Fotoğrafı Analiz Et", key="cam_analiz"):
        with st.spinner("Analiz ediliyor..."):
            b64 = base64.b64encode(foto.getvalue()).decode('utf-8')
            try:
                cevap = client.chat.completions.create(model=VISION_MODEL, messages=[{"role": "user", "content": [{"type": "text", "text": "Bu fotoğrafta ne var?"}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}])
                st.session_state.mesajlar.append({"role": "user", "content": "📸 [Kamera Fotoğrafı Çekildi]"})
                st.session_state.mesajlar.append({"role": "assistant", "content": f"🖼️ **Analiz:**\n\n{cevap.choices[0].message.content}"})
                kaydet_sohbet(st.session_state.mesajlar)
                st.rerun()
            except Exception as e:
                st.error(f"Hata: {e}")

# --- MİKROFON ---
st.markdown("**🎤 Sesli Giriş:**")
st.components.v1.html("""
<script>function startDictation() { if (window.hasOwnProperty('webkitSpeechRecognition')) { var recognition = new webkitSpeechRecognition(); recognition.continuous = false; recognition.interimResults = false; recognition.lang = "tr-TR"; recognition.start(); recognition.onresult = function(e) { alert("Duyduğum: " + e.results[0][0].transcript); recognition.stop(); }; } }</script>
<button onclick="startDictation()" style="background: #4d6bfe; color: white; padding: 10px; border-radius: 10px; border: none; cursor: pointer; width: 100%;">🎤 Konuş ve Yazıya Çevir</button>
""", height=60)

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
                else:
                    cevap = "Görsel oluşturulamadı."
            except Exception as e:
                cevap = f"Görsel hatası: {e}"
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
                mesajlar_gonder.append({"role": "system", "content": f"Kullanıcı hakkında bilmen gerekenler: {st.session_state.hafiza}"})
                
            if arama_sonucu:
                mesajlar_gonder.append({"role": "system", "content": f"İşte güncel bilgiler:\n{arama_sonucu}"})
            
            mesajlar_gonder += st.session_state.mesajlar
            
            stream = client.chat.completions.create(
                model=model, 
                messages=mesajlar_gonder, 
                stream=True, 
                temperature=0.6 
            )
            for parca in stream:
                tam += parca.choices[0].delta.content or ""
            cevap = tam
            
            if arama_sonucu:
                cevap += f"\n\n{CEVIRI['tr']['kaynaklar']}\n"
                for r in res.get("results", []):
                    cevap += f"- [{r['title']}]({r['url']})\n"
                    
        except Exception as e:
            hata_mesaji = str(e)
            if "429" in hata_mesaji or "rate limit" in hata_mesaji.lower():
                st.error("⏳ **API Limitine Takıldık!** Lütfen 1 dakika bekleyip tekrar deneyin.")
                cevap = "Sistem şu an yoğun, lütfen birazdan tekrar deneyin."
            else:
                st.error(f"⚠️ Beklenmeyen bir hata oluştu: {e}")
                cevap = "Bir hata oluştu."
    
    st.session_state.mesajlar.append({"role": "assistant", "content": cevap})
    kaydet_sohbet(st.session_state.mesajlar)
    
    if st.session_state.otomatik_ses and cevap != "Bir hata oluştu.":
        sesli_oku(cevap)
        
    st.rerun()
