import sys

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from document_store import DocumentStore

debugIt = False

app = FastAPI()

doc_store = DocumentStore()
doc_store.load_doug_date()

origins = [
    "http://localhost",
    "http://localhost:3002",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryModel(BaseModel):
    input: str
    collection_name: str


@app.post("/query/")
def query(query_data: QueryModel):
    debug("Query received")
    outside_context = doc_store.query_with_doug(query_data.input)
    debug("The returned context is: " + outside_context)
    return {"results": outside_context}


@app.get("/health/", status_code=200)
def health():
    return {}


def debug(message):
    if debugIt:
        print(message)


if __name__ == '__main__':
    args = sys.argv[1:]

    if len(args) > 0 and args[0] == "debug":
        debug = True

    uvicorn.run("main:app", host="0.0.0.0", port=8002,
                reload=False, log_level="debug")
