import streamlit as st
from groq import Groq
import sqlite3
import json
from datetime import datetime
import requests
from io import BytesIO
import uuid
import base64
import hashlib
import qrcode
import streamlit.components.v1 as components

st.set_page_config(page_title="BlazeX", page_icon="🔥", layout="centered")

# --- ÇEVİRİ ---
CEVIRI = {
    "tr": {
        "baslik": "BlazeX", "alt_baslik": "Düşünen, Görsel ve Akıllı Asistan ⚡",
        "hosgeldin": "Merhaba! Ben BlazeX 🔥 Benimle sohbet edebilir, resim çizebilir veya bir web sitesini okutabilirsin!",
        "sor": "Bir şey sor...", "hata": "⚠️ Hata",
        "sesli_dinle": "🔊 Dinle", "kopyala": "📋",
        "aydinlatma": "📜 Gizlilik ve Çerez Politikası", 
        "aydinlatma_metni": "Size daha iyi hizmet verebilmek için çerezler kullanıyoruz. Devam etmek için lütfen kabul edin.",
        "giris_yap": "👤 Giriş Yap", "kayit_ol": "📝 Hesap Aç",
        "misafir_giris": "🚀 Hesapsız Giriş (Misafir)",
        "galeri": "🎨 Sanat Galerisi", "qr_kod": "📱 QR Kod Üretici",
        "model": "🧠 Model", "kisilik": "🎭 Kişilik", "ses_tonu": "🗣️ Ses Tonu" # Eksik olanlar geri eklendi
    }
}

