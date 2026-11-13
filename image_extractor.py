
import fitz
import os

IMAGE_FOLDER = "data/extracted_images"

os.makedirs(IMAGE_FOLDER, exist_ok=True)


def extract_images(pdf_path):

    pdf_path = str(pdf_path)
    filename = os.path.basename(pdf_path)
    pdf_name = os.path.splitext(filename)[0]

    print(f"Extracting images from: {filename}")

    extracted_images = []

    pdf = fitz.open(pdf_path)

    try:
        for page_number, page in enumerate(pdf, start=1):

            images = page.get_images(full=True)

            for image_index, image in enumerate(images):

                xref = image[0]

                image_data = pdf.extract_image(xref)

                image_bytes = image_data["image"]
                image_ext = image_data["ext"]

                image_name = (
                    f"{pdf_name}_page{page_number}"
                    f"_image{image_index + 1}.{image_ext}"
                )

                image_path = os.path.join(
                    IMAGE_FOLDER, image_name
                )

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

    print(f"Images extracted: {len(extracted_images)}")

    return extracted_images


if __name__ == "__main__":

    PDF_FOLDER = "data/documents"

    for filename in os.listdir(PDF_FOLDER):

        if filename.lower().endswith(".pdf"):

            pdf_path = os.path.join(PDF_FOLDER, filename)
            extract_images(pdf_path)

    print("Image extraction completed!")
