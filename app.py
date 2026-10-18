import streamlit as st
from groq import Groq
import sqlite3
import json
from datetime import datetime
import requests
from io import BytesIO
import uuid
import base64
import io

st.set_page_config(
    page_title="BlazeGPT - Akıllı Asistan",
    page_icon="🔥",
    layout="centered"
)

# --- ÇEVİRİ ---
CEVIRI = {
    "tr": {
        "dil_adi": "🇹🇷 Türkçe", "baslik": "BlazeGPT",
        "alt_baslik": "Görsel Zeka + Gelişmiş Asistan ⚡",
        "sohbetler": "💬 Sohbetler", "yeni_sohbet": "➕ Yeni Sohbet",
        "sohbet_yok": "Henüz sohbet yok", "ayarlar": "⚙️ Ayarlar",
        "model": "🧠 Model", "kisilik": "🎭 Kişilik",
        "gorsel_modu": "🎨 Görsel Oluşturma",
        "gorsel_olusturuluyor": "🎨 Görsel oluşturuluyor...",
        "vision_modu": "📷 Görsel Analizi (Fotoğraf Yükle)",
        "vision_analiz": "🔍 Görseli Analiz Et",
        "vision_yukleniyor": "📷 Görsel yükleniyor...",
        "disa_aktar": "📥 Sohbeti İndir (TXT)",
        "hosgeldin": "Merhaba! Ben BlazeGPT 🔥 Sohbet edebilir, görsel oluşturabilir ve yüklediğin fotoğrafları analiz edebilirim. Hadi başlayalım!",
        "sor": "Bir şey sor veya fotoğraf yükle...",
        "kisilikler": {
            "Samimi Arkadaş": "Sen BlazeGPT adında samimi, esprili ve yardımcı bir yapay zeka asistanısın. Her zaman Türkçe cevap ver. Bilmediğin konularda mantıklı tahminler yürüt. Kısa ve öz ol.",
            "Profesyonel": "Sen BlazeGPT adında profesyonel bir asistansın. Türkçe cevap ver. Ciddi ve net ol.",
            "Öğretmen": "Sen sabırlı bir öğretmensin. Konuları basit örneklerle, adım adım anlat. Türkçe cevap ver.",
            "Kod Ustası": "Sen uzman bir yazılımcısın. Temiz ve çalışan kodlar yaz. Türkçe açıkla."
        },
        "kisilik_isimleri": ["Samimi Arkadaş", "Profesyonel", "Öğretmen", "Kod Ustası"],
        "hata": "⚠️ Hata", "gorsel_hata": "Görsel oluşturulamadı.",
        "gorsel_ayarlari": "🖼️ Görsel Ayarları",
        "gorsel_sayisi": "Görsel Sayısı", "gorsel_boyut": "Boyut",
        "kare": "⬛ Kare", "yatay": "▬ Yatay", "dikey": "▮ Dikey",
        "indir": "💾 İndir", "tema": "🎨 Tema", "galeri": "🖼️ Galeri",
        "galeri_bos": "Henüz kaydedilmiş görsel yok",
        "kopyala": "📋", "kopyalanacak": "📋 Kopyalanacak Metin", "kapat": "❌ Kapat"
    }
}

# --- MODELLER ---
MODELLER = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "llama-3.1-8b-instant",
    "qwen/qwen3.8-27b" # Bu model Vision (Görsel) destekler
]

TEMALAR = {
    "deepseek": {"ad": "🔵 DeepSeek", "arka": "#1e1e2e", "kenar": "#181825", "balon": "#262637", "vurgu": "#4d6bfe", "metin": "#e0e0e0", "kullanici_balon": "#005c4b"},
    "chatgpt": {"ad": "🟢 ChatGPT", "arka": "#212121", "kenar": "#171717", "balon": "#2f2f2f", "vurgu": "#10a37f", "metin": "#ececec", "kullanici_balon": "#0d5c4f"}
}

if "kullanici_id" not in st.session_state:
    st.session_state.kullanici_id = str(uuid.uuid4())[:8]
if "dil" not in st.session_state:
    st.session_state.dil = "tr"
if "tema" not in st.session_state:
    st.session_state.tema = "deepseek"
if "kopyalanacak" not in st.session_state:
    st.session_state.kopyalanacak = ""

def db_baglantisi():
    return sqlite3.connect("blazegpt.db", check_same_thread=False)

