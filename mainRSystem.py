# coding: utf-8

# Author: bkyada
#
# implemented a content-based recommendation algorithm.
# It will use the list of genres for a movie as the content.
# The data come from the MovieLens project: http://grouplens.org/datasets/movielens/

from collections import Counter, defaultdict
import math
import numpy as np
import os
import pandas as pd
import re
from scipy.sparse import csr_matrix
import urllib.request
import zipfile

def download_data():
    """ Download and unzip data.
    """
    url = 'https://www.dropbox.com/s/h9ubx22ftdkyvd5/ml-latest-small.zip?dl=1'
    urllib.request.urlretrieve(url, 'ml-latest-small.zip')
    zfile = zipfile.ZipFile('ml-latest-small.zip')
    zfile.extractall()
    zfile.close()


def tokenize_string(my_string):
    """ convert string into token.
    """
    return re.findall('[\w\-]+', my_string.lower())


def tokenize(movies):
    """
    Append a new column to the movies DataFrame with header 'tokens'.
    This will contain a list of strings, one per token, extracted
    from the 'genre' field of each movie.
    
    Params:
      movies...The movies DataFrame
    Returns:
      The movies DataFrame, augmented to include a new column called 'tokens'.

    >>> movies = pd.DataFrame([[123, 'Horror|Romance'], [456, 'Sci-Fi']], columns=['movieId', 'genres'])
    >>> movies = tokenize(movies)
    >>> movies['tokens'].tolist()
    [['horror', 'romance'], ['sci-fi']]
    """
  
    tokens=[]
    
    for row in movies['genres']:
        tokens.append(tokenize_string(row))
    movies['tokens']=tokens
    return movies
    pass


def featurize(movies):
    """
    Append a new column to the movies DataFrame with header 'features'.
    Each row will contain a csr_matrix of shape (1, num_features). Each
    entry in this matrix will contain the tf-idf value of the term, as
    defined in class:
    tfidf(i, d) := tf(i, d) / max_k tf(k, d) * log10(N/df(i))
    where:
    i is a term
    d is a document (movie)
    tf(i, d) is the frequency of term i in document d
    max_k tf(k, d) is the maximum frequency of any term in document d
    N is the number of documents (movies)
    df(i) is the number of unique documents containing term i

    Params:
      movies...The movies DataFrame
    Returns:
      A tuple containing:
      - The movies DataFrame, which has been modified to include a column named 'features'.
      - The vocab, a dict from term to int. Make sure the vocab is sorted alphabetically as in a2 (e.g., {'aardvark': 0, 'boy': 1, ...})
    """
  
    token_list = []
    N = movies.shape[0]
    
    for row in movies['tokens']:
        for r in row:
            token_list.append(r)
    
    final_token_list = sorted(set(token_list))
    vocab = {k: v for v, k in enumerate(final_token_list)}

    dfdict = {}
    for v in vocab.items():
        dfdict[v[0]] = movies.genres.str.lower().str.contains(v[0]).sum()
    value =[]
    for row in movies['tokens']:
        data = []
        rows = []
        column = []
        most_common_term,max_k_tf = Counter(row).most_common(1)[0]
        
        for term in set(row):
            tf = row.count(term)
            tfidf = tf / max_k_tf*math.log10(N / dfdict[term])
            rows.append(0)
            column.append(vocab[term])
            data.append(tfidf)
        value.append(csr_matrix((data, (rows, column)),shape=(1,len(vocab))))

    movies['features']= value

    return movies,vocab
    pass


def train_test_split(ratings):
    """
    Returns a random split of the ratings matrix into a training and testing set.
    """
    test = set(range(len(ratings))[::1000])
    train = sorted(set(range(len(ratings))) - test)
    test = sorted(test)
    return ratings.iloc[train], ratings.iloc[test]


def cosine_sim(a, b):
    """
    Compute the cosine similarity between two 1-d csr_matrices.
    Each matrix represents the tf-idf feature vector of a movie.
    Params:
      a...A csr_matrix with shape (1, number_features)
      b...A csr_matrix with shape (1, number_features)
    Returns:
      The cosine similarity, defined as: dot(a, b) / ||a|| * ||b||
      where ||a|| indicates the Euclidean norm (aka L2 norm) of vector a.
    """
    
    value = 0.0
    valueA=0
    for i in a.data:
        valueA += i*i
    normA = math.sqrt(valueA)
    
    valueB=0
    for i in b.data:
        valueB += i*i
    normB = math.sqrt(valueB)

    i = 0
    size = a._shape[1]
    while i<size:
        ab = b[0,i] * a[0,i]
        value +=ab
        i+=1

    return value/(normA*normB)
    pass


def make_predictions(movies, ratings_train, ratings_test):
    """
    Using the ratings in ratings_train, predict the ratings for each
    row in ratings_test.

    To predict the rating of user u for movie i: Compute the weighted average
    rating for every other movie that u has rated.  Restrict this weighted
    average to movies that have a positive cosine similarity with movie
    i. The weight for movie m corresponds to the cosine similarity between m
    and i.

    If there are no other movies with positive cosine similarity to use in the
    prediction, use the mean rating of the target user in ratings_train as the
    prediction.

    Params:
      movies..........The movies DataFrame.
      ratings_train...The subset of ratings used for making predictions. These are the "historical" data.
      ratings_test....The subset of ratings that need to predicted. These are the "future" data.
    Returns:
      A numpy array containing one predicted rating for each element of ratings_test.
    """
    
    predicted=[]
    for row in ratings_test.itertuples():
        arr=[]
        feat_test = movies[movies['movieId']==row.movieId]
        users = ratings_train[ratings_train.userId==row.userId]
        rating_train = users['rating']
        
        for row in users.itertuples():
            feat_train = movies[movies.movieId==row.movieId]
            s = cosine_sim(feat_train['features'].values[0], feat_test['features'].values[0])
            arr.append(s)
        cosine_arr = [a*b for a,b in zip(rating_train,arr)]
        Scosine = sum(cosine_arr)
        if(Scosine>0.0):
            pre = sum(cosine_arr)/sum(arr)
        else:
            pre = sum(rating_train)/len(rating_train)
        
        predicted.append(pre)
    
    return np.array(predicted)
    pass


def mean_absolute_error(predictions, ratings_test):
    """
    Return the mean absolute error of the predictions.
    """
    return np.abs(predictions - np.array(ratings_test.rating)).mean()


def main():
    download_data()
    path = 'ml-latest-small'
    ratings = pd.read_csv(path + os.path.sep + 'ratings.csv')
    movies = pd.read_csv(path + os.path.sep + 'movies.csv')
    movies = tokenize(movies)
    movies, vocab = featurize(movies)
    print('vocab:')
    print(sorted(vocab.items())[:10])
    ratings_train, ratings_test = train_test_split(ratings)
    print('%d training ratings; %d testing ratings' % (len(ratings_train), len(ratings_test)))
    predictions = make_predictions(movies, ratings_train, ratings_test)
    print('error=%f' % mean_absolute_error(predictions, ratings_test))
    print(predictions[:10])


if __name__ == '__main__':
    main()
