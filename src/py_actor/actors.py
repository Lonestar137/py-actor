import time
import xoscar
import psutil
import asyncio
import argparse
from xoscar import Actor, ActorRef, create_actor_pool, context
from typing import Dict, Any, Optional
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway


class MasterActor(Actor):

    def __init__(self,
                 prometheus_pushgateway: Optional[str] = None,
                 secondary_master_ref=None):
        self.telemetry_data = {}
        self.prometheus_pushgateway = prometheus_pushgateway  # e.g., "localhost:9091"
        self.secondary_master_ref = secondary_master_ref
        # Prometheus metrics
        self.registry = CollectorRegistry()
        self.cpu_gauge = Gauge('cpu_percent',
                               'CPU usage percentage', ['worker_id'],
                               registry=self.registry)
        self.mem_percent_gauge = Gauge('memory_percent',
                                       'Memory usage percentage',
                                       ['worker_id'],
                                       registry=self.registry)
        self.mem_available_gauge = Gauge('memory_available_mb',
                                         'Available memory in MB',
                                         ['worker_id'],
                                         registry=self.registry)

    async def receive_telemetry(self, worker_id: str, data: Dict[str, Any]):
        """Receive telemetry data from worker actors"""
        self.telemetry_data[worker_id] = data
        print(f"Master received telemetry from {worker_id}: {data}")
        await self.forward_telemetry(worker_id, data)
        return {"status": "received"}

    async def forward_telemetry(self, worker_id: str, data: Dict[str, Any]):
        """Forward telemetry data to secondary master or Prometheus"""
        # Forward to secondary master if configured
        if self.secondary_master_ref:
            try:
                await self.secondary_master_ref.receive_telemetry(
                    worker_id, data)
                print(
                    f"Forwarded telemetry from {worker_id} to secondary master"
                )
            except Exception as e:
                print(f"Failed to forward to secondary master: {str(e)}")

        # Forward to Prometheus if pushgateway is configured
        if self.prometheus_pushgateway:
            try:
                # Update Prometheus metrics
                self.cpu_gauge.labels(worker_id=worker_id).set(
                    data['cpu_percent'])
                self.mem_percent_gauge.labels(worker_id=worker_id).set(
                    data['memory_percent'])
                self.mem_available_gauge.labels(worker_id=worker_id).set(
                    data['available_memory_mb'])

                # Push to Prometheus gateway
                push_to_gateway(self.prometheus_pushgateway,
                                job=f'telemetry_{worker_id}',
                                registry=self.registry)
                print(
                    f"Pushed telemetry from {worker_id} to Prometheus at {self.prometheus_pushgateway}"
                )
            except Exception as e:
                print(f"Failed to push to Prometheus: {str(e)}")

    async def get_all_telemetry(self) -> Dict[str, Dict]:
        """Return all collected telemetry data"""
        return self.telemetry_data


class TelemetryActor(Actor):

    def __init__(self, master_refs: list[ActorRef]):
        self.master_refs = master_refs
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
                for master_ref in self.master_refs:
                    response = await master_ref.receive_telemetry(
                        self.worker_id, data)
                    print(f"Worker {self.worker_id} got response: {response}")
                time.sleep(interval)
            except Exception as e:
                print(f"Error in worker {self.worker_id}: {str(e)}")
                time.sleep(interval)


async def loop(args):
    service_host_interface = f"{args.ip_address}:{args.port}"
    master_refs: list[ActorRef] = []
    print(f"Actors listening on: {service_host_interface}")
    # Create actor pool
    async with await create_actor_pool(address=service_host_interface,
                                       n_process=1) as pool:

        if args.masters:
            for master_address in args.masters:
                master_ref = await xoscar.create_actor(
                    MasterActor,
                    prometheus_pushgateway=
                    "prometheus_gateway:9091",  # Set to None if not using Prometheus
                    address=master_address)
                master_refs.append(master_ref)

        if args.is_master:
            if args.post_prom:
                print("Prometheus configured")
                local_master = await xoscar.create_actor(
                    MasterActor,
                    prometheus_pushgateway=
                    "prometheus_gateway:9091",  # Set to None if not using Prometheus
                    address=service_host_interface,
                    uid="local_master")
            else:
                local_master = await xoscar.create_actor(
                    MasterActor,
                    address=service_host_interface,
                    uid="local_master")
            # print("DEBUG: ", local_master.telemetry_data)
            # print("DEBUG: ", local_master.prometheus_pushgateway)
            master_refs.append(local_master)

        # # Create primary master with Prometheus pushgateway and secondary master reference
        # master_ref = await xoscar.create_actor(
        #     MasterActor,
        #     prometheus_pushgateway=
        #     "prometheus_gateway:9091",  # Set to None if not using Prometheus
        #     secondary_master_ref=local_master,
        #     address="localhost:9777",
        #     uid="master_actor")

        if args.has_telemetry:
            print(f"Master listening on: {service_host_interface}")
            # Create multiple telemetry workers
            worker_ref = await xoscar.create_actor(
                TelemetryActor, master_refs, address=service_host_interface)

            await worker_ref.run(interval=5.0)

        # # Keep main running to observe results
        while True:
            if args.is_master:
                all_data = await local_master.get_all_telemetry()
            # print("\nCurrent telemetry snapshot:", all_data)
            time.sleep(5.0)


class MastersAction(argparse.Action):

    def __call__(self, parser, namespace, values, option_string=None):
        if not (namespace.is_master or namespace.has_telemetry):
            parser.error(
                "--masters requires either --is-master or --has-telemetry to be set"
            )
        setattr(namespace, self.dest, values)


def main():

    parser = argparse.ArgumentParser()

    # Create a mutually exclusive group for --is-master and --has-telemetry
    # role_group = parser.add_mutually_exclusive_group()
    role_group = parser
    role_group.add_argument("--is-master",
                            action="store_true",
                            help="If set, spawns a master actor here.")
    role_group.add_argument("--has-telemetry",
                            action="store_true",
                            help="If set, spawns a telemetry actor here.")
    role_group.add_argument(
        "--post-prom",
        default="localhost:9091",
        help="IP Address of the Prometheus push gateway to publish to")
    role_group.add_argument("-i",
                            "--ip-address",
                            default="localhost",
                            help="IP Address for the service to listen on.")
    role_group.add_argument("-p",
                            "--port",
                            default="9777",
                            help="Port for the service to listen on.")

    # Add the --masters argument with the custom action
    parser.add_argument("-m",
                        "--masters",
                        nargs="+",
                        action=MastersAction,
                        help="List of masters to report to.")

    args = parser.parse_args()

    try:
        asyncio.run(loop(args))
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    main()
