import pypdf
import os

pdf_path = r"c:\Users\isyaa\OneDrive\Documents\Web and Code\vending_api\Plan\Laporan\Form 3 - ERP Based Inventory Monitoring Framework for Three Month Demand Forecasting Using Supervised Machine Learning.pdf"
output_path = r"c:\Users\isyaa\OneDrive\Documents\Web and Code\vending_api\Plan\Laporan\extracted_full_text.txt"

reader = pypdf.PdfReader(pdf_path)
print(f"Total pages: {len(reader.pages)}")

with open(output_path, "w", encoding="utf-8") as f:
    for i, page in enumerate(reader.pages):
        f.write(f"\n===== HALAMAN {i+1} =====\n")
        text = page.extract_text()
        if text:
            f.write(text)
        else:
            f.write("[Tidak ada teks / Berupa gambar]\n")

print("Extraction done successfully!")