KISILIKLER = {
    "Normal": "Sen BlazeX adında samimi ve yardımcı bir asistansın. Türkçe cevap ver.",
    "Psikolog": "Sen empatik, dinleyen ve rahatlatıcı bir psikologsun.",
    "Dijital İkiz": "Sen kullanıcının dijital ikizisin. Onun üslubuyla cevap ver."
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
if "sayfa" not in st.session_state: st.session_state.sayfa = "giris"
if "ses_tonu" not in st.session_state: st.session_state.ses_tonu = "tr-TR"
if "galeri" not in st.session_state: st.session_state.galeri = []

# --- VERİTABANI ---
def db_baglantisi(): return sqlite3.connect("blazegpt.db", check_same_thread=False)
def db_olustur():
    c = db_baglantisi().cursor()
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
    if res and res[0] == sifre_hashle(sifre): return True
    return False

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def sesli_oku(metin, dil_kodu="tr-TR"):
    safe_metin = metin.replace('"', '\\"').replace('\n', ' ')
    js = f"<script>var msg = new SpeechSynthesisUtterance(\"{safe_metin}\"); msg.lang = '{dil_kodu}'; window.speechSynthesis.speak(msg);</script>"
    components.html(js, height=0)

# --- ÇEREZ ONAY ---
if not st.session_state.cerez_onay:
    with st.container(border=True):
        st.markdown("### 🍪 Çerez Politikası")
        st.write(CEVIRI["tr"]["aydinlatma_metni"])
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Kabul Ediyorum", type="primary", use_container_width=True):
                st.session_state.cerez_onay = True; st.rerun()
        with col2:
            if st.button("❌ Reddediyorum", use_container_width=True):
                st.error("Kabul etmelisiniz.")
    st.stop()

# --- GİRİŞ EKRANI ---
if not st.session_state.giris_yapildi and st.session_state.sayfa == "giris":
    st.markdown("<h1 style='text-align: center; color: #4d6bfe; font-size: 4em;'>🔥 BlazeX</h1>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs([CEVIRI["tr"]["giris_yap"], CEVIRI["tr"]["kayit_ol"]])
    
    with tab1:
        k_adi = st.text_input("Kullanıcı Adı", key="giris_kadi")
        sifre = st.text_input("Şifre", type="password", key="giris_sifre")
        if st.button("Giriş Yap", use_container_width=True, type="primary"):
            if giris_yap(k_adi, sifre):
                st.session_state.giris_yapildi = True; st.session_state.kullanici_id = k_adi; st.session_state.sayfa = "uygulama"; st.rerun()
            else: st.error("Hatalı giriş!")
            
    with tab2:
        y_kadi = st.text_input("Yeni Kullanıcı Adı", key="kayit_kadi")
        y_sifre = st.text_input("Yeni Şifre", type="password", key="kayit_sifre")
        if st.button("Hesap Aç", use_container_width=True):
            if kayit_ol(y_kadi, y_sifre): st.success("Kayıt başarılı!")
            else: st.error("Kullanıcı adı alınmış.")
            
    st.write("---")
    if st.button(CEVIRI["tr"]["misafir_giris"], use_container_width=True):
        st.session_state.giris_yapildi = True; st.session_state.kullanici_id = "Misafir_" + str(uuid.uuid4())[:4]; st.session_state.sayfa = "uygulama"; st.rerun()
    st.stop()

# --- UYGULAMA ---
if st.session_state.sayfa == "uygulama":
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.kullanici_id}")
        if st.button("🚪 Çıkış Yap"): 
            st.session_state.giris_yapildi = False; st.session_state.sayfa = "giris"; st.session_state.mesajlar = []; st.rerun()
        st.markdown("---")
        
        model = st.selectbox(CEVIRI["tr"]["model"], MODELLER, index=0) 
        kisi_secim = st.selectbox(CEVIRI["tr"]["kisilik"], list(KISILIKLER.keys()))
        kisi = KISILIKLER[kisi_secim]
        
        ses_secenekleri = {"Normal": "tr-TR", "Korsan": "en-GB", "Robot": "en-US"}
        secilen_ses = st.selectbox(CEVIRI["tr"]["ses_tonu"], list(ses_secenekleri.keys()))
        st.session_state.ses_tonu = ses_secenekleri[secilen_ses]

        st.markdown("---")
        
        with st.expander("🌐 Web Sitesi Okuyucu"):
            url_input = st.text_input("Link Yapıştır:")
            if st.button("Siteyi Oku"):
                with st.spinner("Okunuyor..."):
                    try:
                        res = requests.get(url_input, timeout=10)
                        import re
                        temiz_metin = re.sub('<[^<]+?>', '', res.text)
                        st.session_state.mesajlar.append({"role": "user", "content": f"Şu sitedeki metni özetle:\n{temiz_metin[:3000]}"})
                        st.rerun()
                    except Exception as e: st.error(f"Okunamadı: {e}")

        with st.expander("📱 QR Kod Üretici"):
            qr_link = st.text_input("Link veya Metin Girin:")
            if st.button("QR Kod Oluştur"):
                if qr_link:
                    qr = qrcode.QRCode(box_size=10, border=4)
                    qr.add_data(qr_link)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white")
                    buf = BytesIO()
                    img.save(buf, format="PNG")
                    st.image(buf.getvalue(), caption="QR Kodunuz")

        with st.expander("🎨 Sanat Galerisi"):
            if not st.session_state.galeri:
                st.caption("Henüz görsel yok.")
            for idx, img_bytes in enumerate(st.session_state.galeri):
                st.image(img_bytes, use_container_width=True)

        st.markdown("---")
        st.session_state.otomatik_ses = st.toggle("🔊 Otomatik Ses", value=st.session_state.otomatik_ses)

    # --- LOGO VE BAŞLIK ---
    try:
        with open("logo.png", "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode()
        st.markdown(f'<div style="display: flex; justify-content: center; margin-top: 10px;"><img src="data:image/png;base64,{logo_base64}" width="100" style="border-radius: 15px; box-shadow: 0 4px 15px rgba(77, 107, 254, 0.3);"></div>', unsafe_allow_html=True)
    except: pass
        
    st.markdown(f'<h1 style="text-align: center; color: #4d6bfe; margin-top: 0;">🔥 {CEVIRI["tr"]["baslik"]}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p style="text-align: center; color: #a0a0b0;">{CEVIRI["tr"]["alt_baslik"]}</p>', unsafe_allow_html=True)
    
    if not st.session_state.mesajlar: st.info(CEVIRI["tr"]["hosgeldin"])

    # --- MESAJLARI GÖSTER ---
    for i, m in enumerate(st.session_state.mesajlar):
        if not isinstance(m["content"], str): continue
        avatar = "👤" if m["role"] == "user" else "🔥"
        with st.chat_message(m["role"], avatar=avatar):
            st.markdown(m["content"])
            if m["role"] == "assistant":
                c1, c2 = st.columns([1, 10])
                with c1:
                    if st.button("🔊", key=f"tts_{i}"): sesli_oku(m["content"], st.session_state.ses_tonu)

    # --- GİRİŞ KUTUSU VE ANİMASYON ---
    if soru := st.chat_input(CEVIRI["tr"]["sor"]):
        st.session_state.mesajlar.append({"role": "user", "content": soru})
        with st.chat_message("user", avatar="👤"): st.markdown(soru)
            
        with st.chat_message("assistant", avatar="🔥"):
            yer = st.empty()
            try:
                if "çiz" in soru.lower() or "resim" in soru.lower() or "görsel" in soru.lower():
                    with yer.container():
                        st.write("🎨 *Görsel oluşturuluyor...*")
                        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(soru)}?width=1024&height=1024&nologo=true"
                        r = requests.get(url, timeout=90)
                        if r.status_code == 200:
                            st.image(BytesIO(r.content), use_container_width=True)
                            st.session_state.galeri.append(r.content)
                            cevap = f"🖼️ Görsel oluşturuldu: {soru}"
                            st.session_state.mesajlar.append({"role": "assistant", "content": cevap})
                        else: cevap = "Görsel oluşturulamadı."
                else:
                    yer.markdown("🤔 *BlazeX düşünüyor...*")
                    mesajlar_gonder = [{"role": "system", "content": kisi}]
                    if st.session_state.hafiza: mesajlar_gonder.append({"role": "system", "content": f"Kullanıcı Bilgisi: {st.session_state.hafiza}"})
                    mesajlar_gonder += st.session_state.mesajlar
                    
                    stream = client.chat.completions.create(model=model, messages=mesajlar_gonder, stream=True, temperature=0.6)
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
                cevap = "Hata."
        
        if st.session_state.otomatik_ses and cevap: sesli_oku(cevap, st.session_state.ses_tonu)
        st.rerun()