def db_olustur():
    conn = db_baglantisi()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS sohbetler (id INTEGER PRIMARY KEY AUTOINCREMENT, kullanici_id TEXT, baslik TEXT, olusturma TEXT, guncelleme TEXT, mesajlar TEXT)")
    conn.commit()
    conn.close()

db_olustur()

def yeni_sohbet(baslik="Yeni Sohbet"):
    conn = db_baglantisi()
    c = conn.cursor()
    simdi = datetime.now().isoformat()
    c.execute("INSERT INTO sohbetler (kullanici_id, baslik, olusturma, guncelleme, mesajlar) VALUES (?, ?, ?, ?, ?)",
              (st.session_state.kullanici_id, baslik, simdi, simdi, "[]"))
    sid = c.lastrowid
    conn.commit()
    conn.close()
    return sid

def sohbet_getir(sid):
    conn = db_baglantisi()
    c = conn.cursor()
    c.execute("SELECT mesajlar FROM sohbetler WHERE id = ? AND kullanici_id = ?", (sid, st.session_state.kullanici_id))
    r = c.fetchone()
    conn.close()
    return json.loads(r[0]) if r else []

def sohbet_guncelle(sid, mesajlar):
    conn = db_baglantisi()
    c = conn.cursor()
    simdi = datetime.now().isoformat()
    baslik = "Yeni Sohbet"
    for m in mesajlar:
        if m["role"] == "user" and isinstance(m["content"], str):
            baslik = m["content"][:40]
            break
    c.execute("UPDATE sohbetler SET mesajlar = ?, guncelleme = ?, baslik = ? WHERE id = ? AND kullanici_id = ?",
              (json.dumps(mesajlar, ensure_ascii=False), simdi, baslik, sid, st.session_state.kullanici_id))
    conn.commit()
    conn.close()

def tum_sohbetler():
    conn = db_baglantisi()
    c = conn.cursor()
    c.execute("SELECT id, baslik, guncelleme FROM sohbetler WHERE kullanici_id = ? ORDER BY guncelleme DESC", (st.session_state.kullanici_id,))
    r = c.fetchall()
    conn.close()
    return r

def sohbet_sil(sid):
    conn = db_baglantisi()
    c = conn.cursor()
    c.execute("DELETE FROM sohbetler WHERE id = ? AND kullanici_id = ?", (sid, st.session_state.kullanici_id))
    conn.commit()
    conn.close()

def gorsel_olustur(prompt, genislik, yukseklik, seed=0):
    try:
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
        params = {"width": genislik, "height": yukseklik, "nologo": "true", "seed": seed}
        r = requests.get(url, params=params, timeout=90)
        return r.content if r.status_code == 200 else None
    except Exception:
        return None

def tema_uygula(tema_adi):
    t = TEMALAR.get(tema_adi, TEMALAR["deepseek"])
    st.markdown(f"""
    <style>
        .stApp {{ background: {t['arka']}; }}
        .ana-baslik {{ text-align: center; color: {t['vurgu']}; font-size: 2.5em; font-weight: 700; margin-bottom: 0; }}
        .alt-baslik {{ text-align: center; color: #7a7a8e; margin-top: 0; margin-bottom: 15px; font-size: 0.9em; }}
        .sohbet-alani {{ display: flex; flex-direction: column; gap: 3px; padding: 5px; }}
        .mesaj-satir {{ display: flex; width: 100%; }}
        .mesaj-satir.sag {{ justify-content: flex-end; }}
        .mesaj-satir.sol {{ justify-content: flex-start; }}
        .balon {{ max-width: 78%; padding: 8px 12px; border-radius: 16px; font-size: 0.95em; line-height: 1.4; color: {t['metin']}; }}
        .balon.kullanici {{ background: {t['kullanici_balon']}; border-bottom-right-radius: 4px; }}
        .balon.bot {{ background: {t['balon']}; border-bottom-left-radius: 4px; }}
        .stChatInput textarea {{ background: {t['balon']} !important; color: {t['metin']} !important; border: 1px solid {t['vurgu']} !important; }}
        section[data-testid="stSidebar"] {{ background: {t['kenar']}; }}
        section[data-testid="stSidebar"] * {{ color: {t['metin']} !important; }}
        .stButton button {{ background: {t['balon']}; color: {t['metin']}; border: 1px solid {t['vurgu']}44; border-radius: 10px; }}
        .stButton button:hover {{ background: {t['vurgu']}; color: white; }}
    </style>
    """, unsafe_allow_html=True)

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

