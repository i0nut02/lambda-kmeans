from .testBuilder import TestBuilder


if __name__ == "__main__":
    try:
        basic_tester = (
            TestBuilder()
            .with_counts(small=2, medium=1, large=0)
            .with_k_range(k_min=2, k_max=5)
            .with_concurrent_requests(2)
            .with_url("https://httpbin.org/post")
            .build()
        )
        basic_tester.run_tests()
    except ValueError as e:
        print(f"Error creating test: {e}")