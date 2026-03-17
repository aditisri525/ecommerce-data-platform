import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    from_json, col, when, current_timestamp, round as spark_round
)
from pyspark.sql.types import (
    StructType, StructField,
    StringType, IntegerType, DoubleType, TimestampType
)


spark = (
    SparkSession.builder
    .appName("OrdersStreamProcessor")
    .config(
        "spark.jars.packages",
        "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1"
    )
    .getOrCreate()
)


spark.sparkContext.setLogLevel("WARN")

print("Spark session created successfully!")


orders_schema = StructType([
    StructField("order_id", StringType(),  nullable=True),
    StructField("user_id", StringType(),  nullable=True),
    StructField("product_id", StringType(),  nullable=True),
    StructField("product_name", StringType(),  nullable=True),
    StructField("category", StringType(),  nullable=True),
    StructField("quantity", IntegerType(), nullable=True),
    StructField("unit_price", DoubleType(),  nullable=True),
    StructField("total_price", DoubleType(),  nullable=True),
    StructField("currency", StringType(),  nullable=True),
    StructField("status", StringType(),  nullable=True),
    StructField("payment_method", StringType(),  nullable=True),
    StructField("timestamp", StringType(),  nullable=True),
])


print("Connecting to Kafka...")

raw_stream = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "kafka:29092")
    .option("subscribe", "orders")
    .option("startingOffsets", "latest")
    .option("failOnDataLoss", "false")
    .load()
)


parsed_stream = (
    raw_stream
    .select(col("value").cast("string").alias("json_string"))
    .select(from_json(col("json_string"), orders_schema).alias("data"))
    .select("data.*")
)

#cleaning the stream
cleaned_stream = (
    parsed_stream
    .filter(
        col("order_id").isNotNull() &
        col("user_id").isNotNull() &
        col("product_id").isNotNull()
    )
    # Normalize text to lowercase for consistency
    .withColumn("category",       col("category"))
    .withColumn("status",         col("status"))
    .withColumn("payment_method", col("payment_method"))
    # Round total_price to 2 decimal places
    .withColumn("total_price", spark_round(col("total_price"), 2))
    .withColumn("unit_price",  spark_round(col("unit_price"),  2))
    # Checks if total_price matches what we'd expect from unit * quantity - checking data quality
    .withColumn(
        "is_price_valid",
        when(
            spark_round(col("unit_price") * col("quantity"), 2) == col("total_price"),
            True
        ).otherwise(False)
    )
    # ingestion timestamp
    .withColumn("_ingested_at", current_timestamp())
)

# writing to console
print(" Starting Orders Stream Processor...")
print("Waiting for messages from Kafka topic: orders")
print("Press Ctrl+C to stop.\n")

query = (
    cleaned_stream.writeStream
    .outputMode("append")
    .format("console")
    .option("truncate", False)
    .option("numRows", 5)
    .option("checkpointLocation", "/tmp/checkpoints/orders")
    .trigger(processingTime="10 seconds")
    .start()
)

# streaming job running until manually stopped
query.awaitTermination()
