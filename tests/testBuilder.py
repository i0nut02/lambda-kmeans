import asyncio
import aiohttp
import random
import json
import time
from typing import Dict, List, Any
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestResult:
    def __init__(self):
        self.successful_requests = []
        self.failed_requests = []
        self.total_time = 0
        self.start_time = None
        self.end_time = None
    
    def add_success(self, request_data: Dict[str, Any]):
        self.successful_requests.append(request_data)
    
    def add_failure(self, request_data: Dict[str, Any]):
        self.failed_requests.append(request_data)
    
    def get_summary(self) -> Dict[str, Any]:
        total_requests = len(self.successful_requests) + len(self.failed_requests)
        success_rate = len(self.successful_requests) / total_requests * 100 if total_requests > 0 else 0
        
        response_times = [req.get('response_time_ms', 0) for req in self.successful_requests]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            'total_requests': total_requests,
            'successful_requests': len(self.successful_requests),
            'failed_requests': len(self.failed_requests),
            'success_rate_percent': round(success_rate, 2),
            'total_test_time_seconds': self.total_time,
            'average_response_time_ms': round(avg_response_time, 2),
            'min_response_time_ms': min(response_times) if response_times else 0,
            'max_response_time_ms': max(response_times) if response_times else 0
        }

class Test:
    index_map = {0: "small", 1: "medium", 2: "large"}
    
    def __init__(self, small, medium, large, k_min, k_max, concurrent, url):
        self.counter = [small, medium, large]
        self.min_k = k_min
        self.max_k = k_max
        self.concurrent = concurrent
        self.url = url
        self.results = TestResult()
        
        # Validate that we have images to test
        if sum(self.counter) == 0:
            raise ValueError("At least one image count must be greater than 0")
    
    async def _send_request(self, session: aiohttp.ClientSession, url: str, k: int, image_name: str) -> Dict[str, Any]:
        """Send a single request to the Lambda function"""
        headers = {"Content-Type": "application/json"}
        body = {"image_key": image_name, "k_clusters": k}
        
        start_time = time.time()
        request_data = {
            'image_name': image_name,
            'k_clusters': k,
            'timestamp': start_time
        }
        
        try:
            async with session.post(url, headers=headers, json=body, timeout=aiohttp.ClientTimeout(total=300)) as response:
                response_time = (time.time() - start_time) * 1000
                request_data['response_time_ms'] = response_time
                request_data['status_code'] = response.status
                
                if response.status == 200:
                    response_text = await response.text()
                    try:
                        response_json = json.loads(response_text)
                        request_data['response_body'] = response_json
                        request_data['status'] = 'success'
                        logger.info(f"✅ Success: {image_name} (K={k}) - {response_time:.2f}ms")
                        return request_data
                    except json.JSONDecodeError:
                        request_data['status'] = 'json_decode_error'
                        request_data['error'] = f"Invalid JSON response: {response_text[:100]}..."
                        logger.error(f"❌ JSON decode error for {image_name}: {response_text[:100]}...")
                        return request_data
                else:
                    error_text = await response.text()
                    request_data['status'] = 'http_error'
                    request_data['error'] = f"HTTP {response.status}: {error_text}"
                    logger.error(f"❌ HTTP error for {image_name}: {response.status} - {error_text}")
                    return request_data
                    
        except asyncio.TimeoutError:
            request_data['status'] = 'timeout'
            request_data['error'] = 'Request timed out'
            request_data['response_time_ms'] = (time.time() - start_time) * 1000
            logger.error(f"❌ Timeout for {image_name}")
            return request_data
            
        except Exception as e:
            request_data['status'] = 'exception'
            request_data['error'] = str(e)
            request_data['response_time_ms'] = (time.time() - start_time) * 1000
            logger.error(f"❌ Exception for {image_name}: {str(e)}")
            return request_data
    
    def _get_first_available_index(self, start=0):
        """Get the first available image type index"""
        attempts = 0
        while attempts < len(self.counter):
            index = (start + attempts) % len(self.counter)
            if self.counter[index] > 0:
                return index
            attempts += 1
        return None
    
    async def _run_tests(self):
        """Run the load test"""
        logger.info(f"🚀 Starting load test with {sum(self.counter)} total requests")
        logger.info(f"   Target URL: {self.url}")
        logger.info(f"   Concurrent requests: {self.concurrent}")
        logger.info(f"   K-means range: {self.min_k}-{self.max_k}")
        
        self.results.start_time = time.time()
        
        # Create the session with proper timeout
        timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            while sum(self.counter) > 0:
                tasks = []
                
                # Create batch of concurrent requests
                for _ in range(min(self.concurrent, sum(self.counter))):
                    if sum(self.counter) == 0:
                        break
                        
                    # Get random image type that still has images available
                    start_index = random.randint(0, len(self.counter) - 1)
                    type_index = self._get_first_available_index(start_index)
                    
                    if type_index is None:
                        break
                    
                    self.counter[type_index] -= 1
                    k = random.randint(self.min_k, self.max_k)
                    image_name = f"{self.index_map[type_index]}_{random.randint(1, 200)}.jpg"
                    
                    task = asyncio.create_task(
                        self._send_request(session, self.url, k, image_name)
                    )
                    tasks.append(task)
                
                if tasks:
                    logger.info(f"📤 Sending batch of {len(tasks)} requests...")
                    batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for result in batch_results:
                        if isinstance(result, Exception):
                            logger.error(f"❌ Task exception: {result}")
                            self.results.add_failure({
                                'status': 'task_exception',
                                'error': str(result),
                                'timestamp': time.time()
                            })
                        elif result.get('status') == 'success':
                            self.results.add_success(result)
                        else:
                            self.results.add_failure(result)
                    
                    # Small delay between batches to avoid overwhelming the service
                    if sum(self.counter) > 0:
                        await asyncio.sleep(0.1)
                else:
                    logger.info("✅ No more requests to make.")
                    break
        
        self.results.end_time = time.time()
        self.results.total_time = self.results.end_time - self.results.start_time
        
        # Print summary
        summary = self.results.get_summary()
        logger.info("📊 TEST SUMMARY:")
        logger.info(f"   Total requests: {summary['total_requests']}")
        logger.info(f"   Successful: {summary['successful_requests']}")
        logger.info(f"   Failed: {summary['failed_requests']}")
        logger.info(f"   Success rate: {summary['success_rate_percent']}%")
        logger.info(f"   Total test time: {summary['total_test_time_seconds']:.2f}s")
        logger.info(f"   Average response time: {summary['average_response_time_ms']:.2f}ms")
        
        if self.results.failed_requests:
            logger.info("❌ Failed requests details:")
            for failure in self.results.failed_requests:
                logger.info(f"   - {failure.get('image_name', 'Unknown')}: {failure.get('error', 'Unknown error')}")
    
    def run_tests(self):
        """Run the tests synchronously"""
        try:
            asyncio.run(self._run_tests())
        except KeyboardInterrupt:
            logger.info("🛑 Test interrupted by user")
        except Exception as e:
            logger.error(f"❌ Test failed with exception: {e}")
            raise

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
        return self

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
        
        if self._small == 0 and self._medium == 0 and self._large == 0:
            logger.warning("No image counts set. Defaulting to 1 small image.")
            self._small = 1

        return Test(
            small=self._small,
            medium=self._medium,
            large=self._large,
            k_min=self._k_min,
            k_max=self._k_max,
            concurrent=self._concurrent,
            url=self._url
        )
