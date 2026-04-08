# Service Languages Overview

Tổng hợp ngôn ngữ lập trình của các services trong OpenTelemetry Demo.

## Services theo ngôn ngữ

### Go
- **checkout** - Xử lý thanh toán
- **shipping** - Tính phí vận chuyển
- **product-catalog** - Quản lý sản phẩm
- **accounting** - Xử lý kế toán
- **flagd** - Feature flags service

### Python
- **recommendation** - Đề xuất sản phẩm
- **load-generator** - Tạo traffic giả lập

### JavaScript/Node.js
- **payment** - Xử lý payment gateway

### TypeScript
- **frontend** - Giao diện web (Next.js)

### Java
- **ad** - Quảng cáo service
- **kafka** - Message broker

### C++
- **currency** - Chuyển đổi tiền tệ

### .NET (C#)
- **cart** - Giỏ hàng

### Ruby
- **email** - Gửi email xác nhận

### PHP
- **quote** - Báo giá shipping

### Kotlin
- **fraud-detection** - Phát hiện gian lận

## Tóm tắt

| Ngôn ngữ | Số lượng | Services |
|----------|----------|----------|
| Go | 5 | checkout, shipping, product-catalog, accounting, flagd |
| Python | 2 | recommendation, load-generator |
| JavaScript | 1 | payment |
| TypeScript | 1 | frontend |
| Java | 2 | ad, kafka |
| C++ | 1 | currency |
| .NET | 1 | cart |
| Ruby | 1 | email |
| PHP | 1 | quote |
| Kotlin | 1 | fraud-detection |

## Infrastructure Services

- **valkey-cart** - Redis-compatible cache (Valkey)
- **postgresql** - Database
- **jaeger** - Distributed tracing (Go)
- **otelcol** - OpenTelemetry Collector
- **prometheus** - Metrics collection
- **grafana** - Dashboards
- **opensearch** - Log aggregation
