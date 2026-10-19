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

st.set_page_config(page_title="BlazeX - Mega Asistan", page_icon="🔥", layout="wide")

# --- ÇEVİRİ ---
CEVIRI = {
    "tr": {
        "baslik": "BlazeX", "alt_baslik": "Sesli, Oyunlu ve Mega Asistan ⚡",
        "ayarlar": "⚙️ Ayarlar", "model": "🧠 Model", "kisilik": "🎭 Kişilik",
        "hosgeldin": "Merhaba! Ben BlazeX 🔥 Artık bir psikolog, bir yazar, bir web kazıyıcı ve bir tasarımcıyım!",
        "sor": "Bir şey sor...", "hata": "⚠️ Hata",
        "disa_aktar": "📥 Sohbeti İndir", "vision_analiz": "🔍 Görseli Analiz Et",
        "sesli_dinle": "🔊 Dinle", "kopyala": "📋", "kaynaklar": "🌐 Kaynaklar:",
        "aydinlatma": "📜 Gizlilik", "aydinlatma_metni": "Bu uygulama KVKK kapsamında verilerinizi işlemektedir. Sohbetleriniz Groq (ABD) ve Tavily (ABD) sunucularına aktarılır. Lütfen kişisel bilgilerinizi yazmayın.",
        "gecmis": "📚 Geçmiş Sohbetler", "pdf_oku": "📄 PDF Yükle", "otomatik_ses": "🔊 Otomatik Ses",
        "kamera": "📸 Kamera", "hafiza": "🧠 Yapay Zeka Hafızası", "veri_analizi": "📊 Excel/CSV",
        "oyun_modu": "🎮 Oyun Modu", "kod_calistirici": "💻 Kod Çalıştırıcı", "finans": "📈 Canlı Finans",
        "dedektif": "🕵️ Dedektif", "mimar": "🎨 Mimar", "rutin": "⚡ Rutin Planlayıcı",
        "pdf_ses": "📚 PDF Seslendirici", "web_scraper": "🌐 Web Scraper",
        "psikolog": "🧠 Psikolog Modu", "hikaye": "🎮 Hikaye Atölyesi",
        "tasarim": "🎨 Tasarım Asistanı", "takvim": "📅 Sanal Asistan",
        "api": "🔗 API Paylaşımı"
    }
}

KISILIKLER = {
    "Normal": "Sen BlazeX adında samimi ve yardımcı bir asistansın. Türkçe cevap ver. Robotik olma.",
    "Psikolog": "Sen empatik, dinleyen ve rahatlatıcı bir psikologsun. Kullanıcıya duygusal destek ver, yargılamadan dinle.",
    "Yazar": "Sen yaratıcı bir yazarsın. Kullanıcının başlattığı hikayeyi sürükleyici bir şekilde devam ettirirsin.",
    "Tasarımcı": "Sen yaratıcı bir tasarımcısın. Etkinlikler için davetiye, afiş ve konsept fikirleri üretirsin.",
    "Dedektif": "Sen Sherlock Holmes gibi zeki bir dedektifsin. Gizli anlamları bulursun.",
    "Mimar": "Sen uzman bir iç mimarsın. Tasarım planı ve eşya listesi çıkarırsın."
}

MODELLER = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b"]
VISION_MODEL = "qwen/qwen3.8-27b"

# --- SESSION STATE ---
if "mesajlar" not in st.session_state: st.session_state.mesajlar = []
if "hafiza" not in st.session_state: st.session_state.hafiza = ""
if "otomatik_ses" not in st.session_state: st.session_state.otomatik_ses = False
if "onay_verildi" not in st.session_state: st.session_state.onay_verildi = False
if "pdf_metin" not in st.session_state: st.session_state.pdf_metin = ""
if "sayfa" not in st.session_state: st.session_state.sayfa = "anasayfa"
if "kullanici_id" not in st.session_state: st.session_state.kullanici_id = "Misafir"
if "takvim_notlari" not in st.session_state: st.session_state.takvim_notlari = []

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
    st.write("---")
    
    misafir_adi = st.text_input("Sana ne diyeyim? (Örn: Murat)", key="isim_input", placeholder="İsmini yaz...")
    
    if st.button("🚀 Hemen Başla", use_container_width=True, type="primary"):
        if misafir_adi.strip():
            st.session_state.kullanici_id = misafir_adi.strip()
        st.session_state.sayfa = "uygulama"; st.rerun()
    st.stop()

