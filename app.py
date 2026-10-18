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

st.set_page_config(page_title="BlazeGPT - Süper", page_icon="🔥", layout="centered")

# --- ÇEVİRİ ---
CEVIRI = {
    "tr": {
        "baslik": "BlazeGPT", "alt_baslik": "Sesli, Görsel ve Akıllı Asistan ⚡",
        "sohbetler": "💬 Sohbetler", "yeni_sohbet": "➕ Yeni Sohbet",
        "ayarlar": "⚙️ Ayarlar", "model": "🧠 Model", "kisilik": "🎭 Kişilik",
        "gorsel_modu": "🎨 Görsel Oluşturma", "hosgeldin": "Merhaba! Ben BlazeGPT 🔥 Artık sesli konuşabiliyor, dosya okuyabiliyor ve özel karakterlere bürünebiliyorum!",
        "sor": "Bir şey sor...", "hata": "⚠️ Hata",
        "ozel_karakter": "Kendi Karakterini Yarat", "karakter_yaz": "Karakter talimatını yaz (örn: Sen korsan gibi konuşan bir yazılımcısın)...",
        "disa_aktar": "📥 Sohbeti İndir", "vision_analiz": "🔍 Görseli Analiz Et",
        "sesli_dinle": "🔊 Dinle", "kopyala": "📋", "kaynaklar": "🌐 Kaynaklar:"
    }
}

MODELLER = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
VISION_MODEL = "qwen/qwen3.8-27b"

if "kullanici_id" not in st.session_state:
    st.session_state.kullanici_id = str(uuid.uuid4())[:8]
if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = []

# --- VERİTABANI (Basitleştirilmiş) ---
def db_baglantisi():
    return sqlite3.connect("blazegpt.db", check_same_thread=False)

def db_olustur():
    conn = db_baglantisi()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS sohbetler (id INTEGER PRIMARY KEY AUTOINCREMENT, kullanici_id TEXT, baslik TEXT, mesajlar TEXT)")
    conn.commit()
    conn.close()
db_olustur()

def kaydet_sohbet(mesajlar):
    conn = db_baglantisi()
    c = conn.cursor()
    baslik = "Sohbet"
    for m in mesajlar:
        if m["role"] == "user" and isinstance(m["content"], str):
            baslik = m["content"][:30]
            break
    c.execute("INSERT INTO sohbetler (kullanici_id, baslik, mesajlar) VALUES (?, ?, ?)", (st.session_state.kullanici_id, baslik, json.dumps(mesajlar, ensure_ascii=False)))
    conn.commit()
    conn.close()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])
tavily = TavilyClient(api_key=st.secrets.get("TAVILY_API_KEY", ""))

# --- TTS (Sesli Okuma) JS Kodu ---
def sesli_oku(metin):
    # Metni güvenli hale getir
    safe_metin = metin.replace('"', '\\"').replace('\n', ' ')
    js = f"""
    <script>
        function speak() {{
            var msg = new SpeechSynthesisUtterance("{safe_metin}");
            msg.lang = 'tr-TR';
            window.speechSynthesis.speak(msg);
        }}
        speak();
    </script>
    """
    st.components.v1.html(js, height=0)

# --- BAŞLIK ---
st.markdown(f'<h1 style="text-align: center; color: #4d6bfe; font-size: 2.5em; margin-bottom: 0;">🔥 {CEVIRI["tr"]["baslik"]}</h1>', unsafe_allow_html=True)
st.markdown(f'<p style="text-align: center; color: #888;">{CEVIRI["tr"]["alt_baslik"]}</p>', unsafe_allow_html=True)

# --- KENAR ÇUBUĞU ---
with st.sidebar:
    st.markdown(f"## {CEVIRI['tr']['ayarlar']}")
    model = st.selectbox(CEVIRI["tr"]["model"], MODELLER)
    
    kisi_secim = st.selectbox(CEVIRI["tr"]["kisilik"], ["Normal", "Öğretmen", "Kod Ustası", "Özel Karakter"])
    
    if kisi_secim == "Özel Karakter":
        ozel_kisi = st.text_area(CEVIRI["tr"]["karakter_yaz"], "Sen yardımcı bir asistansın.")
        kisi = ozel_kisi
    elif kisi_secim == "Öğretmen":
        kisi = "Sen sabırlı bir öğretmensin. Türkçe cevap ver."
    elif kisi_secim == "Kod Ustası":
        kisi = "Sen uzman bir yazılımcısın. Türkçe açıkla."
    else:
        kisi = "Sen yardımcı bir asistansın. Türkçe cevap ver."
        
    st.markdown("---")
    if st.button(CEVIRI["tr"]["disa_aktar"]):
        sohbet_metni = "".join([f"{m['role']}: {m['content']}\n\n" for m in st.session_state.mesajlar if isinstance(m['content'], str)])
        st.download_button("Tıkla ve İndir", data=sohbet_metni, file_name="blazegpt_sohbet.txt", mime="text/plain")
    
    st.markdown("---")
    gorsel_modu = st.toggle(CEVIRI["tr"]["gorsel_modu"], value=False)

