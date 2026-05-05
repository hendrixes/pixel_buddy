FACES = {
    "neutral": "(•‿•)",
    "happy": "(^‿^)",
    "curious": "(◕‿◕)",
    "tired": "(⇀‿↼)",
    "hungry": "(•︿•)",
    "confused": "(#__#)",
    "cool": "(⌐■_■)",
}


def get_face(mood):
    return FACES.get(mood, FACES["neutral"])
