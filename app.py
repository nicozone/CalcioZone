import os, re, tempfile, textwrap
from pathlib import Path
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips

st.set_page_config(page_title="CalcioZone · Football AI Studio", page_icon="⚽", layout="wide")
st.title("⚽ Football AI Studio")
st.caption("Generatore di video calcistici verticali · crea, controlla, esporta")

with st.sidebar:
    st.header("Impostazioni")
    api_key = st.text_input("Chiave OpenAI (facoltativa)", type="password",
        help="Serve per generare copioni originali con AI. Non inserirla in file condivisi.")
    topic = st.text_input("Argomento (facoltativo)", placeholder="Es. 5 curiosità su Messi")
    category = st.selectbox("Categoria", ["Mix calcistico", "Notizie", "Calciomercato",
        "Curiosità", "Storie", "Classifiche e confronti", "Analisi tattica"])
    duration = st.select_slider("Durata indicativa", options=[30, 45, 60], value=45)
    count = st.selectbox("Copioni da preparare", [1, 3, 5], index=2)
    uploaded = st.file_uploader("Immagini tue o con licenza (facoltativo)", type=["jpg","jpeg","png"], accept_multiple_files=True)
    st.caption("Senza immagini caricate il video usa sfondi grafici originali.")

def make_scripts(topic, category, count, api_key, duration):
    if api_key:
        from openai import OpenAI
        client=OpenAI(api_key=api_key)
        prompt=f"""Scrivi {count} copioni diversi in italiano per video calcistici verticali di circa {duration} secondi.
Categoria: {category}. Argomento preferito: {topic or 'scegli temi calcistici evergreen e non inventare notizie recenti'}.
Per ciascuno restituisci: TITOLO: ..., TESTO: ... (circa 85-120 parole), DESCRIZIONE: ..., HASHTAG: ...
Tono dinamico ma accurato. Non inventare statistiche, citazioni, trasferimenti o fatti recenti.
Se il tema riguarda notizie attuali, segnala nel testo che i fatti vanno verificati prima della pubblicazione."""
        r=client.responses.create(model="gpt-4.1-mini", input=prompt)
        raw=r.output_text
        chunks=re.split(r'(?=TITOLO:)', raw)
        return [c.strip() for c in chunks if c.strip()][:count]
    seeds = [topic] if topic else [
        "Tre record incredibili nella storia del calcio",
        "Come è cambiato il ruolo del centravanti",
        "Cinque curiosità sulla Champions League",
        "Le rimonte più memorabili del calcio",
        "Cosa rende speciale un grande numero 10"]
    return [f"TITOLO: {s}\nTESTO: Oggi parliamo di {s.lower()}. Nel calcio, i dettagli fanno spesso la differenza: talento, preparazione, lavoro di squadra e capacità di reagire nei momenti decisivi. Dietro ogni grande storia c'è un percorso fatto di allenamento, scelte e sacrifici. Qual è l'aspetto che ti sorprende di più? Scrivilo nei commenti e seguici per altre storie di calcio.\nDESCRIZIONE: Una pillola di calcio. Commenta la tua opinione.\nHASHTAG: #calcio #football #seriea #championsleague #shorts" for s in seeds[:count]]

