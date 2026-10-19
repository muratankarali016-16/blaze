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

st.set_page_config(page_title="BlazeX - Akıllı Asistan", page_icon="🔥", layout="wide")

# --- ÇEVİRİ ---
CEVIRI = {
    "tr": {
        "baslik": "BlazeX", "alt_baslik": "Sohbet, Oyun, Finans ve Daha Fazlası ⚡",
        "ayarlar": "⚙️ Ayarlar", "model": "🧠 Model", "kisilik": "🎭 Kişilik",
        "gorsel_modu": "🎨 Görsel Oluşturma", "hosgeldin": "Merhaba! Ben BlazeX 🔥 Artık ne zaman internete bakmam gerektiğine kendim karar veriyorum!",
        "sor": "Bir şey sor...", "hata": "⚠️ Hata",
        "disa_aktar": "📥 Sohbeti İndir", "vision_analiz": "🔍 Görseli Analiz Et",
        "sesli_dinle": "🔊 Dinle", "kopyala": "📋", "kaynaklar": "🌐 Kaynaklar:",
        "aydinlatma": "📜 Gizlilik", "aydinlatma_metni": "Bu uygulama KVKK kapsamında verilerinizi işlemektedir. Sohbetleriniz Groq (ABD) ve Tavily (ABD) sunucularına aktarılır. Lütfen kişisel bilgilerinizi yazmayın.",
        "gecmis": "📚 Geçmiş Sohbetler", "pdf_oku": "📄 PDF Yükle", "otomatik_ses": "🔊 Otomatik Ses",
        "kamera": "📸 Kamera", "hafiza": "🧠 Yapay Zeka Hafızası", "veri_analizi": "📊 Excel/CSV",
        "oyun_modu": "🎮 Oyun Modu", "kod_calistirici": "💻 Kod Çalıştırıcı", "finans": "📈 Canlı Finans",
        "dedektif": "🕵️ Dedektif", "mimar": "🎨 Mimar", "rutin": "⚡ Rutin Planlayıcı",
        "pdf_ses": "📚 PDF Seslendirici", "web_tasarim": "🌐 Web Üretici", "muzik": "🎵 Müzik"
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
ADMIN_SIFRE = "admin123" # BURAYI KENDİ ŞİFRENLE DEĞİŞTİR!

# --- SESSION STATE ---
if "kullanici_id" not in st.session_state: st.session_state.kullanici_id = str(uuid.uuid4())[:8]
if "mesajlar" not in st.session_state: st.session_state.mesajlar = []
if "hafiza" not in st.session_state: st.session_state.hafiza = ""
if "otomatik_ses" not in st.session_state: st.session_state.otomatik_ses = False
if "onay_verildi" not in st.session_state: st.session_state.onay_verildi = False
if "pdf_metin" not in st.session_state: st.session_state.pdf_metin = ""
if "giris_yapildi" not in st.session_state: st.session_state.giris_yapildi = False
if "kullanici_adi" not in st.session_state: st.session_state.kullanici_adi = "Misafir"
if "sayfa" not in st.session_state: st.session_state.sayfa = "anasayfa"

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
    return res and res[0] == sifre_hashle(sifre)

def kaydet_sohbet(mesajlar, k_id):
    baslik = "Sohbet"
    for m in mesajlar:
        if m["role"] == "user" and isinstance(m["content"], str):
            baslik = m["content"][:30]; break
    c = db_baglantisi().cursor()
    c.execute("INSERT INTO sohbetler (kullanici_id, baslik, mesajlar) VALUES (?, ?, ?)", (k_id, baslik, json.dumps(mesajlar, ensure_ascii=False)))
    db_baglantisi().commit()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])
tavily = TavilyClient(api_key=st.secrets.get("TAVILY_API_KEY", ""))

# --- NİYET ANALİZİ ---
def niyet_analizi_yap(soru):
    try:
        cevap = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "Sen bir niyet analizi asistanısın. Kullanıcının sorusu güncel bir bilgi (hava durumu, haber, maç skoru, fiyat vb.) gerektiriyorsa sadece 'ARA' yaz. Eğer genel kültür, kod yazma, sohbet, şiir gibi internet gerektirmeyen bir konuysa sadece 'ARAMA' yaz. Başka hiçbir şey yazma."},
                {"role": "user", "content": soru}
            ],
            max_tokens=5, temperature=0.0
        )
        return "ARA" in cevap.choices[0].message.content.strip().upper()
    except: return False

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
    col1, col2, col3 = st.columns(3)
    with col1: st.info("🧠 **Hafızalı Sohbet**\nSeni hatırlar, sana özel cevap verir.")
    with col2: st.info("📈 **Finans ve Kod**\nHisse takibi yapar, Python kodu çalıştırır.")
    with col3: st.info("🎮 **Oyun ve Eğlence**\nMacera oyunları ve IQ testleri.")
    st.write("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Hemen Başla (Misafir)", use_container_width=True, type="primary"):
            st.session_state.sayfa = "uygulama"; st.rerun()
    with col2:
        if st.button("👤 Giriş Yap / Kayıt Ol", use_container_width=True):
            st.session_state.sayfa = "giris"; st.rerun()
    st.stop()

