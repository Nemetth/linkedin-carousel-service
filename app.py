from fastapi import FastAPI, Response
from pydantic import BaseModel
from PIL import Image, ImageDraw, ImageFont
import io, os, textwrap

app = FastAPI()

# ===== Config: paths =====
ASSETS_DIR = "assets"
BG_PATH = os.path.join(ASSETS_DIR, "bg.png")          # Fondo 1080x1350
FONT_BOLD = os.path.join(ASSETS_DIR, "Baskervville-Italic")
FONT_REG  = os.path.join(ASSETS_DIR, "Poppins-Regular.ttf")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")      # opcional

# ===== Config: layout =====
CANVAS_W, CANVAS_H = 1080, 1350
MARGIN = 96
COLOR_BG = (11, 9, 31)        # fallback si no hay bg.png
COLOR_TEXT = (255, 255, 255)

# Slide 7 fijo (agradecimiento)
ADD_THANKYOU = True
THANKYOU_BIG  = "Gracias por leer"
THANKYOU_SMALL= "Seguime para más ideas de UX y diseño"

class Payload(BaseModel):
    slide1_text_big: str
    slide2_number: str
    slide2_text_small: str
    slide3_text_big: str
    slide3_text_small: str
    slide4_text_big: str
    slide5_number: str
    slide5_text_small: str
    slide6_text_big: str
    slide6_text_small: str

def load_bg():
    if os.path.exists(BG_PATH):
        bg = Image.open(BG_PATH).convert("RGB")
        return bg.resize((CANVAS_W, CANVAS_H))
    # fallback color liso
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), COLOR_BG)
    return img

def safe_font(path, size, fallback="arial"):
    try:
        return ImageFont.truetype(path, size)
    except:
        return ImageFont.load_default()

def fit_text(draw, text, max_width_px, max_height_px, font_path, start_size, min_size=28, line_width_chars=None):
    """Baja tamaño de fuente hasta que el texto (envuelto) entra en el rectángulo dado."""
    size = start_size
    while size >= min_size:
        font = safe_font(font_path, size)
        # si no me dan ancho de línea, estimo por caracteres
        wrap_chars = line_width_chars or max(10, int(max_width_px / (size * 0.6)))
        wrapped = textwrap.fill(text, width=wrap_chars)
        bbox = draw.multiline_textbbox((0,0), wrapped, font=font, align="center", spacing=8)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        if w <= max_width_px and h <= max_height_px:
            return wrapped, font
        size -= 2
    # último recurso
    return text, safe_font(font_path, min_size)

def draw_centered(draw, text, font, y_center):
    bbox = draw.multiline_textbbox((0,0), text, font=font, align="center", spacing=8)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (CANVAS_W - w)//2
    y = int(y_center - h/2)
    draw.multiline_text((x,y), text, font=font, fill=COLOR_TEXT, align="center", spacing=8)

def render_slide(kind, big=None, small=None, number=None):
    img = load_bg()
    draw = ImageDraw.Draw(img)

    # áreas útiles
    box_w = CANVAS_W - 2*MARGIN
    box_h = CANVAS_H - 2*MARGIN

    if kind == "big":
        wrapped, font = fit_text(draw, big, box_w, box_h, FONT_BOLD, start_size=110)
        draw_centered(draw, wrapped, font, CANVAS_H/2)

    elif kind == "num_small":
        # número arriba
        num_wrapped, num_font = fit_text(draw, number, box_w, int(box_h*0.45), FONT_BOLD, start_size=220, line_width_chars=6)
        draw_centered(draw, num_wrapped, num_font, CANVAS_H*0.38)
        # texto chico abajo
        small_wrapped, small_font = fit_text(draw, small, box_w, int(box_h*0.4), FONT_REG, start_size=52)
        draw_centered(draw, small_wrapped, small_font, CANVAS_H*0.72)

    elif kind == "big_small":
        big_wrapped, big_font = fit_text(draw, big, box_w, int(box_h*0.5), FONT_BOLD, start_size=110)
        draw_centered(draw, big_wrapped, big_font, CANVAS_H*0.4)
        small_wrapped, small_font = fit_text(draw, small, box_w, int(box_h*0.35), FONT_REG, start_size=52)
        draw_centered(draw, small_wrapped, small_font, CANVAS_H*0.72)

    return img

def render_thankyou():
    img = load_bg()
    draw = ImageDraw.Draw(img)
    box_w = CANVAS_W - 2*MARGIN
    big_wrapped, big_font = fit_text(draw, THANKYOU_BIG, box_w, 400, FONT_BOLD, start_size=110)
    small_wrapped, small_font = fit_text(draw, THANKYOU_SMALL, box_w, 300, FONT_REG, start_size=52)
    draw_centered(draw, big_wrapped, big_font, CANVAS_H*0.42)
    draw_centered(draw, small_wrapped, small_font, CANVAS_H*0.70)
    return img

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/render")
def render(payload: Payload):
    slides = []
    slides.append(render_slide("big", big=payload.slide1_text_big))
    slides.append(render_slide("num_small", number=payload.slide2_number, small=payload.slide2_text_small))
    slides.append(render_slide("big_small", big=payload.slide3_text_big, small=payload.slide3_text_small))
    slides.append(render_slide("big", big=payload.slide4_text_big))
    slides.append(render_slide("num_small", number=payload.slide5_number, small=payload.slide5_text_small))
    slides.append(render_slide("big_small", big=payload.slide6_text_big, small=payload.slide6_text_small))

    if ADD_THANKYOU:
        slides.append(render_thankyou())

    buf = io.BytesIO()
    slides[0].save(buf, format="PDF", save_all=True, append_images=slides[1:])
    pdf_bytes = buf.getvalue()
    return Response(content=pdf_bytes, media_type="application/pdf")
