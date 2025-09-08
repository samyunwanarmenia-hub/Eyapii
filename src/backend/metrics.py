from prometheus_client import Counter, Gauge, Summary

# Prometheus метрики
joins_total = Counter('pyramid_joins_total', 'Total joins')
stability_gauge = Gauge('pyramid_stability_forecast', 'Stability forecast')
transactions_total = Counter('pyramid_transactions_total', 'Total transactions', ['type'])
events_active = Gauge('pyramid_events_active', 'Active events')
request_duration = Summary('pyramid_request_duration_seconds', 'Request duration')