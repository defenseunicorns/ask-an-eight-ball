import unittest

from document_store import DocumentStore


class ChromaServerTests(unittest.TestCase):
    def test_retrieval(self):
        doc_store = DocumentStore()
        doc_store.load_pdf("../preload/")

        result = doc_store.query_langchain("Who is moby dick?")

        print(result)

        self.assertIsNotNone(result)
        self.assertNotEquals(result, [])
        self.assertNotEquals(result, "")


if __name__ == '__main__':
    unittest.main()
