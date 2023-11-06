import os
import unittest

from coda_ingester import CodaIngester

document_api_key = os.environ.get("CODA_API_KEY")


class CodaTest(unittest.TestCase):
    def test_coda_doc_retrieval(self):
        ingester = CodaIngester()
        doc = ingester.get_document(document_api_key)
        self.assertEqual(doc.name, "Doug's Guide to the Galaxy")  # add assertion here

    def test_coda_sections_list(self):
        ingester = CodaIngester()
        doc = ingester.get_document(document_api_key)
        sections = doc.list_sections()
        self.assertNotEquals(sections, [])


if __name__ == '__main__':
    unittest.main()
