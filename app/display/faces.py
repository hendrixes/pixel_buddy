FACES = {
    "neutral": "(•‿•)",
    "happy": "(^‿^)",
    "curious": "(◕‿◕)",
    "tired": "(⇀‿↼)",
    "hungry": "(•︿•)",
    "confused": "(#__#)",
    "cool": "(⌐■_■)",
    "alert": "(⊙_⊙)",
    "angry": "(ಠ_ಠ)",
}


def get_face(mood):
    return FACES.get(mood, FACES["neutral"])
