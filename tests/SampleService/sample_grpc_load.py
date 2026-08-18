"""
gRPC load-test template.

This is a TEMPLATE, not a runnable load test. gRPC needs stubs generated from
your own .proto files, which cannot ship here, so the task bodies below have
nothing to call.

Left as-is it would print and sleep, which in a Locust UI is indistinguishable
from a load test that is running and passing. It therefore refuses to start
until you have generated stubs and wired up the calls; see the commented
examples in each task.

To use it:
  1. python -m grpc_tools.protoc -I proto --python_out=proto_generated \
       --grpc_python_out=proto_generated proto/your_service.proto
  2. import the generated modules below
  3. replace each task body with a real GrpcClient.make_request call
  4. delete the guard in on_start
"""
import random
import sys
import os
from locust import User, TaskSet, task, between

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from util.grpc_helper import GrpcClient

# Note: You'll need to generate your proto files and import them
# from proto_generated import your_service_pb2, your_service_pb2_grpc


class SampleGrpcTasks(TaskSet):
    """TaskSet for sample gRPC operations"""

    def on_start(self):
        """Initialize gRPC client on user start"""
        # Parse host from locust host parameter (format: grpc://host:port)
        host_parts = self.user.host.replace("grpc://", "").split(":")
        host = host_parts[0] if len(host_parts) > 0 else "localhost"
        port = int(host_parts[1]) if len(host_parts) > 1 else 50051

        # Guard: without generated stubs the tasks below issue no RPCs, and a
        # run would look healthy while testing nothing. Delete this once the
        # tasks make real calls.
        raise RuntimeError(
            "sample_grpc_load.py is a template. Generate stubs from your .proto "
            "files, wire the tasks to GrpcClient.make_request, then remove this "
            "guard. See the module docstring."
        )

        self.grpc_client = GrpcClient(host=host, port=port, use_ssl=False)
        self.grpc_client.connect()
        self.user_id = random.randint(1000, 9999)

    @task(3)
    def get_user_info(self):
        """
        Sample gRPC call to get user information

        Note: This is a template. You'll need to:
        1. Generate your protobuf files using grpcio-tools
        2. Import the generated stub and message classes
        3. Replace this with actual gRPC call
        """
        # Example structure:
        # request = your_service_pb2.GetUserRequest(user_id=self.user_id)
        # stub = your_service_pb2_grpc.YourServiceStub(self.grpc_client.channel)
        # response = self.grpc_client.make_request(
        #     stub.GetUser,
        #     request,
        #     "GetUser"
        # )

        print(f"[TEMPLATE] GetUserInfo for user {self.user_id}")
        # Simulate work
        import time
        time.sleep(0.1)

    @task(2)
    def process_transaction(self):
        """
        Sample gRPC call to process a transaction

        Note: Replace with actual gRPC implementation
        """
        # Example structure:
        # request = your_service_pb2.TransactionRequest(
        #     user_id=self.user_id,
        #     transaction_id=str(uuid.uuid4()),
        #     amount=100.0
        # )
        # stub = your_service_pb2_grpc.YourServiceStub(self.grpc_client.channel)
        # response = self.grpc_client.make_request(
        #     stub.ProcessTransaction,
        #     request,
        #     "ProcessTransaction"
        # )

        print(f"[TEMPLATE] ProcessTransaction for user {self.user_id}")
        # Simulate work
        import time
        time.sleep(0.15)

    def on_stop(self):
        """Close gRPC connection on user stop"""
        self.grpc_client.close()
        print(f"gRPC User {self.user_id} disconnected")


class SampleGrpcUser(User):
    """gRPC User class for load testing"""
    tasks = [SampleGrpcTasks]
    wait_time = between(1, 3)

    # Format: grpc://host:port
    host = "grpc://localhost:50051"
