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

    pet.energy = clamp(pet.energy - ticks)
    pet.curiosity = clamp(pet.curiosity - ticks)

    pet.last_tick_at = now
    update_mood(pet)
    return True


def update_mood(pet):
    if pet.energy <= 20:
        pet.mood = "tired"
    elif pet.curiosity >= 75:
        pet.mood = "curious"
    else:
        pet.mood = "neutral"
