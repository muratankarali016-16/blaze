import streamlit as st
from groq import Groq
import sqlite3
import json
from datetime import datetime
import requests
from io import BytesIO
import uuid

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="BlazeGPT", page_icon="🔥", layout="centered")

# --- ÇEVİRİ SÖZLÜĞÜ ---
CEVIRI = {
    "tr": {
        "dil_adi": "🇹🇷 Türkçe", "baslik": "BlazeGPT",
        "alt_baslik": "Groq + Pollinations ile görsel zekası ⚡",
        "sohbetler": "💬 Sohbetler", "yeni_sohbet": "➕ Yeni Sohbet",
        "sohbet_yok": "Henüz sohbet yok", "ayarlar": "⚙️ Ayarlar",
        "model": "🧠 Model", "kisilik": "🎭 Kişilik",
        "gorsel_modu": "🎨 Görsel Oluşturma",
        "gorsel_olusturuluyor": "🎨 Görsel oluşturuluyor...",
        "hosgeldin": "### Merhaba! Ben BlazeGPT 🔥\n\n- 💬 Sohbet edebilirsin\n- 🎨 Görsel modunu açıp görsel oluşturabilirsin\n- 💾 Sohbetlerin **otomatik kaydedilir** ve **sadece sana özeldir** 🔒\n\n**Hadi başlayalım!** ⬇️",
        "sor": "Bir şey sor...",
        "kisilikler": {
            "Normal Asistan": "Sen yardımcı, nazik ve zeki bir asistansın. Türkçe cevap ver.",
            "Öğretmen": "Sen sabırlı bir öğretmensin. Basit örneklerle anlatırsın. Türkçe cevap ver.",
            "Şair": "Sen duygusal bir şairsin. Şiirsel bir dille yazarsın. Türkçe cevap ver.",
            "Kod Yazıcı": "Sen uzman bir yazılımcısın. Temiz, yorumlu kod yazarsın. Türkçe açıkla.",
            "Komedyen": "Sen esprili bir komedyensin. Mizah katarsın. Türkçe cevap ver."
        },
        "kisilik_isimleri": ["Normal Asistan", "Öğretmen", "Şair", "Kod Yazıcı", "Komedyen"],
        "hata": "⚠️ Hata", "gorsel_hata": "Görsel oluşturulamadı.",
        "gorsel_ayarlari": "🖼️ Görsel Ayarları",
        "gorsel_sayisi": "Görsel Sayısı",
        "gorsel_boyut": "Boyut",
        "kare": "⬛ Kare (1024x1024)",
        "yatay": "▬ Yatay (1280x720)",
        "dikey": "▮ Dikey (720x1280)",
        "indir": "💾 İndir"
    },
    "en": {
        "dil_adi": "🇬🇧 English", "baslik": "BlazeGPT",
        "alt_baslik": "Visual intelligence with Groq + Pollinations ⚡",
        "sohbetler": "💬 Chats", "yeni_sohbet": "➕ New Chat",
        "sohbet_yok": "No chats yet", "ayarlar": "⚙️ Settings",
        "model": "🧠 Model", "kisilik": "🎭 Personality",
        "gorsel_modu": "🎨 Image Generation",
        "gorsel_olusturuluyor": "🎨 Generating image...",
        "hosgeldin": "### Hello! I'm BlazeGPT 🔥\n\n- 💬 You can chat\n- 🎨 Turn on image mode\n- 💾 Your chats are **auto-saved** and **only for you** 🔒\n\n**Let's start!** ⬇️",
        "sor": "Ask something...",
        "kisilikler": {
            "Normal Assistant": "You are a helpful, kind, and smart assistant. Answer in English.",
            "Teacher": "You are a patient teacher. Explain with simple examples. Answer in English.",
            "Poet": "You are an emotional poet. Write poetically. Answer in English.",
            "Coder": "You are an expert programmer. Write clean, commented code. Explain in English.",
            "Comedian": "You are a funny comedian. Add humor. Answer in English."
        },
        "kisilik_isimleri": ["Normal Assistant", "Teacher", "Poet", "Coder", "Comedian"],
        "hata": "⚠️ Error", "gorsel_hata": "Could not generate image.",
        "gorsel_ayarlari": "🖼️ Image Settings",
        "gorsel_sayisi": "Number of Images",
        "gorsel_boyut": "Size",
        "kare": "⬛ Square (1024x1024)",
        "yatay": "▬ Landscape (1280x720)",
        "dikey": "▮ Portrait (720x1280)",
        "indir": "💾 Download"
    },
    "de": {
        "dil_adi": "🇩🇪 Deutsch", "baslik": "BlazeGPT",
        "alt_baslik": "Visuelle Intelligenz mit Groq + Pollinations ⚡",
        "sohbetler": "💬 Chats", "yeni_sohbet": "➕ Neuer Chat",
        "sohbet_yok": "Noch keine Chats", "ayarlar": "⚙️ Einstellungen",
        "model": "🧠 Modell", "kisilik": "🎭 Persönlichkeit",
        "gorsel_modu": "🎨 Bildgenerierung",
        "gorsel_olusturuluyor": "🎨 Bild wird generiert...",
        "hosgeldin": "### Hallo! Ich bin BlazeGPT 🔥\n\n- 💬 Du kannst chatten\n- 🎨 Aktiviere den Bildmodus\n- 💾 Deine Chats werden **automatisch gespeichert** und sind **nur für dich** 🔒\n\n**Los geht's!** ⬇️",
        "sor": "Frag etwas...",
        "kisilikler": {
            "Normaler Assistent": "Du bist ein hilfsbereiter, freundlicher und kluger Assistent. Antworte auf Deutsch.",
            "Lehrer": "Du bist ein geduldiger Lehrer. Erkläre mit einfachen Beispielen. Antworte auf Deutsch.",
            "Dichter": "Du bist ein emotionaler Dichter. Schreibe poetisch. Antworte auf Deutsch.",
            "Programmierer": "Du bist ein erfahrener Programmierer. Schreibe sauberen, kommentierten Code. Erkläre auf Deutsch.",
            "Komiker": "Du bist ein lustiger Komiker. Füge Humor hinzu. Antworte auf Deutsch."
        },
        "kisilik_isimleri": ["Normaler Assistent", "Lehrer", "Dichter", "Programmierer", "Komiker"],
        "hata": "⚠️ Fehler", "gorsel_hata": "Bild konnte nicht generiert werden.",
        "gorsel_ayarlari": "🖼️ Bild-Einstellungen",
        "gorsel_sayisi": "Anzahl der Bilder",
        "gorsel_boyut": "Größe",
        "kare": "⬛ Quadrat (1024x1024)",
        "yatay": "▬ Querformat (1280x720)",
        "dikey": "▮ Hochformat (720x1280)",
        "indir": "💾 Herunterladen"
    },
    "fr": {
        "dil_adi": "🇫🇷 Français", "baslik": "BlazeGPT",
        "alt_baslik": "Intelligence visuelle avec Groq + Pollinations ⚡",
        "sohbetler": "💬 Discussions", "yeni_sohbet": "➕ Nouvelle discussion",
        "sohbet_yok": "Pas encore de discussions", "ayarlar": "⚙️ Paramètres",
        "model": "🧠 Modèle", "kisilik": "🎭 Personnalité",
        "gorsel_modu": "🎨 Génération d'images",
        "gorsel_olusturuluyor": "🎨 Génération de l'image...",
        "hosgeldin": "### Bonjour ! Je suis BlazeGPT 🔥\n\n- 💬 Tu peux discuter\n- 🎨 Active le mode image\n- 💾 Tes discussions sont **auto-sauvegardées** et **rien que pour toi** 🔒\n\n**Commençons !** ⬇️",
        "sor": "Pose une question...",
        "kisilikler": {
            "Assistant Normal": "Tu es un assistant utile, gentil et intelligent. Réponds en français.",
            "Professeur": "Tu es un professeur patient. Explique avec des exemples simples. Réponds en français.",
            "Poète": "Tu es un poète émotionnel. Écris poétiquement. Réponds en français.",
            "Programmeur": "Tu es un programmeur expert. Écris du code propre et commenté. Explique en français.",
            "Comédien": "Tu es un comédien drôle. Ajoute de l'humour. Réponds en français."
        },
        "kisilik_isimleri": ["Assistant Normal", "Professeur", "Poète", "Programmeur", "Comédien"],
        "hata": "⚠️ Erreur", "gorsel_hata": "Impossible de générer l'image.",
        "gorsel_ayarlari": "🖼️ Paramètres d'image",
        "gorsel_sayisi": "Nombre d'images",
        "gorsel_boyut": "Taille",
        "kare": "⬛ Carré (1024x1024)",
        "yatay": "▬ Paysage (1280x720)",
        "dikey": "▮ Portrait (720x1280)",
        "indir": "💾 Télécharger"
    },
    "es": {
        "dil_adi": "🇪🇸 Español", "baslik": "BlazeGPT",
        "alt_baslik": "Inteligencia visual con Groq + Pollinations ⚡",
        "sohbetler": "💬 Chats", "yeni_sohbet": "➕ Nuevo chat",
        "sohbet_yok": "Aún no hay chats", "ayarlar": "⚙️ Ajustes",
        "model": "🧠 Modelo", "kisilik": "🎭 Personalidad",
        "gorsel_modu": "🎨 Generación de imágenes",
        "gorsel_olusturuluyor": "🎨 Generando imagen...",
        "hosgeldin": "### ¡Hola! Soy BlazeGPT 🔥\n\n- 💬 Puedes chatear\n- 🎨 Activa el modo imagen\n- 💾 Tus chats se **guardan automáticamente** y son **solo para ti** 🔒\n\n**¡Empecemos!** ⬇️",
        "sor": "Pregunta algo...",
        "kisilikler": {
            "Asistente Normal": "Eres un asistente útil, amable e inteligente. Responde en español.",
            "Profesor": "Eres un profesor paciente. Explica con ejemplos simples. Responde en español.",
            "Poeta": "Eres un poeta emocional. Escribe poéticamente. Responde en español.",
            "Programador": "Eres un programador experto. Escribe código limpio y comentado. Explica en español.",
            "Comediante": "Eres un comediante divertido. Añade humor. Responde en español."
        },
        "kisilik_isimleri": ["Asistente Normal", "Profesor", "Poeta", "Programador", "Comediante"],
        "hata": "⚠️ Error", "gorsel_hata": "No se pudo generar la imagen.",
        "gorsel_ayarlari": "🖼️ Ajustes de imagen",
        "gorsel_sayisi": "Número de imágenes",
        "gorsel_boyut": "Tamaño",
        "kare": "⬛ Cuadrado (1024x1024)",
        "yatay": "▬ Horizontal (1280x720)",
        "dikey": "▮ Vertical (720x1280)",
        "indir": "💾 Descargar"
    }
}

