import pyspark.sql.functions as F
from pyspark import SparkConf
from pyspark.sql import SparkSession
from pyspark.sql.window import Window
from pyspark.sql.types import StructType, StructField, StringType

sparkConf = SparkConf()
sparkConf = sparkConf.set('spark.hadoop.fs.gs.requester.pays.mode', 'AUTO')
sparkConf = sparkConf.set('spark.hadoop.fs.gs.requester.pays.project.id',
                          'open-targets-eu-dev')

spark = (
    SparkSession.builder
    .config(conf=sparkConf)
    .master('yarn')
    .getOrCreate()
)


platformRelease = "21.06"
predictionsPath = "gs://ot-team/dochoa/predictions_stop.tsv"
evdPath = (
    "gs://open-targets-data-releases/" +
    platformRelease +
    "/output/etl/parquet/evidence"
)
diseasePath = (
    "gs://open-targets-data-releases/" +
    platformRelease +
    "/output/etl/parquet/diseases"
)

# ClinVar evidence we are interested
clinvarValids = [
    "affects",
    "risk factor",
    "pathogenic",
    "likely pathogenic",
    "protective",
    "drug response"
]

# Load platform datasets
evidence = spark.read.parquet(evdPath)
disease = spark.read.parquet(diseasePath)

# Stop predictions from Olesya
nonNeutralPredictions = [
    "Negative",
    "Safety_Sideeffects",
    "Success",
    "Business_Administrative",
    "Invalid_Reason"
]
stopPredictions = (
    spark.read
    .option("delimiter", "\t")
    .option("header", True)
    .csv(predictionsPath)
    .filter(F.col("prediction").isNotNull())
    .select(F.col("nct_id").alias("nctid"), "prediction")
    .distinct()
    # add prediction metaclass
    .withColumn("metaprediction",
                F.when(F.col("prediction").isin(nonNeutralPredictions),
                       F.col("prediction"))
                .otherwise(F.lit("Neutral")))
)


# Cleaned evidence (exclude "benign" clinvar genetic evidence)
cleanedEvidence = (
    evidence
    .withColumn("evaValids", F.array([F.lit(x) for x in clinvarValids]))
    .withColumn("evaFilter",
                F.arrays_overlap("evaValids", "clinicalSignificances"))
    .filter((F.col("evaFilter").isNull()) |
            (F.col("evaFilter")))
)

# disease ancestors LUT
diseaseAncestors = (
    disease
    .withColumn("propagatedDiseaseId", F.explode("ancestors"))
    .select(F.col("id").alias("diseaseId"),
            F.col("propagatedDiseaseId"))
    .union(
        disease
        .select(F.col("id").alias("diseaseId"),
                F.col("id").alias("propagatedDiseaseId"))
    )
    .distinct()
)

# pseudo-associations: ontology propagation + max datasource score
associations = (
    cleanedEvidence
    .join(diseaseAncestors, on="diseaseId", how="left")
    .drop("diseaseId")
    .withColumnRenamed("propagatedDiseaseId", "diseaseId")
    .select("targetId", "diseaseId", "datasourceId", "datatypeId")
    .distinct()
)

stoppedStatus = ["Terminated", "Withdrawn", "Suspended"]

# relevant clinical information
clinical = (
    evidence
    .filter(F.col("sourceId") == "chembl")
    .withColumn("urls", F.explode("urls"))
    .withColumn("nctid",
                F.regexp_extract(F.col("urls.url"),
                                 "(.+)(id=%22)(.+)(%22)",
                                 3))
    .withColumn("nctid",
                F.when(F.col("nctid") != "", F.col("nctid"))
                .otherwise(None))
    .withColumn("stopStatus",
                F.when(F.col("clinicalStatus").isin(stoppedStatus),
                       F.col("clinicalStatus"))
                .otherwise(F.lit(None)))
    .withColumn("isStopped",
                F.when(F.col("clinicalStatus").isin(stoppedStatus),
                       F.lit("stopped"))
                .otherwise(F.lit(None)))
    .withColumn("phase4",
                F.when(F.col("clinicalPhase") == 4,
                       F.lit("Phase IV"))
                .otherwise(F.lit(None)))
    .withColumn("phase3",
                F.when(F.col("clinicalPhase") >= 3,
                       F.lit("Phase III+"))
                .otherwise(F.lit(None)))
    .withColumn("phase2",
                F.when(F.col("clinicalPhase") >= 2,
                       F.lit("Phase II+"))
                .otherwise(F.lit(None)))
    .select("targetId", "diseaseId", "nctid",
            "clinicalStatus", "clinicalPhase",
            "studyStartDate", "stopStatus", "isStopped",
            "phase4", "phase3", "phase2")
    .distinct()
    # Create ID
    .withColumn("id", F.monotonically_increasing_id())
    # Olesya's data
    .join(stopPredictions, on="nctid", how="left")
    # Datasources and Datatypes
    .join(
        associations,
        on=["targetId", "diseaseId"],
        how="left")
    .persist()
)

comparisons = spark.createDataFrame(
    data=[("datasourceId", "byDatasource"),
          ("datatypeId", "byDatatype")],
    schema=StructType([
        StructField("comparison", StringType(), True),
        StructField("comparisonType", StringType(), True)]))

predictions = spark.createDataFrame(
    data=[("prediction", "reason"),
          ("metaprediction", "metareason"),
          ("stopStatus", "stopStatus"),
          ("isStopped", "isStopped"),
          ("phase4", "clinical"),
          ("phase3", "clinical"),
          ("phase2", "clinical")],
    schema=StructType([
        StructField("prediction", StringType(), True),
        StructField("predictionType", StringType(), True)]))


def aggregations(df,
                 comparisonColumn,
                 comparisonType,
                 predictionColumn,
                 predictionType
                 ):
    """
    Obtains aggregations for comparison and prediction
    """
    wComparison = Window.partitionBy(comparisonColumn)
    wPrediction = Window.partitionBy(predictionColumn)
    wPredictionComparison = Window.partitionBy(comparisonColumn,
                                               predictionColumn)
    uniqIds = df.select("id").distinct().count()
    out = (
        df
        .withColumn("comparisonType", F.lit(comparisonType))
        .withColumn("predictionType", F.lit(predictionType))
        .withColumn("total", F.lit(uniqIds))
        .withColumn("a",
                    F.approx_count_distinct("id", rsd=0.001)
                    .over(wPredictionComparison))
        .withColumn("predictionTotal",
                    F.approx_count_distinct("id", rsd=0.001)
                    .over(wPrediction))
        .withColumn("comparisonTotal",
                    F.approx_count_distinct("id", rsd=0.001)
                    .over(wComparison))
        .select(F.col(predictionColumn).alias("prediction"),
                F.col(comparisonColumn).alias("comparison"),
                "comparisonType",
                "predictionType",
                "a",
                "predictionTotal",
                "comparisonTotal",
                "total")
        .filter(F.col("prediction").isNotNull())
        .filter(F.col("comparison").isNotNull())
        .distinct()
    )
    out.write.parquet(
        "gs://ot-team/dochoa/predictions_aggregations/" +
        comparisonColumn +
        "_" +
        predictionColumn +
        ".parquet")


# All combinations of comparisons and pjredictions
aggSetups = (
    comparisons.join(predictions, how="full")
    .collect()
)

for row in aggSetups:
    aggregations(clinical, *row)

# theList = [aggregations(clinical, *row) for row in aggSetups]
# out = reduce(lambda A, e: A.unionByName(e), theList)

# out.write.parquet(
#     path="gs://ot-team/dochoa/predictions_aggregations.parquet"
#     )
