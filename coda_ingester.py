from codaio import Coda, Document
import os
import fitz


class CodaIngester:
    def __init__(self):
        self.coda = Coda(os.environ.get("CODA_API_KEY"))

    def get_document(self, id):
        doc = Document(id, coda=self.coda)
        return doc

    def list_document_sections(self, id):
        return self.get_document(id).list_sections()


def extract_sections(filePath, start_keywords):
    pdf = fitz.open(filePath)
    sections_dict = {}
    current_section = []
    current_keyword = None
    max_font_size = 0

    # Normalize keywords to lowercase for case-insensitive matching
    start_keywords_lower = set(keyword.lower() for keyword in start_keywords)

    # First, identify the maximum font size in the document
    for page in pdf:
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        if int(round(span['size'])) > max_font_size:
                            max_font_size = int(round(span['size']))

    # Now, iterate again to collect the sections and subsections
    for page in pdf:
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span['text']
                        font_size = int(round(span['size']))

                        if font_size == max_font_size and text.lower() in start_keywords_lower:
                            if current_keyword is not None:  # Finish the last section before starting a new one
                                sections_dict[current_keyword] = current_section
                            current_keyword = text
                            current_section = []
                        elif current_keyword is not None:  # We are inside a section
                            if font_size == max_font_size:
                                # Start a new subsection
                                current_section.append(text)
                            else:
                                # Continue adding text to the current subsection
                                if current_section:
                                    current_section[-1] += ' ' + text
                                else:
                                    # If the current_section is empty, initialize with the current text
                                    current_section.append(text)

    # Add the last section
    if current_keyword is not None and current_section:
        sections_dict[current_keyword] = current_section

    pdf.close()
    return sections_dict