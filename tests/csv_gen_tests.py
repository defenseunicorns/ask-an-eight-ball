import unittest
from gen_csv import generate_csv
from doug_loader import load_csv_into_iterable_map


class CSVTest(unittest.TestCase):
    def test_generating_csv(self):
        generate_csv("tests/test_pdf/doug_guide_to_galaxy_mini.pdf","tests/dougs_guide_categories.csv")
        csv_map = load_csv_into_iterable_map("tests/dougs_guide_categories.csv")
        headings = []
        for row in enumerate(csv_map):
            headings.append(row['Category'])

        self.assertEqual(headings, ['Defense Unicorns', 'Handbook Introduction', 'Goal'])

if __name__ == '__main__':
    unittest.main()
