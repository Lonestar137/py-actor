import esper
import polars as pl
import random


# Define Components
class Position:

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y


class Velocity:

    def __init__(self, dx: float, dy: float):
        self.dx = dx
        self.dy = dy


class Name:

    def __init__(self, name: str):
        self.name = name


# Define a Processor to update positions
class MovementProcessor(esper.Processor):

    def process(self):
        for ent, (pos, vel) in esper.get_components(Position, Velocity):
            pos.x += vel.dx
            pos.y += vel.dy


# Function to create sample entities and generate a Polars DataFrame
def generate_sample_dataframe(num_entities: int = 5) -> pl.DataFrame:
    # Create an ESPER ECS instance (replacing World)

    # Add the movement processor
    esper.add_processor(MovementProcessor())

    # Lists to store component data
    names = []
    x_positions = []
    y_positions = []
    x_velocities = []
    y_velocities = []

    # Create some sample entities
    for i in range(num_entities):
        # Generate random data
        entity_name = f"Entity_{i}"
        x = random.uniform(0, 100)
        y = random.uniform(0, 100)
        dx = random.uniform(-1, 1)
        dy = random.uniform(-1, 1)

        # Create entity with components
        entity = esper.create_entity(Name(entity_name), Position(x, y),
                                     Velocity(dx, dy))

        # Store data
        names.append(entity_name)
        x_positions.append(x)
        y_positions.append(y)
        x_velocities.append(dx)
        y_velocities.append(dy)

    # Simulate a few updates
    for _ in range(3):
        esper.process()

    # Update positions after simulation
    updated_x = []
    updated_y = []
    for ent, (pos, _) in esper.get_components(Position, Velocity):
        updated_x.append(pos.x)
        updated_y.append(pos.y)

    # Create Polars DataFrame
    df = pl.DataFrame({
        "Name": names,
        "Initial_X": x_positions,
        "Initial_Y": y_positions,
        "Velocity_X": x_velocities,
        "Velocity_Y": y_velocities,
        "Updated_X": updated_x,
        "Updated_Y": updated_y
    })

    return df


def main():
    # Generate the DataFrame
    sample_df = generate_sample_dataframe(5)

    # Print the DataFrame
    print("Sample DataFrame with ESPER ECS and Polars:")
    print(sample_df)

    # Optional: Save to CSV
    sample_df.write_csv("sample_esper_polars_data.csv")
    print("\nDataFrame saved to 'sample_esper_polars_data.csv'")


# Main execution
if __name__ == "__main__":
    main()
