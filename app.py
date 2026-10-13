import streamlit as st
from groq import Groq
import sqlite3
import json
from datetime import datetime, timedelta
import requests
from io import BytesIO
import pandas as pd

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
        "hosgeldin": "### Merhaba! Ben BlazeGPT 🔥\n\n- 💬 Sohbet edebilirsin\n- 🎨 Görsel modunu açıp görsel oluşturabilirsin\n- 💾 Sohbetlerin **otomatik kaydedilir**\n\n**Hadi başlayalım!** ⬇️",
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
        "analitik": "📊 Analitik", "toplam_sohbet": "Toplam Sohbet",
        "toplam_mesaj": "Toplam Mesaj", "kullanilan_diller": "Kullanılan Diller",
        "en_cok_kisilik": "En Çok Seçilen Kişilik", "gunluk_kullanim": "Günlük Kullanım",
        "son_aktiviteler": "Son Aktiviteler"
    },
    "en": {
        "dil_adi": "🇬🇧 English", "baslik": "BlazeGPT",
        "alt_baslik": "Visual intelligence with Groq + Pollinations ⚡",
        "sohbetler": "💬 Chats", "yeni_sohbet": "➕ New Chat",
        "sohbet_yok": "No chats yet", "ayarlar": "⚙️ Settings",
        "model": "🧠 Model", "kisilik": "🎭 Personality",
        "gorsel_modu": "🎨 Image Generation",
        "gorsel_olusturuluyor": "🎨 Generating image...",
        "hosgeldin": "### Hello! I'm BlazeGPT 🔥\n\n- 💬 You can chat\n- 🎨 Turn on image mode\n- 💾 Your chats are **auto-saved**\n\n**Let's start!** ⬇️",
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
        "analitik": "📊 Analytics", "toplam_sohbet": "Total Chats",
        "toplam_mesaj": "Total Messages", "kullanilan_diller": "Languages Used",
        "en_cok_kisilik": "Most Used Personality", "gunluk_kullanim": "Daily Usage",
        "son_aktiviteler": "Recent Activities"
    },
    "de": {
        "dil_adi": "🇩🇪 Deutsch", "baslik": "BlazeGPT",
        "alt_baslik": "Visuelle Intelligenz mit Groq + Pollinations ⚡",
        "sohbetler": "💬 Chats", "yeni_sohbet": "➕ Neuer Chat",
        "sohbet_yok": "Noch keine Chats", "ayarlar": "⚙️ Einstellungen",
        "model": "🧠 Modell", "kisilik": "🎭 Persönlichkeit",
        "gorsel_modu": "🎨 Bildgenerierung",
        "gorsel_olusturuluyor": "🎨 Bild wird generiert...",
        "hosgeldin": "### Hallo! Ich bin BlazeGPT 🔥\n\n- 💬 Du kannst chatten\n- 🎨 Aktiviere den Bildmodus\n- 💾 Deine Chats werden **automatisch gespeichert**\n\n**Los geht's!** ⬇️",
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
        "analitik": "📊 Analytik", "toplam_sohbet": "Chats insgesamt",
        "toplam_mesaj": "Nachrichten insgesamt", "kullanilan_diller": "Verwendete Sprachen",
        "en_cok_kisilik": "Beliebteste Persönlichkeit", "gunluk_kullanim": "Tägliche Nutzung",
        "son_aktiviteler": "Letzte Aktivitäten"
    },
    "fr": {
        "dil_adi": "🇫🇷 Français", "baslik": "BlazeGPT",
        "alt_baslik": "Intelligence visuelle avec Groq + Pollinations ⚡",
        "sohbetler": "💬 Discussions", "yeni_sohbet": "➕ Nouvelle discussion",
        "sohbet_yok": "Pas encore de discussions", "ayarlar": "⚙️ Paramètres",
        "model": "🧠 Modèle", "kisilik": "🎭 Personnalité",
        "gorsel_modu": "🎨 Génération d'images",
        "gorsel_olusturuluyor": "🎨 Génération de l'image...",
        "hosgeldin": "### Bonjour ! Je suis BlazeGPT 🔥\n\n- 💬 Tu peux discuter\n- 🎨 Active le mode image\n- 💾 Tes discussions sont **auto-sauvegardées**\n\n**Commençons !** ⬇️",
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
        "analitik": "📊 Analytique", "toplam_sohbet": "Total des discussions",
        "toplam_mesaj": "Total des messages", "kullanilan_diller": "Langues utilisées",
        "en_cok_kisilik": "Personnalité la plus utilisée", "gunluk_kullanim": "Utilisation quotidienne",
        "son_aktiviteler": "Activités récentes"
    },
    "es": {
        "dil_adi": "🇪🇸 Español", "baslik": "BlazeGPT",
        "alt_baslik": "Inteligencia visual con Groq + Pollinations ⚡",
        "sohbetler": "💬 Chats", "yeni_sohbet": "➕ Nuevo chat",
        "sohbet_yok": "Aún no hay chats", "ayarlar": "⚙️ Ajustes",
        "model": "🧠 Modelo", "kisilik": "🎭 Personalidad",
        "gorsel_modu": "🎨 Generación de imágenes",
        "gorsel_olusturuluyor": "🎨 Generando imagen...",
        "hosgeldin": "### ¡Hola! Soy BlazeGPT 🔥\n\n- 💬 Puedes chatear\n- 🎨 Activa el modo imagen\n- 💾 Tus chats se **guardan automáticamente**\n\n**¡Empecemos!** ⬇️",
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
        "analitik": "📊 Analíticas", "toplam_sohbet": "Total de chats",
        "toplam_mesaj": "Total de mensajes", "kullanilan_diller": "Idiomas utilizados",
        "en_cok_kisilik": "Personalidad más usada", "gunluk_kullanim": "Uso diario",
        "son_aktiviteler": "Actividades recientes"
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
    .metrik-kart {
        background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%);
        color: white; padding: 20px; border-radius: 15px;
        text-align: center; margin-bottom: 10px;
    }
    .metrik-sayi { font-size: 2.5em; font-weight: bold; margin: 0; }
    .metrik-baslik { font-size: 0.9em; opacity: 0.9; margin: 0; }
