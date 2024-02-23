import ipaddress
import os
import re

import outlines.models as models
import outlines.text.generate as generate
import requests
from langchain.text_splitter import (MarkdownHeaderTextSplitter,
                                     RecursiveCharacterTextSplitter)

GH_PA_TOKEN = os.environ.get("GH_PA_TOKEN")
HEADERS = {'Authorization': f'token {GH_PA_TOKEN}'}
model = None

CHUNK_SIZE = 2000
CHUNK_OVERLAP = 150


def make_valid_collection_name(description):
    # Check if the string is a valid IPv4 address
    try:
        ipaddress.IPv4Address(description)
        # If it is, append an underscore to make it invalid
        description += '_'
    except ipaddress.AddressValueError:
        # If it's not a valid IPv4 address, do nothing
        pass

    # Remove all characters that are not alphanumeric, underscore, or hyphen
    description = re.sub(r'[^a-zA-Z0-9-_]+', '_', description)

    # Replace any sequence of two or more periods with a single period
    description = re.sub(r'\.\.+', '.', description)

    # If the string is too short, append underscores
    if len(description) < 3:
        description += '_' * (3 - len(description))
    # If the string is too long, truncate it
    elif len(description) > 63:
        description = description[:63]

    # Ensure the string starts and ends with an alphanumeric character
    description = description.strip(".-_")
    if not description[0].isalnum():
        description = 'z' + description[1:]
    if not description[-1].isalnum():
        description = description[:-1] + 'z'

    return description


def fetch_markdown(url, path=''):

    response = requests.get(url + path, timeout=5, headers=HEADERS)

    if response.status_code != 200:
        print(
            f"ERROR: HTTP error {response.status_code} when accessing {url + path}")
        return []

    data = response.json()

    files = []
    for file in data:
        if file['type'] == 'dir':
            files.extend(fetch_markdown(url, file['path']))
        elif file['type'] == 'file' and file['name'].endswith('.md'):
            files.append(file)
    return files


def read_file(file):
    content = requests.get(file['download_url'],
                           timeout=5, headers=HEADERS).content

    return content


def create_description(metadata):
    print(metadata)
    return '_'.join(metadata.values())


def extract_title_from_hugo_frontmatter(markdown_content):
    """
    Extracts the title property from the Hugo frontmatter in a markdown document.

    """

    frontmatter_pattern = r'^---\s+(.*?)\s+---'
    frontmatter_match = re.search(
        frontmatter_pattern, markdown_content, re.DOTALL | re.MULTILINE)
    if not frontmatter_match:
        return ""  # No frontmatter found

    # If frontmatter is found, search for the title property within it
    frontmatter_content = frontmatter_match.group(1)
    title_pattern = r'^title:\s*(.*?)\s*(?:\n|$)'
    title_match = re.search(title_pattern, frontmatter_content, re.MULTILINE)
    if title_match:
        # Return the captured title, stripping quotes if present
        return title_match.group(1).strip('"').strip("'")
    else:
        return ""


def load_markdown_data(chroma_client, url):

    history_raw_text = ""

    files = fetch_markdown(url, "content/en/docs")

    for file in files:
        content = read_file(file)
        history_raw_text = history_raw_text + content.decode('utf-8')

    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
        ("####", "Header 4"),
    ]

    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on)

    data = md_splitter.split_text(history_raw_text)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    docs = text_splitter.split_documents(data)

    for idx, row in enumerate(docs):
        metadata = row.metadata

        h1 = ""
        if "Header 1" not in metadata:
            h1 = {"Header 1": extract_title_from_hugo_frontmatter(
                row.page_content)}
            metadata = {**h1, **metadata}

        row_number = str(idx)

        row_description = create_description(metadata)
        valid_keyword = make_valid_collection_name(row_description)

        category = ""
        for value in metadata.values():
            category = category + " " + (value if value is not None else "")

        metadata["category"] = category

        store_text_with_header(
            chroma_client, row_description, metadata, row_number)
        section_collection = chroma_client.get_or_create_collection(
            name=valid_keyword)
        section_collection.add(documents=[row.page_content], ids=str(idx))


def store_text_with_header(chroma_client, text, header_metadata, doc_id):
    category_collection = chroma_client.get_or_create_collection(
        name="categories")

    descriptions = [text]
    header_metadatas = [header_metadata]
    doc_ids = [doc_id]

    chroma_id = category_collection.add(
        documents=descriptions, metadatas=header_metadatas, ids=doc_ids)

    return chroma_id


def find_most_similar(input_string, string_list):
    result = generate.choice(model=model, choices=string_list)(
        f"Which one of these items is most relevant to this question: {input_string}")
    return result


def query_with_doug(chroma_client, text, generative=False):
    global model
    category = ""

    # Use a generative model like Synthia-7b
    if generative:
        if model is None:
            model = models.transformers(
                "TheBloke/SynthIA-7B-v2.0-GPTQ", device="cuda:0")

        doug_categories = load_csv_into_iterable_map(
            "metadata/dougs_guide_categories.csv")
        descriptions = [d["Description"] for d in doug_categories]
        description = find_most_similar(text, descriptions)

        for d in doug_categories:

            if d["Description"] == description:
                category = d["Category"]
    # Use similarity search using an embedding model like "sentence-transformers/all-MiniLM-L6-v2"
    else:
        collection = chroma_client.get_collection(name="categories")

        results = collection.query(query_texts=[text], n_results=1)
        category = results["metadatas"][0][0]['category']

    valid_category = make_valid_collection_name(category)
    collection = chroma_client.get_collection(name=valid_category)
    narrowed_result = collection.query(query_texts=[text], n_results=1)

    return narrowed_result
