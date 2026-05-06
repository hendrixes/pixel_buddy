from tests.conftest import create_user, login


def test_pet_json_no_longer_exposes_legacy_hunger(app):
    user = create_user()

    assert "hunger" not in user.pet.to_dict()


def test_legacy_pet_action_routes_are_removed(client, app):
    create_user()
    login(client)

    for path in (
        "/pets/action/feed",
        "/pets/action/play",
        "/pets/action/sleep",
        "/pets/action/observe",
    ):
        assert client.post(path).status_code == 404
