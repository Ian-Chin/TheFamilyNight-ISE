"""In-place white background removal and snatcher sheet slicer."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

TERRY_DIR = ASSETS / "sprites" / "terry market game"
SNATCHERS_DIR = ASSETS / "market snatchers"
INGREDIENTS_DIR = ASSETS / "market ingredients"


def has_transparency(img: Image.Image) -> bool:
    """Returns True if image already has transparent/semi-transparent pixels."""
    if img.mode not in ("RGBA", "LA") and "transparency" not in img.info:
        return False
    alpha = img.convert("RGBA").split()[-1]
    # Check if any pixel has alpha < 250
    return min(alpha.getdata()) < 250


def strip_white(img: Image.Image) -> Image.Image:
    """Keys out near-white backgrounds with soft edge ramping."""
    img = img.convert("RGBA")
    data = img.getdata()
    new_data = []
    for r, g, b, a in data:
        if r > 240 and g > 240 and b > 240:
            new_data.append((255, 255, 255, 0))
        elif r > 214 and g > 214 and b > 214:
            alpha_val = int(255 * (1.0 - (min(r, g, b) - 214) / 26))
            new_data.append((r, g, b, alpha_val))
        else:
            new_data.append((r, g, b, a))
    img.putdata(new_data)
    return img


def process_folder(folder_path: Path):
    if not folder_path.exists():
        return
    for file in folder_path.glob("*.*"):
        if file.suffix.lower() in (".jpg", ".jpeg", ".png"):
            # Skip sliced output files if already generated
            if "fall_" in file.name or "grab_" in file.name:
                continue
            try:
                with Image.open(file) as im:
                    if has_transparency(im):
                        continue
                    clean_im = strip_white(im)
                    # Save as PNG directly
                    target_path = file.with_suffix(".png")
                    clean_im.save(target_path, "PNG")
                    if file.suffix.lower() != ".png":
                        file.unlink()  # Remove older jpg
                    print(f"[CLEANED] {target_path.name}")
            except Exception as err:
                print(f"[ERROR] Could not process {file}: {err}")


# At the bottom of prep_sprites.py
def run_prep():
    process_folder(TERRY_DIR) 
    process_folder(INGREDIENTS_DIR)

    if SNATCHERS_DIR.exists():
        for sub in SNATCHERS_DIR.iterdir():
            if sub.is_dir():
                process_folder(sub)
                for sheet_file in list(sub.glob("*.png")) + list(sub.glob("*.jpg")):
                    if "movement" in sheet_file.name.lower() or "frame" in sheet_file.name.lower():
                        if (sub / "fall_0.png").exists():
                            continue
                        with Image.open(sheet_file) as sheet:
                            w, h = sheet.size
                            frame_w = w // 6
                            frame_h = h // 2
                            
                            pad_x = 8  #size of each frame

                            # Row 0: fall
                            for i in range(6):
                                left = (i * frame_w) + pad_x
                                right = ((i + 1) * frame_w) - pad_x
                                box = (left, 0, right, frame_h)
                                sheet.crop(box).save(sub / f"fall_{i}.png")

                            # Row 1: grab
                            for i in range(6):
                                left = (i * frame_w) + pad_x
                                right = ((i + 1) * frame_w) - pad_x
                                box = (left, frame_h, right, 2 * frame_h)
                                sheet.crop(box).save(sub / f"grab_{i}.png")
                        print(f"[SLICED] {sub.name} animation frames")
    print("All asset folders processed and updated.")

if __name__ == "__main__":
    run_prep()