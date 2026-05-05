FACES = {
    "neutral": "(•‿•)",
    "happy": "(^‿^)",
    "curious": "(◕‿◕)",
    "tired": "(⇀‿↼)",
    "confused": "(#__#)",
    "cool": "(⌐■_■)",
}


def get_face(mood):
    return FACES.get(mood, FACES["neutral"])
