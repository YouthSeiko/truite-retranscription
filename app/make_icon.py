from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent


def draw_trout(size: int, with_background: bool) -> Image.Image:
    scale = 4
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))

    if with_background:
        grad = Image.new("RGBA", (s, s))
        top, bottom = (34, 184, 207), (8, 47, 73)
        rows = []
        for y in range(s):
            t = y / (s - 1)
            color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (255,)
            rows.extend([color] * s)
        grad.putdata(rows)
        mask = Image.new("L", (s, s), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, s - 1, s - 1], radius=int(s * 0.23), fill=255
        )
        img.paste(grad, (0, 0), mask)

    d = ImageDraw.Draw(img)
    body = (228, 246, 255, 255)
    fin = (110, 231, 218, 255)
    fin_soft = (150, 236, 228, 235)
    spot = (56, 201, 210, 190)
    dark = (10, 55, 85, 255)

    def P(points):
        return [(x * s, y * s) for x, y in points]

    d.polygon(P([(0.76, 0.50), (0.95, 0.28), (0.90, 0.50), (0.95, 0.72)]), fill=fin)
    d.polygon(
        P(
            [
                (0.14, 0.50),
                (0.20, 0.41),
                (0.30, 0.345),
                (0.42, 0.32),
                (0.55, 0.33),
                (0.66, 0.365),
                (0.76, 0.43),
                (0.78, 0.50),
                (0.76, 0.57),
                (0.66, 0.635),
                (0.55, 0.67),
                (0.42, 0.68),
                (0.30, 0.655),
                (0.20, 0.59),
            ]
        ),
        fill=body,
    )
    d.polygon(P([(0.40, 0.335), (0.50, 0.17), (0.62, 0.355)]), fill=fin)
    d.polygon(P([(0.42, 0.665), (0.50, 0.83), (0.60, 0.675)]), fill=fin)
    d.polygon(P([(0.34, 0.565), (0.40, 0.75), (0.52, 0.60)]), fill=fin_soft)

    for sx, sy in [
        (0.38, 0.40),
        (0.46, 0.375),
        (0.54, 0.395),
        (0.62, 0.425),
        (0.42, 0.475),
        (0.50, 0.445),
        (0.58, 0.485),
        (0.66, 0.50),
        (0.36, 0.465),
        (0.48, 0.535),
        (0.56, 0.55),
    ]:
        r = 0.016 * s
        d.ellipse([sx * s - r, sy * s - r, sx * s + r, sy * s + r], fill=spot)

    d.ellipse([0.24 * s, 0.415 * s, 0.315 * s, 0.48 * s], fill=(255, 255, 255, 255))
    d.ellipse([0.262 * s, 0.437 * s, 0.298 * s, 0.468 * s], fill=dark)
    d.arc(
        [0.112 * s, 0.452 * s, 0.20 * s, 0.548 * s],
        75,
        285,
        fill=dark,
        width=max(2, int(0.010 * s)),
    )
    return img


def main() -> None:
    master = draw_trout(256, with_background=True)
    master.resize((64, 64), Image.LANCZOS).save(HERE / "icon.png")
    master.save(HERE / "icon.ico", sizes=[(64, 64), (48, 48), (32, 32), (16, 16)])
    logo = draw_trout(256, with_background=False)
    logo.resize((96, 96), Image.LANCZOS).save(HERE / "logo.png")
    print("icon.ico, icon.png, logo.png generees")


if __name__ == "__main__":
    main()
