"""
gRPC Helper Utility
Common functions for gRPC-based load tests
"""
import grpc
import time
import logging
from locust import events
from typing import Optional


class GrpcClient:
    """Base class for gRPC clients in Locust tests"""

    def __init__(self, host: str, port: int, use_ssl: bool = False):
        """
        Initialize gRPC client

        Args:
            host: Server host
            port: Server port
            use_ssl: Whether to use SSL/TLS
        """
        self.endpoint = f"{host}:{port}"
        self.use_ssl = use_ssl
        self.channel: Optional[grpc.Channel] = None

    def connect(self):
        """Establish gRPC connection"""
        try:
            if self.use_ssl:
                credentials = grpc.ssl_channel_credentials()
                self.channel = grpc.secure_channel(self.endpoint, credentials)
            else:
                self.channel = grpc.insecure_channel(
                    self.endpoint,
                    options=(('grpc.enable_http_proxy', 0),)
                )
            logging.info(f"Connected to gRPC endpoint: {self.endpoint}")
        except Exception as e:
            logging.error(f"Failed to connect to gRPC endpoint: {e}")
            raise

    def close(self):
        """Close gRPC connection"""
        if self.channel:
            self.channel.close()
            logging.debug(f"Closed gRPC connection to {self.endpoint}")

    @staticmethod
    def fire_locust_event(
        request_type: str,
        name: str,
        response_time: float,
        response_length: int = 0,
        exception: Optional[str] = None
    ):
        """
        Fire Locust request event for gRPC calls

        Args:
            request_type: Type of request (e.g., "grpc")
            name: Name of the request
            response_time: Response time in milliseconds
            response_length: Size of response in bytes
            exception: Exception message if request failed
        """
        if exception:
            events.request.fire(
                request_type=request_type,
                name=name,
                response_time=response_time,
                response_length=response_length,
                exception=exception
            )
        else:
            events.request.fire(
                request_type=request_type,
                name=name,
                response_time=response_time,
                response_length=response_length
            )

    def make_request(self, stub_method, request, request_name: str):
        """
        Make a gRPC request and track metrics

        Args:
            stub_method: gRPC stub method to call
            request: Request message
            request_name: Name for tracking in Locust

        Returns:
            Response from gRPC call
        """
        start_time = time.time()
        exception = None
        response = None

        try:
            response = stub_method(request)
        except grpc.RpcError as e:
            exception = str(e)
            logging.error(f"gRPC error in {request_name}: {exception}")
        except Exception as e:
            exception = str(e)
            logging.error(f"Unexpected error in {request_name}: {exception}")

        response_time = int((time.time() - start_time) * 1000)

        self.fire_locust_event(
            request_type="grpc",
            name=request_name,
            response_time=response_time,
            exception=exception
        )

        return response
