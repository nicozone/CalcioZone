import os
import re
import json
import tempfile
import textwrap
from pathlib import Path
from io import BytesIO

import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import asyncio
import edge_tts
from moviepy import AudioFileClip, ImageSequenceClip

st.set_page_config(page_title="CalcioZone Studio", page_icon="⚽", layout="wide")

W, H, FPS = 720, 1280, 12
ACCENT = (255, 205, 45)
WHITE = (255, 255, 255)

st.markdown("""
<style>
.stApp { background: #080d18; color: #fff; }
section[data-testid="stSidebar"] { background: #101827; }
h1, h2, h3, p, label { color: #fff !important; }
div.stButton > button { background: #e52b45; color: white; border: 0; border-radius: 12px; font-weight: 800; min-height: 3rem; }
div.stButton > button:hover { background: #ff405b; color: white; }
.stDownloadButton button { background: #19a875; color: white; border: 0; border-radius: 12px; font-weight: 800; }
div[data-testid="stAlert"] { border-radius: 12px; }
</style>
""", unsafe_allow_html=True)

st.title("⚽ CALCIOZONE")
st.caption("Viral Football Studio · Crea video verticali per TikTok, Reels e YouTube Shorts")
st.markdown("**NUOVO STILE:** scene dinamiche · sottotitoli parola per parola · zoom · grafiche sportive")

