import asyncio
import aiohttp
import random

class Test():
    index_map = {0 : "small", 1 : "medium", 2 : "large"}

    def __init__(self, small, medium, large, k_min, k_max, conccurent, url):
        self.counter = [small, medium, large]
        self.min_k = k_min
        self.max_k = k_max
        self.conccurent = conccurent
        self.url = url

        self.results = []
        self.failed_requests = []
    
    async def _send_request(self, session, url, k, image_name):
        headers = { "Content-Type": "application/json" }
        body = {"image_key": image_name, "k_clusters": k}

        async with session.post(url, headers=headers, json=body) as response:
            response.raise_for_status()
            return await response.text()
        
    def _get_first_available_index(self, start = 0):
        while self.counter[start % len(self.counter)] == 0:
            start += 1
        return start % len(self.counter)
    
    async def _run_tests(self):
        async with aiohttp.ClientSession as session:
            while sum(self.counter) != 0:
                tasks = []
                for _ in range(self.conccurent):
                    type_index = self._get_first_available_index(random.randint(0, len(self.counter)-1))
                    self.counter[type_index % len(self.counter)] -= 1
                    k = random.randint(self.min_k, self.max_k)
                    image_name = f"{self.index_map[type_index]}_{random.randint(1, 200)})"
                    tasks.append(asyncio.create_task(self._send_request(session, self.url, k, image_name)))
                    if sum(self.counter) == 0:
                        break
                if tasks:
                    print(f"Initiating {len(tasks)} concurrent requests...")
                    batch_results = await asyncio.gather(*tasks)
                    self.results.extend(batch_results)

                    for res in batch_results:
                        if res["status"] != "success":
                            self.failed_requests.append(res)
                            print(f"Request failed for {res['image_name']}: {res.get('error', 'Unknown error')}")
                else:
                    print("No more requests to make.")
                    break
    def run_tests(self):
        asyncio.run(self._run_tests())