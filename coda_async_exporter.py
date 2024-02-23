import asyncio
import time

import aiohttp
import requests

HTTP_TIMEOUT = 10
POLLING_DELAY = 1
RATE_LIMIT_DELAY = 6
RETRY_DELAY = 3


def list_all_documents(api_token):
    """
    Fetches a list of document IDs and names accessible by the user from Coda.

    Returns:
        List of dicts, each representing a document with 'id' and 'name'.
    """

    url = "https://coda.io/apis/v1/docs"
    headers = {"Authorization": f"Bearer {api_token}"}

    try:
        response = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
        response.raise_for_status()  # Raises HTTPError for bad responses

        # Extract document info from the response
        documents = response.json().get('items', [])
        doc_ids = [doc['id'] for doc in documents]
        results = []

        limited_list = doc_ids[:20]  # TODO: Remove limit
        doc_ids = limited_list

        # Iterate over each doc_id
        for doc_id in doc_ids:
            # Retrieve the list of page_ids for the current doc_id
            page_ids = list_all_pages_for_doc(api_token, doc_id)

            # Iterate over each page_id and construct the pair object
            for page_id in page_ids:
                pair = {'doc_id': doc_id, 'page_id': page_id}
                # Append the pair object to the result list
                results.append(pair)

        print(f"Found {len(results)} documents")
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
        response = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
        response.raise_for_status()  # Raises HTTPError for bad responses

        # Extract document info from the response
        pages = response.json().get('items', [])
        page_info = [page['id'] for page in pages]

        print(f"Found {len(pages)} pages for document {doc_id}")

        return page_info
    except requests.RequestException as e:
        print(f"Error fetching pages for docId: {doc_id} from Coda: {e}")
        return []


# async def start_export(session, doc_id, page_id, api_token):
#     """
#     Asynchronously starts the export process for a given document and page.
#     """
#     url = f"https://coda.io/apis/v1/docs/{doc_id}/pages/{page_id}/export"
#     headers = {"Authorization": f"Bearer {api_token}"}
#     payload = {"outputFormat": "markdown"}

#     async with session.post(url, json=payload, headers=headers, timeout=HTTP_TIMEOUT) as response:
#         if response.status == 202:
#             resp_json = await response.json()
#             return resp_json.get("id")
#         else:
#             print(f"Error Exporting doc:{doc_id}, page:{page_id} - {response.status}:{await response.text()}")
#             return None


async def start_export(session, doc_id, page_id, api_token, retries=3):
    """
    Sends an HTTP request and retries on 429 status up to 'retries' times.

    Args:
    - retries (int): Number of retries on 429 status.

    Returns:
    - Response data as JSON or None if request ultimately fails.
    """
    url = f"https://coda.io/apis/v1/docs/{doc_id}/pages/{page_id}/export"
    headers = {"Authorization": f"Bearer {api_token}"}
    payload = {"outputFormat": "markdown"}

    for attempt in range(retries + 1):
        async with session.post(url, json=payload, headers=headers) as response:
            if response.status == 429 and attempt < retries:
                print(
                    f"Rate limit hit, retrying in {RETRY_DELAY} seconds...")
                await asyncio.sleep(RETRY_DELAY)
                continue
            elif response.status == 202:
                return await response.json()  # Successful request
            else:
                print(f"Request failed: {response.status}")
                return None  # Request failed, not retrying further
    # If all retries are exhausted
    print("All retries exhausted")
    return None


async def poll_export_status(session, doc_id, page_id, request_id, api_token):
    """
    Asynchronously polls the export status until it is 'complete'.
    """
    url = f"https://coda.io/apis/v1/docs/{doc_id}/pages/{page_id}/export/{request_id}"
    headers = {"Authorization": f"Bearer {api_token}"}

    while True:
        await asyncio.sleep(RETRY_DELAY)
        async with session.get(url, headers=headers, timeout=HTTP_TIMEOUT) as response:
            if response.status == 200:
                status_data = await response.json()
                print(f"Polling export for doc:{doc_id}, request:{request_id}")
                if status_data.get("status") == "complete":
                    return status_data.get("downloadLink")
                elif "error" in status_data:
                    print(
                        f"Error polling export for doc:{doc_id}, request:{request_id} - {status_data.get('error')}")
                    return None
            else:
                print(f"Error checking status for doc:{doc_id}, request:{request_id} - {response.status}:{await response.text()}")
                return None


async def download_exported_file(session, download_link):
    """
    Asynchronously downloads the exported markdown content from the given download link.
    """
    async with session.get(download_link, timeout=HTTP_TIMEOUT) as response:
        if response.status == 200:
            return await response.text()
        else:
            print(f"Error downloading file from {download_link}: {await response.text()}")
            return None


# async def export_documents_as_markdown(documents, api_token):
#     """
#     Orchestrates the export and download of documents from Coda as markdown asynchronously.
#     """
#     async with aiohttp.ClientSession() as session:
#         tasks = []
#         for doc in documents:
#             task = handle_document_export(session, doc, api_token)
#             tasks.append(task)
#             # Implement rate limiting for up to 10 tasks every 6 seconds here if necessary
#         results = await asyncio.gather(*tasks)
#         return results

async def export_documents_as_markdown(documents, api_token):
    """
    Orchestrates the export and download of documents from Coda as markdown asynchronously,
    running tasks in batches of 5 with a 5-second delay between batches.
    """
    async with aiohttp.ClientSession() as session:
        results = []
        for i in range(0, len(documents), 5):  # Process in batches of 5
            batch = documents[i:i+5]
            tasks = [handle_document_export(
                session, doc, api_token) for doc in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            if i + 5 < len(documents):  # Check if there's a next batch
                # Wait for 5 seconds before the next batch
                await asyncio.sleep(5)
        return results


async def handle_document_export(session, doc, api_token):
    """
    Handles the full export process for a single document asynchronously.
    """
    request_id = await start_export(session, doc['doc_id'], doc['page_id'], api_token)
    if request_id:
        download_link = await poll_export_status(session, doc['doc_id'], doc['page_id'], request_id, api_token)
        if download_link:
            content = await download_exported_file(session, download_link)
            return content


def get_coda_docs(api_token):
    documents = list_all_documents(api_token)
    results = asyncio.run(export_documents_as_markdown(documents, api_token))

    return results