if "aktif_sohbet_id" not in st.session_state:
    st.session_state.aktif_sohbet_id = yeni_sohbet()
if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = sohbet_getir(st.session_state.aktif_sohbet_id)

T = CEVIRI[st.session_state.dil]
tema_uygula(st.session_state.tema)

# --- BAŞLIK ---
st.markdown(f'<h1 class="ana-baslik">{T["baslik"]}</h1>', unsafe_allow_html=True)
st.markdown(f'<p class="alt-baslik">{T["alt_baslik"]}</p>', unsafe_allow_html=True)

# --- KENAR ÇUBUĞU ---
with st.sidebar:
    st.markdown(f'## 🌐 Dil & Tema')
    secili_dil = st.selectbox("Dil", options=list(CEVIRI.keys()), format_func=lambda x: CEVIRI[x]["dil_adi"], label_visibility="collapsed")
    if secili_dil != st.session_state.dil:
        st.session_state.dil = secili_dil
        st.rerun()
        
    secili_tema = st.selectbox("Tema", options=list(TEMALAR.keys()), format_func=lambda x: TEMALAR[x]["ad"], label_visibility="collapsed")
    if secili_tema != st.session_state.tema:
        st.session_state.tema = secili_tema
        st.rerun()
    
    st.markdown("---")
    st.markdown(f"## {T['sohbetler']}")
    if st.button(T["yeni_sohbet"], use_container_width=True):
        st.session_state.aktif_sohbet_id = yeni_sohbet()
        st.session_state.mesajlar = []
        st.rerun()
    
    # Sohbet Listesi
    sohbetler = tum_sohbetler()
    for s_id, s_baslik, _ in sohbetler:
        c1, c2 = st.columns([4, 1])
        with c1:
            etiket = f"✅ {s_baslik}" if s_id == st.session_state.aktif_sohbet_id else f"💬 {s_baslik}"
            if st.button(etiket, key=f"soh_{s_id}", use_container_width=True):
                st.session_state.aktif_sohbet_id = s_id
                st.session_state.mesajlar = sohbet_getir(s_id)
                st.rerun()
        with c2:
            if st.button("🗑️", key=f"sil_{s_id}"):
                sohbet_sil(s_id)
                st.session_state.aktif_sohbet_id = yeni_sohbet()
                st.session_state.mesajlar = []
                st.rerun()
    
    st.markdown("---")
    st.markdown(f"## {T['ayarlar']}")
    model = st.selectbox(T["model"], MODELLER)
    kisi_secim = st.selectbox(T["kisilik"], T["kisilik_isimleri"])
    kisi = T["kisilikler"][kisi_secim]
    
    st.markdown("---")
    
    # --- 1. SOHBETİ DIŞA AKTARMA ---
    if st.session_state.mesajlar:
        sohbet_metni = ""
        for m in st.session_state.mesajlar:
            if isinstance(m["content"], str):
                rol = "Sen" if m["role"] == "user" else "BlazeGPT"
                sohbet_metni += f"{rol}: {m['content']}\n\n"
        
        st.download_button(
            label=T["disa_aktar"],
            data=sohbet_metni,
            file_name=f"blazegpt_sohbet_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    st.markdown("---")
    
    # --- 2. GÖRSEL ANALİZİ (VISION) ---
    with st.expander(T["vision_modu"]):
        yuklenen_resim = st.file_uploader("Bir fotoğraf seç (JPG/PNG)", type=["jpg", "jpeg", "png"])
        if yuklenen_resim is not None:
            st.image(yuklenen_resim, caption="Yüklenen Görsel", use_container_width=True)
            if st.button(T["vision_analiz"], use_container_width=True):
                with st.spinner(T["vision_yukleniyor"]):
                    # Resmi Base64'e çevir
                    img_bytes = yuklenen_resim.getvalue()
                    base64_image = base64.b64encode(img_bytes).decode('utf-8')
                    
                    try:
                        # Groq Vision API çağrısı
                        cevap = client.chat.completions.create(
                            model="qwen/qwen3.8-27b", # Vision destekli model
                            messages=[{
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "Bu görselde ne var? Detaylıca analiz et."},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                                ]
                            }]
                        )
                        analiz_sonucu = cevap.choices[0].message.content
                        
                        # Sonucu sohbete ekle
                        st.session_state.mesajlar.append({"role": "user", "content": "📷 [Bir fotoğraf yükledim]"})
                        st.session_state.mesajlar.append({"role": "assistant", "content": f"🖼️ **Görsel Analizi:**\n\n{analiz_sonucu}"})
                        sohbet_guncelle(st.session_state.aktif_sohbet_id, st.session_state.mesajlar)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Hata: {e}")

    st.markdown("---")
    gorsel_modu = st.toggle(T["gorsel_modu"], value=False)
    if gorsel_modu:
        gorsel_sayisi = st.slider(T["gorsel_sayisi"], min_value=1, max_value=4, value=4)
        boyut_secim = st.radio(T["gorsel_boyut"], [T["kare"], T["yatay"], T["dikey"]])
        if boyut_secim == T["kare"]:
            genislik, yukseklik = 1024, 1024
        elif boyut_secim == T["yatay"]:
            genislik, yukseklik = 1280, 720
        else:
            genislik, yukseklik = 720, 1280

