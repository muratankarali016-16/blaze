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

st.set_page_config(page_title="BlazeX - Süper Asistan", page_icon="🔥", layout="wide")

# --- ÇEVİRİ ---
CEVIRI = {
    "tr": {
        "baslik": "BlazeX", "alt_baslik": "Sesli, Görsel ve Akıllı Asistan ⚡",
        "sohbetler": "💬 Sohbetler", "yeni_sohbet": "➕ Yeni Sohbet",
        "ayarlar": "⚙️ Ayarlar", "model": "🧠 Model", "kisilik": "🎭 Kişilik",
        "gorsel_modu": "🎨 Görsel Oluşturma", "hosgeldin": "Merhaba! Ben BlazeX 🔥",
        "sor": "Bir şey sor...", "hata": "⚠️ Hata",
        "ozel_karakter": "Kendi Karakterini Yarat", "karakter_yaz": "Karakter talimatını yaz...",
        "disa_aktar": "📥 Sohbeti İndir", "vision_analiz": "🔍 Görseli Analiz Et",
        "sesli_dinle": "🔊 Dinle", "kopyala": "📋", "kaynaklar": "🌐 Kaynaklar:",
        "aydinlatma": "📜 Gizlilik",
        "aydinlatma_metni": """
        **Veri Sorumlusu:** BlazeX (Kişisel Kullanım)
        Bu uygulama KVKK kapsamında verilerinizi işlemektedir. 
        Sohbetleriniz Groq (ABD) ve Tavily (ABD) sunucularına aktarılır.
        ⚠️ Lütfen kişisel bilgilerinizi yazmayın.
        """,
        "hazir_sorular": "💡 Hazır Sorular", "gecmis": "📚 Geçmiş Sohbetler",
        "pdf_oku": "📄 PDF Yükle ve Oku", "otomatik_ses": "🔊 Otomatik Sesli Okuma"
    }
}

KISILIKLER = {
    "Normal": "Sen BlazeX adında samimi ve yardımcı bir asistansın. Türkçe cevap ver. Eğer kullanıcının yazdığı metin üzgün veya kızgın bir tondaysa, ona göre daha sakin ve empatik bir yanıt ver. Robotik olma.",
    "Öğretmen": "Sen sabırlı bir öğretmensin. Türkçe cevap ver.",
    "Kod Ustası": "Sen uzman bir yazılımcısın. Türkçe cevap ver. Kod bloklarını ```python ... ``` şeklinde yaz."
}

MODELLER = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b"]
VISION_MODEL = "qwen/qwen3.8-27b"

# --- SESSION STATE ---
if "kullanici_id" not in st.session_state:
    st.session_state.kullanici_id = str(uuid.uuid4())[:8]
if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = []
if "otomatik_ses" not in st.session_state:
    st.session_state.otomatik_ses = False

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
        return metin[:5000] # Limitli okuyalım
    except Exception as e:
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

# --- TTS (Sesli Okuma) ---
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

