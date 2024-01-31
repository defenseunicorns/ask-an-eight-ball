import base64
import csv
import ipaddress
import json
import os
import re

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


def make_valid_collection_name(s):
    # Ensure the string starts and ends with an alphanumeric character
    s = s.strip(".-_")

    # Replace any series of invalid characters with a single underscore
    s = re.sub(r'[^a-zA-Z0-9-_]+', '_', s)
    s = re.sub(r'__+', '_', s)
    s = re.sub(r'\.-|-\.', '-', s)
    s = re.sub(r'\.\.', '.', s)

    # Shorten the string if it's longer than 63 characters or lengthen if it's shorter than 3
    if len(s) > 63:
        s = s[:63]
        s = s.strip(".-_")  # Ensure it still ends with an alphanumeric character
    elif len(s) < 3:
        s += '_' * (3 - len(s))

    # Check if the string is a valid IPv4 address and modify it if necessary
    try:
        ipaddress.IPv4Address(s)
        # If it is a valid IPv4 address, add an underscore at the end to invalidate it
        if len(s) < 63:
            s += '_'
        else:
            s = '_' + s[1:]
    except ipaddress.AddressValueError:
        pass  # It is not a valid IPv4 address, so we're fine

    return s


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


def getHeader2(row):
    try:
        header_2_value = row.metadata.get("Header 2", "None")
    except KeyError:
        header_2_value = "None"
    return header_2_value

def get_files(url, path=''):
   

    response = requests.get(url + path, timeout=5, headers=HEADERS)

    if response.status_code != 200:
        print(f"HTTP error {response.status_code} when accessing {url + path}")
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

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    docs = text_splitter.split_documents(data)

    doug_categories=[]
    for idx, row in enumerate(docs):
        metadata = row.metadata
        # print(f'{idx}  {row.metadata} {row.page_content} ')


        header_2_value = getHeader2(row)
            
            
        row_description=header_2_value
        row_metadata = create_header_metadata(row)
        store_text_with_header(chroma_client, row_description, row_metadata, str(idx))
        valid_keyword = make_valid_collection_name(row_description)
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
    return


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
