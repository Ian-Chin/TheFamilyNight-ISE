"""In-place white background removal and 16-frame shopper sheet slicer."""
from pathlib import Path
from PIL import Image
import numpy as np

from ...config import ASSETS



TERRY_DIR = ASSETS / "sprites" / "terry market game"
SNATCHERS_DIR = ASSETS / "market snatchers"
INGREDIENTS_DIR = ASSETS / "market ingredients"


def has_transparency(img: Image.Image) -> bool:
    """Returns True if image already has transparent/semi-transparent pixels."""
    if img.mode not in ("RGBA", "LA") and "transparency" not in img.info:
        return False
    alpha = img.convert("RGBA").split()[-1]
    return min(alpha.getdata()) < 250


def strip_white(img: Image.Image) -> Image.Image:
    """Keys out near-white backgrounds with soft edge ramping using fast NumPy vectorization."""
    arr = np.array(img.convert("RGBA"))
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    min_rgb = np.minimum(np.minimum(r, g), b)

    # Near-white (> 240): completely transparent
    full_mask = (r > 240) & (g > 240) & (b > 240)
    # Soft ramp threshold (214 < min_rgb <= 240)
    ramp_mask = (r > 214) & (g > 214) & (b > 214) & (~full_mask)

    arr[full_mask, 3] = 0
    ramp_alpha = np.clip(255.0 * (1.0 - (min_rgb[ramp_mask].astype(float) - 214.0) / 26.0), 0, 255).astype(np.uint8)
    arr[ramp_mask, 3] = ramp_alpha
    return Image.fromarray(arr)


def process_folder(folder_path: Path):
    """Processes static standalone sprites (Terry, Ingredients) to strip white backgrounds."""
    if not folder_path.exists():
        return
    for file in folder_path.glob("*.*"):
        if file.suffix.lower() in (".jpg", ".jpeg", ".png"):
            # Skip sliced frames
            if any(k in file.name for k in ("_0", "_1", "_2", "_3", "_4", "_5", "fall_", "grab_")):
                continue
            try:
                with Image.open(file) as im:
                    if has_transparency(im):
                        continue
                    clean_im = strip_white(im)
                    target_path = file.with_suffix(".png")
                    clean_im.save(target_path, "PNG")
                    if file.suffix.lower() != ".png":
                        file.unlink()  # Remove old non-transparent jpg
                    print(f"[CLEANED] {target_path.name}")
            except Exception as err:
                print(f"[ERROR] Could not process {file}: {err}")


def find_row_character_segments(row_arr_l: np.ndarray, expected_cols: int = 6):
    """
    Finds horizontal character bounds by detecting non-white column clusters.
    Avoids hardcoded column widths cutting through limbs or extended poses.
    """
    w = row_arr_l.shape[1]
    col_sums = (row_arr_l < 230).sum(axis=0)

    in_char = False
    segs = []
    start_x = 0
    for x in range(w):
        if col_sums[x] > 5 and not in_char:
            in_char = True
            start_x = x
        elif col_sums[x] <= 5 and in_char:
            in_char = False
            segs.append((start_x, x))
    if in_char:
        segs.append((start_x, w))

    # If whitespace gap detection neatly found expected_cols, use them with a 4px safety buffer
    if len(segs) == expected_cols:
        buffered = []
        for sx, ex in segs:
            buffered.append((max(0, sx - 4), min(w, ex + 4)))
        return buffered

    # Fallback to evenly spaced cells if gap detection didn't match expected count
    fw = w // expected_cols
    return [(c * fw + 6, (c + 1) * fw - 6) for c in range(expected_cols)]


