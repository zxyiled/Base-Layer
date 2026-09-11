def bubble_sort(arr):
    """Sort a list with Bubble Sort.

    Repeatedly steps through the list, comparing adjacent
    elements and swapping them when they are out of order.
    Time complexity: O(n^2).
    """
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
    """Sort a list with Selection Sort.

    Repeatedly selects the smallest remaining element and
    places it at the beginning of the unsorted part.
    Time complexity: O(n^2).
    """
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
    """Sort a list with Insertion Sort.

    Builds the sorted list one element at a time, inserting
    each new element into its correct position.
    Time complexity: O(n^2).
    """
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
    """Sort a list with Merge Sort (recursive).

    Splits the list in half, sorts each half recursively,
    and then merges the two sorted halves together.
    Time complexity: O(n log n).
    """
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


def heap_sort(arr):
    """Sort a list with Heap Sort (max-heap).

    Builds a max-heap from the list and then repeatedly moves
    the current maximum to the end of the list.
    Time complexity: O(n log n).
    """
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
    """Restore the max-heap property for the subtree rooted at i."""
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
    """Sort a list of non-negative integers with Counting Sort.

    Counts how many times each value appears and then rebuilds
    the sorted list from those counts. Requires all values >= 0.
    Time complexity: O(n + k), where k is the maximum value.
    """
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
