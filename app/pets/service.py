from datetime import datetime, timezone


TICK_RATE_SECONDS = 60


def utc_now():
    return datetime.now(timezone.utc)


def as_utc(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def clamp(value, minimo=0, maximo=100):
    return max(minimo, min(value, maximo))


def tick_pet(pet):
    now = utc_now()
    last_tick_at = as_utc(pet.last_tick_at)
    elapsed_seconds = int((now - last_tick_at).total_seconds())

    if elapsed_seconds < TICK_RATE_SECONDS:
        return False

    ticks = elapsed_seconds // TICK_RATE_SECONDS

    pet.hunger = clamp(pet.hunger + ticks)
    pet.energy = clamp(pet.energy - ticks)
    pet.happiness = clamp(pet.happiness - ticks)
    pet.curiosity = clamp(pet.curiosity - ticks)

    pet.last_tick_at = now
    update_mood(pet)
    return True


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
