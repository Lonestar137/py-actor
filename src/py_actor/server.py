import asyncio
import xoscar as xo

# Define a simple actor class
class ExampleActor(xo.Actor):
    def __init__(self):  # Synchronous __init__
        self.value = 0

    async def increment(self):  # Async method for actor operations
        self.value += 1
        return self.value

    async def __post_create__(self):  # Optional: Async initialization
        print(f"Actor {self.uid} created at {self.address}")

async def main():
    # Start the actor pool with n_process=1 and register the actor
    pool = await xo.create_actor_pool(address="127.0.0.1:8000", n_process=1)
    async with pool:
        # Create the actor with UID 'ExampleActor'
        await xo.create_actor(ExampleActor, uid="ExampleActor", address="127.0.0.1:8000")
        print("Actor pool running on 127.0.0.1:8000...")
        await asyncio.Future()  # Keep the pool running indefinitely

if __name__ == "__main__":
    asyncio.run(main())
