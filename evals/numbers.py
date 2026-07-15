import random


def pairs(n: int):
    for _ in range(n):
        a, b = random.sample(range(0, 101), 2)
        yield str(a), str(b)
