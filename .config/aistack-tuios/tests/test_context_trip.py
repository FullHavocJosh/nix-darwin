"""Test aidev_guard.context_trip function."""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "aidev_guard", os.path.join(HERE, "..", "aidev_guard.py")
)
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


def check(name, cond, extra=""):
    print(
        f"{'PASS' if cond else 'FAIL'}: {name}"
        + (f" ({extra})" if extra and not cond else "")
    )
    return cond


def main():
    results = []

    # Test 95% footer - should not trip (below 80% threshold)
    # Wait, 95% should trip. Let me re-read the task...
    # "Footer fill: find the last match of re.compile(r'(\d+(?:\.\d+)?)%/(\d+)k') 
    # (pi footer, for example '61.8%/66k') and return 'context full' when its percentage >= CONTEXT_FILL_PCT."
    # So 95% >= 80% should trip.
    results.append(
        check(
            "95%/66k trips",
            a.context_trip("61.8%/66k\n\n\n\n\n\n\n\n\n95%/66k") == "context full",
        )
    )

    # Test 79.9% - should not trip
    results.append(
        check(
            "79.9%/66k none",
            a.context_trip("79.9%/66k") is None,
        )
    )

    # Test exactly 80% - should trip
    results.append(
        check(
            "80%/66k context full",
            a.context_trip("80%/66k") == "context full",
        )
    )

    # Test 94.6% - should trip
    results.append(
        check(
            "94.6%/66k context full",
            a.context_trip("94.6%/66k") == "context full",
        )
    )

    # Test only the last footer counts - old 95% then 10%/66k gives None
    results.append(
        check(
            "only last footer counts",
            a.context_trip("95%/66k\n\n\n10%/66k") is None,
        )
    )

    # Test truncated message - should return 'truncated'
    results.append(
        check(
            "Response was truncated before completion gives truncated",
            a.context_trip("Response was truncated before completion") == "truncated",
        )
    )

    # Test both present - truncation wins
    results.append(
        check(
            "both present gives truncated",
            a.context_trip("85%/66k\n\n\nResponse was truncated before completion") == "truncated",
        )
    )

    # Test empty text - should return None
    results.append(
        check(
            "empty text None",
            a.context_trip("") is None,
        )
    )

    # Test with no footer
    results.append(
        check(
            "no footer None",
            a.context_trip("This is some text without any footer") is None,
        )
    )

    # Test case-insensitive truncation
    results.append(
        check(
            "response was truncated case insensitive",
            a.context_trip("response was truncated before completion") == "truncated",
        )
    )

    return 1 if not all(results) else 0


if __name__ == "__main__":
    sys.exit(main())
