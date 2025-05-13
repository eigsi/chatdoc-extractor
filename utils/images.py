import fitz
import os
import uuid
import re

# ----------------  REGEX TO DETECT STEPS & THE END OF THE STEPS LIST ----------------
step_re = re.compile(r"^Step\s+(\d+):")
nextSection_re  = re.compile(r"^Section\s+\d+:")

# ---------------- EXTRACT IMAGE IGNORING HEADER & FOOTER ----------------
def _extract_images_from_page(page: fitz.Page, output_dir: str, header_margin_ratio: float) -> list[str]:
    """
    Extract all visible images except from footer and header sections
    Return a list of the paths of the PNGs
    """
    height = page.rect.height
    images = []

    for img_meta in page.get_images(full=True):
        xref, *_, img_name = img_meta[:8]
        bbox = page.get_image_bbox(img_name)
        y0, y1 = bbox[1], bbox[3]

        # ignore image if to close to the edges
        if y0 < height * header_margin_ratio or y1 > height * (1 - header_margin_ratio):
            continue

        pix = fitz.Pixmap(page.parent, xref)
        fname = f"{uuid.uuid4()}.png"
        out_path = os.path.join(output_dir, fname)
        pix.save(out_path)
        pix = None
        images.append(out_path)

    return images


# ---------------- EXTRACT STEPS IMAGES ----------------
def extract_step_images(pdf_path: str, output_dir: str = "images/", header_margin_ratio: float = 0.2) -> dict:
    """
    Return a dict :
      {
        "step_images": {
           "Step 1": [paths...],
           "Step 2": [...],
           ...
        }
      }
    """
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    result = {"step_images": {}}

    current_step = None
    # ---------------- 3) IRERATE PAGES ----------------
    for page_index in range(len(doc)):
        page  = doc.load_page(page_index)
        text  = page.get_text("text")
        lines = text.splitlines()

        # a) DETECT NEW STEP OR END OF THE RECIPE
        for line in lines:
            stripped = line.strip()
            m_step = step_re.match(stripped)
            if m_step:
                num = m_step.group(1)
                current_step = f"Step {num}"
                # init list if first time
                result["step_images"].setdefault(current_step, [])
                break

            if nextSection_re.match(stripped):
                # end of the recipe -> stop
                return result
            
        # b) IF WE'RE IN A STEP -> TAKE IMAGES
        if current_step:
            for img_path in _extract_images_from_page(page, output_dir, header_margin_ratio):
                result["step_images"][current_step].append(img_path)

    return result

# ---------------- EXTRACT MAIN IMAGE - PAGE 2 ----------------
def extract_main_image(
    pdf_path: str,
    output_dir: str = "images/",
    header_margin_ratio: float = 0.2
) -> str:
    """
    Extract the first image from page 2.
    Return the path or ""
    """
    doc = fitz.open(pdf_path)

    if len(doc) < 2:
        return ""

    page = doc.load_page(1)  # index 1 = page 2

    # FETCH ALL IMAGES EXCEPT HEADER & FOOTER 
    imgs = _extract_images_from_page(page, output_dir, header_margin_ratio)
    return imgs[0] if imgs else ""