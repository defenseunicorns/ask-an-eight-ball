import unittest

import chromadb

from coda_ingester import extract_sections
from doug_loader import load_doug_data, query_with_doug, load_csv_into_iterable_map


class DougsGuide(unittest.TestCase):
    def test_csv_load(self):
        self.client = chromadb.PersistentClient(path="db")
        self.collection = self.client.get_or_create_collection(name="default")
        load_doug_data(self.client, "../metadata/dougs_guide_categories.csv", "../preload/Doug_Guide_to_the_Galaxy.pdf")
        collection = self.client.get_collection(name="categories")
        data = collection.get(ids=["1"])
        self.assertEqual(data['documents'][0], "The Vision & Mission section outlines Defense Unicorns' vision and "
                                            "mission statements.")
        self.assertEqual(data['metadatas'][0]['category'], "Vision & Mission")

    def test_query(self):
        self.client = chromadb.PersistentClient(path="db")
        self.collection = self.client.get_or_create_collection(name="default")
        load_doug_data(self.client, "../metadata/dougs_guide_categories.csv", "../preload/Doug_Guide_to_the_Galaxy.pdf")
        data = query_with_doug(self.client, "Tell me about Defense Unicorns core values")
        self.assertTrue(data['documents'][0].contains("What are core values? They are a small set of vital and "
                                                      "timeless guiding principles for your company. A good rule of "
                                                      "thumb is to limit them to somewhere between three and seven. "
                                                      "As always, less is more."))

    def test_extraction(self):
        category_dict_list = load_csv_into_iterable_map("../metadata/dougs_guide_categories.csv")
        categories_list = [d["Category"] for d in category_dict_list]
        sections = extract_sections('../preload/Doug_Guide_to_the_Galaxy.pdf', categories_list)
        self.assertEqual(sections, "")


if __name__ == '__main__':
    unittest.main()
