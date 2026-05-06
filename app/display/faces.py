FACES = {
    "neutral": "(•‿•)",
    "curious": "(◕‿◕)",
    "tired": "(⇀‿↼)",
    "alert": "(⊙_⊙)",
    "angry": "(ಠ_ಠ)",
}


def get_face(mood):
    return FACES.get(mood, FACES["neutral"])
