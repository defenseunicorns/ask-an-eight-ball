import ipaddress
import os
import re

import outlines.models as models
import outlines.text.generate as generate
import requests
from langchain.text_splitter import (MarkdownHeaderTextSplitter,
                                     RecursiveCharacterTextSplitter)

import coda_exporter as coda

GH_PA_TOKEN = os.environ.get("GH_PA_TOKEN")
CODA_API = os.environ.get("CODA_API")

HEADERS = {"Authorization": f"token {GH_PA_TOKEN}"}
model = None

CHUNK_SIZE = 2000
CHUNK_OVERLAP = 150

descriptions = []


def make_valid_collection_name(description):
    # Check if the string is a valid IPv4 address
    try:
        ipaddress.IPv4Address(description)
        # If it is, append an underscore to make it invalid
        description += "_"
    except ipaddress.AddressValueError:
        # If it's not a valid IPv4 address, do nothing
        pass

    # Remove all characters that are not alphanumeric, underscore, or hyphen
    description = re.sub(r"[^a-zA-Z0-9-_]+", "_", description)

    # Replace any sequence of two or more periods with a single period
    description = re.sub(r"\.\.+", ".", description)

    # If the string is too short, append underscores
    if len(description) < 3:
        description += "_" * (3 - len(description))
    # If the string is too long, truncate it
    elif len(description) > 63:
        description = description[:63]

    # Ensure the string starts and ends with an alphanumeric character
    description = description.strip(".-_")
    if not description[0].isalnum():
        description = "z" + description[1:]
    if not description[-1].isalnum():
        description = description[:-1] + "z"

    return description


def fetch_markdown(url, path=""):

    response = requests.get(url + path, timeout=5, headers=HEADERS)

    if response.status_code != 200:
        print(
            f"ERROR: HTTP error {response.status_code} when accessing {url + path}")
        return []

    data = response.json()

    files = []
    for file in data:
        if file["type"] == "dir":
            files.extend(fetch_markdown(url, file["path"]))
        elif file["type"] == "file" and file["name"].endswith(".md"):
            files.append(file)
    return files


def read_file(file):
    content = requests.get(file["download_url"],
                           timeout=5, headers=HEADERS).content

    return content


def create_description(metadata):
    return "_".join(metadata.values())


def summarize_page_content(page_content):
    """
    Summarizes the page content to a maximum of 220 characters, preferring to break on whitespace.

    Args:
    - page_content (str): The content of the page as a string.

    Returns:
    - str: A summary of the page content.
    """
    initial_slice = page_content[:220]

    last_space = initial_slice.rfind(' ')

    if last_space == -1 or last_space > 200:
        summary = page_content[:200]
    else:
        summary = initial_slice[:last_space]

    return summary


def get_hugo_title(row):
    if not row.metadata:
        h1_match = re.search(r'^#\s+(.+)', row.page_content, re.MULTILINE)
        if h1_match:
            return {"Header 1": h1_match.group(1)}

        # Try to find a title in frontmatter
        frontmatter_match = re.search(
            r'^---\s+(.*?[^\\])\s+---', row.page_content, re.DOTALL)
        if frontmatter_match:
            frontmatter_content = frontmatter_match.group(1)
            title_match = re.search(
                r'^title:\s*(.+)$', frontmatter_content, re.MULTILINE)
            if title_match:
                return {"Header 1": title_match.group(1)}

    # If neither H1 nor frontmatter title is found
    return {"Header 1": "None"}


def load_markdown_data(chroma_client, url, path):
    global descriptions
    history_raw_text = ""

    descriptions = []

    files = fetch_markdown(url, path)

    for file in files:
        content = read_file(file)
        history_raw_text = history_raw_text + content.decode("utf-8")

    # coda_docs = coda.get_coda_docs(CODA_API)

    # for coda_doc in coda_docs:
    #     history_raw_text = history_raw_text + coda_doc

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
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    docs = text_splitter.split_documents(data)

    for idx, row in enumerate(docs):

        metadata = get_hugo_title(row)

        row_number = str(idx)

        row_description = create_description(metadata)
        valid_keyword = make_valid_collection_name(row_description)

        descriptions.append({'category': row_description,
                            'description': summarize_page_content(row.page_content)})

        store_text_with_header(
            chroma_client, row_description, metadata, row_number)
        section_collection = chroma_client.get_or_create_collection(
            name=valid_keyword)
        section_collection.add(documents=[row.page_content], ids=str(idx))


def store_text_with_header(chroma_client, text, header_metadata, doc_id):
    category_collection = chroma_client.get_or_create_collection(
        name="categories")

    desc = [text]
    header_metadatas = [header_metadata]
    doc_ids = [doc_id]

    chroma_id = category_collection.add(
        documents=desc, metadatas=header_metadatas, ids=doc_ids
    )

    return chroma_id


def find_most_similar(input_string, string_list):
    result = generate.choice(model=model, choices=string_list)(
        f"Which one of these items is most relevant to this question: {input_string}"
    )
    print(result)
    return result


def create_desc_list(desc):
    return list(desc)


def query_with_doug(chroma_client, text, generative=False):
    global model
    category = ""

    # Use a generative model like Synthia-7b
    if generative:
        if model is None:
            model = models.transformers(
                "TheBloke/SynthIA-7B-v2.0-GPTQ", device="cuda:0"
            )

        categories = create_desc_list(descriptions)

        description = find_most_similar(text, descriptions)

        for category in categories:
            if category["description"] == description:
                category = category["category"]
    # Use similarity search using an embedding model like "sentence-transformers/all-MiniLM-L6-v2"
    else:
        collection = chroma_client.get_collection(name="categories")
        results = collection.query(query_texts=[text], n_results=1)

        print(results)
        category = results["metadatas"][0][0]["category"]

    valid_category = make_valid_collection_name(category)
    collection = chroma_client.get_collection(name=valid_category)
    narrowed_result = collection.query(query_texts=[text], n_results=1)

    return narrowed_result
