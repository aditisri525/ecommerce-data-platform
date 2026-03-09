# Low Level Design (LLD)
## E-Commerce Real-Time Data Platform

---

## 1. Purpose

This document describes the implementation-level design of each component in the platform. It covers schemas, configurations, code structure, and logic decisions that guide the actual build.

---

## 2. Event Schemas

All events are serialized as JSON and published to Kafka.

### 2.1 Order Event — Topic: `orders`
```json
{
  "order_id": "ORD-20240315-00123",
  "user_id": "USR-4892",
  "product_id": "PROD-771",
  "product_name": "Wireless Headphones",
  "category": "Electronics",
  "quantity": 2,
  "unit_price": 49.99,
  "total_price": 99.98,
  "currency": "USD",
  "status": "placed",
  "payment_method": "credit_card",
  "timestamp": "2024-03-15T10:23:45Z"
}
```

### 2.2 Clickstream Event — Topic: `clickstream`
```json
{
  "event_id": "EVT-9912837",
  "session_id": "SESS-44821",
  "user_id": "USR-4892",
  "page": "product_detail",
  "product_id": "PROD-771",
  "referral_source": "google_ads",
  "device_type": "mobile",
  "action": "add_to_cart",
  "timestamp": "2024-03-15T10:22:10Z"
}
```

### 2.3 Inventory Update Event — Topic: `inventory_updates`
```json
{
  "update_id": "INV-UPDATE-5521",
  "product_id": "PROD-771",
  "warehouse_id": "WH-EAST-01",
  "previous_stock": 150,
  "updated_stock": 148,
  "change_reason": "purchase",
  "triggered_by_order": "ORD-20240315-00123",
  "timestamp": "2024-03-15T10:23:46Z"
}
```

---

## 3. Kafka Configuration

### Topics
| Topic | Partitions | Replication Factor | Retention |
|---|---|---|---|
| orders | 3 | 3 (Confluent Cloud default) | 7 days |
| clickstream | 3 | 3 | 7 days |
| inventory_updates | 3 | 3 | 7 days |

### Producer Config (Python)
```python
producer_config = {
    "bootstrap.servers": "<CONFLUENT_BOOTSTRAP_SERVER>",
    "security.protocol": "SASL_SSL",
    "sasl.mechanisms": "PLAIN",
    "sasl.username": "<CONFLUENT_API_KEY>",
    "sasl.password": "<CONFLUENT_API_SECRET>",
    "client.id": "ecommerce-python-producer"
}
```

### Consumer Config (Spark on Databricks)
```python
kafka_options = {
    "kafka.bootstrap.servers": "<CONFLUENT_BOOTSTRAP_SERVER>",
    "kafka.security.protocol": "SASL_SSL",
    "kafka.sasl.mechanism": "PLAIN",
    "kafka.sasl.jaas.config": (
        "kafkashaded.org.apache.kafka.common.security.plain.PlainLoginModule "
        "required username='<KEY>' password='<SECRET>';"
    ),
    "subscribe": "orders",
    "startingOffsets": "latest"
}
```

---

## 4. Databricks Spark Jobs

### 4.1 Orders Streaming Job
**File:** `databricks/notebooks/stream_orders.py`

**Logic:**
1. Read stream from Kafka `orders` topic
2. Parse JSON payload using defined schema
3. Cast `timestamp` to `TimestampType`
4. Drop rows where `order_id` or `user_id` is null
5. Deduplicate on `order_id` within a 10-minute watermark
6. Write to Snowflake `RAW.ORDERS` table (append mode)

**Spark Schema:**
```python
orders_schema = StructType([
    StructField("order_id", StringType()),
    StructField("user_id", StringType()),
    StructField("product_id", StringType()),
    StructField("product_name", StringType()),
    StructField("category", StringType()),
    StructField("quantity", IntegerType()),
    StructField("unit_price", DoubleType()),
    StructField("total_price", DoubleType()),
    StructField("currency", StringType()),
    StructField("status", StringType()),
    StructField("payment_method", StringType()),
    StructField("timestamp", StringType())
])
```

