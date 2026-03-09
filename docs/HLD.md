# High Level Design (HLD)
## E-Commerce Real-Time Data Platform

---

## 1. Purpose

This document describes the high-level architecture of the e-commerce real-time data platform. It is intended to communicate the overall system design, component responsibilities, data flow, and technology decisions without going into implementation-level detail.

---

## 2. Goals & Requirements

### Functional Requirements
- Ingest real-time e-commerce events: orders, clickstream, and inventory updates
- Process and clean incoming event streams
- Store raw and transformed data in a cloud data warehouse
- Provide analytics-ready data models for business consumption
- Automate and monitor the full pipeline

### Non-Functional Requirements
- **Latency:** Events should be available in Snowflake within 2 minutes of generation
- **Scalability:** System should handle up to 10,000 events/minute
- **Reliability:** Pipeline failures should trigger alerts and support automatic retries
- **Maintainability:** All transformations version-controlled and tested

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                             │
│                                                                 │
│   [Order Service]   [Web/App Frontend]   [Inventory System]     │
│         |                  |                      |             │
└─────────┼──────────────────┼──────────────────────┼────────────┘
          |                  |                      |
          ▼                  ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                     INGESTION LAYER                             │
│                                                                 │
│              Apache Kafka (Confluent Cloud)                     │
│                                                                 │
│    Topic: orders   Topic: clickstream   Topic: inventory        │
└──────────────────────────┬──────────────────────────────────────┘
                           |
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PROCESSING LAYER                             │
│                                                                 │
│                Databricks (Apache Spark)                        │
│           Spark Structured Streaming Jobs                       │
│                                                                 │
│   - Type casting & schema enforcement                           │
│   - Deduplication                                               │
│   - Null handling & data cleaning                               │
│   - Write to Snowflake RAW schema                               │
└──────────────────────────┬──────────────────────────────────────┘
                           |
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     STORAGE LAYER                               │
│                                                                 │
│                       Snowflake                                 │
│                                                                 │
│    RAW schema          STAGING schema        MARTS schema       │
│  (Spark writes)    (dbt staging models)  (dbt mart models)      │
└──────────────────────────┬──────────────────────────────────────┘
                           |
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  TRANSFORMATION LAYER                           │
│                                                                 │
│                          dbt                                    │
│                                                                 │
│   staging models → cleaned, typed, renamed columns             │
│   mart models    → facts & dimensions, business logic          │
│   dbt tests      → not null, unique, referential integrity     │
└──────────────────────────┬──────────────────────────────────────┘
                           |
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  ORCHESTRATION LAYER                            │
│                                                                 │
│                      Apache Airflow                             │
│                                                                 │
│   - Triggers Databricks jobs                                    │
│   - Triggers dbt runs                                           │
│   - Monitors pipeline health                                    │
│   - Sends failure alerts                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Breakdown

### 4.1 Event Generator (Python)
A Python script simulates the data sources by producing fake but realistic e-commerce events. In a real system, this would be replaced by actual application services. It uses the `faker` and `kafka-python` libraries.

**Produces events to:**
- `orders` topic
- `clickstream` topic
- `inventory_updates` topic

---

### 4.2 Apache Kafka (Confluent Cloud)
Kafka acts as the central message bus. All events flow through Kafka before being processed. Using Confluent Cloud (free tier) avoids the complexity of self-managing Kafka brokers while making the architecture production-realistic.

**Key design decisions:**
- 3 topics, one per event domain
- Each topic has 3 partitions for parallelism
- Retention set to 7 days

---

### 4.3 Databricks (Apache Spark)
Databricks hosts the Spark Structured Streaming jobs that consume from Kafka. Each topic has a dedicated notebook/job. Spark reads the stream continuously, applies transformations, and writes results to Snowflake using the Snowflake Spark Connector.

**Key design decisions:**
- One Spark job per Kafka topic for isolation and independent scaling
- Databricks Community Edition used (free)
- Write mode: append to Snowflake RAW tables

---

### 4.4 Snowflake
Snowflake serves as the single cloud data warehouse. Data flows through three schemas reflecting its maturity:

| Schema | Contents | Populated By |
|---|---|---|
| RAW | Unmodified events from Spark | Databricks |
| STAGING | Cleaned, typed, renamed | dbt staging models |
| MARTS | Business-ready facts & dims | dbt mart models |

---

### 4.5 dbt
dbt handles all SQL-based transformations inside Snowflake. It enforces software engineering best practices on SQL: version control, modular models, documentation, and automated testing.

**Model layers:**
- `staging/` — one model per raw table, light cleaning only
- `marts/` — fact and dimension tables built from staging models

---

### 4.6 Apache Airflow
Airflow orchestrates the pipeline end-to-end. It runs on Docker locally. The main DAG triggers Databricks jobs and dbt runs in the correct sequence, and alerts on failure.

**DAG structure:**
```
trigger_databricks_jobs >> wait_for_spark >> run_dbt_staging >> run_dbt_marts >> data_quality_check
```

---

## 5. Data Flow Summary

```
Event generated (Python)
    → Published to Kafka topic
        → Consumed by Spark on Databricks
            → Written to Snowflake RAW schema
                → dbt staging model cleans and types the data
                    → dbt mart model builds facts & dimensions
                        → Airflow confirms success / alerts on failure
```

---

## 6. Technology Choice Rationale

| Tool | Why Chosen |
|---|---|
| Kafka | Industry standard for event streaming; decouples producers from consumers |
| Databricks | Managed Spark; used by most Fortune 500 data teams |
| Snowflake | Leading cloud data warehouse; excellent dbt integration |
| dbt | Gold standard for SQL transformation; brings software engineering to analytics |
| Airflow | Most widely used orchestration tool in data engineering |
| Docker | Reproducible local development environment |

---

## 7. Limitations & Scope

This is a portfolio project designed to demonstrate data engineering skills. The following are intentional simplifications:

- Events are generated by a Python script, not real application services
- Confluent Cloud free tier has rate limits (sufficient for demo purposes)
- Databricks Community Edition has no SLA or uptime guarantees
- No BI dashboard layer (Tableau / Looker) is included in scope
- Security (encryption, access control) is simplified for local development
