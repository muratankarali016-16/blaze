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
import streamlit.components.v1 as components

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
        "aydinlatma": "📜 Gizlilik ve Çerez Politikası", 
        "aydinlatma_metni": "Bu uygulama, size daha iyi hizmet verebilmek ve sohbet geçmişinizi güvenli bir şekilde saklamak için çerezler (cookies) ve yerel depolama kullanmaktadır. Devam etmek için lütfen kabul edin.",
        "gecmis": "📚 Geçmiş Sohbetler", "pdf_oku": "📄 PDF Yükle", "otomatik_ses": "🔊 Otomatik Ses",
        "kamera": "📸 Kamera", "hafiza": "🧠 Yapay Zeka Hafızası", "veri_analizi": "📊 Excel/CSV",
        "oyun_modu": "🎮 Oyun Modu", "kod_calistirici": "💻 Kod Çalıştırıcı", "finans": "📈 Canlı Finans",
        "dedektif": "🕵️ Dedektif", "mimar": "🎨 Mimar", "rutin": "⚡ Rutin Planlayıcı",
        "pdf_ses": "📚 PDF Seslendirici", "web_scraper": "🌐 Web Scraper",
        "psikolog": "🧠 Psikolog Modu", "hikaye": "🎮 Hikaye Atölyesi",
        "tasarim": "🎨 Tasarım Asistanı", "takvim": "📅 Sanal Asistan",
        "api": "🔗 API Paylaşımı", "giris_yap": "👤 Giriş Yap", "kayit_ol": "📝 Hesap Aç",
        "misafir_giris": "🚀 Hesapsız Giriş (Misafir)"
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
if "cerez_onay" not in st.session_state: st.session_state.cerez_onay = False
if "giris_yapildi" not in st.session_state: st.session_state.giris_yapildi = False
if "kullanici_id" not in st.session_state: st.session_state.kullanici_id = "Misafir"
if "sayfa" not in st.session_state: st.session_state.sayfa = "giris" # Başlangıç ekranı

# --- VERİTABANI ---
def db_baglantisi(): return sqlite3.connect("blazegpt.db", check_same_thread=False)
def db_olustur():
    c = db_baglantisi().cursor()
    c.execute("CREATE TABLE IF NOT EXISTS sohbetler (id INTEGER PRIMARY KEY AUTOINCREMENT, kullanici_id TEXT, baslik TEXT, mesajlar TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS kullanicilar (kullanici_adi TEXT PRIMARY KEY, sifre TEXT)")
    db_baglantisi().commit()
db_olustur()

def sifre_hashle(sifre): return hashlib.sha256(sifre.encode()).hexdigest()

def kayit_ol(kullanici_adi, sifre):
    try:
        c = db_baglantisi().cursor()
        c.execute("INSERT INTO kullanicilar (kullanici_adi, sifre) VALUES (?, ?)", (kullanici_adi, sifre_hashle(sifre)))
        db_baglantisi().commit()
        return True
    except sqlite3.IntegrityError: return False

def giris_yap(kullanici_adi, sifre):
    c = db_baglantisi().cursor()
    c.execute("SELECT sifre FROM kullanicilar WHERE kullanici_adi = ?", (kullanici_adi,))
    res = c.fetchone()
    if res and res[0] == sifre_hashle(sifre):
        return True
    return False

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
    components.html(js, height=0)

# --- 1. ÇEREZ ONAY EKRANI (localStorage Kullanarak) ---
# Tarayıcı hafızasında 'cerez_kabul' var mı diye kontrol ediyoruz
cookie_check_js = """
<script>
    var cookieAccepted = localStorage.getItem("blazex_cerez_kabul");
    if (cookieAccepted === "true") {
        window.parent.document.getElementById("cerez_durumu").value = "true";
    }
</script>
<input type="hidden" id="cerez_durumu" value="false">
"""
components.html(cookie_check_js, height=0)

if not st.session_state.cerez_onay:
    with st.container(border=True):
        st.markdown("### 🍪 Çerez Politikası")
        st.write(CEVIRI["tr"]["aydinlatma_metni"])
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Kabul Ediyorum", type="primary", use_container_width=True):
                # Çerezi tarayıcıya kaydet
                components.html("<script>localStorage.setItem('blazex_cerez_kabul', 'true');</script>", height=0)
                st.session_state.cerez_onay = True
                st.rerun()
        with col2:
            if st.button("❌ Reddediyorum", use_container_width=True):
                st.error("Sistemi kullanabilmek için çerezleri kabul etmelisiniz.")
    st.stop() # Çerez kabul edilmeden aşağıya geçme