# --- KENAR ÇUBUĞU ---
with st.sidebar:
    st.markdown(f"## {CEVIRI['tr']['ayarlar']}")
    model = st.selectbox(CEVIRI["tr"]["model"], MODELLER, index=0) 
    
    kisi_secim = st.selectbox(CEVIRI["tr"]["kisilik"], ["Normal", "Öğretmen", "Kod Ustası", "Özel Karakter"])
    
    if kisi_secim == "Özel Karakter":
        ozel_kisi = st.text_area(CEVIRI["tr"]["karakter_yaz"], "Sen yardımcı bir asistansın.")
        kisi = ozel_kisi
    else:
        kisi = KISILIKLER[kisi_secim]
        
    st.markdown("---")
    
    # 1. PDF YÜKLEME
    with st.expander(CEVIRI["tr"]["pdf_oku"]):
        pdf_file = st.file_uploader("PDF Seç", type=["pdf"])
        if pdf_file:
            if st.button("📄 PDF'i Oku ve Özetle"):
                with st.spinner("Okunuyor..."):
                    metin = pdf_metin_cikar(pdf_file)
                    if metin:
                        st.session_state.mesajlar.append({"role": "user", "content": f"Şu PDF'in içeriğini özetle:\n{metin}"})
                        st.success("PDF yüklendi, sorunuzu sorun!")
                    else:
                        st.error("PDF okunamadı.")
    
    # 2. HAZIR SORULAR
    with st.expander(CEVIRI["tr"]["hazir_sorular"]):
        if st.button("💡 Bana bir iş fikri ver"):
            st.session_state.mesajlar.append({"role": "user", "content": "Bana yenilikçi bir iş fikri ver."})
            st.rerun()
        if st.button("📝 İngilizceye Çevir"):
            st.session_state.mesajlar.append({"role": "user", "content": "Şu metni İngilizceye çevir: 'Merhaba dünya'"})
            st.rerun()
        if st.button("😂 Beni güldür"):
            st.session_state.mesajlar.append({"role": "user", "content": "Bana kısa ve komik bir fıkra anlat."})
            st.rerun()

    # 3. GEÇMİŞ SOHBETLER
    with st.expander(CEVIRI["tr"]["gecmis"]):
        gecmis = gecmis_sohbetleri_getir()
        if gecmis:
            for sid, baslik in gecmis:
                if st.button(f"💬 {baslik}", key=f"gecmis_{sid}"):
                    sohbet_yukle(sid)
                    st.rerun()
        else:
            st.caption("Henüz geçmiş yok.")

    st.markdown("---")
    
    # 4. OTOMATİK SES
    st.session_state.otomatik_ses = st.toggle(CEVIRI["tr"]["otomatik_ses"], value=st.session_state.otomatik_ses)
    
    gorsel_modu = st.toggle(CEVIRI["tr"]["gorsel_modu"], value=False)
    web_arama_modu = st.toggle("🌐 İnternette Ara", value=False)
    
    with st.expander(CEVIRI["tr"]["aydinlatma"]):
        st.write(CEVIRI["tr"]["aydinlatma_metni"])

# --- SOHBET ALANI ---
if not st.session_state.mesajlar:
    st.info(CEVIRI["tr"]["hosgeldin"])

for i, m in enumerate(st.session_state.mesajlar):
    if not isinstance(m["content"], str): continue
    
    # WhatsApp Tarzı Balonlar ve Markdown Desteği
    if m["role"] == "user":
        st.markdown(f'<div style="text-align: right; margin-bottom: 10px;"><span style="background: #005c4b; padding: 12px; border-radius: 15px; color: white; display: inline-block; max-width: 80%;">{m["content"]}</span></div>', unsafe_allow_html=True)
    else:
        # Bot mesajlarını markdown olarak göster (kodları renklendirmek için)
        with st.chat_message("assistant", avatar="🔥"):
            st.markdown(m["content"])
            
        # Sesli okuma ve kopyalama butonları
        c1, c2, c3 = st.columns([1, 1, 8])
        with c1:
            if st.button(CEVIRI["tr"]["sesli_dinle"], key=f"tts_{i}"):
                sesli_oku(m["content"])
        with c2:
            if st.button(CEVIRI["tr"]["kopyala"], key=f"cpy_{i}"):
                st.code(m["content"])

# --- DOSYA YÜKLEME (GÖRSEL) ---
with st.expander("📎 Görsel Ekle"):
    yuklenen_resim = st.file_uploader("Görsel seç", type=["jpg", "png", "jpeg"])
    if yuklenen_resim and st.button(CEVIRI["tr"]["vision_analiz"]):
        with st.spinner("Analiz ediliyor..."):
            img_bytes = yuklenen_resim.getvalue()
            b64 = base64.b64encode(img_bytes).decode('utf-8')
            try:
                cevap = client.chat.completions.create(model=VISION_MODEL, messages=[{"role": "user", "content": [{"type": "text", "text": "Bu görselde ne var?"}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}])
                st.session_state.mesajlar.append({"role": "user", "content": "📷 [Görsel Yüklendi]"})
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
                st.error("⏳ **API Limitine Takıldık!** Groq'un ücretsiz limiti doldu. Lütfen 1 dakika bekleyip tekrar deneyin.")
                cevap = "Sistem şu an yoğun, lütfen birazdan tekrar deneyin."
            else:
                st.error(f"⚠️ Beklenmeyen bir hata oluştu: {e}")
                cevap = "Bir hata oluştu."
    
    st.session_state.mesajlar.append({"role": "assistant", "content": cevap})
    kaydet_sohbet(st.session_state.mesajlar)
    
    # Otomatik Sesli Okuma (Eğer açıksa)
    if st.session_state.otomatik_ses and cevap != "Bir hata oluştu.":
        sesli_oku(cevap)
        
    st.rerun()
