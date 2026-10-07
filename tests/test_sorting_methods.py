import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from api import get_data  # noqa: E402
from sorting_methods import (  # noqa: E402
    ALGORITHMS,
    bubble_sort,
    bucket_sort,
    counting_sort,
    heap_sort,
    insertion_sort,
    merge_sort,
    quick_sort,
    radix_sort,
    selection_sort,
)


class SortAlgorithmEdgeCasesMixin:
    """Shared edge-case checks for every comparison-based sort."""

    sort_func = None
    repeated_input = [4, 4, 1, 4, 3]
    repeated_expected = [1, 3, 4, 4, 4]

    def test_empty_list(self):
        self.assertEqual(self.sort_func([]), [])

    def test_single_element(self):
        self.assertEqual(self.sort_func([5]), [5])

    def test_small_list(self):
        self.assertEqual(self.sort_func([3, 1, 2]), [1, 2, 3])

    def test_repeated_elements(self):
        self.assertEqual(self.sort_func(self.repeated_input), self.repeated_expected)

    def test_negative_values(self):
        self.assertEqual(self.sort_func([-5, 0, -1, 3]), [-5, -1, 0, 3])

    def test_does_not_mutate_input(self):
        original = [3, 1, 2]
        result = self.sort_func(original)
        self.assertEqual(original, [3, 1, 2])
        self.assertEqual(result, [1, 2, 3])


class TestBubbleSort(SortAlgorithmEdgeCasesMixin, unittest.TestCase):

    sort_func = staticmethod(bubble_sort)


class TestSelectionSort(SortAlgorithmEdgeCasesMixin, unittest.TestCase):

    sort_func = staticmethod(selection_sort)


class TestInsertionSort(SortAlgorithmEdgeCasesMixin, unittest.TestCase):

    sort_func = staticmethod(insertion_sort)


class TestMergeSort(SortAlgorithmEdgeCasesMixin, unittest.TestCase):

    sort_func = staticmethod(merge_sort)


class TestQuickSort(SortAlgorithmEdgeCasesMixin, unittest.TestCase):

    sort_func = staticmethod(quick_sort)


class TestHeapSort(SortAlgorithmEdgeCasesMixin, unittest.TestCase):

    sort_func = staticmethod(heap_sort)


class TestBucketSort(SortAlgorithmEdgeCasesMixin, unittest.TestCase):

    sort_func = staticmethod(bucket_sort)


class TestCountingSortEdgeCases(unittest.TestCase):

    def test_empty_list(self):
        self.assertEqual(counting_sort([]), [])

    def test_single_element(self):
        self.assertEqual(counting_sort([5]), [5])

    def test_small_list(self):
        self.assertEqual(counting_sort([3, 1, 2]), [1, 2, 3])

    def test_repeated_elements(self):
        self.assertEqual(counting_sort([4, 4, 1, 4, 3]), [1, 3, 4, 4, 4])

    def test_zero_and_positive_values(self):
        self.assertEqual(counting_sort([0, 2, 0]), [0, 0, 2])

    def test_negative_values_raise(self):
        with self.assertRaises(ValueError):
            counting_sort([-5, 0, -1, 3])

    def test_non_integer_values_raise(self):
        with self.assertRaises(TypeError):
            counting_sort([1.5, 2, 3])


class TestRadixSortEdgeCases(unittest.TestCase):

    def test_empty_list(self):
        self.assertEqual(radix_sort([]), [])

    def test_single_element(self):
        self.assertEqual(radix_sort([5]), [5])

    def test_small_list(self):
        self.assertEqual(radix_sort([3, 1, 2]), [1, 2, 3])

    def test_repeated_elements(self):
        self.assertEqual(radix_sort([4, 4, 1, 4, 3]), [1, 3, 4, 4, 4])

    def test_zero_and_positive_values(self):
        self.assertEqual(radix_sort([0, 2, 0]), [0, 0, 2])

    def test_negative_values_raise(self):
        with self.assertRaises(ValueError):
            radix_sort([-5, 0, -1, 3])

    def test_non_integer_values_raise(self):
        with self.assertRaises(TypeError):
            radix_sort([1.5, 2, 3])


