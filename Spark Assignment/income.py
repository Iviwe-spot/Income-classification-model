# -*- coding: utf-8 -*-
"""income.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1Ms-zv7a1sL7KgW7uVaL1fGFI9AnPbR3S
"""

!pip install pyspark
!pip install pandas

import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.functions import col
from pyspark.ml.feature import StringIndexer, VectorAssembler, StandardScaler
from pyspark.ml.classification import DecisionTreeClassifier, RandomForestClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.mllib.evaluation import MulticlassMetrics

spark = SparkSession.builder.appName("IncomeClassifierModel").getOrCreate()

spark

from google.colab import files
uploaded = files.upload()

data_path = list(uploaded.keys())[0]
data = spark.read.csv(data_path, header=True, inferSchema=True)

data = data.dropna()

data.printSchema()
data.show(5)

categorical_columns = [col for col in data.columns if data.schema[col].dataType == 'string' and col != 'income_class']
indexers = [StringIndexer(inputCol=col, outputCol=col + "_index").fit(data) for col in categorical_columns]

# Apply StringIndexer transformations
for indexer in indexers:
    data = indexer.transform(data)

# Inspect the schema and data to verify indexed columns
data.printSchema()
data.show(5)

for column in categorical_columns:
    indexer = StringIndexer(inputCol=column, outputCol=column + "_index")
    data = indexer.fit(data).transform(data)

from pyspark.sql.types import StringType

categorical_columns = [c for c, t in data.dtypes if t == 'string' and c != 'income_class']
print("Categorical columns:", categorical_columns)

data.printSchema()
data.show(5)

numerical_columns = [c for c, t in data.dtypes if t in ['int', 'double'] and c != 'income_class']
print("Numerical columns:", numerical_columns)

assembler_numerical = VectorAssembler(inputCols=numerical_columns, outputCol="numerical_features")
data = assembler_numerical.transform(data)

data.select("numerical_features").show(5, truncate=False)

scaler = StandardScaler(inputCol="numerical_features", outputCol="scaled_numerical_features", withMean=True, withStd=True)
scaler_model = scaler.fit(data)
data = scaler_model.transform(data)

data.select("scaled_numerical_features").show(5, truncate=False)

feature_columns = ["scaled_numerical_features"] + [col + "_index" for col in categorical_columns]
assembler = VectorAssembler(inputCols=feature_columns, outputCol="features")
data = assembler.transform(data)

data.select("features").show(5, truncate=False)

label_indexer = StringIndexer(inputCol="income_class", outputCol="label").fit(data)
data = label_indexer.transform(data)

data.select("label").show(5)

data = data.select("features", "label")

data.show(5, truncate=False)

train_data, test_data = data.randomSplit([0.7, 0.3], seed=42)

dt = DecisionTreeClassifier(labelCol="label", featuresCol="features", maxBins=50)
dt_model = dt.fit(train_data)

rf = RandomForestClassifier(labelCol="label", featuresCol="features", maxBins=50)
rf_model = rf.fit(train_data)

dt_predictions = dt_model.transform(test_data)
rf_predictions = rf_model.transform(test_data)

evaluator = MulticlassClassificationEvaluator(labelCol="label", predictionCol="prediction", metricName="accuracy")
dt_accuracy = evaluator.evaluate(dt_predictions)
print(f"Decision Tree Accuracy: {dt_accuracy:.2f}")

rf_accuracy = evaluator.evaluate(rf_predictions)
print(f"Random Forest Accuracy: {rf_accuracy:.2f}")

def print_confusion_matrix(predictions, model_name):
    prediction_and_labels = predictions.select("prediction", "label").rdd
    metrics = MulticlassMetrics(prediction_and_labels)
    confusion_matrix = metrics.confusionMatrix().toArray()
    print(f"Confusion Matrix for {model_name}:\n{confusion_matrix}")

print_confusion_matrix(dt_predictions, "Decision Tree")

print_confusion_matrix(rf_predictions, "Random Forest")

if rf_accuracy > dt_accuracy:
    print("Random Forest is the better model.")
else:
    print("Decision Tree is the better model.")

spark.stop()