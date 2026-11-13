import ollama
from PIL import Image

from backend.retrieval import model, image_collection
from image_extractor import extract_images


MIN_SIZE = 200        # px: skip icons, logos and decorative fragments
MAX_IMAGES = 15       # max images described per PDF
VISION_MODEL = "llava:7b"


def get_image_area(image_path):
    """Return width * height, or 0 if the image can't be opened."""
    try:
        with Image.open(image_path) as img:
            width, height = img.size
        if width < MIN_SIZE or height < MIN_SIZE:
            return 0
        return width * height
    except Exception:
        return 0


def ingest_pdf_images(pdf_path):

    print(f"Starting image ingestion: {pdf_path}")

    extracted_images = extract_images(pdf_path)

    if not extracted_images:
        return {
            "status": "completed",
            "images_found": 0,
            "images_indexed": 0
        }

    total_found = len(extracted_images)

    # Keep only reasonably large images, biggest first, capped at MAX_IMAGES
    sized = [(get_image_area(img["path"]), img) for img in extracted_images]
    sized = [(area, img) for area, img in sized if area > 0]
    sized.sort(key=lambda pair: pair[0], reverse=True)
    selected = [img for _, img in sized[:MAX_IMAGES]]

    print(
        f"Images extracted: {total_found} | "
        f"after filtering: {len(selected)}"
    )

    indexed = 0

    for image in selected:

        filename = image["filename"]
        image_path = image["path"]
        image_id = f"image_{filename}"

        # Skip images that were already described and stored
        try:
            existing = image_collection.get(ids=[image_id])
            if existing and existing.get("ids"):
                print(f"Already indexed, skipping: {filename}")
                continue
        except Exception:
            pass

        print(f"Generating description: {filename}")

        try:
            response = ollama.chat(
                model=VISION_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Describe this image in detail. "
                            "Identify diagrams, charts, labels, "
                            "important objects and visible text."
                        ),
                        "images": [image_path]
                    }
                ]
            )

            description = response["message"]["content"]

            if not description.strip():
                continue

            embedding = model.encode(
                [description],
                show_progress_bar=False
            ).tolist()

            # Save each image right away so a later failure loses nothing
            image_collection.upsert(
                documents=[description],
                embeddings=embedding,
                metadatas=[{
                    "source": image["source"],
                    "page": image["page"],
                    "image": filename,
                    "type": "image"
                }],
                ids=[image_id]
            )

            indexed += 1

        except Exception as e:
            print(f"Skipping {filename}: {e}")
            continue

    return {
        "status": "completed",
        "images_found": total_found,
        "images_processed": len(selected),
        "images_indexed": indexed
    }