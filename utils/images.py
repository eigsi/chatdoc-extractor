import fitz
import os
import uuid
import re

# ---------------- EXTRACT IMAGE IGNORING HEADER & FOOTER ----------------
def _extract_images_from_page(page: fitz.Page, output_dir: str, header_margin_ratio: float, y_start: float = None, y_end: float = None) -> list[str]:
    """
    Extract images from a specific vertical range of the page
    y_start and y_end are optional vertical coordinates to limit the image extraction area
    """
    height = page.rect.height
    images = []

    for img_meta in page.get_images(full=True):
        xref, *_, img_name = img_meta[:8]
        bbox = page.get_image_bbox(img_name)
        y0, y1 = bbox[1], bbox[3]

        # ignore image if too close to the edges
        if y0 < height * header_margin_ratio or y1 > height * (1 - header_margin_ratio):
            continue

        # if y_start and y_end are provided, only take images in that range
        if y_start is not None and y_end is not None:
            if y0 < y_start or y1 > y_end:
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
           "Step 0": [paths...],
           "Step 1": [...],
           ...
        }
      }
    """
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    result = {"step_images": {}}
    
    # ----------------  REGEX TO DETECT STEPS & THE END OF THE STEPS LIST ----------------
    step_re = re.compile(r"^Step\s+(\d+):", re.MULTILINE)
    nextSection_re = re.compile(r"^Section\s+\d+:", re.MULTILINE)

    # First pass: identify all steps and their vertical positions
    steps_content = {}  # {step_num: {"start_page": X, "start_y": Y, "end_page": Z, "end_y": W}}
    current_step = None
    current_step_start_y = None
    
    for page_index in range(len(doc)):
        page = doc.load_page(page_index)
        text = page.get_text("text")
        lines = text.splitlines()

        # a) DETECT NEW STEP OR END OF THE RECIPE
        for line in lines:
            stripped = line.strip()
            m_step = step_re.match(stripped)
            if m_step:
                num = int(m_step.group(1))
                # Get the vertical position of this step
                text_instances = page.search_for(stripped)
                if text_instances:
                    y_pos = text_instances[0].y0  # y0 is the top coordinate
                    
                    # If we had a previous step, set its end position
                    if current_step:
                        steps_content[current_step]["end_page"] = page_index
                        steps_content[current_step]["end_y"] = y_pos
                    
                    current_step = f"Step {num}"
                    print(f"🔄 Nouveau step détecté: {current_step} (ligne: {repr(line)})")
                    steps_content[current_step] = {
                        "start_page": page_index,
                        "start_y": y_pos
                    }

            if nextSection_re.match(stripped):
                print(f"⏹️  Fin de la recette détectée: '{stripped}'")
                if current_step:
                    steps_content[current_step]["end_page"] = page_index
                    # Get the vertical position of the section header
                    text_instances = page.search_for(stripped)
                    if text_instances:
                        steps_content[current_step]["end_y"] = text_instances[0].y0
                break

    # Set end position for the last step if not set
    if current_step and "end_y" not in steps_content[current_step]:
        steps_content[current_step]["end_page"] = len(doc) - 1
        steps_content[current_step]["end_y"] = doc[-1].rect.height

    # Second pass: extract images for each step using their vertical positions
    for step, content in steps_content.items():
        result["step_images"][step] = []
        
        # Handle single page case
        if content["start_page"] == content["end_page"]:
            page = doc.load_page(content["start_page"])
            images = _extract_images_from_page(
                page, 
                output_dir, 
                header_margin_ratio,
                content["start_y"],
                content["end_y"]
            )
            result["step_images"][step].extend(images)
        else:
            # Handle first page
            page = doc.load_page(content["start_page"])
            images = _extract_images_from_page(
                page,
                output_dir,
                header_margin_ratio,
                content["start_y"],
                page.rect.height
            )
            result["step_images"][step].extend(images)
            
            # Handle middle pages if any
            for page_index in range(content["start_page"] + 1, content["end_page"]):
                page = doc.load_page(page_index)
                images = _extract_images_from_page(
                    page,
                    output_dir,
                    header_margin_ratio
                )
                result["step_images"][step].extend(images)
            
            # Handle last page
            if content["end_page"] > content["start_page"]:
                page = doc.load_page(content["end_page"])
                images = _extract_images_from_page(
                    page,
                    output_dir,
                    header_margin_ratio,
                    0,
                    content["end_y"]
                )
                result["step_images"][step].extend(images)

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