import csv
import ipaddress
import os
import re
import sys

import outlines.models as models
import outlines.text.generate as generate
import requests
from langchain.text_splitter import (MarkdownHeaderTextSplitter,
                                     RecursiveCharacterTextSplitter)

TOKEN = os.environ.get("TOKEN")
HEADERS = {'Authorization': f'token {TOKEN}'}
model = None

from coda_ingester import extract_sections


def load_csv_into_iterable_map(csv_file_path):
    with open(csv_file_path, "r", encoding="utf-8") as csv_file:
        dict_reader = csv.DictReader(csv_file)
        iterable_map = map(lambda row: {key: row[key] for key in row.keys()}, dict_reader)
        iterable_map_list = list(iterable_map)
        return iterable_map_list


def remove_trailing_non_alpha(s):
    """
    Remove any non-alpha character.
    """
    # The pattern r'[^\w\s]*$' matches any number of non-alphabetic characters at the end of the string
    return re.sub(r'[^\w\s]*$', '', s)

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


def load_doug_data(chroma_client, csv_location, doc_location):
    doug_categories = load_csv_into_iterable_map(csv_location)

    for idx, row in enumerate(doug_categories):
        row_metadata = create_header_metadata(row)
        row_description = row['Description']
        store_text_with_header(chroma_client, row_description, row_metadata, str(idx))

    categories_list = [d["Category"] for d in doug_categories]
    sections = extract_sections(doc_location, categories_list)

    for keyword, content_list in sections.items():
        valid_keyword = make_valid_collection_name(keyword)
        section_collection = chroma_client.get_or_create_collection(name=valid_keyword)
        for i, content in enumerate(content_list):
            section_collection.add(documents=[content], ids=str(i))



def get_files(url, path=''):
   

    response = requests.get(url + path, timeout=5, headers=HEADERS)

    if response.status_code != 200:
        logger.error("HTTP error %s when accessing %s", response.status_code, url + path)
        return []

    data = response.json()

    files = []
    for file in data:
        if file['type'] == 'dir':
            files.extend(get_files(url, file['path']))
        elif file['type'] == 'file' and file['name'].endswith('.md'):
            files.append(file)
    return files

def read_file(file):
    content = requests.get(file['download_url'], timeout=5, headers=HEADERS).content

    return content

def create_description(metadata):
    return '_'.join(metadata.values())

def load_markdown_data(chroma_client, url):

    history_raw_text = ""

    files = get_files(url, "content/en/docs")

    # response = requests.get(url, timeout=5, headers=headers)
    for file in files:
        # file_data = json.loads(read_file(file))
        content = read_file(file)
        history_raw_text = history_raw_text + content.decode('utf-8')

    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
        ("####", "Header 4"),
    ]

    md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

    data = md_splitter.split_text(history_raw_text)

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=150)
    docs = text_splitter.split_documents(data)

    for idx, row in enumerate(docs):
        metadata = row.metadata
        if not metadata:
            title = re.search(r'\ntitle: (.*?)\n', row.page_content).group(1)
            if title:
                metadata = {"Header 1":title}
            else:
                metadata = {"Header 1":"None"}
    
        row_number = str(idx)
            
        row_description=create_description(metadata)
        valid_keyword = make_valid_collection_name(row_description)


        print("Row:", row_number, "Title:", row_description, "Index:", valid_keyword)

        # print("Page Content:",chunk.page_content,"\n")
        # print("Character Count:",len(str(chunk)),"\n")
        # print("Token Count:",len(str(chunk).split()),"\n")
        # print("Metadata:",str(chunk.metadata),"\n"


        store_text_with_header(chroma_client, row_description, metadata, row_number)
        section_collection = chroma_client.get_or_create_collection(name=valid_keyword)
        section_collection.add(documents=[row.page_content], ids=str(idx))


    #bdf
    # doug_categories = load_csv_into_iterable_map(csv_location)

    # for idx, row in enumerate(doug_categories):
    #     row_description = row['Description']
    #     row_metadata = create_header_metadata(row)
    #     store_text_with_header(chroma_client, row_description, row_metadata, str(idx))

    # for keyword, content_list in sections.items():
    #     valid_keyword = make_valid_collection_name(keyword)
    #     section_collection = chroma_client.get_or_create_collection(name=valid_keyword)
    #     for i, content in enumerate(content_list):
    #         section_collection.add(documents=[content], ids=str(i))


def create_header_metadata(doug_row):

    return {
        "category": getHeader2(doug_row),
    }


def store_text_with_header(chroma_client, text, header_metadata, doc_id):
    category_collection = chroma_client.get_or_create_collection(name="categories")

    descriptions = [text]
    header_metadatas = [header_metadata]
    doc_ids = [doc_id]

    chroma_id = category_collection.add(documents=descriptions, metadatas=header_metadatas, ids=doc_ids)

    return chroma_id


def find_most_similar(input_string, string_list):
    result = generate.choice(model=model, choices=string_list)(
        f"Which one of these items is most relevant to this question: {input_string}")
    print(result)
    return result


def query_with_doug(chroma_client, text, generative=False):
    global model
    category = ""

    # Use a generative model like Synthia-7b
    if generative:
        if model is None:
            model = models.transformers("TheBloke/SynthIA-7B-v2.0-GPTQ", device="cuda:0")

        doug_categories = load_csv_into_iterable_map("metadata/dougs_guide_categories.csv")
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
