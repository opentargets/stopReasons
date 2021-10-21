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


platformRelease = "21.09"
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
targetPath = (
    "gs://open-targets-data-releases/" +
    platformRelease +
    "/output/etl/parquet/targets"
)
hpaPath = "gs://ot-team/dochoa/proteinatlas.json.gz"

# ClinVar evidence we are interested
clinvarValids = [
    "affects",
    "risk factor",
    "pathogenic",
    "likely pathogenic",
    "protective",
    "drug response"
]

# Load datasets
evidence = spark.read.parquet(evdPath)
disease = spark.read.parquet(diseasePath)
target = spark.read.parquet(targetPath)
hpa = spark.read.json(hpaPath)

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

# l2g by datasource with some arbitrary cut-offs
l2g = (
    evidence
    .filter(F.col("datasourceId") == "ot_genetics_portal")
    .groupBy("targetId", "diseaseId")
    .agg(F.max("score").alias("max_l2g"))
    .withColumn("l2g_075",
                F.when(F.col("max_l2g") > 0.75,
                       "l2g_0.75")
                .otherwise(F.lit(None)))
    .withColumn("l2g_05",
                F.when(F.col("max_l2g") > 0.5,
                       "l2g_0.5")
                .otherwise(F.lit(None)))
    .withColumn("l2g_025",
                F.when(F.col("max_l2g") > 0.25,
                       "l2g_0.25")
                .otherwise(F.lit(None)))
    .withColumn("l2g_01",
                F.when(F.col("max_l2g") > 0.1,
                       "l2g_0.1")
                .otherwise(F.lit(None)))
    .withColumn("l2g_005",
                F.when(F.col("max_l2g") > 0.05,
                       "l2g_0.05")
                .otherwise(F.lit(None)))
)

stoppedStatus = ["Terminated", "Withdrawn", "Suspended"]


# Assigning 1 and only 1 TA to every disease
taDf = (
    spark.createDataFrame(
        data=[
            (
                "MONDO_0045024",
                "cell proliferation disorder",
                "Oncology"
            ),
            (
                "EFO_0005741",
                "infectious disease",
                "Other"
            ),
            (
                "OTAR_0000014",
                "pregnancy or perinatal disease",
                "Other"
            ),
            (
                "EFO_0005932",
                "animal disease",
                "Other"
            ),
            (
                "MONDO_0024458",
                "disease of visual system",
                "Other"
            ),
            (
                "EFO_0000319",
                "cardiovascular disease",
                "Other"
            ),
            (
                "EFO_0009605",
                "pancreas disease",
                "Other"
            ),
            (
                "EFO_0010282",
                "gastrointestinal disease",
                "Other"
            ),
            (
                "OTAR_0000017",
                "reproductive system or breast disease",
                "Other"
            ),
            (
                "EFO_0010285",
                "integumentary system disease",
                "Other"
            ),
            ("EFO_0001379", "endocrine system disease", "Other"),
            ("OTAR_0000010", "respiratory or thoracic disease", "Other"),
            ("EFO_0009690", "urinary system disease",
             "Other"),
            ("OTAR_0000006", "musculoskeletal or connective tissue disease",
             "Other"),
            ("MONDO_0021205", "disease of ear", "Other"),
            ("EFO_0000540", "immune system disease", "Other"),
            ("EFO_0005803", "hematologic disease", "Other"),
            ("EFO_0000618", "nervous system disease",
             "Other"),
            ("MONDO_0002025", "psychiatric disorder", "Other"),
            ("MONDO_0024297", "nutritional or metabolic disease", "Other"),
            ("OTAR_0000018",
             "genetic, familial or congenital disease",
             "Other"),
            ("OTAR_0000009",
             "injury, poisoning or other complication",
             "Other"),
            ("EFO_0000651", "phenotype", "Other"),
            ("EFO_0001444", "measurement", "Other"),
            ("GO_0008150", "biological process", "Other")],
        schema=StructType([
            StructField("taId", StringType(), True),
            StructField("taLabel", StringType(), True),
            StructField("taLabelSimple", StringType(), True)]))
    .withColumn("taRank", F.monotonically_increasing_id())
)

wByDisease = Window.partitionBy("diseaseId")
diseaseTA = (
    disease
    .withColumn("taId", F.explode("therapeuticAreas"))
    .select(F.col("id").alias("diseaseId"),
            "taId")
    .join(taDf, on="taId", how="left")
    .withColumn("minRank", F.min("taRank").over(wByDisease))
    .filter(F.col("taRank") == F.col("minRank"))
    .drop("taRank", "minRank")
)

# target genetic constrain
targetGC = (
    target
    .withColumn("gc", F.explode("constraint.upperBin6"))
    .select(F.col("id").alias("targetId"),
            F.col("gc").cast("string"))
)

targetPLI = (
    target
    .withColumn("gc", F.explode("constraint"))
    .filter(F.col("gc.constraintType") == "lof")    
    .select(F.col("id").alias("targetId"),
            F.col("gc.score").alias("pLI"))
    .withColumn("lof_tolerance",
                F.when(F.col("pLI") > 0.9,
                       F.lit("LoF intolerant"))
                .otherwise(
                    F.when(F.col("pLI") < 0.1, F.lit("LoF tolerant"))
                    .otherwise(F.lit(None))
                ))
    .drop("pLI")
)

# hpa expression
hpaExpr = (
    hpa
    .select(F.col("Ensembl").alias("targetId"),
            F.col("RNA tissue distribution").alias("rnaDistribution"),
            F.col("RNA tissue specificity").alias("rnaSpecificity"))
)

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
    # L2G cut-offs
    .join(l2g, on=["targetId", "diseaseId"], how="left")
    # Disease therapeutic area (only one by disease)
    .join(diseaseTA, on="diseaseId", how="left")
    # Target genetic constrain
    .join(targetGC, on="targetId", how="left")
    # Target lof tolerance
    .join(targetPLI, on="targetId", how="left")
    # Expression specificity
    .join(hpaExpr, on="targetId", how="left")
    # Datasources and Datatypes
    .join(
        associations,
        on=["targetId", "diseaseId"],
        how="left")
    .persist()
)

comparisons = spark.createDataFrame(
    data=[("datasourceId", "byDatasource"),
          ("datatypeId", "byDatatype"),
          ("taLabelSimple", "ta"),
          ("gc", "geneticConstrain"),
          ("lof_tolerance", "lof_tolerance"),
          ("rnaDistribution", "rnaDistribution"),
          ("rnaSpecificity", "rnaSpecificity"),
          ("l2g_075", "l2g"),
          ("l2g_05", "l2g"),
          ("l2g_025", "l2g"),
          ("l2g_01", "l2g"),
          ("l2g_005", "l2g")],
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
