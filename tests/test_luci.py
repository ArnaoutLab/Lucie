import sys
import os
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from lucie.import_fns import *

# trigger error conditions to get higher coverage
def trig_err(f):
    try:
        f()
    except Exception as e:
        pass

# parameter errors
trig_err(lambda: fetch_ucirepo(id=5, name='arrhythmia'))
trig_err(lambda: fetch_ucirepo(name=5))
trig_err(lambda: fetch_ucirepo(id='arrhythmia'))
trig_err(lambda: fetch_ucirepo())
trig_err(lambda: fetch_ucirepo(id=9999))

# datasets with errors on the UCI end
trig_err(lambda: fetch_ucirepo(id=516))
trig_err(lambda: fetch_ucirepo(id=611))
trig_err(lambda: fetch_ucirepo(id=683))

# the 6 datasets that failed
trig_err(lambda: fetch_ucirepo(id=7))
trig_err(lambda: fetch_ucirepo(id=25))
trig_err(lambda: fetch_ucirepo(id=130))
trig_err(lambda: fetch_ucirepo(id=180))
trig_err(lambda: fetch_ucirepo(id=432))
trig_err(lambda: fetch_ucirepo(id=470))

# try importing a dataset that already has a built-in import function
fetch_ucirepo(id=1)

# these are the non-importable datasets
datasets = [5, 34, 51, 102, 113, 121, 125, 132, 137, 228, 236, 240, 280, 321, 331, 502]

## import the four datasets that we built a special case for
fetch_ucirepo(name='movie')
fetch_ucirepo(name='diabetes')
fetch_ucirepo(name='reuters')
fetch_ucirepo(name='eeg')

## import one dataset from each of our dataset types

# delete arrhythmia so that we can trigger the download script
import shutil
if os.path.exists('extracted_files'):
    shutil.rmtree('extracted_files')
if os.path.exists('arrhythmia.zip'):
    os.remove('arrhythmia.zip')
fetch_ucirepo(id=5) # arrhythmia
fetch_ucirepo(id=113) # twenty newsgroups
fetch_ucirepo(id=236) # seeds.zip
fetch_ucirepo(id=228) # sms spam collection

## import additional datasets to hit as many cases as possible
fetch_ucirepo(id=502) # Online Retail II
extract_and_get_path('bogus_sets/diabetes.zip') # diabetes
extract_and_get_path('bogus_sets/Book1.zip') # bogus gzip dataset
extract_and_get_path('bogus_sets/bogus_json.zip') # bogus json dataset

# trigger download timeout
try:
    download_file('http://archive.ics.uci.edu/static/public/447/condition+monitoring+of+hydraulic+systems.zip', 'test_file.zip', connect_timeout=1, read_timeout=1) 
except:
    pass