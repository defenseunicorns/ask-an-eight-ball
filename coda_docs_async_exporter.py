import asyncio
import os

import aiohttp
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

def export_pages_as_markdown(documents, api_token):
    """
    Exports specified pages from a list of Coda documents as markdown.

    Parameters:
    - doc_page_pairs (list of tuples): Each tuple contains `doc_id` and `page_id_or_name`.
    - api_token (str): The API token for Coda authentication.

    Returns:
    - list of dicts: Each dict contains 'doc_id', 'page_id_or_name', and 'markdown' content or an error message.
    """
    exports = []
    for doc in documents:
        doc_id = doc['id']
        doc_name = doc.get('name', 'Unnamed Document')
        url = f"https://coda.io/apis/v1/docs/{doc_id}/pages/{doc_name}/export"
        headers = {"Authorization": f"Bearer {api_token}"}
        payload = {"outputFormat": "markdown"}

        response = requests.post(url, json=payload, headers=headers)
        if response.status_code > 299:
            exports.append({"doc_id": doc_id, "doc_name": doc_name, "error": f"Failed to export page as markdown. Status code: {response.status_code}"})
        else :
            exports.append({"doc_id": doc_id, "doc_name": doc_name, "markdown": response.text})

    
    return exports


async def export_document(session, doc_id, page_id_or_name, api_token):
    start_url = f"https://coda.io/apis/v1/docs/{doc_id}/pages/{page_id_or_name}/export"
    headers = {"Authorization": f"Bearer {api_token}"}
    payload = {"outputFormat": "markdown"}

    # Start the export process
    async with session.post(start_url, json=payload, headers=headers) as response:
        if response.status == 202:
            start_data = await response.json()
            request_id = start_data.get("id")
            return await poll_for_completion(session, doc_id, page_id_or_name, request_id, headers)
        else:
            return {"error": "Failed to start export"}

async def poll_for_completion(session, doc_id, page_id_or_name, request_id, headers):
    status_url = f"https://coda.io/apis/v1/docs/{doc_id}/pages/{page_id_or_name}/export/{request_id}"
    
    while True:
        async with session.get(status_url, headers=headers) as status_response:
            if status_response.status == 200:
                status_data = await status_response.json()
                if status_data.get("status") == "complete":
                    return await download_exported_file(session, status_data.get("downloadLink"))
                elif "error" in status_data:
                    return {"error": status_data.get("error")}
            else:
                await asyncio.sleep(5)  # Polling interval

async def download_exported_file(session, download_link):
    async with session.get(download_link) as download_response:
        if download_response.status == 200:
            # Assuming you want to return the content directly; adjust as needed
            content = await download_response.text()
            return {"content": content}
        else:
            return {"error": "Failed to download exported file"}

async def export_documents_as_markdown(documents, api_token):
    async with aiohttp.ClientSession() as session:
        tasks = [export_document(session, doc['id'], doc['name'], api_token) for doc in documents]
        return await asyncio.gather(*tasks)

def get_coda_docs(api_token):
    documents = list_all_documents(api_token)
    results = asyncio.run(export_documents_as_markdown(documents, api_token))

    return results