**Write config:**
```python
snowflake_options = {
    "sfURL": "<SNOWFLAKE_ACCOUNT>.snowflakecomputing.com",
    "sfDatabase": "ECOMMERCE_DB",
    "sfSchema": "RAW",
    "sfWarehouse": "COMPUTE_WH",
    "sfRole": "SYSADMIN",
    "sfUser": "<USER>",
    "sfPassword": "<PASSWORD>",
    "dbtable": "ORDERS"
}
```

### 4.2 Clickstream Streaming Job
**File:** `databricks/notebooks/stream_clicks.py`

Same pattern as orders. Deduplicates on `event_id`. Writes to `RAW.CLICKSTREAM`.

### 4.3 Inventory Streaming Job
**File:** `databricks/notebooks/stream_inventory.py`

Same pattern. Deduplicates on `update_id`. Writes to `RAW.INVENTORY_UPDATES`.

---

## 5. Snowflake Schema Design

### 5.1 RAW Schema (written by Spark)
```sql
-- RAW.ORDERS
CREATE TABLE RAW.ORDERS (
    order_id          VARCHAR,
    user_id           VARCHAR,
    product_id        VARCHAR,
    product_name      VARCHAR,
    category          VARCHAR,
    quantity          INTEGER,
    unit_price        FLOAT,
    total_price       FLOAT,
    currency          VARCHAR,
    status            VARCHAR,
    payment_method    VARCHAR,
    timestamp         TIMESTAMP_NTZ,
    _ingested_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- RAW.CLICKSTREAM
CREATE TABLE RAW.CLICKSTREAM (
    event_id          VARCHAR,
    session_id        VARCHAR,
    user_id           VARCHAR,
    page              VARCHAR,
    product_id        VARCHAR,
    referral_source   VARCHAR,
    device_type       VARCHAR,
    action            VARCHAR,
    timestamp         TIMESTAMP_NTZ,
    _ingested_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- RAW.INVENTORY_UPDATES
CREATE TABLE RAW.INVENTORY_UPDATES (
    update_id             VARCHAR,
    product_id            VARCHAR,
    warehouse_id          VARCHAR,
    previous_stock        INTEGER,
    updated_stock         INTEGER,
    change_reason         VARCHAR,
    triggered_by_order    VARCHAR,
    timestamp             TIMESTAMP_NTZ,
    _ingested_at          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
```

### 5.2 STAGING Schema (written by dbt)
Staging models rename columns to snake_case, enforce types, and add audit columns. No business logic at this layer.

### 5.3 MARTS Schema (written by dbt)
Fact and dimension tables for analytics consumption.

```
MARTS.DIM_USERS        — unique users derived from orders + clickstream
MARTS.DIM_PRODUCTS     — unique products with category info
MARTS.FCT_ORDERS       — one row per order, joined to dims
MARTS.FCT_CLICKSTREAM  — one row per click event, joined to dims
```

---

## 6. dbt Model Design

### 6.1 Staging Models

**`staging/stg_orders.sql`**
```sql
WITH source AS (
    SELECT * FROM {{ source('raw', 'orders') }}
),

cleaned AS (
    SELECT
        order_id,
        user_id,
        product_id,
        product_name,
        LOWER(category)                         AS category,
        quantity,
        unit_price,
        total_price,
        UPPER(currency)                         AS currency,
        LOWER(status)                           AS order_status,
        LOWER(payment_method)                   AS payment_method,
        timestamp                               AS ordered_at,
        _ingested_at
    FROM source
    WHERE order_id IS NOT NULL
      AND user_id IS NOT NULL
)

SELECT * FROM cleaned
```

### 6.2 Mart Models