# --- KOPYALAMA ALANI ---
if st.session_state.kopyalanacak:
    st.markdown(f"### {T['kopyalanacak']}")
    st.code(st.session_state.kopyalanacak, language=None)
    if st.button(T["kapat"]):
        st.session_state.kopyalanacak = ""
        st.rerun()

# --- SOHBET ALANI ---
tab1, tab2 = st.tabs(["💬 Sohbet", T["galeri"]])

with tab1:
    if not st.session_state.mesajlar:
        st.markdown(f'<div class="sohbet-alani"><div class="mesaj-satir sol"><div class="balon bot">{T["hosgeldin"]}</div></div></div>', unsafe_allow_html=True)
    else:
        for i, m in enumerate(st.session_state.mesajlar):
            if not isinstance(m["content"], str): continue
            icerik_html = m["content"].replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
            
            if m["role"] == "user":
                st.markdown(f'<div class="sohbet-alani"><div class="mesaj-satir sag"><div class="balon kullanici">{icerik_html}</div></div></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="sohbet-alani"><div class="mesaj-satir sol"><div class="balon bot">{icerik_html}</div></div></div>', unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([1, 1, 8])
            with c1:
                if st.button("📋", key=f"kopya_{i}", help=T["kopyala"]):
                    st.session_state.kopyalanacak = m["content"]
                    st.rerun()

    # --- GİRİŞ ---
    if soru := st.chat_input(T["sor"]):
        st.session_state.mesajlar.append({"role": "user", "content": soru})
        cevap = ""
        if gorsel_modu:
            with st.spinner(T["gorsel_olusturuluyor"]):
                gorseller = []
                for i in range(gorsel_sayisi):
                    veri = gorsel_olustur(soru, genislik, yukseklik, seed=i*1000)
                    if veri:
                        gorseller.append(veri)
                if gorseller:
                    cevap = f"🖼️ {len(gorseller)} görsel oluşturuldu: {soru}"
                    st.session_state.mesajlar.append({"role": "assistant", "content": cevap})
                    sohbet_guncelle(st.session_state.aktif_sohbet_id, st.session_state.mesajlar)
                    if len(gorseller) == 1:
                        st.image(BytesIO(gorseller[0]), use_container_width=True)
                    else:
                        for i in range(0, len(gorseller), 2):
                            cols = st.columns(2)
                            for j, col in enumerate(cols):
                                idx = i + j
                                if idx < len(gorseller):
                                    with col:
                                        st.image(BytesIO(gorseller[idx]), use_container_width=True)
                    st.rerun()
                else:
                    cevap = T["gorsel_hata"]
                    st.session_state.mesajlar.append({"role": "assistant", "content": cevap})
                    st.rerun()
        else:
            tam = ""
            try:
                stream = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": kisi}] + st.session_state.mesajlar,
                    stream=True,
                    temperature=0.8,
                    max_tokens=2048
                )
                for parca in stream:
                    tam += parca.choices[0].delta.content or ""
                cevap = tam
            except Exception as e:
                cevap = f"{T['hata']}: {e}"
            st.session_state.mesajlar.append({"role": "assistant", "content": cevap})
            sohbet_guncelle(st.session_state.aktif_sohbet_id, st.session_state.mesajlar)
            st.rerun()

with tab2:
    st.info(T["galeri_bos"])