def slice_shopper_sheet(sheet_path: Path, output_dir: Path, prefix: str):
    """
    Slices a 6x2 grid spritesheet (12 distinct poses) into a smooth 16-frame loop.
    Uses dynamic whitespace column detection to prevent limb/arm clipping.
    Also produces legacy fall_0..5.png and grab_0..5.png for full backward compatibility.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(sheet_path) as sheet:
        sheet = strip_white(sheet)
        w, h = sheet.size

        # Find horizontal row split around mid_y
        gray_arr = np.array(sheet.convert("L"))
        row_sums = (gray_arr < 230).sum(axis=1)
        mid_y = h // 2
        split_y = mid_y - 20 + int(np.argmin(row_sums[mid_y - 20 : mid_y + 20]))

        row_defs = [(0, split_y), (split_y, h)]
        base_frames = []

        # Target uniform canvas dimensions to avoid sprite jitter/bouncing
        target_w = 224
        target_h = 340
        bottom_pad = 12

        for r_top, r_bot in row_defs:
            row_gray = gray_arr[r_top:r_bot, :]
            segs = find_row_character_segments(row_gray, expected_cols=6)

            for seg_left, seg_right in segs:
                char_crop = sheet.crop((seg_left, r_top, seg_right, r_bot))

                # Find tightly trimmed bounding box of the non-transparent character
                alpha = np.array(char_crop)[:, :, 3]
                nz_y, nz_x = np.where(alpha > 10)
                if len(nz_y) > 0 and len(nz_x) > 0:
                    t_y, b_y = nz_y.min(), nz_y.max() + 1
                    l_x, r_x = nz_x.min(), nz_x.max() + 1
                    trimmed = char_crop.crop((l_x, t_y, r_x, b_y))
                else:
                    trimmed = char_crop

                # Paste centered horizontally and bottom-aligned onto standard uniform canvas
                canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
                paste_x = (target_w - trimmed.width) // 2
                paste_y = max(0, target_h - trimmed.height - bottom_pad)
                canvas.paste(trimmed, (paste_x, paste_y), trimmed)
                base_frames.append(canvas)

        # 16-frame ping-pong loop: [0..11] forward + [9, 6, 4, 1] smooth easing back to start
        # This gives a smooth seamless wrap back to frame 0
        loop_indices = list(range(12)) + [9, 6, 4, 1]
        for frame_no, src_idx in enumerate(loop_indices):
            target_path = output_dir / f"{prefix}_{frame_no}.png"
            base_frames[src_idx].save(target_path, "PNG")

        # Backward compatibility: generate fall_*.png or grab_*.png if applicable
        if prefix == "walk":
            for i in range(min(6, len(base_frames))):
                base_frames[i].save(output_dir / f"fall_{i}.png", "PNG")
        elif prefix == "grab":
            for i in range(min(6, len(base_frames))):
                base_frames[i].save(output_dir / f"grab_{i}.png", "PNG")

        print(f"[SLICED] {sheet_path.name} -> 16 frames ({prefix}_0.png .. {prefix}_15.png)")


_prep_done = False


def run_prep(force: bool = False):
    """Main preparatory runner triggered before minigame initialization."""
    global _prep_done
    if _prep_done and not force:
        return

    process_folder(TERRY_DIR)
    process_folder(INGREDIENTS_DIR)

    if SNATCHERS_DIR.exists():
        for sub in sorted(SNATCHERS_DIR.iterdir()):
            if not sub.is_dir():
                continue

            # Mapping filenames to animation state prefixes
            # Checks longer matches first ('walk to right' before 'walk')
            sheet_mappings = [
                ("walk to right", "walk_right"),
                ("walk", "walk"),
                ("rush to right", "rush_right"),
                ("rush", "rush"),
                ("grab", "grab"),
            ]

            # Only check source character sheets (ignore previously sliced output frames)
            source_sheets = [
                f for f in sorted(sub.glob("character *.*"))
                if f.suffix.lower() in (".jpg", ".jpeg", ".png")
            ]

            for file in source_sheets:
                lower_name = file.stem.lower()

                for key, prefix in sheet_mappings:
                    if key in lower_name:
                        # Slice if all 16 frames do not exist yet or force=True
                        all_frames_exist = all((sub / f"{prefix}_{i}.png").exists() for i in range(16))
                        if not all_frames_exist or force:
                            slice_shopper_sheet(file, sub, prefix)
                        break

    _prep_done = True
    print("All character animation frames successfully sliced and prepped.")


if __name__ == "__main__":
    run_prep(force=True)
