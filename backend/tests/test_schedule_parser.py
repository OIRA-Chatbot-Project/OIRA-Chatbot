import unittest

from schedule_parser import parse_schedule_entries


class ParseScheduleEntriesTests(unittest.TestCase):
    def test_detects_courses_with_varied_formats(self):
        raw_text = """
        CSCI 204 01  |  Spring 2024  |  Software Engineering
        MATH-205-02 Calculus II (Fall 2023)
        ENGL204A Creative Writing Workshop
        Random text that should be ignored
        """

        entries = parse_schedule_entries(raw_text)
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0]["course_code"], "CSCI 204")
        self.assertEqual(entries[0]["term"], "Spring 2024")
        self.assertEqual(entries[1]["course_code"], "MATH 205")
        self.assertEqual(entries[1]["term"], "Fall 2023")
        self.assertEqual(entries[2]["course_code"], "ENGL 204A")
        self.assertIsNone(entries[2]["term"])

    def test_returns_empty_list_when_no_courses_found(self):
        self.assertEqual(parse_schedule_entries("Lunch with advisor"), [])


if __name__ == "__main__":
    unittest.main()
