from PIL import Image, ImageFont

from app.display.renderer import bottom_stats, render_pet_screen
from tests.conftest import create_user


def test_bottom_stats_do_not_repeat_mood(app):
    user = create_user()

    stats = bottom_stats(user.pet)

    assert stats == [
        ("ENG", user.pet.energy),
        ("XP", user.pet.network_xp),
        ("CUR", user.pet.curiosity),
    ]


def test_dark_renderer_inverts_screen_colors(app, monkeypatch):
    user = create_user()
    monkeypatch.setattr(
        "app.display.renderer.load_font",
        lambda _size, bold=False: ImageFont.load_default(),
    )

    image = Image.open(render_pet_screen(user.pet, theme="dark"))

    assert image.getpixel((10, 40)) == 0
    assert image.getpixel((0, 0)) == 255
