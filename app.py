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
        "hosgeldin": "Merhaba! Ben **BlazeGPT** 🔥 Sohbet edebilir, görsel oluşturabilirsin. Sohbetlerin otomatik kaydedilir ve sadece sana özeldir 🔒",
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
        "indir": "💾 İndir",
        "tema": "🎨 Tema",
        "galeri": "🖼️ Galeri",
        "galeri_bos": "Henüz kaydedilmiş görsel yok"
    },
    "en": {
        "dil_adi": "🇬🇧 English", "baslik": "BlazeGPT",
        "alt_baslik": "Visual intelligence with Groq + Pollinations ⚡",
        "sohbetler": "💬 Chats", "yeni_sohbet": "➕ New Chat",
        "sohbet_yok": "No chats yet", "ayarlar": "⚙️ Settings",
        "model": "🧠 Model", "kisilik": "🎭 Personality",
        "gorsel_modu": "🎨 Image Generation",
        "gorsel_olusturuluyor": "🎨 Generating image...",
        "hosgeldin": "Hello! I'm **BlazeGPT** 🔥 You can chat and generate images. Chats are auto-saved and private 🔒",
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
        "indir": "💾 Download",
        "tema": "🎨 Theme",
        "galeri": "🖼️ Gallery",
        "galeri_bos": "No saved images yet"
    }
}

# --- TEMALAR ---
TEMALAR = {
    "deepseek": {"ad": "🔵 DeepSeek", "arka": "#1e1e2e", "kenar": "#181825", "balon": "#262637", "vurgu": "#4d6bfe", "metin": "#e0e0e0", "kullanici_balon": "#005c4b"},
    "chatgpt": {"ad": "🟢 ChatGPT", "arka": "#212121", "kenar": "#171717", "balon": "#2f2f2f", "vurgu": "#10a37f", "metin": "#ececec", "kullanici_balon": "#0d5c4f"},
    "blaze": {"ad": "🔥 Blaze", "arka": "#0f0f0f", "kenar": "#1a0f08", "balon": "#1a1a1a", "vurgu": "#ff6b35", "metin": "#e8e8e8", "kullanici_balon": "#8b2500"},
    "gece": {"ad": "🌙 Gece Mavisi", "arka": "#0a1929", "kenar": "#061220", "balon": "#132f4c", "vurgu": "#5090d3", "metin": "#e7ebf0", "kullanici_balon": "#0d4770"},
    "mor": {"ad": "🟣 Mor", "arka": "#1a0f2e", "kenar": "#100820", "balon": "#2a1a45", "vurgu": "#a855f7", "metin": "#e8e0f0", "kullanici_balon": "#6b21a8"}
}

# --- SESSION ---
if "kullanici_id" not in st.session_state:
    st.session_state.kullanici_id = str(uuid.uuid4())[:8]
if "dil" not in st.session_state:
    st.session_state.dil = "tr"
if "tema" not in st.session_state:
    st.session_state.tema = "deepseek"

# --- VERİTABANI ---
def db_baglantisi():
    return sqlite3.connect("blazegpt.db", check_same_thread=False)