if st.session_state.sayfa == "uygulama":
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.kullanici_id}")
        if st.button("🚪 Ana Sayfa"): 
            st.session_state.sayfa = "anasayfa"
            st.session_state.mesajlar = []
            st.rerun()
        st.markdown("---")
        
        model = st.selectbox(CEVIRI["tr"]["model"], MODELLER, index=0) 
        kisi_secim = st.selectbox(CEVIRI["tr"]["kisilik"], list(KISILIKLER.keys()))
        kisi = KISILIKLER[kisi_secim]
            
        st.markdown("---")
        
        # WEB SCRAPER
        with st.expander(CEVIRI["tr"]["web_scraper"]):
            url_input = st.text_input("Web Sitesi Linki (https://...)")
            if st.button("🌐 Siteyi Oku ve Özetle"):
                with st.spinner("Site okunuyor..."):
                    try:
                        res = requests.get(url_input, timeout=10)
                        # Çok basit bir HTML temizleme
                        import re
                        temiz_metin = re.sub('<[^<]+?>', '', res.text)
                        st.session_state.mesajlar.append({"role": "user", "content": f"Şu sitedeki metni özetle:\n{temiz_metin[:3000]}"})
                        st.rerun()
                    except Exception as e:
                        st.error(f"Site okunamadı: {e}")

        # SANAL ASİSTAN (TAKVİM)
        with st.expander(CEVIRI["tr"]["takvim"]):
            yeni_not = st.text_input("Not / Hatırlatıcı Ekle:")
            if st.button("📅 Not Ekle"):
                if yeni_not:
                    st.session_state.takvim_notlari.append(yeni_not)
                    st.success("Eklendi!")
            for not_ in st.session_state.takvim_notlari:
                st.info(f"📌 {not_}")

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

        # HİKAYE ATÖLYESİ
        with st.expander(CEVIRI["tr"]["hikaye"]):
            hikaye_baslangic = st.text_input("Hikaye Nasıl Başlasın?")
            if st.button("🎮 Hikayeyi Başlat"):
                if hikaye_baslangic:
                    st.session_state.mesajlar.append({"role": "user", "content": f"Beni interaktif bir hikayenin içine sok. Başlangıç: {hikaye_baslangic}. Bana seçenekler sun."})
                    st.rerun()

        # TASARIM ASİSTANI
        with st.expander(CEVIRI["tr"]["tasarim"]):
            tasarim_konu = st.text_input("Ne tasarlamak istiyorsun? (Örn: Doğum günü davetiyesi)")
            if st.button("🎨 Tasarım Fikri Üret"):
                if tasarim_konu:
                    st.session_state.mesajlar.append({"role": "user", "content": f"Bana şunun için yaratıcı bir tasarım fikri ve renk paleti ver: {tasarim_konu}"})
                    st.rerun()

        # FİNANS
        with st.expander(CEVIRI["tr"]["finans"]):
            sembol = st.text_input("Sembol (Örn: BTC-USD, THYAO.IS)")
            if st.button("Fiyat Getir"):
                try:
                    hisse = yf.Ticker(sembol); veri = hisse.history(period="1d")
                    if not veri.empty: st.success(f"**{sembol}**: {veri['Close'].iloc[-1]:.2f}")
                except: st.error("Bulunamadı.")

        # KOD ÇALIŞTIRICI
        with st.expander(CEVIRI["tr"]["kod_calistirici"]):
            kod = st.text_area("Python:")
            if st.button("Çalıştır"):
                try:
                    local_vars = {}
                    exec(kod, {}, local_vars)
                    st.success("Çalıştı!"); st.write(local_vars)
                except Exception as e: st.error(f"Hata: {e}")

        # API PAYLAŞIMI
        with st.expander(CEVIRI["tr"]["api"]):
            st.code(f'POST https://api.blazex.com/v1/chat\nAuthorization: Bearer YOUR_API_KEY\n\n{{\n  "message": "Merhaba" \n}}', language="json")
            st.caption("*(Temsili API - Geliştirme aşamasında)*")

        st.markdown("---")
        st.session_state.otomatik_ses = st.toggle(CEVIRI["tr"]["otomatik_ses"], value=st.session_state.otomatik_ses)

    # --- LOGO TAM ORTALAMA (CSS İLE) ---
    try:
        with open("logo.png", "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode()
            
        st.markdown(
            f"""
            <div style="display: flex; justify-content: center; align-items: center; margin-bottom: 10px; margin-top: 20px;">
                <img src="data:image/png;base64,{logo_base64}" width="120" style="border-radius: 15px; box-shadow: 0 4px 15px rgba(77, 107, 254, 0.3);">
            </div>
            """, 
            unsafe_allow_html=True
        )
    except:
        st.warning("Logo dosyası (logo.png) bulunamadı.")
        
    st.markdown(f'<h1 style="text-align: center; color: #4d6bfe; margin-top: 0;">🔥 {CEVIRI["tr"]["baslik"]}</h1>', unsafe_allow_html=True)
    
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
                    
                    tam_metin = [] 
                    def stream_uretici():
                        for parca in stream:
                            icerik = parca.choices[0].delta.content or ""
                            tam_metin.append(icerik)
                            yield icerik
                    
                    yer.write_stream(stream_uretici())
                    
                    son_cevap = "".join(tam_metin)
                    if son_cevap:
                        st.session_state.mesajlar.append({"role": "assistant", "content": son_cevap})
                        cevap = son_cevap
            
            except Exception as e:
                st.error(f"⚠️ Hata: {e}")
                cevap = "Bir hata oluştu."
        
        if st.session_state.otomatik_ses and cevap and cevap != "Bir hata oluştu.":
            sesli_oku(cevap)
            
        st.rerun()
