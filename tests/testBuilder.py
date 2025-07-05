from .test import Test

class TestBuilder:
    def __init__(self):
        self._small = 0
        self._medium = 0
        self._large = 0
        self._k_min = 1
        self._k_max = 10
        self._concurrent = 1
        self._url = None

    def with_counts(self, small: int, medium: int, large: int):
        """Sets the initial counts for small, medium, and large image types."""
        if not all(isinstance(n, int) and n >= 0 for n in [small, medium, large]):
            raise ValueError("Counts must be non-negative integers.")
        self._small = small
        self._medium = medium
        self._large = large
        return self # Return self for method chaining

    def with_k_range(self, k_min: int, k_max: int):
        """Sets the range for k_clusters."""
        if not (isinstance(k_min, int) and isinstance(k_max, int) and 0 < k_min <= k_max):
            raise ValueError("k_min and k_max must be positive integers, and k_min <= k_max.")
        self._k_min = k_min
        self._k_max = k_max
        return self

    def with_concurrent_requests(self, concurrent: int):
        """Sets the maximum number of concurrent requests."""
        if not (isinstance(concurrent, int) and concurrent > 0):
            raise ValueError("Concurrent requests must be a positive integer.")
        self._concurrent = concurrent
        return self

    def with_url(self, url: str):
        """Sets the target URL for the requests."""
        if not isinstance(url, str) or not url.startswith("http"):
            raise ValueError("URL must be a valid http(s) string.")
        self._url = url
        return self

    def build(self) -> Test:
        """Constructs and returns a Test instance with the configured parameters."""
        if self._url is None:
            raise ValueError("URL must be set before building the Test object.")
        
        # Ensure that at least one count is set if not explicitly configured
        if self._small == 0 and self._medium == 0 and self._large == 0:
             print("Warning: No image counts set. Defaulting to 1 small image.")
             self._small = 1 # Or raise an error, depending on desired behavior

        return Test(
            small=self._small,
            medium=self._medium,
            large=self._large,
            k_min=self._k_min,
            k_max=self._k_max,
            concurrent=self._concurrent,
            url=self._url
        )