class TestAlgorithmClasses(unittest.TestCase):
    """Check the class interface the CLI uses on top of the sort functions."""

    def test_registry_keeps_menu_order(self):
        self.assertEqual(
            list(ALGORITHMS),
            ["bubble", "selection", "insertion", "merge", "quick", "heap", "counting", "radix", "bucket"],
        )

    def test_sort_does_not_mutate_input(self):
        for key, algorithm in ALGORITHMS.items():
            with self.subTest(algorithm=key):
                original = [3, 1, 2]
                self.assertEqual(algorithm.sort(original), [1, 2, 3])
                self.assertEqual(original, [3, 1, 2])

    def test_comparison_sorts_accept_numbers_and_text(self):
        for key in ["bubble", "selection", "insertion", "merge", "quick", "heap"]:
            with self.subTest(algorithm=key):
                self.assertTrue(ALGORITHMS[key].can_sort([-1.5, 2, 0]))
                self.assertTrue(ALGORITHMS[key].can_sort(["b", "a"]))
                self.assertFalse(ALGORITHMS[key].can_sort(["b", 1]))

    def test_bucket_sort_requires_numbers(self):
        self.assertTrue(ALGORITHMS["bucket"].can_sort([-1.5, 2, 0]))
        self.assertFalse(ALGORITHMS["bucket"].can_sort(["b", "a"]))

    def test_counting_and_radix_require_non_negative_integers(self):
        for key in ["counting", "radix"]:
            with self.subTest(algorithm=key):
                self.assertTrue(ALGORITHMS[key].can_sort([0, 3, 1]))
                self.assertFalse(ALGORITHMS[key].can_sort([-5, 0, 3]))
                self.assertFalse(ALGORITHMS[key].can_sort([1.5, 2, 3]))
                self.assertFalse(ALGORITHMS[key].can_sort(["a"]))

    def test_can_sort_matches_actual_failures(self):
        # Every combination declared incompatible must really fail when sorted
        samples = [[-5, 0, 3], [1.5, 2.0, 0.5], ["b", "a"]]
        for key, algorithm in ALGORITHMS.items():
            for values in samples:
                with self.subTest(algorithm=key, values=values):
                    if algorithm.can_sort(values):
                        self.assertEqual(algorithm.sort(values), sorted(values))
                    else:
                        with self.assertRaises((TypeError, ValueError)):
                            algorithm.sort(values)


class TestAlgorithmsAgreeOnDataset(unittest.TestCase):
    """Check the algorithms against the real dataset from api.py."""

    ALL_ALGORITHMS = [
        bubble_sort,
        selection_sort,
        insertion_sort,
        merge_sort,
        quick_sort,
        heap_sort,
        counting_sort,
        radix_sort,
        bucket_sort,
    ]

    RECORDS_ALGORITHMS = [
        bubble_sort,
        selection_sort,
        insertion_sort,
        merge_sort,
        quick_sort,
        heap_sort,
    ]

    DECIMAL_ALGORITHMS = [
        bubble_sort,
        selection_sort,
        insertion_sort,
        merge_sort,
        quick_sort,
        heap_sort,
        bucket_sort,
    ]

    @classmethod
    def setUpClass(cls):
        cls.records = get_data()

    def _skip_if_offline(self):
        if self.records is None:
            self.skipTest("The dataset could not be downloaded (API unavailable)")

    def test_all_algorithms_sort_years_like_reference(self):
        self._skip_if_offline()
        years = [int(r["ano"]) for r in self.records]
        reference = sorted(years)
        for algorithm in self.ALL_ALGORITHMS:
            with self.subTest(algorithm=algorithm.__name__):
                self.assertEqual(algorithm(years), reference)

    def test_comparison_algorithms_agree_on_decimal_generation(self):
        self._skip_if_offline()
        values = [float(r["generacion_total_gwh"]) for r in self.records]
        reference = sorted(values)
        for algorithm in self.DECIMAL_ALGORITHMS:
            with self.subTest(algorithm=algorithm.__name__):
                self.assertEqual(algorithm(values), reference)

    def test_comparison_algorithms_sort_records_by_year(self):
        self._skip_if_offline()
        items = [(int(r["ano"]), i, r) for i, r in enumerate(self.records)]
        expected_years = sorted(item[0] for item in items)
        for algorithm in self.RECORDS_ALGORITHMS:
            with self.subTest(algorithm=algorithm.__name__):
                sorted_items = algorithm(items)
                self.assertEqual([item[0] for item in sorted_items], expected_years)
                self.assertEqual(len(sorted_items), len(self.records))

    def test_dataset_has_repeated_and_in_range_years(self):
        self._skip_if_offline()
        years = [int(r["ano"]) for r in self.records]
        self.assertGreater(len(years), len(set(years)))
        self.assertLessEqual(min(years), max(years))


if __name__ == "__main__":
    unittest.main()