# --- ÖZEL CSS ---
st.markdown("""
<style>
    .ana-baslik {
        text-align: center;
        background: linear-gradient(90deg, #ff6b35 0%, #f7931e 50%, #ffcc00 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3.5em; font-weight: bold; margin-bottom: 0;
    }
    .alt-baslik { text-align: center; color: #888; margin-bottom: 30px; }
    .stChatMessage { border-radius: 15px; padding: 12px 16px; margin-bottom: 10px; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #1a1a1a 0%, #2a1a0a 100%); }
    section[data-testid="stSidebar"] * { color: #e0e0e0 !important; }
    .stButton button {
        background: linear-gradient(90deg, #ff6b35 0%, #f7931e 100%);
        color: white; border: none; border-radius: 20px;
        font-weight: bold; width: 100%;
    }
    .stDownloadButton button {
        background: linear-gradient(90deg, #ff6b35 0%, #f7931e 100%);
        color: white; border: none; border-radius: 15px;
        font-size: 0.85em; padding: 5px 10px;
    }
    .kullanici-bilgi {
        text-align: center;
        background: linear-gradient(90deg, #ff6b35 0%, #f7931e 100%);
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 0.85em;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- API ---
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- KULLANICI OTURUM ID (Benzersiz) ---
if "kullanici_id" not in st.session_state:
    st.session_state.kullanici_id = str(uuid.uuid4())[:8]
    # Kısa ve benzersiz bir ID (ör: "a3f9b2c1")

# --- DİL ---
if "dil" not in st.session_state:
    st.session_state.dil = "tr"

# --- VERİTABANI ---
def db_baglantisi():
    return sqlite3.connect("blazegpt.db", check_same_thread=False)

def db_olustur():
    conn = db_baglantisi()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS sohbetler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kullanici_id TEXT,
            baslik TEXT, olusturma TEXT, guncelleme TEXT, mesajlar TEXT
        )
    """)
    # Eski tabloyu kontrol et ve kullanici_id kolonu ekle (yoksa)
    try:
        c.execute("ALTER TABLE sohbetler ADD COLUMN kullanici_id TEXT")
    except sqlite3.OperationalError:
        pass  # Zaten var
    conn.commit()
    conn.close()

