# -*- coding: utf-8 -*-
# Author: Xi Zhang. (xizhang1@cs.stonybrook.edu)

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from os import system

from pyspark.ml import Pipeline
from pyspark.ml.feature import RegexTokenizer, StopWordsRemover, CountVectorizer
from pyspark.ml.feature import HashingTF, IDF

from pyspark.ml.classification import LogisticRegression, LogisticRegressionModel
from pyspark.ml.evaluation import BinaryClassificationEvaluator

from pyspark.sql.types import *

from pyspark import SparkContext

import pandas as pd
from nltk.stem.snowball import SnowballStemmer

###############################################################################
# Importing data 
def ImportData():
	newDF=[StructField('creator_name',StringType(),True),
		StructField('userid',StringType(),True),
		StructField('comment',StringType(),True),
		StructField('label',IntegerType(),True)]
	structure = StructType(fields=newDF)

	df = spark.read.csv('data/step1.csv', header=True, schema=structure)
	
	# other_df = df.filter( df.label == 0 )
	# owner_df = df.filter( df.label != 0 )
	
	# print other_df.count(), owner_df.count()

	return df

###############################################################################
# Tokenizing, Stemming and Removing the stopwords in each content
def ProcessData( data ):
	# Tokenize the content
	regexTokenizer = RegexTokenizer(inputCol="comment", outputCol="words", pattern="\\W")

	# Remove stopwords
	remover = StopWordsRemover(inputCol="words", outputCol="filtered")
	# remover.transform( regexTokenized ).select("Words", "Filtered").show(truncate=False)

	# Fit the pipeline and generate the final table
	pipeline = Pipeline(stages=[regexTokenizer, remover])
	
	df = pipeline.fit(data).transform(data)
	# df.printSchema()
	
	df = df.withColumn('size', F.size(F.col('filtered')) )
	new_df = df.filter(F.col('size') >= 1)

	# new_df.printSchema()
	new_df = new_df.drop('size')

	print("======== Finish Processing Data =========")

	return new_df


###############################################################################
# Stemming tokens
def StemTokens( df ):
	# Stem tokens
	stemmer = SnowballStemmer(language='english')
	
	words_stemmed = []
	for row in df.select('filtered').collect():
		content_stem = [stemmer.stem(word) for word in row['filtered']]
		words_stemmed.append( content_stem )
	
	stemmer = spark.createDataFrame(words_stemmed, ArrayType(StringType()))

	stemmer = stemmer.withColumn("id", F.monotonically_increasing_id())
	df = df.withColumn("id", F.monotonically_increasing_id())

	new_df = df.join( stemmer, stemmer.id == df.id )

	new_df = new_df.drop('id')
	new_df = new_df.drop('words')
	new_df = new_df.withColumnRenamed('value', 'stemmed')

	new_df.printSchema()
	# new_df.show(10)

	return new_df
	

###############################################################################
# Getting features for model training [Term Frequency ]
def GetFeatures( data ):
	# Term Frequency
	model = CountVectorizer(inputCol="filtered", outputCol="features", minDF=0.02, vocabSize=3000).fit(data)
	df = model.transform(data)

	# print model.vocabulary

	# TF-IDF Score
	# hashingTF = HashingTF(inputCol="filtered", outputCol="rawFeatures", numFeatures=3000)
	# idf = IDF(inputCol="rawFeatures", outputCol="features", minDocFreq=2.0)
	# pipeline = Pipeline(stages=[hashingTF, idf])
	# df = pipeline.fit(data).transform(data)

	print("========= Finish Getting Features for Training =========")

	return df, model.vocabulary

###############################################################################
# Training logistic regression
def TrainModel( trainData ):
	# Create classifier
	model = LogisticRegression(featuresCol='features', labelCol='label', maxIter=10, regParam=0.2).fit( trainData )	
	
	return model

###############################################################################
# Getting the feature-weight map
def FeatureMap( vocabulary, coefficients ):
	feature_weight = []
	for i in range( len(coefficients) ):
		feature_weight.append( [vocabulary[i], coefficients[i]])

	weights = pd.DataFrame(feature_weight)

	print("========= Finish Getting Feature Maps =========")

	return weights


def Ranking():
	newDF=[	StructField('features', StringType(),True),
			StructField('weights', DoubleType(),True)]
	structure = StructType(fields=newDF)

	df = spark.read.csv('data/featuremaps.csv', header=True, schema=structure)

	
	df.sort(F.col("weights").desc()).show( 5 )
	df.sort(F.col("weights")).show( 5 )


	
if __name__ == '__main__':

	name = 'step4'
	spark = SparkSession.builder.appName(name).getOrCreate()
	
	'''
	data = ProcessData( ImportData() )
	new_data = data.filter( data.label != 2 )
	new_data = StemTokens( new_data )
	new_df, vocabulary = GetFeatures( new_data )

	lrmodel = TrainModel( new_df )

	weights = FeatureMap( vocabulary, lrmodel.coefficients )
	weights.to_csv('data/featuremaps.csv', index = None, header = True )
	'''

	Ranking()

