BG_DEEP = (7, 7, 10)
BG_WARM = (30, 22, 18)
BG_LAMP = (92, 62, 34)
BG_COOL = (18, 22, 28)

INK = (12, 11, 13)
BONE = (226, 214, 198)
PAPER = (208, 196, 178)
ASH = (120, 114, 108)
SMOKE = (58, 54, 54)

BLOOD = (118, 22, 26)
BLOOD_BRIGHT = (172, 40, 38)
WINE = (74, 16, 24)
GOLD = (166, 132, 74)
GOLD_PALE = (208, 176, 118)
CANDLE = (232, 168, 92)

SKIN_LIGHT = (232, 196, 168)
SKIN_BASE = (212, 170, 142)
SKIN_SHADOW = (156, 112, 90)
SKIN_DEEP = (104, 70, 58)
SKIN_COOL = (132, 104, 104)

LIP_DARK = (142, 82, 78)
LIP_BASE = (176, 108, 100)
LIP_LIGHT = (204, 136, 126)

IRIS_AMBER = (122, 82, 38)
IRIS_GREEN = (72, 96, 66)
IRIS_BLUE = (74, 96, 112)

HAIR_DARK = (32, 24, 21)
HAIR_BASE = (54, 40, 33)
HAIR_LIGHT = (92, 68, 50)

SUIT = (15, 15, 18)
SUIT_LIGHT = (38, 38, 44)
SHIRT = (198, 192, 180)
TIE = (46, 14, 20)

EYE_WHITE = (214, 200, 184)
EYE_SHADOW = (150, 134, 120)


def mix(c1, c2, t):
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    return (
        c1[0] + (c2[0] - c1[0]) * t,
        c1[1] + (c2[1] - c1[1]) * t,
        c1[2] + (c2[2] - c1[2]) * t,
    )


def shade(c, k):
    return (c[0] * k, c[1] * k, c[2] * k)


def warm(c, k):
    return (c[0] * (1.0 + 0.12 * k), c[1] * (1.0 + 0.03 * k), c[2] * (1.0 - 0.10 * k))


def cool(c, k):
    return (c[0] * (1.0 - 0.08 * k), c[1] * (1.0 + 0.01 * k), c[2] * (1.0 + 0.14 * k))