db_olustur()

def yeni_sohbet(baslik="Yeni Sohbet"):
    conn = db_baglantisi()
    c = conn.cursor()
    simdi = datetime.now().isoformat()
    c.execute(
        "INSERT INTO sohbetler (kullanici_id, baslik, olusturma, guncelleme, mesajlar) VALUES (?, ?, ?, ?, ?)",
        (st.session_state.kullanici_id, baslik, simdi, simdi, "[]")
    )
    sid = c.lastrowid
    conn.commit()
    conn.close()
    return sid

def sohbet_getir(sid):
    conn = db_baglantisi()
    c = conn.cursor()
    # SADECE kendi sohbetini getir
    c.execute(
        "SELECT mesajlar FROM sohbetler WHERE id = ? AND kullanici_id = ?",
        (sid, st.session_state.kullanici_id)
    )
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
            baslik = m["content"][:40] + ("..." if len(m["content"]) > 40 else "")
            break
    # SADECE kendi sohbetini güncelle
    c.execute(
        "UPDATE sohbetler SET mesajlar = ?, guncelleme = ?, baslik = ? WHERE id = ? AND kullanici_id = ?",
        (json.dumps(mesajlar, ensure_ascii=False), simdi, baslik, sid, st.session_state.kullanici_id)
    )
    conn.commit()
    conn.close()

