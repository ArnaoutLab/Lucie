# Lucie

A Python package that will automatically import un-importable datasets on the UCI ML repository, by using heuristics to figure out how each dataset is likely to be laid out. 

Preserves the UCIML API to the best of its ability, with one minor change (see below). 

Succeeds on around 83% of datasets with valid download links, and includes manually cleaned datasets to allow all top 100 datasets to be imported. 

GitHub: https://github.com/ArnaoutLab/Lucie
PyPI Package:
ArXiV Paper: 

## Usage and API Changes

For previously importable datasets, we have one minor change: instead of returning the dataset itself, this program will return a tuple, with the first element indicating the dataset format, and the second representing the dataset. 

Example:
<pre lang="python">
from lucie import fetch_ucirepo 
  
# fetch dataset 
iris = fetch_ucirepo(id=53)<span style="color:red;">[1]</span>
  
# data (as pandas dataframes) 
X = iris.data.features 
y = iris.data.targets 
  
# metadata 
print(iris.metadata) 
  
# variable information 
print(iris.variables) 
</pre>

For datasets that were previously not importable, but are importable via `lucie`, we return a dictionary, with keys representing filenames and values representing the associated Pandas dataframe. For example:

```python
from lucie import fetch_ucirepo
arrhythmia = fetch_ucirepo(id=5)
print('arrhythmia')

"""
output is:
('custom',
 {'arrhythmia.data':                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      0 75 0 190 80 91 193 371 174 121.....
  ...
  ...
 }
)
"""

print(arrythmia[1]['arrhythmia.data'])

"""
output is:
75 0 190 80 91 ...
56 1 165 64 81 ...
54 0 172 95 138...
.. .. .. .. ..
"""
```

In some rare cases, we instead return a JSON dictionary representing the directory structure. However, in practice we did not encounter this in any of the top 250 datasets. If you would like to see how that API would work, we have created a bogus dataset to test this functionality. You can try it by running this script: 

```python
from lucie import extract_and_get_path

extract_and_get_path('bogus_sets/bogus_json.zip') # bogus json dataset
```