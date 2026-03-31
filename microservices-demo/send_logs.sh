#!/bin/bash
# namespace của OTEL Collector
NS="observability"
OTEL="otel-collector.$NS.svc.cluster.local:4318"

# Các pod muốn gửi log thử
PODS=(
  "adservice"
  "cartservice"
  "checkoutservice"
  "currencyservice"
  "emailservice"
  "frontend"
  "loadgenerator"
  "paymentservice"
  "productcatalogservice"
  "recommendationservice"
  "redis-cart"
  "shippingservice"
)

for pod in "${PODS[@]}"; do
  kubectl exec -n default log-sender -- \
    curl -s -X POST "http://$OTEL/v1/logs" \
    -H "Content-Type: application/json" \
    -d "{
          \"resourceLogs\":[
            {
              \"resource\":{\"attributes\":[{\"key\":\"pod\",\"value\":\"$pod\"}]},
              \"instrumentationLibraryLogs\":[
                {
                  \"logs\":[
                    {\"timeUnixNano\":$(date +%s%N),\"severityText\":\"INFO\",\"body\":\"Log test từ pod $pod\"}
                  ]
                }
              ]
            }
          ]
        }"
  echo "Đã gửi log từ pod $pod"
done
