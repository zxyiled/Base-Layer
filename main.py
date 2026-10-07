import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from api import get_data
from dataset import COLUMNS, column_values, format_table, head, round_values, tail
from sorting_methods import ALGORITHMS

COLUMN_NAMES = list(COLUMNS)

MAX_DECIMALS = 6

PREVIEWS = {
    "head": head,
    "tail": tail,
}


def ask_int(prompt, minimum, maximum):
    while True:
        answer = input(f"{prompt} ({minimum}-{maximum}): ").strip()
        try:
            number = int(answer)
        except ValueError:
            print(f"'{answer}' is not a whole number.")
            continue
        if minimum <= number <= maximum:
            return number
        print(f"Please enter a number between {minimum} and {maximum}.")


def ask_option(prompt, options):
    """Ask the user to pick one of `options`, by its name or its number."""
    for number, option in enumerate(options, start=1):
        print(f"  {number}. {option}")
    while True:
        answer = input(f"{prompt} ").strip().lower()
        if answer in options:
            return answer
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1]
        print(f"Invalid option '{answer}'. Please choose one from the list.")


def ask_rows(records):
    print("\nRows to use:")
    mode = ask_option("Take the first rows (head) or the last rows (tail)?", list(PREVIEWS))
    count = ask_int("How many rows?", 1, len(records))
    return PREVIEWS[mode](records, count)


def ask_rounding(values):
    print("\nRound the values before sorting?")
    if ask_option("Choose an option:", ["no", "yes"]) == "no":
        return values
    decimals = ask_int("How many decimals? (0 converts them to integers)", 0, MAX_DECIMALS)
    return round_values(values, decimals)


def preview(records):
    print(f"\nAvailable columns: {', '.join(COLUMN_NAMES)}")
    count = ask_int("How many columns would you like to display?", 1, len(COLUMN_NAMES))
    rows = ask_rows(records)

    print()
    print(format_table(rows, COLUMN_NAMES[:count]))


def print_sorted(values, column, algorithm):
    sorted_values = algorithm.sort(values)

    print("\n" + "=" * 40)
    print(f"Column sorted: {column}")
    print(f"Method: {algorithm.name}")
    print("=" * 40)
    print("Original:")
    for value in values:
        print(f"  {value}")
    print("Sorted:")
    for value in sorted_values:
        print(f"  {value}")


def sort_column(records):
    print("\nAvailable columns:")
    column = ask_option("Which column would you like to sort?", COLUMN_NAMES)
    values = column_values(ask_rows(records), column)
    if COLUMNS[column] is float:
        values = ask_rounding(values)

    print("\nAvailable sorting methods:")
    algorithm = ALGORITHMS[ask_option("Which sorting method would you like to use?", list(ALGORITHMS))]

    if not algorithm.can_sort(values):
        print(f"\n{algorithm.name} cannot be applied to column '{column}'.")
        print(f"This algorithm requires {algorithm.requirement}.")
        print("Please select another column or algorithm.")
        return

    print_sorted(values, column, algorithm)


ACTIONS = {
    "preview": preview,
    "sort": sort_column,
    "exit": None,
}


def main():
    print("Fetching dataset from the API...")
    records = get_data()
    if records is None:
        print("Could not retrieve data.")
        return
    if not isinstance(records, list) or not records:
        print("The dataset is empty or has an unexpected format.")
        return

    while True:
        print("\nWhat would you like to do?")
        action = ask_option("Choose an option:", list(ACTIONS))
        if action == "exit":
            print("Goodbye.")
            return
        ACTIONS[action](records)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye.")
