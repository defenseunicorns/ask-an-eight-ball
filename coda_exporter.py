import time

import requests

POLLING_DELAY = 1
RATE_LIMIT_DELAY = 1


def list_all_documents(api_token):
    """
    Fetches a list of document IDs and names accessible by the user from Coda.

    Returns:
        List of dicts, each representing a document with 'id' and 'name'.
    """

    url = "https://coda.io/apis/v1/docs"
    headers = {"Authorization": f"Bearer {api_token}"}

    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()  # Raises HTTPError for bad responses

        # Extract document info from the response
        documents = response.json().get('items', [])
        doc_ids = [doc['id'] for doc in documents]
        results = []

        # Iterate over each doc_id
        for doc_id in doc_ids:
            # Retrieve the list of page_ids for the current doc_id
            page_ids = list_all_pages_for_doc(api_token, doc_id)

            # Iterate over each page_id and construct the pair object
            for page_id in page_ids:
                pair = {'doc_id': doc_id, 'page_id': page_id}
                # Append the pair object to the result list
                results.append(pair)

        return results
    except requests.RequestException as e:
        print(f"Error fetching documents from Coda: {e}")
        return []


def list_all_pages_for_doc(api_token, doc_id):
    """
    Fetches a list of document IDs and names accessible by the user from Coda.

    Returns:
        List of dicts, each representing a document with 'id' and 'name'.
    """

    url = f'https://coda.io/apis/v1/docs/{doc_id}/pages'
    headers = {"Authorization": f"Bearer {api_token}"}

    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()  # Raises HTTPError for bad responses

        # Extract document info from the response
        pages = response.json().get('items', [])
        page_info = [page['id'] for page in pages]

        return page_info
    except requests.RequestException as e:
        print(f"Error fetching pages for docId: {doc_id} from Coda: {e}")
        return []


def start_export(doc_id, page_id, api_token):
    """
    Starts the export process for a given document and page.
    """
    url = f"https://coda.io/apis/v1/docs/{doc_id}/pages/{page_id}/export"
    headers = {"Authorization": f"Bearer {api_token}"}
    payload = {"outputFormat": "markdown"}

    response = requests.post(url, json=payload, headers=headers, timeout=5)
    if response.status_code == 202:
        return response.json().get("id")
    else:
        print(
            f"Error Exporting doc:{doc_id}, page:{page_id} -\
                 {response.status_code:}:{response.text}")
        return None


def poll_export_status(doc_id, page_id, request_id, api_token):
    """
    Polls the export status until it is 'complete'.
    """
    url = f"https://coda.io/apis/v1/docs/{doc_id}/pages/{page_id}/export/{request_id}"
    headers = {"Authorization": f"Bearer {api_token}"}

    while True:
        time.sleep(POLLING_DELAY)
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            status_data = response.json()
            print(f"polling export for doc:{doc_id}, request:{request_id}")
            if status_data.get("status") == "complete":
                return status_data.get("downloadLink")
            elif "error" in status_data:
                print(
                    f"Error polling export for doc:{doc_id}, request:{request_id} -\
                         {status_data.get('error')}")
                return None
        else:
            print(
                f"Error checking status for doc:{doc_id}, request:{request_id} - \
                    {response.status_code}:{response.text}")
            return None


def download_exported_file(download_link):
    """
    Downloads the exported markdown content from the given download link.
    """
    response = requests.get(download_link, timeout=5)
    if response.status_code == 200:
        return response.text
    else:
        print(f"Error downloading file from {download_link}: {response.text}")
        return None


def export_documents_as_markdown(documents, api_token):
    """
    Orchestrates the export and download of documents from Coda as markdown.
    """

    results = []

    for doc in documents:
        time.sleep(1)  # Polling interval

        print(f"start_export({doc['doc_id']}, {doc['page_id']}")
        request_id = start_export(doc['doc_id'], doc['page_id'], api_token)
        if request_id:
            download_link = poll_export_status(
                doc['doc_id'], doc['page_id'], request_id, api_token)
            if download_link:
                content = download_exported_file(download_link)
                results.append(content)

    return results


def get_coda_docs(api_token):
    documents = list_all_documents(api_token)
    results = export_documents_as_markdown(documents, api_token)

    print(results)

    return results
