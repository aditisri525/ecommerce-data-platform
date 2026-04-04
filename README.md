# E-Commerce Real-Time Data Platform

## Overview

This project simulates a production-grade data engineering platform for a fictional e-commerce company. It ingests real-time events (orders, clicks, inventory updates), processes them at scale, and serves clean, analytics-ready data models to business stakeholders.

The platform is built using industry-standard tools that mirror what modern data teams use in production environments.

---

## Business Problem

An e-commerce company generates thousands of events per minute — customers browsing products, placing orders, and inventory changing in real-time. Without a reliable data platform:

- Business teams cannot monitor live sales performance
- Inventory alerts are delayed, leading to stockouts or overselling
- Data analysts work from stale, manually-refreshed spreadsheets
- There is no single source of truth for business metrics

This platform solves all of the above.

---

## Solution

A fully automated, end-to-end streaming and batch data pipeline that:

1. **Ingests** real-time e-commerce events via Apache Kafka
2. **Processes** and cleans the stream using Apache Spark on Docker
3. **Stores** raw and transformed data in Snowflake
4. **Models** business-ready datasets using dbt
5. **Orchestrates** the entire workflow using Apache Airflow

---

## Tech Stack

| Layer | Tool | Purpose |
|---|---|---|
| Event Streaming | Apache Kafka (Docker) | Real-time event ingestion |
| Stream Processing | Apache Spark (Docker) | Distributed data processing |
| Data Warehouse | Snowflake | Storage & querying |
| Data Transformation | dbt | Data modeling & testing |
| Orchestration | Apache Airflow | Pipeline scheduling & monitoring |
| Containerization | Docker, Docker Compose | Local Development Environment |
| Language | Python | Producers, Spark jobs, DAGs |
| Version Control | GitHub | Source code & documentation |

---

## Data Domains

### Orders
Captures every purchase event with order ID, user ID, product ID, quantity, price, and timestamp.

### Clickstream
Tracks user browsing behavior — page views, product clicks, session IDs, and referral sources.

### Inventory Updates
Records stock level changes triggered by purchases, restocks, or manual adjustments.

---

## Data Flow

```
[Python Event Generator]
         |
         ▼
  [Kafka Topics]          orders | clickstream | inventory_updates
         |
         ▼
  [Spark]            Spark Structured Streaming
  (Docker Container)     → clean, deduplicate, cast types
         |
         ▼
  [Snowflake]             RAW schema → staging tables
         |
         ▼
  [dbt]                   staging → marts (facts & dimensions)
         |
         ▼
  [Airflow]               orchestrates dbt runs, monitors health
```

---

## Repository Structure

```
ecommerce-data-platform/
├── docker-compose.yml            # Spins up Kafka, Spark and Airflow locally
├── README.md                     # This file
├── PROJECT_OVERVIEW.md           # Project goals and summary
├── docs/
│   ├── HLD.md                    # High Level Design
│   ├── LLD.md                    # Low Level Design
│   └── architecture.png          # Architecture diagram
├── data_generator/
│   ├── generate_orders.py        # Fake order event producer
│   ├── generate_clicks.py        # Fake clickstream producer
│   └── generate_inventory.py     # Fake inventory event producer
├── spark_jobs/
│   ├── stream_orders.py      # Spark Streaming: orders topic
│   ├── stream_clicks.py      # Spark Streaming: clickstream topic
│   └── stream_inventory.py   # Spark Streaming: inventory topic
├── dbt_project/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── models/
│   │   ├── staging/
│   │   │   ├── stg_orders.sql
│   │   │   ├── stg_clicks.sql
│   │   │   └── stg_inventory.sql
│   │   └── marts/
│   │       ├── dim_users.sql
│   │       ├── dim_products.sql
│   │       ├── fct_orders.sql
│   │       └── fct_clickstream.sql
│   └── tests/
│       └── schema.yml            # dbt data quality tests
└── airflow_dags/
    └── ecommerce_pipeline.py     # Main orchestration DAG
```

---

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Snowflake account (30-day free trial)
- Conda (for virtual environment management)

### Quick Start
```bash
# Clone the repo
git clone https://github.com/yourusername/ecommerce-data-platform.git
cd ecommerce-data-platform

# Start Kafka and Airflow
docker-compose up -d

# Start generating events
python data_generator/generate_orders.py
python data_generator/generate_clicks.py
python data_generator/generate_inventory.py
```

Full setup guide in each component's subdirectory README.

---

## Key Outcomes

- Real-time order and inventory visibility with sub-minute latency
- Clean, validated data landing in Snowflake with sub-minute latency
- Data quality checks enforced at the Spark processing layer
- Fully containerised pipeline with one-command local setup

---

## What I Learned

- How to design and build an end-to-end streaming data pipeline
- Connecting Kafka to Databricks Spark Structured Streaming running in Docker
- Writing production-style dbt models with staging and marts layers
- Orchestrating multi-tool pipelines in Airflow
- Managing data quality across raw, staging, and modelled layers

---

## Author

Aditi Srivastava — [LinkedIn](https://linkedin.com/in/aditi-srivastava-941b7917b) | [GitHub](https://github.com/aditisri525)
