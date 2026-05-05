from flask import Blueprint, jsonify
from flask_login import current_user, login_required

from app.core import db
from app.pets.service import (
    feed_pet,
    observe_network,
    play_pet,
    sleep_pet,
    tick_pet,
)


pets = Blueprint("pets", import_name=__name__, url_prefix="/pets")


def run_pet_action(action):
    pet = current_user.pet
    if not pet:
        return jsonify({"error": "pet_not_found"}), 404

    tick_pet(pet)
    action(pet)
    db.session.commit()
    return jsonify(pet.to_dict())


@pets.route("/action/feed", methods=["POST"])
@login_required
def feed():
    return run_pet_action(feed_pet)


@pets.route("/action/play", methods=["POST"])
@login_required
def play():
    return run_pet_action(play_pet)


@pets.route("/action/sleep", methods=["POST"])
@login_required
def sleep():
    return run_pet_action(sleep_pet)


@pets.route("/action/observe", methods=["POST"])
@login_required
def observe():
    return run_pet_action(observe_network)
