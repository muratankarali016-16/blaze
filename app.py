import streamlit as st
from groq import Groq
import base64
import requests
from io import BytesIO

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="BlazeGPT", page_icon="🔥", layout="centered")

# --- ÖZEL CSS ---
st.markdown("""
<style>
    .ana-baslik { text-align: center; background: linear-gradient(90deg, #ff6b35 0%, #f7931e 50%, #ffcc00 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 3.5em; font-weight: bold; }
    .alt-baslik { text-align: center; color: #888; margin-bottom: 30px; }
    .stChatMessage { border-radius: 15px; padding: 12px 16px; margin-bottom: 10px; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #1a1a1a 0%, #2a1a0a 100%); }
    section[data-testid="stSidebar"] * { color: #e0e0e0 !important; }
    .stButton button { background: linear-gradient(90deg, #ff6b35 0%, #f7931e 100%); color: white; border-radius: 20px; width: 100%; }
</style>
""", unsafe_allow_html=True)

# Logo ve başlık yan yana
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image("logo.png", width=120)
st.markdown('<h1 class="ana-baslik">BlazeGPT</h1>', unsafe_allow_html=True)
st.markdown('<p class="alt-baslik">Groq + Pollinations ile görsel zekası ⚡</p>', unsafe_allow_html=True)

# --- API İSTEMCİLERİ ---
client_groq = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- SESSION STATE ---
if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = []

# --- YARDIMCI FONKSİYONLAR ---
def resmi_base64_yap(dosya):
    """Yüklenen resmi base64 formatına çevirir (Groq Vision için)."""
    return base64.b64encode(dosya.getvalue()).decode('utf-8')

def resim_olustur(prompt):
    """Pollinations AI ile metinden görsel oluşturur."""
    try:
        # Pollinations basit GET isteği ile çalışır
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=1024&height=1024&nologo=true"
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            return response.content
        return None
    except Exception as e:
        st.error(f"Görsel oluşturma hatası: {e}")
        return None

# --- KENAR ÇUBUĞU ---
with st.sidebar:
    st.markdown("## ⚙️ Ayarlar")
    
    # Model seçimi (vision yeteneği olan model)
    model = st.selectbox("🧠 Metin Modeli", [
        "qwen/qwen3.8-27b",          # Vision destekli model
        "openai/gpt-oss-120b"
    ])
    
    # Görsel oluşturma modu
    st.markdown("---")
    st.markdown("### 🎨 Görsel Modu")
    gorsel_modu = st.toggle("Görsel Oluşturma Modu", value=False, help="Açıkken yazdığınız metin görsele dönüştürülür.")
    
    st.markdown("---")
    if st.button("🗑️ Sohbeti Temizle"):
        st.session_state.mesajlar = []
        st.rerun()

# --- HOŞGELDİN MESAJI ---
if not st.session_state.mesajlar:
    with st.chat_message("assistant", avatar="🔥"):
        st.markdown("""
### Merhaba! Ben BlazeGPT 🔥

Bana bir şeyler yazabilir, **fotoğraf yükleyebilir** veya **görsel oluşturmamı** isteyebilirsin.

- 📷 **Görsel Analizi:** Fotoğraf yükle, sana anlatsın.
- 🎨 **Görsel Oluşturma:** Sol menüden modu aç, hayalini yaz.
        """)

# --- ESKİ MESAJLARI GÖSTER ---
for m in st.session_state.mesajlar:
    avatar = "👤" if m["role"] == "user" else "🔥"
    with st.chat_message(m["role"], avatar=avatar):
        st.markdown(m["content"])

# --- GİRİŞ ALANI ---
if soru := st.chat_input("Bir şey sor veya bir görsel hayal et..."):
    # Kullanıcı mesajını kaydet ve göster
    st.session_state.mesajlar.append({"role": "user", "content": soru})
    with st.chat_message("user", avatar="👤"):
        st.markdown(soru)

    with st.chat_message("assistant", avatar="🔥"):
        # --- GÖRSEL OLUŞTURMA MODU ---
        if gorsel_modu:
            with st.spinner("🎨 Görsel oluşturuluyor... Bu birkaç saniye sürebilir."):
                resim_verisi = resim_olustur(soru)
                if resim_verisi:
                    # BytesIO ile resmi göster
                    st.image(BytesIO(resim_verisi), caption=f"Prompt: {soru}", use_container_width=True)
                    st.session_state.mesajlar.append({"role": "assistant", "content": f"🖼️ Oluşturulan görsel: {soru}"})
                else:
                    st.error("Görsel oluşturulamadı. Lütfen tekrar deneyin.")
                    st.session_state.mesajlar.append({"role": "assistant", "content": "Görsel oluşturulamadı."})
        
        # --- NORMAL SOHBET / GÖRSEL ANALİZİ ---
        else:
            yer = st.empty()
            tam = ""
            try:
                # Mesajları hazırla
                mesajlar = [{"role": "system", "content": "Sen yardımcı bir asistansın. Türkçe cevap ver. Görsel varsa analiz et."}]
                
                # Geçmiş mesajları ekle
                for m in st.session_state.mesajlar:
                    # Sadece metin içerenleri ekle (görsel içerenleri Groq'a göndermiyoruz)
                    if isinstance(m["content"], str):
                        mesajlar.append({"role": m["role"], "content": m["content"]})
                
                stream = client_groq.chat.completions.create(
                    model=model,
                    messages=mesajlar,
                    stream=True
                )
                
                for parca in stream:
                    icerik = parca.choices[0].delta.content or ""
                    tam += icerik
                    yer.markdown(tam + "▌")
                yer.markdown(tam)
                
            except Exception as e:
                yer.error(f"⚠️ Hata: {e}")
                tam = "Üzgünüm, bir hata oluştu."
        
        st.session_state.mesajlar.append({"role": "assistant", "content": tam if not gorsel_modu else "Görsel oluşturuldu."})

# --- DOSYA YÜKLEME ALANI (GÖRSEL ANALİZİ İÇİN) ---
with st.sidebar:
    st.markdown("---")
    st.markdown("### 📷 Görsel Analizi")
    yuklenen_dosya = st.file_uploader("Bir resim yükle", type=["jpg", "jpeg", "png"])
    
    if yuklenen_dosya:
        if st.button("🔍 Bu Görseli Analiz Et"):
            with st.spinner("Görsel analiz ediliyor..."):
                try:
                    # Resmi base64'e çevir
                    base64_resim = resmi_base64_yap(yuklenen_dosya)
                    
                    # Groq Vision API çağrısı
                    cevap = client_groq.chat.completions.create(
                        model="qwen/qwen3.8-27b",
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Bu görselde ne var? Detaylı açıkla."},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_resim}"}}
                            ]
                        }]
                    )
                    
                    # Sonucu göster
                    st.success("Analiz Tamamlandı!")
                    st.write(cevap.choices[0].message.content)
                    
                    # Sohbet geçmişine ekle
                    st.session_state.mesajlar.append({"role": "user", "content": "📷 [Görsel Yüklendi]"})
                    st.session_state.mesajlar.append({"role": "assistant", "content": cevap.choices[0].message.content})
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Görsel analizi hatası: {e}")
