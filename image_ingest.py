
import os
import chromadb
import ollama
from sentence_transformers import SentenceTransformer

IMAGE_FOLDER = "data/extracted_images"

print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

client = chromadb.PersistentClient(path="./vectorstore")

# Create a separate image collection
try:
    client.delete_collection(name="images")
except Exception:
    pass

collection = client.create_collection(name="images")

documents = []
metadatas = []
ids = []

image_files = [
    filename for filename in os.listdir(IMAGE_FOLDER)
    if filename.lower().endswith(
        (".png", ".jpg", ".jpeg", ".webp")
    )
]


print(f"Total images to process: {len(image_files)}")

for filename in image_files:
        image_path = os.path.join(IMAGE_FOLDER, filename)

        print(f"Analysing: {filename}")

        response = ollama.chat(
            model="llava:7b",
            messages=[
                {
                    "role": "user",
                    "content": """
                    Describe this image in detail.
                    Identify diagrams, charts, labels,
                    important objects and visible text.
                    """,
                    "images": [image_path]
                }
            ]
        )

        description = response["message"]["content"]

        documents.append(description)

        # Extract source PDF name from image filename
        source = filename.split("_page")[0] + ".pdf"

        page_number = filename.split("_page")[1].split("_")[0]

        metadatas.append({
            "source": source,
            "page": int(page_number),
            "image": filename,
            "type": "image"
        })

        ids.append(f"image_{len(ids)}")

if documents:

    embeddings = model.encode(documents).tolist()

    collection.add(
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )

print("\nImage indexing completed!")
print("Total images indexed:", collection.count())
