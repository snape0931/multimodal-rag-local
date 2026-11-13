from pathlib import Path

import pymupdf

from backend.retrieval import model, table_collection


def clean(value):
    if value is None:
        return ""
    return " ".join(str(value).split())


def ingest_pdf_tables(pdf_path):

    pdf_path = Path(pdf_path)
    source = pdf_path.name

    print(f"Extracting tables from: {source}")

    # Remove old records so re-uploading the same PDF doesn't duplicate rows
    try:
        table_collection.delete(where={"source": source})
    except Exception:
        pass

    documents = []
    metadatas = []
    ids = []
    tables_found = 0

    pdf = pymupdf.open(str(pdf_path))

    try:
        for page_number, page in enumerate(pdf, start=1):

            try:
                found = page.find_tables()
            except Exception:
                continue

            for table_number, table in enumerate(found.tables, start=1):

                rows = table.extract()

                if not rows or len(rows) < 2:
                    continue

                tables_found += 1

                headers = [
                    clean(cell) or f"Column_{i}"
                    for i, cell in enumerate(rows[0])
                ]

                for row_number, row in enumerate(rows[1:], start=1):

                    text = (
                        f"Source: {source}\n"
                        f"Page: {page_number}\n"
                        f"Table: {table_number}\n"
                    )

                    has_data = False

                    for i, value in enumerate(row):
                        if i < len(headers):
                            value = clean(value)
                            if value:
                                has_data = True
                            text += f"{headers[i]}: {value}\n"

                    if not has_data:
                        continue

                    documents.append(text)
                    metadatas.append({
                        "source": source,
                        "page": page_number,
                        "type": "table"
                    })
                    ids.append(
                        f"{source}_p{page_number}_t{table_number}_r{row_number}"
                    )
    finally:
        pdf.close()

    if documents:
        embeddings = model.encode(
            documents,
            batch_size=64,
            show_progress_bar=False
        ).tolist()

        table_collection.upsert(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

    print(f"Tables found: {tables_found}, rows indexed: {len(documents)}")

    return {
        "status": "completed",
        "tables_found": tables_found,
        "rows_indexed": len(documents)
    }