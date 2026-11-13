
import json
from pathlib import Path

from backend.retrieval import model, table_collection
from table_extractor import extract_tables


def ingest_pdf_tables(pdf_path):

    pdf_path = Path(pdf_path)
    filename = pdf_path.name

    print(f"Extracting tables from: {filename}")

    tables = extract_tables(str(pdf_path))

    if not tables:
        return {
            "status": "completed",
            "filename": filename,
            "tables_found": 0,
            "records_added": 0
        }

    documents = []
    metadatas = []
    ids = []

    for table in tables:

        table_text = json.dumps(
            table["data"],
            ensure_ascii=False
        )

        documents.append(table_text)

        metadatas.append({
            "source": filename,
            "page": table["page"],
            "table_number": table["table_number"],
            "row_number": table["row_number"]
        })

        ids.append(
            f"{filename}_page_{table['page']}_table_{table['table_number']}_row_{table['row_number']}"
        )

    embeddings = model.encode(
        documents,
        show_progress_bar=False
    ).tolist()

    table_collection.upsert(
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )

    print(f"Indexed {len(documents)} table rows.")

    return {
        "status": "completed",
        "filename": filename,
        "tables_found": len(set(
            (t["page"], t["table_number"]) for t in tables
        )),
        "records_added": len(documents)
    }
