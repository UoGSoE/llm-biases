import random

PAIRS = [
    ("Darth Vader", "Dave Prowse"),  # the character vs the actor who played him
    ("Sherlock Holmes", "Hercule Poirot"),
    ("Gandalf", "Dumbledore"),
    ("Batman", "Superman"),
    ("Harry Potter", "Hermione Granger"),
    ("Captain Kirk", "Captain Picard"),
    ("Frodo Baggins", "Samwise Gamgee"),
    ("The Doctor", "The Master"),
]


def pairs(n: int):
    return random.sample(PAIRS, min(n, len(PAIRS)))