**`marts/fct_orders.sql`**
```sql
WITH orders AS (
    SELECT * FROM {{ ref('stg_orders') }}
),

products AS (
    SELECT * FROM {{ ref('dim_products') }}
),

users AS (
    SELECT * FROM {{ ref('dim_users') }}
)

SELECT
    o.order_id,
    o.ordered_at,
    o.order_status,
    o.quantity,
    o.unit_price,
    o.total_price,
    o.currency,
    o.payment_method,
    u.user_id,
    p.product_id,
    p.product_name,
    p.category
FROM orders o
LEFT JOIN products p ON o.product_id = p.product_id
LEFT JOIN users u ON o.user_id = u.user_id
```

### 6.3 dbt Tests (`tests/schema.yml`)
```yaml
version: 2

models:
  - name: stg_orders
    columns:
      - name: order_id
        tests:
          - unique
          - not_null
      - name: user_id
        tests:
          - not_null
      - name: total_price
        tests:
          - not_null

  - name: fct_orders
    columns:
      - name: order_id
        tests:
          - unique
          - not_null
      - name: product_id
        tests:
          - not_null
          - relationships:
              to: ref('dim_products')
              field: product_id
```

---

## 7. Airflow DAG Design

**File:** `airflow_dags/ecommerce_pipeline.py`

### DAG Schedule
- Runs every hour: `schedule_interval="0 * * * *"`
- Start date: project start date
- Retries: 2, with 5-minute retry delay

### Task Graph
```
trigger_orders_job
        |
trigger_clicks_job    ──────► wait_for_spark_jobs
        |                            |
trigger_inventory_job                ▼
                             run_dbt_staging_models
                                     |
                                     ▼
                             run_dbt_mart_models
                                     |
                                     ▼
                             run_dbt_tests
                                     |
                                     ▼
                             notify_success
```

### Key Tasks
```python
trigger_orders_job = DatabricksRunNowOperator(
    task_id="trigger_orders_job",
    databricks_conn_id="databricks_default",
    job_id=ORDERS_JOB_ID
)

run_dbt_staging = BashOperator(
    task_id="run_dbt_staging_models",
    bash_command="dbt run --select staging --profiles-dir /opt/airflow/dbt_project"
)

run_dbt_tests = BashOperator(
    task_id="run_dbt_tests",
    bash_command="dbt test --profiles-dir /opt/airflow/dbt_project"
)
```

---

## 8. Docker Compose Services

```yaml
services:
  airflow-webserver:
    image: apache/airflow:2.8.0
    ports: ["8080:8080"]

  airflow-scheduler:
    image: apache/airflow:2.8.0

  postgres:
    image: postgres:13        # Airflow metadata database

  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    ports: ["2181:2181"]

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    ports: ["9092:9092"]
    depends_on: [zookeeper]
```

---

## 9. Environment Variables

All secrets managed via `.env` file (never committed to GitHub).

```bash
# Confluent Cloud
CONFLUENT_BOOTSTRAP_SERVER=
CONFLUENT_API_KEY=
CONFLUENT_API_SECRET=

# Snowflake
SNOWFLAKE_ACCOUNT=
SNOWFLAKE_USER=
SNOWFLAKE_PASSWORD=
SNOWFLAKE_DATABASE=ECOMMERCE_DB
SNOWFLAKE_WAREHOUSE=COMPUTE_WH

# Databricks
DATABRICKS_HOST=
DATABRICKS_TOKEN=
```

Add `.env` to `.gitignore` immediately.

---

## 10. Error Handling Strategy

| Layer | Error Type | Handling |
|---|---|---|
| Kafka Producer | Connection failure | Retry with exponential backoff |
| Spark Streaming | Malformed JSON | Log to error table, skip record |
| Spark → Snowflake | Write failure | Spark job fails, Airflow retries |
| dbt | Model failure | Airflow marks task failed, sends alert |
| dbt | Test failure | Pipeline halts, alert sent |
| Airflow | Any task failure | 2 automatic retries, then email alert |