def tum_sohbetler():
    conn = db_baglantisi()
    c = conn.cursor()
    # SADECE kendi sohbetlerini getir
    c.execute(
        "SELECT id, baslik, guncelleme FROM sohbetler WHERE kullanici_id = ? ORDER BY guncelleme DESC",
        (st.session_state.kullanici_id,)
    )
    r = c.fetchall()
    conn.close()
    return r

def sohbet_sil(sid):
    conn = db_baglantisi()
    c = conn.cursor()
    # SADECE kendi sohbetini sil
    c.execute(
        "DELETE FROM sohbetler WHERE id = ? AND kullanici_id = ?",
        (sid, st.session_state.kullanici_id)
    )
    conn.commit()
    conn.close()

# --- GÖRSEL OLUŞTURMA ---
def gorsel_olustur(prompt, genislik, yukseklik, seed=0):
    try:
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
        params = {"width": genislik, "height": yukseklik, "nologo": "true", "seed": seed}
        r = requests.get(url, params=params, timeout=90)
        if r.status_code == 200:
            return r.content
        return None
    except Exception:
        return None

# --- SESSION STATE ---
if "aktif_sohbet_id" not in st.session_state:
    st.session_state.aktif_sohbet_id = yeni_sohbet()

if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = sohbet_getir(st.session_state.aktif_sohbet_id)

T = CEVIRI[st.session_state.dil]

# --- BAŞLIK ---
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    st.image("logo.png", width=120)
st.markdown(f'<h1 class="ana-baslik">{T["baslik"]}</h1>', unsafe_allow_html=True)
st.markdown(f'<p class="alt-baslik">{T["alt_baslik"]}</p>', unsafe_allow_html=True)

