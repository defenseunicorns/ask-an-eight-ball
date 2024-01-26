from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import fitz  # PyMuPDF
import re
import csv

def extract_headers_from_pdf(pdf_file_path):
    headers = []

    # Open the PDF file
    with fitz.open(pdf_file_path) as doc:
        # Iterate through each page
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text("html")

            lines = text.split("\n")

            # # Iterate through each line
            for line in lines:
                if line.startswith("<h") or "<b>" in line or "<i>" in line:
                    headerHTML = re.findall(r'<(h\d*|b|i)[^>]*>(.*?)</(h\d*|b|i)>', line, flags=re.IGNORECASE | re.DOTALL)
                    for match in headerHTML:
                        _, inner_html, _ = match
                        headerTxt = re.findall(r'>(.*?)<', inner_html, flags=re.IGNORECASE)


            # Append header text to the list
            headers.extend(headerTxt)

    return headers

def save_titles_to_csv(titles, csv_path):
    with open(csv_path, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        # Write the titles to the CSV file
        writer.writerow(['Category', "Description"])  # Header
        writer.writerows([[title,title] for title in titles])

if __name__ == "__main__":
    pdf_path = "preload/Doug_Guide_to_the_Galaxy.pdf"
    csv_path = "metadata/dougs_guide_categories.csv"
    extracted_titles = extract_headers_from_pdf(pdf_path)
    save_titles_to_csv(extracted_titles, csv_path)
    print(f"Titles extracted and saved to {csv_path}")