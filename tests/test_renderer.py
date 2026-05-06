from app.display.renderer import bottom_stats
from tests.conftest import create_user


def test_bottom_stats_do_not_repeat_mood(app):
    user = create_user()

    stats = bottom_stats(user.pet)

    assert stats == [
        ("ENG", user.pet.energy),
        ("XP", user.pet.network_xp),
        ("CUR", user.pet.curiosity),
    ]
