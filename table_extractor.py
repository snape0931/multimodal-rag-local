
import pdfplumber
import json
import os

PDF_FOLDER = "data/documents"
OUTPUT_FOLDER = "data/extracted_tables"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def extract_tables(pdf_path):

    all_tables = []

    with pdfplumber.open(pdf_path) as pdf:

        for page_number, page in enumerate(pdf.pages, start=1):

            tables = page.extract_tables()

            for table_number, table in enumerate(tables):

                if not table or len(table) < 2:
                    continue

                headers = [
                    str(cell).strip() if cell else f"Column_{i}"
                    for i, cell in enumerate(table[0])
                ]

                for row_index, row in enumerate(table[1:]):

                    row_data = {}

                    for i, value in enumerate(row):

                        if i < len(headers):
                            row_data[headers[i]] = (
                                str(value).strip() if value else ""
                            )

                    all_tables.append({
                        "page": page_number,
                        "table_number": table_number + 1,
                        "row_number": row_index + 1,
                        "data": row_data
                    })

    return all_tables


# Run this section only when executing table_extractor.py directly
if __name__ == "__main__":

    for filename in os.listdir(PDF_FOLDER):

        if filename.lower().endswith(".pdf"):

            pdf_path = os.path.join(PDF_FOLDER, filename)

            print(f"Processing: {filename}")

            tables = extract_tables(pdf_path)

            output_file = os.path.join(
                OUTPUT_FOLDER,
                os.path.splitext(filename)[0] + "_tables.json"
            )

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(tables, f, indent=4, ensure_ascii=False)

            print(f"Tables extracted: {len(tables)}")

    print("Table extraction completed!")