def db_olustur():
    conn = db_baglantisi()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS sohbetler (id INTEGER PRIMARY KEY AUTOINCREMENT, kullanici_id TEXT, baslik TEXT, olusturma TEXT, guncelleme TEXT, mesajlar TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS galeri (id INTEGER PRIMARY KEY AUTOINCREMENT, kullanici_id TEXT, prompt TEXT, gorsel BLOB, tarih TEXT)")
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
            baslik = m["content"][:40] + ("..." if len(m["content"]) > 40 else "")
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

def galeri_ekle(prompt, gorsel_bytes):
    conn = db_baglantisi()
    c = conn.cursor()
    simdi = datetime.now().isoformat()
    c.execute("INSERT INTO galeri (kullanici_id, prompt, gorsel, tarih) VALUES (?, ?, ?, ?)",
              (st.session_state.kullanici_id, prompt, gorsel_bytes, simdi))
    conn.commit()
    conn.close()

def galeri_getir():
    conn = db_baglantisi()
    c = conn.cursor()
    c.execute("SELECT id, prompt, gorsel, tarih FROM galeri WHERE kullanici_id = ? ORDER BY tarih DESC", (st.session_state.kullanici_id,))
    r = c.fetchall()
    conn.close()
    return r

def galeri_sil(gid):
    conn = db_baglantisi()
    c = conn.cursor()
    c.execute("DELETE FROM galeri WHERE id = ? AND kullanici_id = ?", (gid, st.session_state.kullanici_id))
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
        .element-container, .stMarkdown, div[data-testid="stVerticalBlock"] > div {{ margin: 0 !important; padding: 0 !important; gap: 0 !important; }}
        .stApp {{ background: {t['arka']}; }}
        .ana-baslik {{ text-align: center; color: {t['vurgu']}; font-size: 2.5em; font-weight: 700; margin-bottom: 0; margin-top: 10px; }}
        .alt-baslik {{ text-align: center; color: #7a7a8e; margin-top: 0; margin-bottom: 15px; font-size: 0.9em; }}
        .sohbet-alani {{ display: flex; flex-direction: column; gap: 3px; padding: 10px 5px; }}
        .mesaj-satir {{ display: flex; width: 100%; }}
        .mesaj-satir.sag {{ justify-content: flex-end; }}
        .mesaj-satir.sol {{ justify-content: flex-start; }}
        .balon {{ max-width: 78%; padding: 8px 12px 4px 12px; border-radius: 16px; font-size: 0.95em; line-height: 1.4; word-wrap: break-word; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.4); color: {t['metin']}; }}
        .balon.kullanici {{ background: {t['kullanici_balon']}; color: #e9edef; border-bottom-right-radius: 4px; }}
        .balon.bot {{ background: {t['balon']}; color: {t['metin']}; border-bottom-left-radius: 4px; }}
        .zaman {{ font-size: 0.65em; color: #a0a0a0; margin-top: 2px; text-align: right; display: block; line-height: 1; }}
        .balon.bot .zaman {{ text-align: left; }}
        .stChatInput textarea {{ background: {t['balon']} !important; color: {t['metin']} !important; border: 1px solid {t['vurgu']} !important; border-radius: 12px !important; }}
        .stChatInput textarea:focus {{ border-color: {t['vurgu']} !important; }}
        section[data-testid="stSidebar"] {{ background: {t['kenar']}; border-right: 1px solid {t['balon']}; }}
        section[data-testid="stSidebar"] * {{ color: {t['metin']} !important; }}
        section[data-testid="stSidebar"] h2 {{ color: {t['vurgu']} !important; }}
        .stButton button {{ background: {t['balon']}; color: {t['metin']}; border: 1px solid {t['vurgu']}44; border-radius: 10px; font-weight: 500; width: 100%; padding: 6px 10px; margin: 2px 0; }}
        .stButton button:hover {{ background: {t['vurgu']}; color: white; border-color: {t['vurgu']}; }}
        .stDownloadButton button {{ background: {t['vurgu']}; color: white; border: none; border-radius: 10px; font-size: 0.85em; padding: 5px 10px; }}
        .kullanici-bilgi {{ text-align: center; background: linear-gradient(90deg, {t['vurgu']} 0%, {t['vurgu']}cc 100%); color: white; padding: 6px 14px; border-radius: 10px; font-size: 0.78em; margin-bottom: 10px; font-weight: 600; }}
        .stSelectbox div[data-baseweb="select"] > div, .stTextInput input {{ background: {t['balon']} !important; color: {t['metin']} !important; border: 1px solid {t['vurgu']}44 !important; border-radius: 10px !important; }}
        .stMarkdown h2 {{ color: {t['vurgu']} !important; }}
        .stMarkdown h3 {{ color: {t['vurgu']}cc !important; }}
        code {{ background: {t['kenar']} !important; color: {t['vurgu']} !important; padding: 2px 6px; border-radius: 6px; }}
        ::-webkit-scrollbar {{ width: 8px; }}
        ::-webkit-scrollbar-track {{ background: {t['kenar']}; }}
        ::-webkit-scrollbar-thumb {{ background: {t['vurgu']}; border-radius: 4px; }}
        img {{ display: block; margin-left: auto; margin-right: auto; filter: drop-shadow(0 0 15px {t['vurgu']}55); }}
        .stAlert {{ background: {t['balon']} !important; border-radius: 10px !important; border-left: 4px solid {t['vurgu']} !important; color: {t['metin']} !important; }}
    </style>
    """, unsafe_allow_html=True)

# --- API ---
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- SESSION DEVAM ---
if "aktif_sohbet_id" not in st.session_state:
    st.session_state.aktif_sohbet_id = yeni_sohbet()
if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = sohbet_getir(st.session_state.aktif_sohbet_id)

T = CEVIRI[st.session_state.dil]

# --- TEMA UYGULA ---
tema_uygula(st.session_state.tema)

# --- BAŞLIK ---
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    st.image("logo.png", width=100)
st.markdown(f'<h1 class="ana-baslik">{T["baslik"]}</h1>', unsafe_allow_html=True)
st.markdown(f'<p class="alt-baslik">{T["alt_baslik"]}</p>', unsafe_allow_html=True)

# --- KENAR ÇUBUĞU ---
with st.sidebar:
    st.markdown(f'<div class="kullanici-bilgi">🔒 Oturum: {st.session_state.kullanici_id}</div>', unsafe_allow_html=True)
    
    st.markdown("## 🌐 Dil")
    secili_dil = st.selectbox("Dil", options=list(CEVIRI.keys()), format_func=lambda x: CEVIRI[x]["dil_adi"], index=list(CEVIRI.keys()).index(st.session_state.dil), label_visibility="collapsed")
    if secili_dil != st.session_state.dil:
        st.session_state.dil = secili_dil
        st.rerun()
    
    st.markdown(f"## {T['tema']}")
    tema_secenekleri = list(TEMALAR.keys())
    secili_tema = st.selectbox(T["tema"], options=tema_secenekleri, format_func=lambda x: TEMALAR[x]["ad"], index=tema_secenekleri.index(st.session_state.tema), label_visibility="collapsed")
    if secili_tema != st.session_state.tema:
        st.session_state.tema = secili_tema
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

# --- SEKMELER ---
tab1, tab2 = st.tabs(["💬 Sohbet", T["galeri"]])

def mesajlari_goster(mesajlar):
    if not mesajlar:
        return
    html = '<div class="sohbet-alani">'
    for m in mesajlar:
        if not isinstance(m["content"], str):
            continue
        icerik = m["content"].replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        zaman = datetime.now().strftime("%H:%M")
        if m["role"] == "user":
            html += f'<div class="mesaj-satir sag"><div class="balon kullanici">{icerik}<span class="zaman">{zaman} ✓✓</span></div></div>'
        else:
            html += f'<div class="mesaj-satir sol"><div class="balon bot">{icerik}<span class="zaman">{zaman}</span></div></div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

with tab1:
    if not st.session_state.mesajlar:
        st.markdown(f'<div class="sohbet-alani"><div class="mesaj-satir sol"><div class="balon bot">{T["hosgeldin"]}</div></div></div>', unsafe_allow_html=True)
    else:
        mesajlari_goster(st.session_state.mesajlar)
    
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
                        galeri_ekle(soru, veri)
                if gorseller:
                    cevap = f"🖼️ {len(gorseller)} görsel oluşturuldu: {soru}"
                    st.session_state.mesajlar.append({"role": "assistant", "content": cevap})
                    sohbet_guncelle(st.session_state.aktif_sohbet_id, st.session_state.mesajlar)
                    if len(gorseller) == 1:
                        st.image(BytesIO(gorseller[0]), use_container_width=True)
                        st.download_button(label=T["indir"], data=gorseller[0], file_name="blazegpt_1.png", mime="image/png")
                    else:
                        for i in range(0, len(gorseller), 2):
                            cols = st.columns(2)
                            for j, col in enumerate(cols):
                                idx = i + j
                                if idx < len(gorseller):
                                    with col:
                                        st.image(BytesIO(gorseller[idx]), use_container_width=True)
                                        st.download_button(label=T["indir"], data=gorseller[idx], file_name=f"blazegpt_{idx+1}.png", mime="image/png", key=f"indir_{idx}")
                    st.rerun()
                else:
                    cevap = T["gorsel_hata"]
                    st.session_state.mesajlar.append({"role": "assistant", "content": cevap})
                    sohbet_guncelle(st.session_state.aktif_sohbet_id, st.session_state.mesajlar)
                    st.rerun()
        else:
            tam = ""
            try:
                stream = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": kisi}] + st.session_state.mesajlar,
                    stream=True
                )
                for parca in stream:
                    icerik = parca.choices[0].delta.content or ""
                    tam += icerik
                cevap = tam
            except Exception as e:
                cevap = f"{T['hata']}: {e}"
            st.session_state.mesajlar.append({"role": "assistant", "content": cevap})
            sohbet_guncelle(st.session_state.aktif_sohbet_id, st.session_state.mesajlar)
            st.rerun()

with tab2:
    st.markdown(f"### {T['galeri']}")
    gorseller = galeri_getir()
    if gorseller:
        for gid, prompt, gorsel_bytes, tarih in gorseller:
            with st.container():
                st.image(BytesIO(gorsel_bytes), use_container_width=True)
                st.caption(f"📝 {prompt}")
                c1, c2 = st.columns(2)
                with c1:
                    st.download_button(label=T["indir"], data=gorsel_bytes, file_name=f"galeri_{gid}.png", mime="image/png", key=f"galeri_indir_{gid}")
                with c2:
                    if st.button("🗑️", key=f"galeri_sil_{gid}"):
                        galeri_sil(gid)
                        st.rerun()
                st.markdown("---")
    else:
        st.info(T["galeri_bos"])
