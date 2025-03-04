import asyncio
import xoscar as xo

async def main():
    # Get a reference to the actor
    ref = await xo.actor_ref(uid="ExampleActor", address="127.0.0.1:8000")
    # Call a method on the actor
    result = await ref.increment()
    print(f"Incremented value: {result}")

if __name__ == "__main__":
    asyncio.run(main())