if st.session_state.sayfa == "giris":
    st.markdown("<h2 style='text-align: center;'>👤 Hesap İşlemleri</h2>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
    with tab1:
        k_adi = st.text_input("Kullanıcı Adı", key="giris_kadi")
        sifre = st.text_input("Şifre", type="password", key="giris_sifre")
        if st.button("Giriş Yap"):
            if giris_yap(k_adi, sifre):
                st.session_state.giris_yapildi = True; st.session_state.kullanici_adi = k_adi; st.session_state.sayfa = "uygulama"; st.rerun()
            else: st.error("Hatalı giriş!")
    with tab2:
        y_kadi = st.text_input("Yeni Kullanıcı Adı", key="kayit_kadi")
        y_sifre = st.text_input("Yeni Şifre", type="password", key="kayit_sifre")
        if st.button("Kayıt Ol"):
            if kayit_ol(y_kadi, y_sifre): st.success("Kayıt başarılı!")
            else: st.error("Bu kullanıcı adı alınmış.")
    if st.button("⬅️ Ana Sayfaya Dön"): st.session_state.sayfa = "anasayfa"; st.rerun()
    st.stop()

if st.session_state.sayfa == "uygulama":
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.kullanici_adi}")
        if st.button("🚪 Çıkış / Ana Sayfa"): st.session_state.sayfa = "anasayfa"; st.rerun()
        st.markdown("---")
        
        if st.session_state.kullanici_adi == "ADMIN":
            with st.expander("👑 Admin Paneli"):
                c = db_baglantisi().cursor()
                c.execute("SELECT COUNT(*) FROM sohbetler"); st.metric("Toplam Sohbet", c.fetchone()[0])
                c.execute("SELECT COUNT(*) FROM kullanicilar"); st.metric("Toplam Kullanıcı", c.fetchone()[0])

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

        with st.expander(CEVIRI["tr"]["oyun_modu"]):
            if st.button("🎮 Maceraya Başla"):
                st.session_state.mesajlar.append({"role": "user", "content": "Beni karanlık bir ormanın girişinde başlatan, seçimlerime göre ilerleyen bir macera oyunu başlat. Bana seçenekler sun."})
                st.rerun()

        st.markdown("---")
        st.session_state.otomatik_ses = st.toggle(CEVIRI["tr"]["otomatik_ses"], value=st.session_state.otomatik_ses)
        gorsel_modu = st.toggle(CEVIRI["tr"]["gorsel_modu"], value=False)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2: st.image("logo.png", width=80)
    st.markdown(f'<h1 style="text-align: center; color: #4d6bfe;">🔥 {CEVIRI["tr"]["baslik"]}</h1>', unsafe_allow_html=True)
    
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
                
                # Niyet Analizi Çağrısı
                internet_gerekli = niyet_analizi_yap(soru) 
                
                if internet_gerekli and tavily:
                    st.toast("🌐 Güncel bilgi gerektiği için internette araştırıyorum...")
                    with st.spinner("🌐 Araştırılıyor..."):
                        try:
                            res = tavily.search(query=soru, max_results=2)
                            for r in res.get("results", []): arama_sonucu += f"Kaynak: {r['url']}\nÖzet: {r['content']}\n\n"
                        except: pass

                mesajlar_gonder = [{"role": "system", "content": kisi}]
                if st.session_state.hafiza: mesajlar_gonder.append({"role": "system", "content": f"Kullanıcı Bilgisi: {st.session_state.hafiza}"})
                if arama_sonucu: mesajlar_gonder.append({"role": "system", "content": f"Güncel Bilgi:\n{arama_sonucu}"})
                mesajlar_gonder += st.session_state.mesajlar
                
                stream = client.chat.completions.create(model=model, messages=mesajlar_gonder, stream=True, temperature=0.6)
                for parca in stream: tam += parca.choices[0].delta.content or ""
                cevap = tam
                
                if arama_sonucu:
                    cevap += f"\n\n{CEVIRI['tr']['kaynaklar']}\n"
                    for r in res.get("results", []): cevap += f"- [{r['title']}]({r['url']})\n"
                        
            except Exception as e:
                if "429" in str(e): st.error("⏳ API Limitine Takıldık! Lütfen bekleyin.")
                else: st.error(f"⚠️ Hata: {e}")
                cevap = "Bir hata oluştu."
        
        st.session_state.mesajlar.append({"role": "assistant", "content": cevap})
        if st.session_state.kullanici_adi != "Misafir":
            kaydet_sohbet(st.session_state.mesajlar, st.session_state.kullanici_adi)
        if st.session_state.otomatik_ses and cevap != "Bir hata oluştu.": sesli_oku(cevap)
        st.rerun()
