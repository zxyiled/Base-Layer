import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from api import get_data
from sorting_methods import (
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

METHODS = {
    "bubble": bubble_sort,
    "selection": selection_sort,
    "insertion": insertion_sort,
    "merge": merge_sort,
    "quick": quick_sort,
    "heap": heap_sort,
    "counting": counting_sort,
    "radix": radix_sort,
    "bucket": bucket_sort,
}


def is_numeric(value):
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def ask_method():
    print("\nAvailable sorting methods:")
    for name in METHODS:
        print(f"  - {name}")
    while True:
        choice = input("Which sorting method would you like to use? ").strip().lower()
        if choice in METHODS:
            return METHODS[choice]
        print(f"Invalid method '{choice}'. Please choose one from the list.")


def ask_field(data):
    if not isinstance(data, list) or not data:
        raise ValueError("The dataset is empty or has an unexpected format.")

    if isinstance(data[0], dict):
        fields = [key for key in data[0] if is_numeric(data[0][key])]
        if not fields:
            raise ValueError("No numeric fields were found in the dataset.")
        print(f"\nAvailable numeric fields: {', '.join(fields)}")
        while True:
            field = input("Which numeric field would you like to sort? ").strip()
            if field in fields:
                values = [float(record[field]) for record in data if is_numeric(record.get(field))]
                return field, values
            print(f"Field '{field}' is not valid.")
    elif is_numeric(data[0]):
        return None, [float(value) for value in data if is_numeric(value)]
    else:
        raise ValueError("The dataset format is not supported.")


def print_sorted(values, field, sort_func):
    original = list(values)
    try:
        sorted_values = sort_func(values)
    except (TypeError, ValueError) as e:
        print(f"\nCannot sort with {sort_func.__name__}: {e}")
        return

    print("\n" + "=" * 40)
    if field:
        print(f"Field sorted: {field}")
    print(f"Method: {sort_func.__name__}")
    print("=" * 40)
    print("Original:")
    for value in original:
        print(f"  {value}")
    print("Sorted:")
    for value in sorted_values:
        print(f"  {value}")


def main():
    print("Fetching dataset from the API...")
    data = get_data()
    if data is None:
        print("Could not retrieve data.")
        return

    field, values = ask_field(data)
    sort_func = ask_method()
    print_sorted(values, field, sort_func)


if __name__ == "__main__":
    main()