import asyncio
import time

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

async def start_export(session, doc_id, page_id_or_name, api_token):
    """Starts the export process asynchronously and returns the request ID."""
    url = f"https://coda.io/apis/v1/docs/{doc_id}/pages/{page_id_or_name}/export"
    headers = {"Authorization": f"Bearer {api_token}"}
    payload = {"outputFormat": "markdown"}
    
    async with session.post(url, json=payload, headers=headers) as response:
        resp_json = await response.json()
        if response.status == 200:
            return resp_json.get("id")
        else:
            print(f"Error starting export for {doc_id}: {resp_json}")
            return None

async def poll_export_status(session, doc_id, page_id_or_name, request_id, api_token):
    """Polls the export status asynchronously until it's 'complete'."""
    url = f"https://coda.io/apis/v1/docs/{doc_id}/pages/{page_id_or_name}/export/{request_id}"
    headers = {"Authorization": f"Bearer {api_token}"}
    
    while True:
        async with session.get(url, headers=headers) as response:
            resp_json = await response.json()
            if response.status == 200 and resp_json.get("status") == "complete":
                return resp_json.get("downloadLink")
            elif "error" in resp_json:
                print(f"Error during export for {doc_id}: {resp_json.get('error')}")
                return None
        await asyncio.sleep(5)  # Polling interval

async def download_exported_file(session, download_link):
    """Downloads the exported file content asynchronously."""
    async with session.get(download_link) as response:
        if response.status == 200:
            return await response.text()  # Or response.read() if binary
        else:
            print(f"Error downloading file from {download_link}")
            return None

async def export_coda(api_token):
    documents = list_all_documents(api_token)
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for doc in documents:
            # Start export and add to tasks
            tasks.append(handle_document_export(session, doc, api_token))
            
            # Respect rate limit: No more than 10 requests every 6 seconds
            if len(tasks) >= 10:
                await asyncio.sleep(6)  # Pause to respect rate limit
                tasks.clear()  # Reset tasks after pause
            
        results = await asyncio.gather(*tasks)
        return results

async def handle_document_export(session, doc, api_token):
    """Handles the full export process for a single document."""
    request_id = await start_export(session, doc['id'], doc['name'], api_token)
    if request_id:
        download_link = await poll_export_status(session, doc['id'], doc['name'], request_id, api_token)
        if download_link:
            content = await download_exported_file(session, download_link)
            return content

# Example usage
# documents = [
#     {'id': 'doc1', 'name': 'Page1'},
#     {'id': 'doc2', 'name': 'Page2'},
#     # Add more documents as needed
# ]
# api_token = "YOUR_API_TOKEN"

# async def main():
#     results = await export_coda(documents, api_token)
#     for result in results:
#         print(result)

# if __name__ == "__main__":
#     asyncio.run(main())
