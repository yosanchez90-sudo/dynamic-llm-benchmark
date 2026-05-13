"""A tiny hand-crafted coding dataset for pipeline testing.

Three problems with clear pass/fail tests. Used to verify the eval
pipeline works end-to-end before scaling to real benchmarks (HumanEval, MBPP).
"""
from dataclasses import dataclass


@dataclass
class CodingProblem:
    problem_id: str
    prompt: str       # what to send to the model
    test_code: str    # Python that exercises the generated function


PROBLEMS: list[CodingProblem] = [
    CodingProblem(
        problem_id="is_prime",
        prompt=(
            "Write a Python function `is_prime(n: int) -> bool` that "
            "returns True if n is a prime number, False otherwise. "
            "Return only the function, no example usage."
        ),
        test_code=(
            "assert is_prime(2) == True\n"
            "assert is_prime(3) == True\n"
            "assert is_prime(4) == False\n"
            "assert is_prime(17) == True\n"
            "assert is_prime(1) == False\n"
            "assert is_prime(0) == False\n"
            "assert is_prime(-5) == False\n"
        ),
    ),
    CodingProblem(
        problem_id="reverse_string",
        prompt=(
            "Write a Python function `reverse_string(s: str) -> str` that "
            "returns the reverse of the input string. "
            "Return only the function, no example usage."
        ),
        test_code=(
            "assert reverse_string('hello') == 'olleh'\n"
            "assert reverse_string('') == ''\n"
            "assert reverse_string('a') == 'a'\n"
            "assert reverse_string('ab') == 'ba'\n"
        ),
    ),
    CodingProblem(
        problem_id="sum_list",
        prompt=(
            "Write a Python function `sum_list(nums: list[int]) -> int` "
            "that returns the sum of all integers in the list. "
            "An empty list returns 0. Return only the function."
        ),
        test_code=(
            "assert sum_list([1, 2, 3]) == 6\n"
            "assert sum_list([]) == 0\n"
            "assert sum_list([-1, 1]) == 0\n"
            "assert sum_list([100]) == 100\n"
        ),
    ),
]


def load() -> list[CodingProblem]:
    return PROBLEMS