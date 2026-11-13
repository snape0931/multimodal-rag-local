
import ollama
import os

image_folder = "data/extracted_images"

images = [
    f for f in os.listdir(image_folder)
    if f.lower().endswith((".png", ".jpg", ".jpeg"))
]

if not images:
    print("No supported images found!")
else:
    image_path = os.path.join(image_folder, images[0])

    print("Testing image:", image_path)
    print("Analysing image...")

    response = ollama.chat(
        model="llava:7b",
        messages=[
            {
                "role": "user",
                "content": """
                Describe this image in detail.
                Identify diagrams, charts, labels,
                objects and any visible text.
                """,
                "images": [image_path]
            }
        ]
    )

    print("\nIMAGE DESCRIPTION:\n")
    print(response["message"]["content"])
