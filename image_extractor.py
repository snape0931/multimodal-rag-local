
import fitz
import os

PDF_FOLDER = "data/documents"
IMAGE_FOLDER = "data/extracted_images"

os.makedirs(IMAGE_FOLDER, exist_ok=True)

for filename in os.listdir(PDF_FOLDER):

    if filename.lower().endswith(".pdf"):

        pdf_path = os.path.join(PDF_FOLDER, filename)

        print(f"\nProcessing: {filename}")

        pdf = fitz.open(pdf_path)

        image_count = 0

        for page_number, page in enumerate(pdf, start=1):

            images = page.get_images(full=True)

            for image_index, image in enumerate(images):

                xref = image[0]

                image_data = pdf.extract_image(xref)

                image_bytes = image_data["image"]
                image_ext = image_data["ext"]

                image_name = (
                    f"{os.path.splitext(filename)[0]}"
                    f"_page{page_number}"
                    f"_image{image_index + 1}.{image_ext}"
                )

                image_path = os.path.join(
                    IMAGE_FOLDER, image_name
                )

                with open(image_path, "wb") as f:
                    f.write(image_bytes)

                image_count += 1

        print(f"Images extracted: {image_count}")

        pdf.close()

print("\nImage extraction completed!")
