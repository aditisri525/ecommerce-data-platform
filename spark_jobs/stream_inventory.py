from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    from_json, col,when, current_timestamp
)
from pyspark.sql.types import (
    StructType, StructField, IntegerType,
    StringType
)

spark = (
    SparkSession.builder
    .appName("InventoryStreamProcessor")
    .config(
        "spark.jars.packages",
        "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1"
    )
    .getOrCreate()
    )

spark.sparkContext.setLogLevel("WARN")
print("Spark session created successfully...")

stream_schema = StructType([
    StructField("update_id", StringType(), nullable = True),
    StructField("product_id", StringType(), nullable = True),
    StructField("warehouse_id", StringType(), nullable = True),
    StructField("previous_stock", IntegerType(), nullable = True),
    StructField("updated_stock", IntegerType(), nullable = True),
    StructField("change_quantity", IntegerType(), nullable = True),
    StructField("change_reason", StringType(), nullable = True),
    StructField("triggered_by_order", StringType(), nullable = True),
    StructField("timestamp", StringType(), nullable = True)
    
])
print("Connecting to Kafka...")

raw_stream = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "kafka:29092")
    .option("subscribe", "inventory_updates")
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
                      col("update_id").isNotNull()&
                      col("product_id").isNotNull()
                      )
                  .withColumn("_ingested_at", current_timestamp())
                  .withColumn("stock_direction", when(col("change_quantity")>0,"increase")
                                                  .when(col("change_quantity")<0,"decrease")
                                                  .otherwise("no_change"))
                  )
#writing to console
print("Starting Inventory Stream Processor...")
print("Waiting for messages from Kafka topic: inventory_updates")
print("press ctrl+c to stop. \n")

query = (cleaned_stream.writeStream
         .outputMode("append")
         .format("console")
         .option("truncate",False)
         .option("numRows", 5)
         .option("checkpointLocation","/tmp/checkpoints/inventory")
         .trigger(processingTime="10 seconds")
         .start()
         )
#stream job  running until manually stopped
query.awaitTermination()