def get_font(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/Library/Fonts/Arial.ttf", "C:/Windows/Fonts/arialbd.ttf"]:
        if os.path.exists(p): return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def render_frame(title, text, idx, total, bg=None):
    W,H=720,1280
    if bg:
        im=Image.open(bg).convert("RGB").resize((W,H))
        overlay=Image.new("RGBA",(W,H),(0,0,0,145)); im=Image.alpha_composite(im.convert("RGBA"),overlay)
    else:
        im=Image.new("RGB",(W,H),(12,22,30)).convert("RGBA")
        d=ImageDraw.Draw(im)
        for y in range(H):
            c=int(18+30*y/H); d.line((0,y,W,y),fill=(8,c,24,255))
        d.ellipse((650,-150,1300,500),fill=(20,95,60,100))
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((65,100,1015,230),radius=35,fill=(20,160,95,255))
    d.text((100,135),"CALCIOZONE",font=get_font(54),fill="white")
    d.text((80,330),f"FOOTBALL STORIES  •  {idx}/{total}",font=get_font(34),fill=(110,240,170))
    words=textwrap.wrap(re.sub(r'\s+',' ',text), width=27)
    # select a short readable excerpt for the visual card
    excerpt=" ".join(words[:7])[:170]
    lines=textwrap.wrap(excerpt,width=22)
    y=650
    for line in lines:
        d.text((80,y),line,font=get_font(64),fill="white",stroke_width=2,stroke_fill=(0,0,0))
        y+=90
    d.rounded_rectangle((70,1570,1010,1740),radius=28,fill=(0,0,0,175))
    d.text((110,1625),"SEGUI CALCIOZONE PER ALTRE STORIE ⚽",font=get_font(38),fill="white")
    return im.convert("RGB")

def extract(part, label):
    m=re.search(label+r":\s*(.*?)(?=\n[A-ZÀ-Ü ]{3,}:|$)",part,re.S|re.I)
    return m.group(1).strip() if m else part.strip()

if "scripts" not in st.session_state: st.session_state.scripts=[]
if st.button("✨ GENERA COPIONI", type="primary", use_container_width=True):
    with st.spinner("Creo i copioni..."):
        try:
            st.session_state.scripts=make_scripts(topic,category,count,api_key,duration)
        except Exception as e: st.error(f"Errore nella generazione: {e}")
if st.session_state.scripts:
    st.subheader("Copioni pronti da controllare")
    for i,part in enumerate(st.session_state.scripts,1):
        title=extract(part,"TITOLO")
        script=extract(part,"TESTO")
        with st.expander(f"{i}. {title[:90]}", expanded=True):
            edited=st.text_area("Copione (puoi modificarlo)",script,key=f"script_{i}",height=150)
            st.text("Descrizione: "+extract(part,"DESCRIZIONE"))
            st.text("Hashtag: "+extract(part,"HASHTAG"))
            if st.button(f"🎬 CREA VIDEO MP4 #{i}",key=f"video_{i}",use_container_width=True):
                with st.spinner("Creo voce italiana e video..."):
                    try:
                        with tempfile.TemporaryDirectory() as td:
                            audio_path=os.path.join(td,"voice.mp3")
                            gTTS(text=edited,lang="it",slow=False).save(audio_path)
                            audio=AudioFileClip(audio_path)
                            bgpath=None
                            if uploaded:
                                f=uploaded[(i-1)%len(uploaded)]
                                bgpath=os.path.join(td,f.name); open(bgpath,"wb").write(f.getvalue())
                            frame=render_frame(title,edited,i,len(st.session_state.scripts),bgpath)
                            frame_path=os.path.join(td,"frame.jpg"); frame.save(frame_path,quality=92)
                            clip=ImageClip(frame_path).with_duration(audio.duration).with_audio(audio)
                            out=f"football_video_{i}.
                            clip.write_videofile(out, fps=15, codec="libx264", audio_codec="aac", preset="ultrafast", threads=1, logger=None)
                            clip.close(); audio.close()
                            data=Path(out).read_bytes()
                        st.success("Video creato. Controllalo prima di pubblicarlo.")
                        st.video(data)
                        st.download_button("⬇️ Scarica MP4",data=data,file_name=out,mime="video/mp4")
                    except Exception as e: st.error(f"Non sono riuscito a creare il video: {e}")

st.divider()
st.info("Identità grafica: CalcioZone · mix virale, giornalistico e documentaristico. Nota: questa prima versione genera un video grafico con voce italiana. Per notizie aggiornate, verifica sempre le fonti; usa solo immagini, filmati e musiche di cui possiedi i diritti. Non caricare highlights televisivi senza autorizzazione.")