</style>
""", unsafe_allow_html=True)

# --- API ---
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

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
            baslik TEXT, olusturma TEXT, guncelleme TEXT, mesajlar TEXT,
            dil TEXT DEFAULT 'tr', kisilik TEXT DEFAULT 'Normal Asistan'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS istatistikler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT, dil TEXT, kisilik TEXT,
            mesaj_sayisi INTEGER DEFAULT 0, gorsel_sayisi INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

db_olustur()

def yeni_sohbet(baslik="Yeni Sohbet"):
    conn = db_baglantisi()
    c = conn.cursor()
    simdi = datetime.now().isoformat()
    c.execute(
        "INSERT INTO sohbetler (baslik, olusturma, guncelleme, mesajlar, dil, kisilik) VALUES (?, ?, ?, ?, ?, ?)",
        (baslik, simdi, simdi, "[]", st.session_state.dil, "Normal")
    )
    sid = c.lastrowid
    conn.commit()
    conn.close()
    return sid

def sohbet_getir(sid):
    conn = db_baglantisi()
    c = conn.cursor()
    c.execute("SELECT mesajlar FROM sohbetler WHERE id = ?", (sid,))
    r = c.fetchone()
    conn.close()
    return json.loads(r[0]) if r else []

def sohbet_guncelle(sid, mesajlar, dil=None, kisilik=None):
    conn = db_baglantisi()
    c = conn.cursor()
    simdi = datetime.now().isoformat()
    baslik = "Yeni Sohbet"
    for m in mesajlar:
        if m["role"] == "user" and isinstance(m["content"], str):
            baslik = m["content"][:40] + ("..." if len(m["content"]) > 40 else "")
            break
    
    if dil and kisilik:
        c.execute(
            "UPDATE sohbetler SET mesajlar = ?, guncelleme = ?, baslik = ?, dil = ?, kisilik = ? WHERE id = ?",
            (json.dumps(mesajlar, ensure_ascii=False), simdi, baslik, dil, kisilik, sid)
        )
    else:
        c.execute(
            "UPDATE sohbetler SET mesajlar = ?, guncelleme = ?, baslik = ? WHERE id = ?",
            (json.dumps(mesajlar, ensure_ascii=False), simdi, baslik, sid)
        )
    conn.commit()
    conn.close()

def tum_sohbetler():
    conn = db_baglantisi()
    c = conn.cursor()
    c.execute("SELECT id, baslik, guncelleme FROM sohbetler ORDER BY guncelleme DESC")
    r = c.fetchall()
    conn.close()
    return r

def sohbet_sil(sid):
    conn = db_baglantisi()
    c = conn.cursor()
    c.execute("DELETE FROM sohbetler WHERE id = ?", (sid,))
    conn.commit()
    conn.close()

def istatistik_kaydet(dil, kisilik, mesaj_adedi=1, gorsel_adedi=0):
    conn = db_baglantisi()
    c = conn.cursor()
    bugun = datetime.now().strftime("%Y-%m-%d")
    c.execute(
        "INSERT INTO istatistikler (tarih, dil, kisilik, mesaj_sayisi, gorsel_sayisi) VALUES (?, ?, ?, ?, ?)",
        (bugun, dil, kisilik, mesaj_adedi, gorsel_adedi)
    )
    conn.commit()
    conn.close()

def istatistik_getir():
    conn = db_baglantisi()
    
    # Toplam sohbet
    toplam_sohbet = pd.read_sql_query("SELECT COUNT(*) as sayi FROM sohbetler", conn).iloc[0]["sayi"]
    
    # Toplam mesaj
    toplam_mesaj = pd.read_sql_query(
        "SELECT COALESCE(SUM(mesaj_sayisi), 0) as sayi FROM istatistikler", conn
    ).iloc[0]["sayi"]
    
    # Dil dağılımı
    dil_df = pd.read_sql_query(
        "SELECT dil, COUNT(*) as sayi FROM istatistikler GROUP BY dil", conn
    )
    
    # Kişilik dağılımı
    kisi_df = pd.read_sql_query(
        "SELECT kisilik, COUNT(*) as sayi FROM istatistikler GROUP BY kisilik ORDER BY sayi DESC LIMIT 1", conn
    )
    
    # Günlük kullanım (son 7 gün)
    gunluk_df = pd.read_sql_query(
        "SELECT tarih, SUM(mesaj_sayisi) as mesaj FROM istatistikler GROUP BY tarih ORDER BY tarih DESC LIMIT 7", conn
    )
    
    # Son aktiviteler
    son_df = pd.read_sql_query(
        "SELECT tarih, dil, kisilik, mesaj_sayisi FROM istatistikler ORDER BY id DESC LIMIT 10", conn
    )
    
    conn.close()
    
    return {
        "toplam_sohbet": toplam_sohbet,
        "toplam_mesaj": int(toplam_mesaj),
        "dil_df": dil_df,
        "en_cok_kisilik": kisi_df.iloc[0]["kisilik"] if len(kisi_df) > 0 else "-",
        "gunluk_df": gunluk_df,
        "son_df": son_df
    }

# --- SESSION STATE ---
if "aktif_sohbet_id" not in st.session_state:
    st.session_state.aktif_sohbet_id = yeni_sohbet()

if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = sohbet_getir(st.session_state.aktif_sohbet_id)

if "sayfa" not in st.session_state:
    st.session_state.sayfa = "sohbet"

T = CEVIRI[st.session_state.dil]

# --- BAŞLIK ---
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    st.image("logo.png", width=120)
st.markdown(f'<h1 class="ana-baslik">{T["baslik"]}</h1>', unsafe_allow_html=True)
st.markdown(f'<p class="alt-baslik">{T["alt_baslik"]}</p>', unsafe_allow_html=True)

# --- SAYFA SEÇİCİ (ÜSTTE) ---
col1, col2 = st.columns(2)
with col1:
    if st.button("💬 Sohbet", use_container_width=True):
        st.session_state.sayfa = "sohbet"
        st.rerun()
with col2:
    if st.button(T["analitik"], use_container_width=True):
        st.session_state.sayfa = "analitik"
        st.rerun()

st.markdown("---")

# --- KENAR ÇUBUĞU ---
with st.sidebar:
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
    
    if st.session_state.sayfa == "sohbet":
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
    else:
        model = "openai/gpt-oss-20b"
        kisi_secim = "Normal"
        kisi = "Sen yardımcı bir asistansın."
        gorsel_modu = False

# --- SAYFA: ANALİTİK ---
if st.session_state.sayfa == "analitik":
    st.markdown(f"## {T['analitik']}")
    
    ist = istatistik_getir()
    
    # Üst metrikler
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="metrik-kart">
            <p class="metrik-sayi">{ist['toplam_sohbet']}</p>
            <p class="metrik-baslik">{T['toplam_sohbet']}</p>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metrik-kart">
            <p class="metrik-sayi">{ist['toplam_mesaj']}</p>
            <p class="metrik-baslik">{T['toplam_mesaj']}</p>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metrik-kart">
            <p class="metrik-sayi">🏆</p>
            <p class="metrik-baslik">{ist['en_cok_kisilik']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Dil dağılımı
    if not ist["dil_df"].empty:
        st.markdown(f"### {T['kullanilan_diller']}")
        dil_df = ist["dil_df"].copy()
        dil_df["dil_adi"] = dil_df["dil"].map(lambda x: CEVIRI.get(x, {}).get("dil_adi", x))
        st.bar_chart(dil_df.set_index("dil_adi")["sayi"])
    
    # Günlük kullanım
    if not ist["gunluk_df"].empty:
        st.markdown(f"### {T['gunluk_kullanim']}")
        gunluk = ist["gunluk_df"].iloc[::-1]
        st.line_chart(gunluk.set_index("tarih")["mesaj"])
    
    # Son aktiviteler
    if not ist["son_df"].empty:
        st.markdown(f"### {T['son_aktiviteler']}")
        goster = ist["son_df"].copy()
        goster.columns = ["Tarih", "Dil", "Kişilik", "Mesaj"]
        st.dataframe(goster, use_container_width=True, hide_index=True)
    
    if ist["toplam_sohbet"] == 0:
        st.info("Henüz veri yok. Sohbet etmeye başla!")

# --- SAYFA: SOHBET ---
else:
    if not st.session_state.mesajlar:
        with st.chat_message("assistant", avatar="🔥"):
            st.markdown(T["hosgeldin"])
    
    for m in st.session_state.mesajlar:
        avatar = "👤" if m["role"] == "user" else "🔥"
        with st.chat_message(m["role"], avatar=avatar):
            if isinstance(m["content"], str):
                st.markdown(m["content"])
    
    if soru := st.chat_input(T["sor"]):
        st.session_state.mesajlar.append({"role": "user", "content": soru})
        with st.chat_message("user", avatar="👤"):
            st.markdown(soru)
        
        with st.chat_message("assistant", avatar="🔥"):
            if gorsel_modu:
                with st.spinner(T["gorsel_olusturuluyor"]):
                    try:
                        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(soru)}?width=1024&height=1024&nologo=true"
                        r = requests.get(url, timeout=60)
                        if r.status_code == 200:
                            st.image(BytesIO(r.content), caption=soru, use_container_width=True)
                            cevap = f"🖼️ {soru}"
                        else:
                            st.error(T["gorsel_hata"])
                            cevap = T["gorsel_hata"]
                    except Exception as e:
                        st.error(f"{T['hata']}: {e}")
                        cevap = T["gorsel_hata"]
                istatistik_kaydet(st.session_state.dil, kisi_secim, 1, 1)
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
                istatistik_kaydet(st.session_state.dil, kisi_secim, 1, 0)
        
        st.session_state.mesajlar.append({"role": "assistant", "content": cevap})
        sohbet_guncelle(
            st.session_state.aktif_sohbet_id,
            st.session_state.mesajlar,
            st.session_state.dil,
            kisi_secim
        )