# --- SOHBET ALANI ---
for i, m in enumerate(st.session_state.mesajlar):
    if not isinstance(m["content"], str): continue
    
    # Balon tasarımı
    if m["role"] == "user":
        st.markdown(f'<div style="text-align: right; margin-bottom: 10px;"><span style="background: #005c4b; padding: 10px; border-radius: 10px; color: white;">{m["content"]}</span></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="text-align: left; margin-bottom: 10px;"><span style="background: #262637; padding: 10px; border-radius: 10px; color: white;">{m["content"]}</span></div>', unsafe_allow_html=True)
    
    # Bot mesajıysa butonları göster
    if m["role"] == "assistant":
        c1, c2, c3 = st.columns([1, 1, 8])
        with c1:
            if st.button(CEVIRI["tr"]["sesli_dinle"], key=f"tts_{i}"):
                sesli_oku(m["content"])
        with c2:
            if st.button(CEVIRI["tr"]["kopyala"], key=f"cpy_{i}"):
                st.code(m["content"])

# --- DOSYA YÜKLEME VE VİZYON ---
with st.expander("📎 Dosya / Görsel Ekle"):
    yuklenen_resim = st.file_uploader("Görsel seç", type=["jpg", "png", "jpeg"])
    if yuklenen_resim and st.button(CEVIRI["tr"]["vision_analiz"]):
        with st.spinner("Analiz ediliyor..."):
            img_bytes = yuklenen_resim.getvalue()
            b64 = base64.b64encode(img_bytes).decode('utf-8')
            try:
                cevap = client.chat.completions.create(
                    model=VISION_MODEL,
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": "Bu görselde ne var?"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                    ]}]
                )
                st.session_state.mesajlar.append({"role": "user", "content": "📷 [Görsel Yüklendi]"})
                st.session_state.mesajlar.append({"role": "assistant", "content": cevap.choices[0].message.content})
                st.rerun()
            except Exception as e:
                st.error(f"Hata: {e}")

# --- MİKROFON (SESLİ GİRİŞ - TARAYICI DESTEKLİYORSA) ---
sesli_giris_js = """
<script>
function startDictation() {
    if (window.hasOwnProperty('webkitSpeechRecognition')) {
        var recognition = new webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = "tr-TR";
        recognition.start();
        recognition.onresult = function(e) {
            document.getElementById('output').value = e.results[0][0].transcript;
            recognition.stop();
        };
    }
}
</script>
<input type="text" id="output" placeholder="Konuşmak için butona bas..." style="width: 100%; padding: 10px; background: #262637; color: white; border: 1px solid #4d6bfe; border-radius: 10px;">
<button onclick="startDictation()" style="background: #4d6bfe; color: white; padding: 10px; border-radius: 10px; margin-top: 5px; width: 100%;">🎤 Mikrofonla Konuş</button>
"""
st.components.v1.html(sesli_giris_js, height=100)

# --- GİRİŞ KUTUSU ---
if soru := st.chat_input(CEVIRI["tr"]["sor"]):
    st.session_state.mesajlar.append({"role": "user", "content": soru})
    
    cevap = ""
    if gorsel_modu:
        # Görsel oluşturma (Basitleştirilmiş)
        with st.spinner("Görsel oluşturuluyor..."):
            url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(soru)}?width=1024&height=1024&nologo=true"
            r = requests.get(url, timeout=90)
            if r.status_code == 200:
                st.image(BytesIO(r.content), use_container_width=True)
                cevap = f"🖼️ Görsel oluşturuldu: {soru}"
            else:
                cevap = "Görsel oluşturulamadı."
    else:
        # WEB ARAMA VEYA NORMAL SOHBET
        tam = ""
        try:
            # Tavily ile arama yap (Eğer API key varsa)
            arama_sonucu = ""
            if tavily:
                with st.spinner("🌐 İnternette araştırıyorum..."):
                    try:
                        res = tavily.search(query=soru, max_results=2)
                        for r in res.get("results", []):
                            arama_sonucu += f"Kaynak: {r['url']}\nÖzet: {r['content']}\n\n"
                    except:
                        pass

            # AI'ya gönder
            mesajlar_gonder = [{"role": "system", "content": kisi}]
            if arama_sonucu:
                mesajlar_gonder.append({"role": "system", "content": f"İşte internette bulduğun güncel bilgiler:\n{arama_sonucu}"})
            mesajlar_gonder += st.session_state.mesajlar
            
            stream = client.chat.completions.create(
                model=model,
                messages=mesajlar_gonder,
                stream=True,
                temperature=0.8
            )
            for parca in stream:
                tam += parca.choices[0].delta.content or ""
            cevap = tam
            
            # Kaynakları göster
            if arama_sonucu:
                cevap += f"\n\n{CEVIRI['tr']['kaynaklar']}\n"
                for r in res.get("results", []):
                    cevap += f"- [{r['title']}]({r['url']})\n"
                    
        except Exception as e:
            cevap = f"Hata: {e}"
    
    st.session_state.mesajlar.append({"role": "assistant", "content": cevap})
    kaydet_sohbet(st.session_state.mesajlar)
    st.rerun()
