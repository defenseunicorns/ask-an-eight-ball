# Ask an Eight Ball

## 🚀 Mission Need/Business Need

This project provides an easy way to ingest data from Coda and provide that information contextually to an LLM to answer user requests about the company.

### 👥 User Persona

An employee from the company

## 💻 Tech Stack

REST API
- [FastAPI](https://pypi.org/project/fastapi/)
- [uvicorn](https://pypi.org/project/uvicorn/)

Data Storage/Retrieval
- [ChromaDB](https://pypi.org/project/chromadb/)

PDF Document Parsing
- [PyMuPDF](https://pypi.org/project/PyMuPDF/)

LLM Integration
- [transformers](https://pypi.org/project/transformers/)
- [langchain](https://pypi.org/project/langchain/)
- [outlines](https://pypi.org/project/outlines/)

## ❓ Questions/Hypothesis

- Can we load data into a RAG backend that is useful to answering company specific questions?
- Can we improve the contextual results returned by a vector db to an LLM using external domain knowledge?

## 🌼 Design

### Features included in the prototype

- Coda pdf loader for ingesting, parsing, and processing the text for an LLM based on coda's html formatting
- Loading a csv file with categories and breaking the coda pdf down into subsections based on those categories
- Creating collections in chromadb for each category and loading all the individual pages under that category into the collection
- Retrieval mechanism that takes a user query and selects a matching category based on the query to narrow down the documents being returned to a single collection
- Category selection via simple embedding based similarity search or via llm guided by guardrails (outlines)
- REST API for performing RAG from an LLM

## 🛸 Future Work

- Integrating directly with the [coda API](https://coda.io/developers/apis/v1#section/Using-the-API/API-Endpoint) to scrape information
- Updating the existing Python [codaio library](https://github.com/Blasterai/codaio) to match the current API
- Benchmarking results between the llm guided category selection and embedding based selection
- Detecting and performing automatic updates when coda file changes
- Add a more detailed selection mechanism
- Modify user query to get better results returned
- Return confidence (similarity) information to LLM to determine when to respond with "I don't know"
- Parse and return coda page POCs for information that can be referenced when confidence is low
- [Utilize Reranking](https://gpt-index.readthedocs.io/en/latest/examples/node_postprocessor/LLMReranker-Gatsby.html)
- Switch all APIs to use langchain and use more advanced langchain features
- Avoid attempting to reload information that already exists into chromadb

## 🧑‍💻 Developing

### Requirements

This repo cannot be run without specifying the `metadata/dougs_guide_categories.csv` and `preload/Doug_Guide_to_the_Galaxy.pdf` files.

The `pdf` file can be obtained from coda:

![coda_menu.png](static%2Fcoda_menu.png)

The `csv` file is in the following format:

`Category,Description`

With entries for each high level category that the document needs to be broken down into. These categories correspond to the largest font size in the pdf.

### Running

```bash
python -m venv venv

source venv/bin/activate

pip install -r requirements.txt

python main.py
```

Once the pdf is fully loaded you can test the application with:

```bash
curl --header "Content-Type: application/json" -d '{"input":"Tell me about Defense Unicorns core values","collection_name":"default"}' localhost:8002/query/
```

### Building (Docker)

```bash
docker build -t defenseunicorns/ask-an-eight-ball .
docker run -rm -d -p 8002:8002 --name ask-an-eight-ball defenseunicorns/ask-an-eight-ball
```