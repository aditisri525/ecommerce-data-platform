from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    from_json, col,when, current_timestamp
)
from pyspark.sql.types import (
    StructType, StructField,
    StringType
)

spark = (
    SparkSession.builder
    .appName("ClickstreamStreamProcessor")
    .config(
        "spark.jars.packages",
        "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1"
    )
    .getOrCreate()
    )

spark.sparkContext.setLogLevel("WARN")
print("Spark session created successfully...")

stream_schema = StructType([
    StructField("event_id", StringType(), nullable = True),
    StructField("session_id", StringType(), nullable = True),
    StructField("user_id", StringType(), nullable = True),
    StructField("page", StringType(), nullable = True),
    StructField("product_id", StringType(), nullable = True),
    StructField("referral_source", StringType(), nullable = True),
    StructField("device_type", StringType(), nullable = True),
    StructField("action", StringType(), nullable = True),
    StructField("timestamp", StringType(), nullable = True)
    
])
print("Connecting to Kafka...")

raw_stream = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "kafka:29092")
    .option("subscribe", "clickstream")
    .option("startingOffsets", "latest")
    .option("failOnDataLoss", "false")
    .load()
)

parsed_stream = (
    raw_stream
    .select(col("value").cast("string").alias("json_string"))
    .select(from_json(col("json_string"), stream_schema).alias("data"))
    .select("data.*")
    )

#cleaning stream
cleaned_stream = (parsed_stream
                  .filter(
                      col("event_id").isNotNull()&
                      col("user_id").isNotNull()
                      )
                  .withColumn("_ingested_at", current_timestamp())
                  .withColumn("is_product_event", when(col("product_id").isNotNull(),True).otherwise(False))
                  )
#writing to console
print("Starting Clickstream Stream Processor...")
print("Waiting for messages from Kafka topic: clickstream")
print("press ctrl+c to stop. \n")

query = (cleaned_stream.writeStream
         .outputMode("append")
         .format("console")
         .option("truncate",False)
         .option("numRows", 5)
         .option("checkpointLocation","/tmp/checkpoints/clickstream")
         .trigger(processingTime="10 seconds")
         .start()
         )
#stream job  running until manually stopped
query.awaitTermination()