import os
import pymupdf as fitz

IMAGE_FOLDER = "data/extracted_images"
MIN_SIZE = 200  # px: skip icons, logos and decorative fragments

os.makedirs(IMAGE_FOLDER, exist_ok=True)


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

                image_bytes = image_data["image"]
                image_ext = image_data["ext"]

                image_name = (
                    f"{pdf_name}_page{page_number}"
                    f"_image{image_index + 1}.{image_ext}"
                )

                image_path = os.path.join(IMAGE_FOLDER, image_name)

                with open(image_path, "wb") as f:
                    f.write(image_bytes)

                extracted_images.append({
                    "filename": image_name,
                    "path": image_path,
                    "source": filename,
                    "page": page_number
                })

    finally:
        pdf.close()

    print(
        f"Images extracted: {len(extracted_images)} "
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