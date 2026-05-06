from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from app.display import get_face

WIDTH = 320
HEIGHT = 180
BACKGROUND = 255
FOREGROUND = 0
BLACK = FOREGROUND
FONT_NAME = "DejaVuSansMono"


def load_font(size, bold=False):
    font_name = f"{FONT_NAME}-Bold" if bold else FONT_NAME
    return ImageFont.truetype(font_name, size)


def draw_centered_text(draw, y, text, font):
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    text_width = right - left
    text_height = bottom - top
    x = (WIDTH - text_width) // 2 - left
    text_y = y - text_height // 2 - top
    draw.text((x, text_y), text, font=font, fill=FOREGROUND)


def bottom_stats(pet):
    return [
        ("ENG", pet.energy),
        ("XP", pet.network_xp),
        ("CUR", pet.curiosity),
    ]


def render_pet_screen(pet):
    image = Image.new("L", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    small_font = load_font(12)
    medium_font = load_font(12)
    text_font = load_font(14, bold=True)
    face_font = load_font(36, bold=True)

    draw.rectangle((0, 0, WIDTH - 1, HEIGHT - 1), outline=FOREGROUND, width=2)
    draw.line((8, 30, WIDTH - 9, 30), fill=FOREGROUND, width=1)
    draw.line((8, 136, WIDTH - 9, 136), fill=FOREGROUND, width=1)

    draw.text((12, 8), f"{pet.name}>", font=text_font, fill=FOREGROUND)

    face = get_face(pet.mood)
    draw_centered_text(draw, 82, face, face_font)

    draw.text((12, 116), f"MOOD {pet.mood.upper()}",
              font=small_font, fill=FOREGROUND)
    for x, (label, value) in zip((12, 122, 232), bottom_stats(pet)):
        draw.text((x, 146), f"{label} {value}", font=medium_font, fill=BLACK)

    image = image.point(lambda value: 0 if value < 210 else 255)

    output = BytesIO()
    image.save(output, format="PNG")
    output.seek(0)

    return output