# --- 2. GİRİŞ / HESAP AÇMA EKRANI ---
if not st.session_state.giris_yapildi and st.session_state.sayfa == "giris":
    st.markdown("<h1 style='text-align: center; color: #4d6bfe; font-size: 4em;'>🔥 BlazeX</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 1.2em;'>Geleceğin Yapay Zeka Asistanı</p>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs([CEVIRI["tr"]["giris_yap"], CEVIRI["tr"]["kayit_ol"]])
    
    with tab1:
        k_adi = st.text_input("Kullanıcı Adı", key="giris_kadi")
        sifre = st.text_input("Şifre", type="password", key="giris_sifre")
        if st.button("Giriş Yap", use_container_width=True, type="primary"):
            if giris_yap(k_adi, sifre):
                st.session_state.giris_yapildi = True
                st.session_state.kullanici_id = k_adi
                st.session_state.sayfa = "uygulama"
                st.rerun()
            else: st.error("Hatalı kullanıcı adı veya şifre!")
            
    with tab2:
        y_kadi = st.text_input("Yeni Kullanıcı Adı", key="kayit_kadi")
        y_sifre = st.text_input("Yeni Şifre", type="password", key="kayit_sifre")
        if st.button("Hesap Aç", use_container_width=True):
            if kayit_ol(y_kadi, y_sifre):
                st.success("Kayıt başarılı! Şimdi giriş yapabilirsiniz.")
            else: st.error("Bu kullanıcı adı zaten alınmış.")
            
    st.write("---")
    # HESAPSIZ GİRİŞ BUTONU
    if st.button(CEVIRI["tr"]["misafir_giris"], use_container_width=True):
        st.session_state.giris_yapildi = True
        st.session_state.kullanici_id = "Misafir_" + str(uuid.uuid4())[:4]
        st.session_state.sayfa = "uygulama"
        st.rerun()
    st.stop()

# --- 3. UYGULAMA (SOHBET EKRANI) ---
if st.session_state.sayfa == "uygulama":
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.kullanici_id}")
        if st.button("🚪 Çıkış Yap"): 
            st.session_state.giris_yapildi = False
            st.session_state.sayfa = "giris"
            st.session_state.mesajlar = []
            st.rerun()
        st.markdown("---")
        
        model = st.selectbox(CEVIRI["tr"]["model"], MODELLER, index=0) 
        kisi_secim = st.selectbox(CEVIRI["tr"]["kisilik"], list(KISILIKLER.keys()))
        kisi = KISILIKLER[kisi_secim]
            
        st.markdown("---")
        
        # HIZLI BAŞLANGIÇ BUTONLARI
        st.markdown("### ⚡ Hızlı Başlangıç")
        if st.button("🎨 Bana Bir Kedi Çiz"):
            st.session_state.mesajlar.append({"role": "user", "content": "Bana sevimli bir kedi çiz."})
            st.rerun()
        if st.button("📝 Kısa Bir Şiir Yaz"):
            st.session_state.mesajlar.append({"role": "user", "content": "Bana doğa hakkında kısa bir şiir yaz."})
            st.rerun()
            
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
            if "pdf_metin" in st.session_state and st.session_state.pdf_metin:
                if st.button("🔊 Dinlemeye Başla"):
                    sesli_oku(st.session_state.pdf_metin)

        st.markdown("---")
        st.session_state.otomatik_ses = st.toggle(CEVIRI["tr"]["otomatik_ses"], value=st.session_state.otomatik_ses)

    # --- LOGO VE BAŞLIK ---
    try:
        with open("logo.png", "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode()
        st.markdown(
            f"""
            <div style="display: flex; justify-content: center; align-items: center; margin-bottom: 10px; margin-top: 20px;">
                <img src="data:image/png;base64,{logo_base64}" width="120" style="border-radius: 15px; box-shadow: 0 4px 15px rgba(77, 107, 254, 0.3);">
            </div>
            """, unsafe_allow_html=True
        )
    except:
        st.warning("Logo dosyası (logo.png) bulunamadı.")
        
    st.markdown(f'<h1 style="text-align: center; color: #4d6bfe; margin-top: 0;">🔥 {CEVIRI["tr"]["baslik"]}</h1>', unsafe_allow_html=True)
    
    if not st.session_state.mesajlar: st.info(CEVIRI["tr"]["hosgeldin"])

    # --- MESAJLARI GÖSTER VE GERİ BİLDİRİM BUTONLARI ---
    for i, m in enumerate(st.session_state.mesajlar):
        if not isinstance(m["content"], str): continue
        
        avatar = "👤" if m["role"] == "user" else "🔥"
        with st.chat_message(m["role"], avatar=avatar):
            st.markdown(m["content"])
            
            # Bot cevabıysa Kopyala, Dinle ve Geri Bildirim butonları
            if m["role"] == "assistant":
                c1, c2, c3, c4 = st.columns([1, 1, 1, 6])
                with c1:
                    if st.button(CEVIRI["tr"]["sesli_dinle"], key=f"tts_{i}"): sesli_oku(m["content"])
                with c2:
                    if st.button(CEVIRI["tr"]["kopyala"], key=f"cpy_{i}"): st.code(m["content"])
                with c3:
                    # GERİ BİLDİRİM (FEEDBACK) BUTONLARI
                    if st.button("👍", key=f"up_{i}"):
                        st.toast("Geri bildiriminiz kaydedildi. Teşekkürler!")
                    if st.button("👎", key=f"down_{i}"):
                        st.toast("Geri bildiriminiz kaydedildi. Geliştireceğiz!")

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
