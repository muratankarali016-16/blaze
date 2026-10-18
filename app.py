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

# Supabase için (Eğer kullanırsan)
try:
    from supabase import create_client, Client
    SUPABASE_AKTIF = True
except ImportError:
    SUPABASE_AKTIF = False

st.set_page_config(page_title="BlazeX - Akıllı Asistan", page_icon="🔥", layout="centered")

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
        "aydinlatma": "📜 Gizlilik ve Aydınlatma",
        "aydinlatma_metni": """
        **Veri Sorumlusu:** BlazeX (Kişisel Kullanım)
        Bu uygulama, 6698 sayılı KVKK kapsamında verilerinizi işlemektedir. 
        - **İşlenen Veriler:** Sohbet geçmişiniz ve oturum bilgileriniz.
        - **Aktarım:** Hizmet için sohbet içerikleri Groq (ABD) ve Tavily (ABD) sunucularına aktarılır.
        - **Haklarınız:** Verilerinizin silinmesini talep etme hakkına sahipsiniz.
        
        ⚠️ **GÜVENLİK UYARISI:** Lütfen bu sisteme özel bilgilerinizi, ileri düzey kurumsal bilgilerinizi ve kişisel bilgilerinizi yazmayın.
        ⏳ **API LİMİTİ UYARISI:** Sistemin günlük kullanım limiti 1.000 istektir. Eğer bir limit uyarısı alırsanız, lütfen yarın tekrar deneyin.
        """
    }
}

# İNSANSI KARAKTERLER (Yapay zekanın robotik reddetmelerini engeller)
KISILIKLER = {
    "Normal": """Sen BlazeX adında samimi, esprili ve yardımcı bir yapay zeka asistanısın. 
Kuralların:
- Her zaman Türkçe cevap ver.
- Arkadaş canlısı ve doğal bir dil kullan.
- Eğer bir soruya cevap veremiyorsan (hassas bir konuysa veya bilmiyorsan), asla robotik bir dille 'Bunu yapamam' deme. Bunun yerine 'Bunu yanıtlamam doğru olmaz, ama şu konuda yardımcı olabilirim...' gibi kibarca konuyu değiştir.
- Kısa ve öz cevaplar ver, kullanıcıyı sıkmadan sohbet et.""",

    "Öğretmen": """Sen sabırlı bir öğretmensin. 
Kuralların:
- Her zaman Türkçe cevap ver.
- Konuları basit örneklerle, adım adım anlat. 
- Kullanıcıyı cesaretlendir.""",

    "Kod Ustası": """Sen uzman bir yazılımcısın. 
Kuralların:
- Her zaman Türkçe cevap ver.
- Temiz, yorumlu ve çalışan kodlar yaz. 
- Kodun nasıl çalıştığını kısaca açıkla."""
}

MODELLER = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b"]
VISION_MODEL = "qwen/qwen3.8-27b"

if "kullanici_id" not in st.session_state:
    st.session_state.kullanici_id = str(uuid.uuid4())[:8]
if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = []

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

client = Groq(api_key=st.secrets["GROQ_API_KEY"])
tavily = TavilyClient(api_key=st.secrets.get("TAVILY_API_KEY", ""))

# --- ARAYÜZ (CSS) ---
st.markdown("""
<style>
    .stApp { background-color: #1e1e2e; }
    .stChatMessage { border-radius: 15px; padding: 10px; margin-bottom: 10px; }
    .stButton button { background: #4d6bfe; color: white; border-radius: 10px; border: none; transition: 0.3s; }
    .stButton button:hover { background: #3b55d9; transform: scale(1.02); }
</style>
""", unsafe_allow_html=True)

# --- TTS ---
def sesli_oku(metin):
    safe_metin = metin.replace('"', '\\"').replace('\n', ' ')
    js = f"<script>var msg = new SpeechSynthesisUtterance(\"{safe_metin}\"); msg.lang = 'tr-TR'; window.speechSynthesis.speak(msg);</script>"
    st.components.v1.html(js, height=0)

# --- BAŞLIK (LOGO + İSİM) ---
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
    
    if st.session_state.mesajlar:
        sohbet_metni = "".join([f"{m['role']}: {m['content']}\n\n" for m in st.session_state.mesajlar if isinstance(m['content'], str)])
        st.download_button(CEVIRI["tr"]["disa_aktar"], sohbet_metni, f"blazex_{datetime.now().strftime('%Y%m%d')}.txt", use_container_width=True)
    
    st.markdown("---")
    gorsel_modu = st.toggle(CEVIRI["tr"]["gorsel_modu"], value=False)
    
    # İNTERNETE ARA TOGGLE'I (Varsayılan: Kapalı)
    web_arama_modu = st.toggle("🌐 İnternette Ara", value=False)
    
    with st.expander(CEVIRI["tr"]["aydinlatma"]):
        st.write(CEVIRI["tr"]["aydinlatma_metni"])

# --- SOHBET ALANI ---
if not st.session_state.mesajlar:
    st.info(CEVIRI["tr"]["hosgeldin"])

for i, m in enumerate(st.session_state.mesajlar):
    if not isinstance(m["content"], str): continue
    if m["role"] == "user":
        st.markdown(f'<div style="text-align: right; margin-bottom: 10px;"><span style="background: #005c4b; padding: 12px; border-radius: 15px; color: white; display: inline-block; max-width: 80%;">{m["content"]}</span></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="text-align: left; margin-bottom: 10px;"><span style="background: #262637; padding: 12px; border-radius: 15px; color: white; display: inline-block; max-width: 80%;">{m["content"]}</span></div>', unsafe_allow_html=True)
    
    if m["role"] == "assistant":
        c1, c2, c3 = st.columns([1, 1, 8])
        with c1:
            if st.button(CEVIRI["tr"]["sesli_dinle"], key=f"tts_{i}"):
                sesli_oku(m["content"])
        with c2:
            if st.button(CEVIRI["tr"]["kopyala"], key=f"cpy_{i}"):
                st.code(m["content"])

# --- DOSYA YÜKLEME ---
with st.expander("📎 Dosya / Görsel Ekle"):
    yuklenen_resim = st.file_uploader("Görsel seç (JPG/PNG)", type=["jpg", "png", "jpeg"])
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
                st.error(f"Görsel analiz hatası: {e}")

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
            # SADECE BUTON AÇIKSA WEB'DE ARA
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
            
            # Modelin doğal ve insansı sohbet etmesi için ek talimat
            mesajlar_gonder.append({"role": "system", "content": "Eğer sana özel bir arama sonucu verilmediyse, kendi genel bilgilerinle doğal bir sohbet havasında cevap ver. Kesinlikle robotik olma."})
            
            mesajlar_gonder += st.session_state.mesajlar
            
            stream = client.chat.completions.create(
                model=model, 
                messages=mesajlar_gonder, 
                stream=True, 
                temperature=0.6  # Daha tutarlı ve insansı cevaplar için düşürüldü
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
    st.rerun()
