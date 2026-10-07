def bubble_sort(arr):

    result = list(arr)
    n = len(result)
    for i in range(n):
        swapped = False
        for j in range(n - 1 - i):
            if result[j] > result[j + 1]:
                result[j], result[j + 1] = result[j + 1], result[j]
                swapped = True
        if not swapped:
            break
    return result

def selection_sort(arr):

    result = list(arr)
    n = len(result)
    for i in range(n):
        min_idx = i
        for j in range(i + 1, n):
            if result[j] < result[min_idx]:
                min_idx = j
        result[i], result[min_idx] = result[min_idx], result[i]
    return result

def insertion_sort(arr):

    result = list(arr)
    for i in range(1, len(result)):
        key = result[i]
        j = i - 1
        while j >= 0 and result[j] > key:
            result[j + 1] = result[j]
            j -= 1
        result[j + 1] = key
    return result

def merge_sort(arr):

    if len(arr) <= 1:
        return list(arr)

    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])

    result = []
    i = j = 0

    # Merge the two sorted halves
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1

    # Add the remaining elements
    result.extend(left[i:])
    result.extend(right[j:])

    return result

def quick_sort(arr):

    if len(arr) <= 1:
        return list(arr)

    pivot = arr[len(arr) // 2]

    # Partition the values around the pivot
    smaller = [value for value in arr if value < pivot]
    equal = [value for value in arr if value == pivot]
    larger = [value for value in arr if value > pivot]

    return quick_sort(smaller) + equal + quick_sort(larger)

def heap_sort(arr):

    result = list(arr)
    n = len(result)

    # Build the max-heap (elements from the middle down are leaves)
    for i in range(n // 2 - 1, -1, -1):
        _heapify(result, n, i)

    # Extract the maximum one by one, moving it to the end of the list
    for end in range(n - 1, 0, -1):
        result[0], result[end] = result[end], result[0]
        _heapify(result, end, 0)

    return result

def _heapify(arr, n, i):

    largest = i
    left = 2 * i + 1
    right = 2 * i + 2

    if left < n and arr[left] > arr[largest]:
        largest = left

    if right < n and arr[right] > arr[largest]:
        largest = right

    if largest != i:
        arr[i], arr[largest] = arr[largest], arr[i]
        _heapify(arr, n, largest)

def counting_sort(arr):

    if not arr:
        return []

    if any(x < 0 for x in arr):
        raise ValueError("Counting Sort requires non-negative integers")

    max_value = max(arr)

    # Count the occurrences of each value
    counts = [0] * (max_value + 1)
    for value in arr:
        counts[value] += 1

    # Reconstruct the sorted list from the counts
    result = []
    for value in range(max_value + 1):
        result.extend([value] * counts[value])

    return result

def radix_sort(arr):

    if not arr:
        return []

    if any(x < 0 for x in arr):
        raise ValueError("Radix Sort requires non-negative integers")

    result = list(arr)
    max_value = max(result)

    # Sort digit by digit, from least significant to most significant
    digit = 1
    while max_value // digit > 0:
        buckets = [[] for _ in range(10)]
        for value in result:
            bucket_index = (value // digit) % 10
            buckets[bucket_index].append(value)
        result = [value for bucket in buckets for value in bucket]
        digit *= 10

    return result

def bucket_sort(arr):

    if not arr:
        return []

    if len(arr) == 1:
        return list(arr)

    min_value = min(arr)
    max_value = max(arr)

    # If all values are equal there is nothing to sort
    if min_value == max_value:
        return list(arr)

    n = len(arr)
    buckets = [[] for _ in range(n)]

    # Distribute each value into a bucket according to its range position
    for value in arr:
        bucket_index = int((value - min_value) / (max_value - min_value) * n)
        bucket_index = min(n - 1, bucket_index)
        buckets[bucket_index].append(value)

    # Sort each bucket and concatenate the results
    result = []
    for bucket in buckets:
        result.extend(insertion_sort(bucket))

    return result

def _all_numbers(values):
    return all(isinstance(value, (int, float)) for value in values)


def _all_non_negative_integers(values):
    return all(isinstance(value, int) and value >= 0 for value in values)


class SortingAlgorithm:
    """Common interface used by the CLI to work with any algorithm.

    `sort` returns a new list without mutating its input. `can_sort` tells,
    before sorting, whether the algorithm can handle the given values.
    """

    key = ""
    name = ""
    requirement = "values of a single comparable type (all numbers or all text)"

    def sort(self, values):
        raise NotImplementedError

    def can_sort(self, values):
        return _all_numbers(values) or all(isinstance(value, str) for value in values)


class BubbleSort(SortingAlgorithm):

    key = "bubble"
    name = "Bubble Sort"
    sort = staticmethod(bubble_sort)


class SelectionSort(SortingAlgorithm):

    key = "selection"
    name = "Selection Sort"
    sort = staticmethod(selection_sort)


class InsertionSort(SortingAlgorithm):

    key = "insertion"
    name = "Insertion Sort"
    sort = staticmethod(insertion_sort)


class MergeSort(SortingAlgorithm):

    key = "merge"
    name = "Merge Sort"
    sort = staticmethod(merge_sort)


class QuickSort(SortingAlgorithm):

    key = "quick"
    name = "Quick Sort"
    sort = staticmethod(quick_sort)


class HeapSort(SortingAlgorithm):

    key = "heap"
    name = "Heap Sort"
    sort = staticmethod(heap_sort)


class CountingSort(SortingAlgorithm):

    key = "counting"
    name = "Counting Sort"
    requirement = "non-negative integer values"
    sort = staticmethod(counting_sort)

    def can_sort(self, values):
        return _all_non_negative_integers(values)


class RadixSort(SortingAlgorithm):

    key = "radix"
    name = "Radix Sort"
    requirement = "non-negative integer values"
    sort = staticmethod(radix_sort)

    def can_sort(self, values):
        return _all_non_negative_integers(values)


class BucketSort(SortingAlgorithm):

    key = "bucket"
    name = "Bucket Sort"
    requirement = "numeric values"
    sort = staticmethod(bucket_sort)

    def can_sort(self, values):
        return _all_numbers(values)


# Single registry of the available algorithms (order = CLI menu order)
ALGORITHMS = {
    algorithm.key: algorithm
    for algorithm in (
        BubbleSort(),
        SelectionSort(),
        InsertionSort(),
        MergeSort(),
        QuickSort(),
        HeapSort(),
        CountingSort(),
        RadixSort(),
        BucketSort(),
    )
}
