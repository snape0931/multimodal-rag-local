import io
from pathlib import Path

import ollama
from PIL import Image

from backend.retrieval import model, image_collection
from backend.image_extractor import extract_images

VISION_MODEL = "llava:7b"        # "moondream" is much faster on CPU (ollama pull moondream)
MIN_SIZE = 200                   # px: skip icons and decorative fragments
MAX_IMAGES = 8                   # max images described per PDF
MAX_SIDE = 768                   # shrink images before sending them to the model
MAX_DESCRIPTION_TOKENS = 150     # lower = faster, but vaguer diagram answers
VISION_TIMEOUT_SECONDS = 240     # a stuck model call is abandoned instead of hanging forever

vision_client = ollama.Client(timeout=VISION_TIMEOUT_SECONDS)

PROMPT = (
    "In 2-3 short sentences, describe this image. Say what kind of figure it is "
    "(diagram, chart, table or photo) and include any readable labels or text."
)


def image_area(path):
    """Width * height, or 0 if the image is too small or unreadable."""
    try:
        with Image.open(path) as img:
            width, height = img.size
        if width < MIN_SIZE or height < MIN_SIZE:
            return 0
        return width * height
    except Exception:
        return 0


def to_small_jpeg(path):
    """Return the image as a downscaled JPEG (bytes)."""
    with Image.open(path) as img:
        img = img.convert("RGB")
        img.thumbnail((MAX_SIDE, MAX_SIDE))
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        return buffer.getvalue()


def ingest_pdf_images(pdf_path, should_cancel=None, on_progress=None):
    """
    should_cancel: optional function returning True when the PDF was deleted
    on_progress:   optional function(done, total) for the status line
    """

    print(f"Starting image ingestion: {pdf_path}")

    extracted_images = extract_images(pdf_path)

    if should_cancel and should_cancel():
        return {"status": "cancelled"}

    # Remove old descriptions so a re-uploaded PDF never keeps stale ones
    try:
        image_collection.delete(where={"source": Path(pdf_path).name})
    except Exception:
        pass

    if not extracted_images:
        return {
            "status": "completed",
            "images_found": 0,
            "images_indexed": 0
        }

    total_found = len(extracted_images)

    # Keep the biggest images, capped at MAX_IMAGES
    sized = [(image_area(img["path"]), img) for img in extracted_images]
    sized = [(area, img) for area, img in sized if area > 0]
    sized.sort(key=lambda pair: pair[0], reverse=True)
    selected = [img for _, img in sized[:MAX_IMAGES]]

    print(f"Images extracted: {total_found} | to describe: {len(selected)}")

    indexed = 0

    for position, image in enumerate(selected, start=1):

        if should_cancel and should_cancel():
            print("Image ingestion cancelled")
            break

        if on_progress:
            on_progress(position, len(selected))

        filename = image["filename"]
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
            response = vision_client.chat(
                model=VISION_MODEL,
                messages=[{
                    "role": "user",
                    "content": PROMPT,
                    "images": [to_small_jpeg(image["path"])],
                }],
                keep_alive="2m",
                options={
                    "num_predict": MAX_DESCRIPTION_TOKENS,
                    "temperature": 0.2,
                },
            )

            description = response["message"]["content"].strip()

            if not description:
                continue

            text = f"Figure on page {image['page']}: {description}"

            embedding = model.encode(
                [text],
                show_progress_bar=False
            ).tolist()

            # The PDF may have been deleted while the model was thinking
            if should_cancel and should_cancel():
                print("Image ingestion cancelled")
                break

            # Save each image right away so a later failure loses nothing
            image_collection.upsert(
                documents=[text],
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

    # Unload the vision model so it doesn't compete with the answer model
    try:
        vision_client.generate(model=VISION_MODEL, prompt="", keep_alive=0)
    except Exception:
        pass

    return {
        "status": "completed",
        "images_found": total_found,
        "images_processed": len(selected),
        "images_indexed": indexed
    }