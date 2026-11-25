"""Generate the demo wedding card (A5 PDF + PNG) and three small invitation PDFs.

Usage: python demo/make_real_card.py
Outputs (in demo/): Priya_Arjun_Wedding_Card.pdf/.png, invitation_card_1.pdf .. invitation_card_3.pdf
All files are plain images of text: harmless.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
DPI = 150
A5 = (int(148 / 25.4 * DPI), int(210 / 25.4 * DPI))  # 874 x 1240 px
PAPER, MAROON, GOLD, INK = "#FBF6EC", "#6B1F2A", "#B8893B", "#2A1E1A"
FUNCTIONS = [
    ("Mehendi", "Thursday, 4 December 2026", "4:00 PM", "Agarwal Bhawan, C-Scheme, Jaipur"),
    ("Sangeet", "Friday, 5 December 2026", "7:00 PM", "Shagun Gardens, Tonk Road, Jaipur"),
    ("Phere", "Saturday, 6 December 2026", "11:00 AM", "Shagun Gardens, Tonk Road, Jaipur"),
    ("Reception", "Sunday, 7 December 2026", "8:00 PM", "Hotel Rajputana, MI Road, Jaipur"),
]


def font(size: int, bold: bool = False, serif: bool = True):
    names = (["georgiab.ttf", "timesbd.ttf", "DejaVuSerif-Bold.ttf"] if bold else
             ["georgia.ttf", "times.ttf", "DejaVuSerif.ttf"]) if serif else \
            (["arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else ["arial.ttf", "DejaVuSans.ttf"])
    for name in names:
        for folder in ("C:/Windows/Fonts", "/usr/share/fonts/truetype/dejavu", "/Library/Fonts", ""):
            try:
                return ImageFont.truetype(str(Path(folder) / name) if folder else name, size)
            except OSError:
                continue
    return ImageFont.load_default(size=size)


def centered(draw, y, text, fnt, fill):
    width = draw.textlength(text, font=fnt)
    draw.text(((A5[0] - width) / 2, y), text, font=fnt, fill=fill)
    return y + fnt.size + 10


def wedding_card() -> Image.Image:
    img = Image.new("RGB", A5, PAPER)
    d = ImageDraw.Draw(img)
    d.rectangle([24, 24, A5[0] - 24, A5[1] - 24], outline=GOLD, width=4)
    d.rectangle([38, 38, A5[0] - 38, A5[1] - 38], outline=MAROON, width=2)
    y = centered(d, 80, "|| Shri Ganeshaya Namah ||", font(26, serif=False), GOLD) + 10
    y = centered(d, y, "The Agarwal family invites you", font(34), INK) + 10
    y = centered(d, y, "Priya weds Arjun", font(66, bold=True), MAROON) + 20
    d.line([(160, y), (A5[0] - 160, y)], fill=GOLD, width=2)
    y += 30
    for name, date, time, venue in FUNCTIONS:
        y = centered(d, y, name, font(40, bold=True), MAROON)
        y = centered(d, y, f"{date}, {time}", font(30), INK)
        y = centered(d, y, venue, font(28), INK) + 22
    centered(d, A5[1] - 110, "With blessings, the Agarwal family", font(26), GOLD)
    return img


def small_invite(index: int) -> Image.Image:
    img = Image.new("RGB", A5, PAPER)
    d = ImageDraw.Draw(img)
    d.rectangle([24, 24, A5[0] - 24, A5[1] - 24], outline=GOLD, width=3)
    couples = ["Neha weds Rohan", "Kavya weds Aditya", "Isha weds Karan"]
    y = centered(d, 200, "You are invited", font(36), INK) + 20
    y = centered(d, y, couples[index - 1], font(56, bold=True), MAROON) + 30
    y = centered(d, y, f"Wedding, Saturday, {12 + index} December 2026, 7:00 PM", font(28), INK)
    centered(d, y + 10, "Rambagh Gardens, Jaipur", font(28), INK)
    return img


if __name__ == "__main__":
    card = wedding_card()
    card.save(HERE / "Priya_Arjun_Wedding_Card.pdf", "PDF", resolution=DPI)
    card.save(HERE / "Priya_Arjun_Wedding_Card.png", "PNG")
    for i in (1, 2, 3):
        small_invite(i).save(HERE / f"invitation_card_{i}.pdf", "PDF", resolution=DPI)
    print("Wrote Priya_Arjun_Wedding_Card.pdf/.png and invitation_card_1..3.pdf in", HERE)
