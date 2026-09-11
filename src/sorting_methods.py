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

