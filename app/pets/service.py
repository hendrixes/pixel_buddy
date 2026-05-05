def clamp(value, minimo=0, maximo=100):
    return max(minimo, min(value, maximo))


def update_mood(pet):
    if pet.energy <= 20:
        pet.mood = "tired"
    elif pet.hunger >= 80:
        pet.mood = "hungry"
    elif pet.happiness >= 75:
        pet.mood = "happy"
    elif pet.curiosity >= 75:
        pet.mood = "curious"
    else:
        pet.mood = "neutral"


def feed_pet(pet):
    pet.hunger = clamp(pet.hunger - 5)
    pet.happiness = clamp(pet.happiness + 3)

    update_mood(pet)


def play_pet(pet):
    pet.happiness = clamp(pet.happiness + 10)
    pet.energy = clamp(pet.energy - 8)
    pet.hunger = clamp(pet.hunger + 5)

    update_mood(pet)


def sleep_pet(pet):
    pet.happiness = clamp(pet.happiness + 5)
    pet.energy = clamp(pet.energy + 12)
    pet.hunger = clamp(pet.hunger + 10)

    update_mood(pet)


def observe_network(pet):
    pet.curiosity = clamp(pet.curiosity + 10)
    pet.energy = clamp(pet.energy - 5)
    pet.hunger = clamp(pet.hunger + 3)
    pet.network_xp += 1

    update_mood(pet)