# --- KENAR ÇUBUĞU ---
with st.sidebar:
    # KULLANICI BİLGİSİ
    st.markdown(
        f'<div class="kullanici-bilgi">🔒 Oturum: {st.session_state.kullanici_id}</div>',
        unsafe_allow_html=True
    )
    
    st.markdown("## 🌐 Dil / Language")
    secili_dil = st.selectbox(
        "Dil", options=list(CEVIRI.keys()),
        format_func=lambda x: CEVIRI[x]["dil_adi"],
        index=list(CEVIRI.keys()).index(st.session_state.dil),
        label_visibility="collapsed"
    )
    if secili_dil != st.session_state.dil:
        st.session_state.dil = secili_dil
        st.rerun()
    
    st.markdown("---")
    st.markdown(f"## {T['sohbetler']}")
    if st.button(T["yeni_sohbet"]):
        st.session_state.aktif_sohbet_id = yeni_sohbet()
        st.session_state.mesajlar = []
        st.rerun()
    st.markdown("---")
    
    sohbetler = tum_sohbetler()
    if sohbetler:
        for s_id, s_baslik, s_tarih in sohbetler:
            c1, c2 = st.columns([5, 1])
            with c1:
                etiket = f"💬 {s_baslik}"
                if s_id == st.session_state.aktif_sohbet_id:
                    etiket = f"✅ {s_baslik}"
                if st.button(etiket, key=f"sohbet_{s_id}"):
                    st.session_state.aktif_sohbet_id = s_id
                    st.session_state.mesajlar = sohbet_getir(s_id)
                    st.rerun()
            with c2:
                if st.button("🗑️", key=f"sil_{s_id}"):
                    sohbet_sil(s_id)
                    if s_id == st.session_state.aktif_sohbet_id:
                        st.session_state.aktif_sohbet_id = yeni_sohbet()
                        st.session_state.mesajlar = []
                    st.rerun()
    else:
        st.caption(T["sohbet_yok"])
    
    st.markdown("---")
    st.markdown(f"## {T['ayarlar']}")
    model = st.selectbox(T["model"], ["openai/gpt-oss-20b", "openai/gpt-oss-120b"])
    kisi_secim = st.selectbox(T["kisilik"], T["kisilik_isimleri"])
    kisi = T["kisilikler"][kisi_secim]
    
    st.markdown("---")
    gorsel_modu = st.toggle(T["gorsel_modu"], value=False)
    
    if gorsel_modu:
        st.markdown(f"### {T['gorsel_ayarlari']}")
        gorsel_sayisi = st.slider(T["gorsel_sayisi"], min_value=1, max_value=4, value=4)
        boyut_secim = st.radio(T["gorsel_boyut"], [T["kare"], T["yatay"], T["dikey"]])
        
        if boyut_secim == T["kare"]:
            genislik, yukseklik = 1024, 1024
        elif boyut_secim == T["yatay"]:
            genislik, yukseklik = 1280, 720
        else:
            genislik, yukseklik = 720, 1280

# --- HOŞGELDİN ---
if not st.session_state.mesajlar:
    with st.chat_message("assistant", avatar="🔥"):
        st.markdown(T["hosgeldin"])

# --- ESKİ MESAJLAR ---
for m in st.session_state.mesajlar:
    avatar = "👤" if m["role"] == "user" else "🔥"
    with st.chat_message(m["role"], avatar=avatar):
        if isinstance(m["content"], str):
            st.markdown(m["content"])

# --- GİRİŞ ---
if soru := st.chat_input(T["sor"]):
    st.session_state.mesajlar.append({"role": "user", "content": soru})
    with st.chat_message("user", avatar="👤"):
        st.markdown(soru)
    
    with st.chat_message("assistant", avatar="🔥"):
        if gorsel_modu:
            with st.spinner(T["gorsel_olusturuluyor"]):
                st.markdown(f"**{soru}**")
                
                gorseller = []
                for i in range(gorsel_sayisi):
                    veri = gorsel_olustur(soru, genislik, yukseklik, seed=i*1000)
                    if veri:
                        gorseller.append(veri)
                
                if gorseller:
                    if len(gorseller) == 1:
                        st.image(BytesIO(gorseller[0]), use_container_width=True)
                        st.download_button(
                            label=T["indir"],
                            data=gorseller[0],
                            file_name="blazegpt_1.png",
                            mime="image/png"
                        )
                    else:
                        for i in range(0, len(gorseller), 2):
                            cols = st.columns(2)
                            for j, col in enumerate(cols):
                                idx = i + j
                                if idx < len(gorseller):
                                    with col:
                                        st.image(BytesIO(gorseller[idx]), use_container_width=True)
                                        st.download_button(
                                            label=T["indir"],
                                            data=gorseller[idx],
                                            file_name=f"blazegpt_{idx+1}.png",
                                            mime="image/png",
                                            key=f"indir_{idx}"
                                        )
                    cevap = f"🖼️ {len(gorseller)} görsel oluşturuldu: {soru}"
                else:
                    st.error(T["gorsel_hata"])
                    cevap = T["gorsel_hata"]
        else:
            yer = st.empty()
            tam = ""
            try:
                stream = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": kisi}]
                             + st.session_state.mesajlar,
                    stream=True
                )
                for parca in stream:
                    icerik = parca.choices[0].delta.content or ""
                    tam += icerik
                    yer.markdown(tam + "▌")
                yer.markdown(tam)
                cevap = tam
            except Exception as e:
                yer.error(f"{T['hata']}: {e}")
                cevap = "Hata"
    
    st.session_state.mesajlar.append({"role": "assistant", "content": cevap})
    sohbet_guncelle(st.session_state.aktif_sohbet_id, st.session_state.mesajlar)
