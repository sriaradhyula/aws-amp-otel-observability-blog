#!/usr/bin/env python

import argparse
import logging
import os
import requests
import sys
from logging import INFO, WARNING, ERROR, DEBUG
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from http.client import HTTPConnection
import base64

# Configure logging
logging.basicConfig(stream=sys.stdout, level=logging.ERROR)
logger = logging.getLogger(__name__)
logger.setLevel(DEBUG)

HTTPConnection.debuglevel = 1

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

SERVICE_NAME = os.environ.get('SERVICE_NAME', "custom_onprem_otel_metric")

def get_location_from_metadata(endpoint):
  """
  Fetch location data from metadata endpoint.

  Args:
    endpoint (str): The metadata endpoint URL.

  Returns:
    dict: The JSON response from the endpoint.
  """
  response = requests.get(endpoint)
  return response.json()

def fetch_oauth2_token():
  """
  Fetch OAuth2 token using AWS Cognito.

  Returns:
    str: The access token.
  """
  url = os.environ.get("OAUTH2_TOKEN_URL")
  headers = {
    "Content-Type": "application/x-www-form-urlencoded"
  }
  data = {
    "grant_type": "client_credentials",
    "client_id": os.environ.get("CLIENT_ID"),
    "client_secret": os.environ.get("CLIENT_SECRET"),
    "scope": os.environ.get("SCOPE", "default-m2m-resource-server-i--cld/read")
  }

  response = requests.post(url, headers=headers, data=data)
  response.raise_for_status()
  return response.json()["access_token"]

if __name__ == "__main__":
  parser = argparse.ArgumentParser(
    description='Export a metric to a Prometheus remote-write endpoint.')
  parser.add_argument('--instrument_name',
            help='OTEL Instrument name')
  parser.add_argument('--instrument_kind',
            choices=['counter', 'histogram', 'up_down_counter'],
            help='OTEL Instrument kind')
  parser.add_argument('--measurement_value',
            type=float,
            help='OTEL Measurement value')
  parser.add_argument('--attrs',
            nargs='*',
            dest='measurement_attrs',
            help="OTEL Measurement attributes passed as KEY=VALUE.\n"
               "Example: --attr key1=val1 key2=val2 ...")
  parser.add_argument('--instrument_description',
            dest='instrument_description',
            help='OTEL Instrument description',
            default='')
  parser.add_argument('--instrument_unit',
            dest='instrument_unit',
            help='OTEL Instrument unit',
            default='')
  parser.add_argument('--service_name',
            dest='SERVICE_NAME',
            help='OTEL Resource service.name',
            default=SERVICE_NAME)
  args = parser.parse_args()

  # Fetch OAuth2 token
  access_token = fetch_oauth2_token()

  # Parse measurement attributes
  attributes = {}
  for pair in args.measurement_attrs or []:
    key, val = pair.split('=')
    attributes[key] = val

  metrics_endpoint = os.getenv('METRICS_ENDPOINT')

  # Configure OTLP Metric Exporter
  exporter = OTLPMetricExporter(
    endpoint=metrics_endpoint,
    headers={'authorization': f"Bearer {access_token}"}
  )

  # Configure Metric Reader
  metric_reader = PeriodicExportingMetricReader(
    exporter, export_interval_millis=10)

  # Configure Resource
  resource = Resource.create({
    "service.name": args.SERVICE_NAME
  })

  # Configure Meter Provider
  provider = MeterProvider(metric_readers=[metric_reader], resource=resource)

  # Set the global default meter provider
  metrics.set_meter_provider(provider)

  # Create a meter for this job
  meter = metrics.get_meter('default')
  logger.log(level=INFO, msg=f"meter: {meter.name}")
  logger.log(level=INFO, msg=f"args: {args}")
  logger.log(level=INFO, msg=f"parsed attrs: {attributes}")

  # Create and send the metric based on the instrument kind
  try:
    if args.instrument_kind == "counter":
      metric = meter.create_counter(
        name=args.instrument_name,
        description=args.instrument_description,
        unit=args.instrument_unit
      )
      metric.add(args.measurement_value, attributes)
      logger.log(level=INFO, msg=f"Sent counter metric: '{args.instrument_name}'")
    elif args.instrument_kind == "histogram":
      metric = meter.create_histogram(
        name=args.instrument_name,
        description=args.instrument_description,
        unit=args.instrument_unit,
      )
      metric.record(args.measurement_value, attributes)
      logger.log(level=INFO, msg=f"Sent histogram metric: '{args.instrument_name}'")
    elif args.instrument_kind == "up_down_counter":
      metric = meter.create_up_down_counter(
        name=args.instrument_name,
        description=args.instrument_description,
        unit=args.instrument_unit
      )
      metric.add(args.measurement_value, attributes)
      logger.log(level=INFO, msg=f"Sent up_down_counter metric: '{args.instrument_name}'")
    else:
      logger.log(level=ERROR, msg=f"Invalid instrument type: {args.instrument_kind}")
  except Exception as e:
    logger.log(level=ERROR, msg=f"Failed to send '{args.instrument_name}' metric: {e}")
    raise