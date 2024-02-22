import time

import requests


def list_all_documents(api_token):
    """
    Fetches a list of document IDs and names accessible by the user from Coda.

    Returns:
        List of dicts, each representing a document with 'id' and 'name'.
    """

    url = "https://coda.io/apis/v1/docs"
    headers = {"Authorization": f"Bearer {api_token}"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raises HTTPError for bad responses
        
        # Extract document info from the response
        documents = response.json().get('items', [])
        document_info = [{'id': doc['id'], 'name': doc['name']} for doc in documents]
        
        return document_info
    except requests.RequestException as e:
        print(f"Error fetching documents from Coda: {e}")
        return []
        

def start_export(doc_id, name, api_token):
    """
    Starts the export process for a given document and page.
    """
    url = f"https://coda.io/apis/v1/docs/{doc_id}/pages/{name}/export"
    headers = {"Authorization": f"Bearer {api_token}"}
    payload = {"outputFormat": "markdown"}
    
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json().get("id")  # Return the markdown.id
    else:
        print(f"Error starting export for doc {doc_id}, page {name}: {response.text}")
        return None

def poll_export_status(doc_id, name, request_id, api_token):
    """
    Polls the export status until it is 'complete'.
    """
    url = f"https://coda.io/apis/v1/docs/{doc_id}/pages/{name}/export/{request_id}"
    headers = {"Authorization": f"Bearer {api_token}"}
    
    while True:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            status_data = response.json()
            if status_data.get("status") == "complete":
                return status_data.get("downloadLink")
            elif "error" in status_data:
                print(f"Error during export for doc {doc_id}, request {request_id}: {status_data.get('error')}")
                return None
        else:
            print(f"Error checking status for doc {doc_id}, request {request_id}: {response.text}")
            return None
        time.sleep(5)  # Polling interval

def download_exported_file(download_link):
    """
    Downloads the exported markdown content from the given download link.
    """
    response = requests.get(download_link)
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

        request_id = start_export(doc['id'], doc.get('name', 'defaultPage'), api_token)  # Adjusted from 'pageIdOrName' to 'name'
        if request_id:
            download_link = poll_export_status(doc['id'], doc.get('name', 'defaultPage'), request_id, api_token)  # Adjusted from 'pageIdOrName' to 'name'
            if download_link:
                content = download_exported_file(download_link)
                results.append(content)
    
    return results

def get_coda_docs(api_token):
    documents = list_all_documents(api_token)
    results = export_documents_as_markdown(documents, api_token)

    print(results)

    return results



