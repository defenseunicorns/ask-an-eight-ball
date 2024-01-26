from langchain_community.document_loaders import PDFMinerPDFasHTMLLoader
import csv


# https://python.langchain.com/docs/modules/data_connection/document_loaders/pdf#using-pdfminer-to-generate-html-text
def load_and_parse_pdf(path_to_pdf):
    loader = PDFMinerPDFasHTMLLoader(path_to_pdf)

    data = loader.load()[0]

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(data.page_content,'html.parser')
    content = soup.find_all('div')

    import re
    cur_fs = None
    cur_text = ''
    snippets = []   # first collect all snippets that have the same font size
    for c in content:
        sp = c.find('span')
        if not sp:
            continue
        st = sp.get('style')
        if not st:
            continue
        fs = re.findall('font-size:(\d+)px',st)
        if not fs:
            continue
        fs = int(fs[0])
        if not cur_fs:
            cur_fs = fs
        if fs == cur_fs:
            cur_text += c.text
        else:
            snippets.append((cur_text,cur_fs))
            cur_fs = fs
            cur_text = c.text
    snippets.append((cur_text,cur_fs))
    # Note: The above logic is very straightforward. One can also add more strategies such as removing duplicate snippets (as
    # headers/footers in a PDF appear on multiple pages so if we find duplicates it's safe to assume that it is redundant info)

    from langchain.docstore.document import Document
    cur_idx = -1
    semantic_snippets = []
    # Assumption: headings have higher font size than their respective content
    for s in snippets:
        # if current snippet's font size > previous section's heading => it is a new heading
        if not semantic_snippets or s[1] > semantic_snippets[cur_idx].metadata['heading_font']:
            metadata={'heading':s[0], 'content_font': 0, 'heading_font': s[1]}
            metadata.update(data.metadata)
            semantic_snippets.append(Document(page_content='',metadata=metadata))
            # semantic_snippets.append(metadata['heading'])
            cur_idx += 1
            continue

        # if current snippet's font size <= previous section's content => content belongs to the same section (one can also create
        # a tree like structure for sub sections if needed but that may require some more thinking and may be data specific)
        if not semantic_snippets[cur_idx].metadata['content_font'] or s[1] <= semantic_snippets[cur_idx].metadata['content_font']:
            semantic_snippets[cur_idx].page_content += s[0]
            semantic_snippets[cur_idx].metadata['content_font'] = max(s[1], semantic_snippets[cur_idx].metadata['content_font'])
            continue

        # if current snippet's font size > previous section's content but less than previous section's heading than also make a new
        # section (e.g. title of a PDF will have the highest font size but we don't want it to subsume all sections)
        metadata={'heading':s[0], 'content_font': 0, 'heading_font': s[1]}
        metadata.update(data.metadata)
        # semantic_snippets.append(metadata['heading'])
        semantic_snippets.append(Document(page_content='',metadata=metadata))
        cur_idx += 1
    return semantic_snippets

def get_headings_from(semantic_snippets):
    headings = []
    for s in semantic_snippets:
        headings.append(s.metadata['heading'].replace('\n',''))
    return headings

def save_titles_to_csv(titles, csv_path):
    with open(csv_path, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(['Category', "Description"])  # Header
        writer.writerows([[title,title] for title in titles])

if __name__ == "__main__":
    pdf_path = "preload/Doug_Guide_to_the_Galaxy.pdf"
    csv_path = "metadata/dougs_guide_categories.csv"
    semantic_snippets =  load_and_parse_pdf(pdf_path)
    headings = get_headings_from(semantic_snippets)
    save_titles_to_csv(headings, csv_path)
    print(f"Titles extracted and saved to {csv_path}")