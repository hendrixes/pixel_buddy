from flask import Blueprint


pets = Blueprint("pets", import_name=__name__, url_prefix="/pets")


@pets.route("/1")
def show_pet():
    return "pet 1"
