import os
import re

import pymupdf as fitz

IMAGE_FOLDER = "data/extracted_images"
MIN_SIZE = 200                 # px: skip icons, logos and decorative fragments

# Vector diagrams (boxes, arrows, charts drawn with paths) are not embedded
# images, so get_images() never sees them. We detect pages with many drawn
# shapes and render just the drawn region to a PNG.
VECTOR_MIN_DRAWINGS = 25       # drawn shapes needed on a page without a caption
VECTOR_CAPTION_DRAWINGS = 10   # lower bar when the page has a "Figure N" caption
MAX_VECTOR_FIGURES = 12        # per PDF
RENDER_ZOOM = 1.5
CAPTION_RE = re.compile(r"\b(?:figure|fig\.)\s*\d+", re.I)

os.makedirs(IMAGE_FOLDER, exist_ok=True)


def _vector_region(page):
    """
    Bounding box of the drawn shapes on a page, ignoring page borders,
    backgrounds, table lines and tiny marks. Returns (rect, shape_count)
    or (None, 0) if nothing diagram-like is found.
    """
    try:
        drawings = page.get_drawings()
    except Exception:
        return None, 0

    if not drawings:
        return None, 0

    page_area = page.rect.width * page.rect.height

    table_boxes = []

    # Table borders are drawn as lines too; don't mistake them for diagrams
    if len(drawings) >= VECTOR_CAPTION_DRAWINGS:
        try:
            table_boxes = [
                fitz.Rect(t.bbox) for t in page.find_tables().tables
            ]
        except Exception:
            table_boxes = []

    kept = []

    for drawing in drawings:
        rect = fitz.Rect(drawing["rect"])

        if max(rect.width, rect.height) < 3:
            continue   # dots, underline fragments

        if rect.width * rect.height > 0.8 * page_area:
            continue   # page border or background

        if any(box.contains(rect) for box in table_boxes):
            continue

        kept.append(rect)

    if not kept:
        return None, 0

    region = fitz.Rect(kept[0])

    for rect in kept[1:]:
        region |= rect   # union

    region = fitz.Rect(
        region.x0 - 10, region.y0 - 10, region.x1 + 10, region.y1 + 10
    ) & page.rect

    return region, len(kept)


def _extract_vector_figures(pdf, pdf_name, filename, pages_with_images):
    figures = []

    for page_number, page in enumerate(pdf, start=1):

        if len(figures) >= MAX_VECTOR_FIGURES:
            break

        # A real image already covers this page's figure
        if page_number in pages_with_images:
            continue

        region, shapes = _vector_region(page)

        if region is None:
            continue

        has_caption = bool(CAPTION_RE.search(page.get_text("text")))
        needed = VECTOR_CAPTION_DRAWINGS if has_caption else VECTOR_MIN_DRAWINGS

        if shapes < needed:
            continue

        try:
            pixmap = page.get_pixmap(
                matrix=fitz.Matrix(RENDER_ZOOM, RENDER_ZOOM), clip=region
            )
        except Exception as e:
            print(f"Could not render page {page_number}: {e}")
            continue

        if pixmap.width < MIN_SIZE or pixmap.height < MIN_SIZE:
            continue

        image_name = f"{pdf_name}_page{page_number}_vector1.png"
        image_path = os.path.join(IMAGE_FOLDER, image_name)
        pixmap.save(image_path)

        figures.append({
            "filename": image_name,
            "path": image_path,
            "source": filename,
            "page": page_number,
        })

    return figures


def extract_images(pdf_path):

    pdf_path = str(pdf_path)
    filename = os.path.basename(pdf_path)
    pdf_name = os.path.splitext(filename)[0]

    print(f"Extracting images from: {filename}")

    extracted_images = []
    seen_xrefs = set()   # same image reused on many pages is saved once
    skipped_small = 0

    pdf = fitz.open(pdf_path)

    try:
        for page_number, page in enumerate(pdf, start=1):

            images = page.get_images(full=True)

            for image_index, image in enumerate(images):

                xref = image[0]

                if xref in seen_xrefs:
                    continue
                seen_xrefs.add(xref)

                try:
                    image_data = pdf.extract_image(xref)
                except Exception as e:
                    print(f"Could not extract image {xref}: {e}")
                    continue

                if not image_data:
                    continue

                # Skip tiny images before writing anything to disk
                if (
                    image_data["width"] < MIN_SIZE
                    or image_data["height"] < MIN_SIZE
                ):
                    skipped_small += 1
                    continue

                image_name = (
                    f"{pdf_name}_page{page_number}"
                    f"_image{image_index + 1}.{image_data['ext']}"
                )

                image_path = os.path.join(IMAGE_FOLDER, image_name)

                with open(image_path, "wb") as f:
                    f.write(image_data["image"])

                extracted_images.append({
                    "filename": image_name,
                    "path": image_path,
                    "source": filename,
                    "page": page_number,
                })

        raster_count = len(extracted_images)
        pages_with_images = {img["page"] for img in extracted_images}

        extracted_images += _extract_vector_figures(
            pdf, pdf_name, filename, pages_with_images
        )

    finally:
        pdf.close()

    print(
        f"Images extracted: {raster_count} embedded + "
        f"{len(extracted_images) - raster_count} vector figures "
        f"(skipped {skipped_small} small images)"
    )

    return extracted_images


if __name__ == "__main__":

    PDF_FOLDER = "data/documents"

    for filename in os.listdir(PDF_FOLDER):

        if filename.lower().endswith(".pdf"):

            pdf_path = os.path.join(PDF_FOLDER, filename)
            extract_images(pdf_path)

    print("Image extraction completed!")