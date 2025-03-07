import psutil
import time
import asyncio
from xoscar import Actor, create_actor_pool, create_actor
from typing import Dict, Any


# Master actor that receives and stores telemetry data
class MasterActor(Actor):

    def __init__(self):
        self.telemetry_data = {}

    async def receive_telemetry(self, worker_id: str, data: Dict[str, Any]):
        """Receive telemetry data from worker actors"""
        self.telemetry_data[worker_id] = data
        print(f"Master received telemetry from {worker_id}: {data}")
        return {"status": "received"}

    async def get_all_telemetry(self) -> Dict[str, Dict]:
        """Return all collected telemetry data"""
        return self.telemetry_data


# Worker actor that collects system telemetry
class TelemetryActor(Actor):

    def __init__(self, master_ref):
        self.master_ref = master_ref
        self.worker_id = f"worker_{id(self)}"

    async def collect_telemetry(self) -> Dict[str, Any]:
        """Collect basic system telemetry"""
        telemetry = {
            "timestamp": time.time(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "available_memory_mb":
            psutil.virtual_memory().available / 1024 / 1024,
            "total_memory_mb": psutil.virtual_memory().total / 1024 / 1024
        }
        return telemetry

    async def run(self, interval: float = 5.0):
        """Continuously collect and send telemetry to master"""
        while True:
            try:
                data = await self.collect_telemetry()
                response = await self.master_ref.receive_telemetry(
                    self.worker_id, data)
                print(f"Worker {self.worker_id} got response: {response}")
                time.sleep(interval)
                # await self.ctx.sleep(interval)
            except Exception as e:
                print(f"Error in worker {self.worker_id}: {str(e)}")
                time.sleep(interval)
                # await self.ctx.sleep(interval)


async def main_loop():
    # Create actor pool
    async with await create_actor_pool(address="localhost:9777",
                                       n_process=1) as pool:
        # pool = await create_actor_pool(address="127.0.0.1:9777", n_process=1)
        # async with pool:
        # Create master actor
        master_ref = await create_actor(MasterActor,
                                        address="localhost:9777",
                                        uid="master_actor")

        # Create multiple telemetry workers
        num_workers = 3
        worker_refs = []
        for _ in range(num_workers):
            worker_ref = await create_actor(TelemetryActor,
                                            master_ref,
                                            address="localhost:9777")
            worker_refs.append(worker_ref)

        # Start telemetry collection in each worker
        for worker_ref in worker_refs:
            await worker_ref.run(interval=5.0)

        # Keep main running to observe results
        try:
            while True:
                # Get and print all telemetry every 10 seconds
                all_data = await master_ref.get_all_telemetry()
                print("\nCurrent telemetry snapshot:", all_data)
                await pool.sleep(10)
        except KeyboardInterrupt:
            print("\nShutting down...")

        # await asyncio.Future()  # Keep the pool running indefinitely


def main():
    asyncio.run(main_loop())


if __name__ == "__main__":
    main()
