# Lucie

A Python package that will automatically import un-importable datasets on the UCI ML repository, by using heuristics to figure out how each dataset is likely to be laid out. Our package name "Lucie" is inspired by its function: loading UCI examples

Preserves the UCIML API to the best of its ability, with one minor change (see below). 

Succeeds on 95.4% of the top 250 datasets, and includes manually cleaned datasets to allow all top 100 datasets to be imported. 

GitHub: https://github.com/ArnaoutLab/Lucie

PyPI Package: `pip install lucie`

ArXiV Paper: https://arxiv.org/abs/2410.09119

## Usage and API Changes

For previously importable datasets, we have one minor change: instead of returning the dataset itself, this program will return a tuple, with the first element indicating the dataset format, and the second representing the dataset. 

Example:
```python
from lucie import fetch_ucirepo 
```
```diff
# fetch dataset 
- iris = fetch_ucirepo(id=53)
+ iris = fetch_ucirepo(id=53)[1]
```
```python
# data (as pandas dataframes) 
X = iris.data.features 
y = iris.data.targets 
  
# metadata 
print(iris.metadata) 

# variable information 
print(iris.variables) 
```

For datasets that were previously not importable, but are importable via `lucie`, we return a dictionary, with keys representing filenames and values representing the associated Pandas dataframe. For example:

```python
from lucie import fetch_ucirepo
diabetes = fetch_ucirepo(name='diabetes')
print(diabetes)

"""
output is:
('custom',
 {'diabetes_complete.tsv':
  0      04-21-1991   9:09  33  009
  1      04-21-1991   9:09  34  013
  2      04-21-1991  17:08  62  119
  3      04-21-1991  17:08  33  007
  ...
 }
)
"""

print(diabetes[1]['diabetes_complete.tsv'])

"""
output is:
0      04-21-1991   9:09  33  009
1      04-21-1991   9:09  34  013
2      04-21-1991  17:08  62  119
3      04-21-1991  17:08  33  007
4      04-21-1991  22:51  48  123
...    ...          ...   .. ...
[29329 rows x 4 columns]
"""
```

In some rare cases, we instead return a JSON dictionary representing the directory structure. However, in practice we did not encounter this in any of the top 250 datasets. If you would like to see how that API would work, we have created a bogus dataset to test this functionality. You can try it by running this script: 

```python
from lucie import extract_and_get_path

extract_and_get_path('bogus_sets/bogus_json.zip') # bogus json dataset
```