with st.sidebar:
    st.header("Impostazioni")
    api_key = st.text_input("Chiave OpenAI (facoltativa)", type="password",
                            help="Facoltativa: senza chiave vengono usati copioni evergreen di esempio.")
    topic = st.text_input("Argomento", placeholder="Es. 5 curiosità su Messi")
    category = st.selectbox("Categoria", ["Mix calcistico", "Notizie", "Calciomercato", "Curiosità", "Storie", "Classifiche e confronti", "Analisi tattica"])
    duration_target = st.select_slider("Durata indicativa", options=[30, 45, 60], value=30)
    count = st.selectbox("Copioni da preparare", [1, 3, 5], index=0)
    uploaded = st.file_uploader("Foto tue o con licenza (facoltative)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    st.caption("Carica immagini che possiedi o che hai il diritto di usare. Senza immagini, il video crea sfondi sportivi animati originali.")
    st.divider()
    st.caption("La versione attuale crea il montaggio e il file MP4. Controlla sempre notizie, nomi e diritti prima della pubblicazione.")

def make_scripts(topic, category, count, api_key, duration):
    if api_key:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        prompt = f"""
Crea {count} copioni originali in italiano per video verticali sul calcio.
Categoria: {category}. Argomento: {topic or "scegli argomenti evergreen interessanti"}.
Durata obiettivo: circa {duration} secondi ciascuno.
Stile: ritmo rapido, apertura-hook molto forte nei primi 2 secondi, frasi brevi e naturali,
curiosità e tensione narrativa, tono coinvolgente ma accurato.
Non inventare statistiche, citazioni o fatti recenti. Se un fatto non è certo, non presentarlo come certo.
Restituisci SOLO JSON valido: un array di oggetti con chiavi title, hook, script, description, hashtags.
Il testo parlato deve essere adatto alla durata, senza indicazioni di scena.
"""
        response = client.responses.create(model="gpt-4.1-mini", input=prompt)
        data = json.loads(response.output_text)
        return data[:count]

    subjects = [topic.strip()] if topic.strip() else [
        "Le curiosità più sorprendenti della storia del calcio",
        "Le rimonte più incredibili del calcio",
        "Cosa rende speciale il numero 10"
    ]
    result = []
    for i in range(count):
        subject = subjects[i % len(subjects)]
        result.append({
            "title": subject,
            "hook": "Aspetta: questa storia del calcio è incredibile!",
            "script": (
                f"{subject}. Nel calcio ci sono storie, dettagli e momenti che spesso passano inosservati. "
                "Dietro ogni grande partita ci sono preparazione, talento, scelte e pressione. "
                "Ed è proprio questo che rende questo sport così imprevedibile. "
                "Qual è il dettaglio che ti ha colpito di più? Scrivilo nei commenti e seguici per altre storie di calcio."
            ),
            "description": "Una storia di calcio da scoprire. Tu cosa ne pensi?",
            "hashtags": "#calcio #football #seriea #championsleague #shorts"
        })
    return result

def load_font(size, bold=True):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def make_gradient_bg(t, scene_idx):
    # Original abstract stadium-style background; no copyrighted match footage.
    im = Image.new("RGB", (W, H), (7, 13, 26))
    px = im.load()
    for y in range(H):
        k = y / H
        col = (int(8 + 5*k), int(16 + 8*k), int(32 + 15*k))
        for x in range(W):
            px[x, y] = col
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    shift = int((t * 34) % 260)
    gd.ellipse((300-shift, 130, 930-shift, 760), fill=(0, 150, 110, 55))
    gd.ellipse((-250+shift//2, 570, 400+shift//2, 1220), fill=(15, 70, 170, 55))
    for n in range(8):
        x = (n*125 + int(t*55)) % (W+180) - 90
        gd.line((x, 0, x-170, H), fill=(255, 255, 255, 12), width=3)
    glow = glow.filter(ImageFilter.GaussianBlur(42))
    return Image.alpha_composite(im.convert("RGBA"), glow).convert("RGB")

def cover_crop(image, t, scene_idx):
    image = image.convert("RGB")
    scale = max(W / image.width, H / image.height)
    nw, nh = int(image.width * scale), int(image.height * scale)
    image = image.resize((nw, nh), Image.Resampling.LANCZOS)
    zoom = 1.0 + 0.10 * ((t % 4.5) / 4.5)
    zw, zh = int(nw*zoom), int(nh*zoom)
    image = image.resize((zw, zh), Image.Resampling.LANCZOS)
    maxx, maxy = max(0, zw-W), max(0, zh-H)
    phase = (t % 4.5) / 4.5
    x = int(maxx * (phase if scene_idx % 2 == 0 else 1-phase))
    y = int(maxy * (0.35 + 0.3*phase))
    return image.crop((x, y, x+W, y+H))

def word_timings(text, total_duration):
    words = re.findall(r"\S+", text.strip())
    if not words:
        return []
    weights = [max(1, len(re.sub(r"[^\wÀ-ÿ]", "", w))) for w in words]
    total = sum(weights)
    cursor = 0.0
    result = []
    for idx, (word, weight) in enumerate(zip(words, weights)):
        end = cursor + total_duration * weight / total
        result.append((word, cursor, end, idx))
        cursor = end
    return result

def draw_wrapped_words(draw, words, active_idx, font, y, max_width=630):
    lines, current = [], []
    for item in words:
        test = current + [item]
        txt = " ".join(w[0] for w in test)
        if draw.textbbox((0, 0), txt, font=font)[2] <= max_width or not current:
            current = test
        else:
            lines.append(current)
            current = [item]
    if current:
        lines.append(current)
    lines = lines[-2:]
    line_h = 62
    start_y = y - (len(lines)-1)*line_h/2
    for li, line in enumerate(lines):
        widths = [draw.textbbox((0,0), w[0], font=font)[2] for w in line]
        spaces = [draw.textbbox((0,0), " ", font=font)[2]] * (len(line)-1)
        total_w = sum(widths) + sum(spaces)
        x = (W-total_w)//2
        yy = int(start_y + li*line_h)
        for j, (word, _, _, idx) in enumerate(line):
            color = ACCENT if idx == active_idx else WHITE
            # Shadow for readability
            draw.text((x+3, yy+4), word, font=font, fill=(0,0,0))
            draw.text((x, yy), word, font=font, fill=color, stroke_width=1, stroke_fill=(0,0,0))
            x += widths[j] + (spaces[j] if j < len(spaces) else 0)

def render_video(title, hook, script, images, duration_limit):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        audio_path = td / "voice.mp3"
        # gTTS is the basic Italian voice in this starter build.
        asyncio.run(
    edge_tts.Communicate(
        text=edited,
        voice="it-IT-DiegoNeural",
        rate="+8%",
        pitch="+2Hz"
    ).save(audio_path)
)
        audio = AudioFileClip(str(audio_path))
        duration = audio.duration
        words = word_timings(script, duration)
        frame_paths = []
        frame_count = max(1, int(duration * FPS))
        hook_font = load_font(66)
        cap_font = load_font(49)
        small_font = load_font(24)
        title_font = load_font(34)

        prepared_images = []
        for uploaded_file in images or []:
            try:
                prepared_images.append(Image.open(BytesIO(uploaded_file.getvalue())).convert("RGB"))
            except Exception:
                pass

        for frame_no in range(frame_count):
            t = frame_no / FPS
            scene_idx = int(t // 4.5)
            if prepared_images:
                base = cover_crop(prepared_images[scene_idx % len(prepared_images)], t, scene_idx)
            else:
                base = make_gradient_bg(t, scene_idx)

            # Darken edges and add cinematic top/bottom overlays.
            overlay = Image.new("RGBA", (W, H), (0,0,0,0))
            od = ImageDraw.Draw(overlay)
            od.rectangle((0,0,W,170), fill=(0,0,0,115))
            od.rectangle((0,830,W,H), fill=(0,0,0,145))
            base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
            d = ImageDraw.Draw(base)

            # Header and category-style label.
            d.text((42, 42), "CALCIOZONE", font=title_font, fill=WHITE, stroke_width=1, stroke_fill=(0,0,0))
            d.rounded_rectangle((W-220, 43, W-42, 91), radius=18, fill=(229,43,69))
            d.text((W-205, 54), "FOOTBALL STORY", font=small_font, fill=WHITE)

            # Scene number and animated progress line.
            d.text((44, 120), f"STORIA {scene_idx+1:02d}", font=small_font, fill=(210,220,235))
            d.rectangle((42, 160, W-42, 168), fill=(255,255,255,90))
            d.rectangle((42, 160, 42+int((W-84)*(t/max(duration,0.1))), 168), fill=ACCENT)

            # First seconds: strong opening hook.
            if t < min(2.8, duration):
                hook_words = re.findall(r"\S+", hook or title)
                hook_text = " ".join(hook_words[:8])
                bbox = d.multiline_textbbox((0,0), textwrap.fill(hook_text, 17), font=hook_font, spacing=12, align="center")
                th = bbox[3]-bbox[1]
                d.rounded_rectangle((35, 420, W-35, 420+th+65), radius=28, fill=(229,43,69,225), outline=ACCENT, width=3)
                d.multiline_text((W//2, 452), textwrap.fill(hook_text, 17), font=hook_font, fill=WHITE, anchor="ma", align="center", spacing=12, stroke_width=2, stroke_fill=(0,0,0))

            # Find current word and show a short moving caption group.
            active = 0
            for word, start, end, idx in words:
                if start <= t < end:
                    active = idx
                    break
                if t >= end:
                    active = idx
            start_idx = max(0, active-2)
            end_idx = min(len(words), active+4)
            caption_words = words[start_idx:end_idx]
            # Large caption panel
            d.rounded_rectangle((28, 900, W-28, 1115), radius=30, fill=(3,8,18,225), outline=(255,205,45,220), width=3)
            draw_wrapped_words(d, caption_words, active, cap_font, 974, max_width=620)

            d.text((42, 1160), "SEGUI CALCIOZONE  •  COMMENTA LA TUA", font=small_font, fill=WHITE)
            # Subtle scene flash marker on scene changes
            if t % 4.5 < 0.10 and t > 0:
                d.rectangle((0,0,W,H), fill=(255,255,255,28))

            frame_path = td / f"frame_{frame_no:05d}.jpg"
            base.save(frame_path, quality=86, optimize=True)
            frame_paths.append(str(frame_path))

        video = ImageSequenceClip(frame_paths, fps=FPS).with_audio(audio)
        output_path = td / "calciozone_video.mp4"
        video.write_videofile(
            str(output_path), fps=FPS, codec="libx264", audio_codec="aac",
            preset="ultrafast", threads=1, logger=None,
            ffmpeg_params=["-pix_fmt", "yuv420p"]
        )
        data = output_path.read_bytes()
        video.close()
        audio.close()
        return data

if "scripts" not in st.session_state:
    st.session_state.scripts = []

if st.button("✨ GENERA COPIONI", type="primary", use_container_width=True):
    with st.spinner("Preparo i copioni..."):
        try:
            st.session_state.scripts = make_scripts(topic, category, count, api_key, duration_target)
        except Exception as e:
            st.error(f"Errore nella generazione dei copioni: {e}")

if st.session_state.scripts:
    st.subheader("Copioni pronti da controllare")
    for i, item in enumerate(st.session_state.scripts, 1):
        with st.expander(f"{i}. {item.get('title','Video CalcioZone')}", expanded=True):
            hook = st.text_input("Apertura d'impatto", value=item.get("hook", ""), key=f"hook_{i}")
            edited = st.text_area("Copione parlato", value=item.get("script", ""), key=f"script_{i}", height=180)
            st.write("Descrizione:", item.get("description", ""))
            st.write("Hashtag:", item.get("hashtags", ""))
            if st.button(f"🎬 CREA VIDEO VIRAL MP4 #{i}", key=f"video_{i}", use_container_width=True):
                if not edited.strip():
                    st.warning("Inserisci prima il testo del copione.")
                else:
                    with st.spinner("Creo voce, scene dinamiche e sottotitoli... Il rendering può richiedere qualche minuto."):
                        try:
                            data = render_video(item.get("title","CalcioZone"), hook, edited, uploaded, duration_target)
                            st.success("Video creato! Guardalo e controllalo prima di pubblicarlo.")
                            st.video(data)
                            st.download_button("⬇️ SCARICA VIDEO MP4", data=data,
                                               file_name=f"CalcioZone_{i}.mp4", mime="video/mp4",
                                               key=f"download_{i}")
                        except Exception as e:
                            st.error(f"Non sono riuscito a creare il video: {e}")

st.divider()
st.info("Questa versione aggiunge sottotitoli dinamici, zoom sulle immagini e scene sportive originali. La voce usa gTTS, quindi è una voce italiana base: la voce AI più espressiva e la musica sincronizzata saranno un miglioramento successivo. Per immagini di calciatori e partite usa solo materiale con diritti.")
