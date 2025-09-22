import json
import pandas as pd
from typing import Optional
import urllib.request
import urllib.parse
import certifi
import ssl

from ucimlrepo.dotdict import dotdict
from ucimlrepo.fetch import DatasetNotFoundError

import traceback

# API endpoints
API_BASE_URL = 'https://archive.ics.uci.edu/api/dataset'
API_LIST_URL = 'https://archive.ics.uci.edu/api/datasets/list'

# base location of data csv files
DATASET_FILE_BASE_URL = 'https://archive.ics.uci.edu/static/public'

# available categories of datasets to filter by 
VALID_FILTERS = ['aim-ahead']

import re

def fetch_ucirepo(
        name: Optional[str] = None, 
        id: Optional[int] = None,
        verbose: bool = False
    ):
    '''
    Loads a dataset from the UCI ML Repository, including the dataframes and metadata information.

    Parameters: 
        id (int): Dataset ID for UCI ML Repository
        name (str): Dataset name, or substring of name
        verbose (bool): If True, prints detailed progress information during download and processing
        (Only provide id or name, not both)

    Returns:
        result (dotdict): object containing dataset metadata, dataframes, and variable info in its properties
    '''

    # check that only one argument is provided
    if name and id:
        raise ValueError('Only specify either dataset name or ID, not both')
    
    # validate types of arguments and add them to the endpoint query string
    api_url = API_BASE_URL
    if name:
        if type(name) != str:
            raise ValueError('Name must be a string')
        api_url += '?name=' + urllib.parse.quote(name)
    elif id:
        if type(id) != int:
            raise ValueError('ID must be an integer')
        api_url += '?id=' + str(id)
    else:
        # no arguments provided
        raise ValueError('Must provide a dataset name or ID')


    # fetch metadata from API
    data = None
    try:
        response = urllib.request.urlopen(api_url, context=ssl.create_default_context(cafile=certifi.where()))
        data = json.load(response)
    except (urllib.error.URLError, urllib.error.HTTPError):
        raise ConnectionError('Error connecting to server')

    # verify that dataset exists 
    if data['status'] != 200:
        error_msg = data['message'] if 'message' in data else 'Dataset not found in repository'
        raise DatasetNotFoundError(error_msg)
    

    # extract ID, name, and URL from metadata
    metadata = data['data']
    if not id:
        id = metadata['uci_id']
    elif not name:
        name = metadata['name']
    
    data_url = metadata['data_url']
    
    # no data URL means that the dataset cannot be imported into Python
    # i.e. it does not yet have a standardized CSV file for pandas to parse
    if not data_url:

        if id==132 or name=='movie':
            return ('custom', special_case_download('movie', verbose))
        elif id==34 or name=='diabetes':
            return ('custom', special_case_download('diabetes', verbose))
        elif id==137 or name=='reuters21578' or name=='reuters+21578+text+categorization+collection':
            return ('custom', special_case_download('reuters', verbose))
        elif id==121 or name=='eeg+database':
            return ('custom', special_case_download('eeg', verbose))
        
        data = get_data(id, name, verbose)

        if data is None:
            raise DatasetNotFoundError('"{}" dataset (id={}) exists in the repository, but is not available for import. Please select a dataset from this list: https://archive.ics.uci.edu/datasets?skip=0&take=10&sort=desc&orderBy=NumHits&search=&Python=true'.format(name, id))

        return ('custom', data)

    # parse into dataframe using pandas
    df = None
    try:
        df = pd.read_csv(data_url)
    except (urllib.error.URLError, urllib.error.HTTPError):
        raise DatasetNotFoundError('Error reading data csv file for "{}" dataset (id={}).'.format(name, id))
    except Exception as e:
        df = pd.read_excel(data_url, engine='openpyxl')
        
    if df.empty:
        raise DatasetNotFoundError('Error reading data csv file for "{}" dataset (id={}).'.format(name, id))


    # header line should be variable names
    headers = df.columns

    # feature information, class labels
    variables = metadata['variables']
    del metadata['variables']      # moved from metadata to a separate property
    
    # organize variables into IDs, features, or targets
    variables_by_role = {
        'ID': [],
        'Feature': [],
        'Target': [],
        'Other': []
    }
    for variable in variables:
        if variable['role'] not in variables_by_role:
            raise ValueError('Role must be one of "ID", "Feature", or "Target", or "Other"')
        variables_by_role[variable['role']].append(variable['name'])

    # extract dataframes for each variable role
    ids_df = df[variables_by_role['ID']] if len(variables_by_role['ID']) > 0 else None
    features_df = df[variables_by_role['Feature']] if len(variables_by_role['Feature']) > 0 else None
    targets_df = df[variables_by_role['Target']] if len(variables_by_role['Target']) > 0 else None

    # place all varieties of dataframes in data object
    data = {
        'ids': ids_df,
        'features': features_df,
        'targets': targets_df,
        'original': df,
        'headers': headers,
    }

    # convert variables from JSON structure to tabular structure for easier visualization
    variables = pd.DataFrame.from_records(variables)

    # alternative usage?: 
    # variables.age.role or variables.slope.description
    # print(variables) -> json-like dict with keys [name] -> details

    # make nested metadata fields accessible via dot notation
    metadata['additional_info'] = dotdict(metadata['additional_info']) if metadata['additional_info'] else None
    metadata['intro_paper'] = dotdict(metadata['intro_paper']) if metadata['intro_paper'] else None
    
    # construct result object
    result = {
        'data': dotdict(data),
        'metadata': dotdict(metadata),
        'variables': variables
    }

    # convert to dictionary with dot notation
    return ('uci', dotdict(result))

import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin
import warnings

def get_data(id, name, verbose=False):
    # URL of the website you want to scrape
    url = f'https://archive.ics.uci.edu/dataset/{id}/{name}'
    
    # Send a GET request to the website
    response = requests.get(url)
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the anchor tag with the text "Download"
        download_link = soup.find_all('a')
        download_link = list(filter(lambda tag: tag.find('span', string='Download'), download_link))
        
        if download_link:
            download_link = download_link[0]
            # Get the href attribute (the URL the link points to)
            download_url = download_link['href']
            if verbose:
                print('Download link found:', download_url)
            full_download_url = urljoin(url, download_url)
            if verbose:
                print('Download link:', full_download_url)

            file_name = os.path.basename(full_download_url)
            file_path = os.path.join(os.getcwd(), file_name)

            clear_extract_folder(verbose)
            
            if os.path.exists(file_path):
                if verbose:
                    warnings.warn('Using locally downloaded archive, since downloading can be very slow...')
                return extract_and_get_path(file_path, verbose)
            
            # Send a GET request to the download URL
            download_file(full_download_url, file_path, verbose=verbose)
            
            if verbose:
                print(f'File downloaded and saved as: {file_path}')

            return extract_and_get_path(file_path, verbose)
        else:
            if verbose:
                print('No download link found.')
    else:
        if verbose:
            print(f'Failed to retrieve the webpage. Status code: {response.status_code}')

def clear_extract_folder(verbose=False):
    import os, shutil
    
    folder = os.path.join(os.getcwd(), 'extracted_files')

    if not os.path.exists(folder):
        os.makedirs(folder)
        return

    for root, dirs, files in os.walk(folder):
        try:
            for file in files:
                file_path = os.path.join(root, file)
                os.chmod(file_path, 0o777)  # Ensure the file is writable
                os.remove(file_path)  # Remove the file
            
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                os.chmod(dir_path, 0o777)  # Ensure the directory is writable
                shutil.rmtree(dir_path)  # Remove the directory
        except Exception as e:
            if verbose:
                print('Failed to delete %s. Reason: %s' % (file_path, e))

import zipfile
import tarfile
import gzip

def extract_and_get_path(file_path, verbose=False):
    """
    Recursively extract nested archives until we get a file
    """
    extract_path = os.path.join(os.getcwd(), 'extracted_files')
    
    # Extract the archive
    name_list = extract_archive(file_path, extract_path, verbose)
    # print('name list:', name_list)
    extracted_files = [os.path.join(extract_path, file) for file in name_list]

    #print('Extracted files:', extracted_files)
    
    archives = []
    text_files = []
    extensionless_files = []
    table_files = []

    for file in extracted_files:
        #print(f'Extracted file: {file}')
        if file.endswith('.data'):
            if verbose:
                print(f'Returning {file}')
            table_files.append(file)
            #return file, False
        if file.endswith('.xlsx'):
            if verbose:
                print(f'Returning {file}')
            table_files.append(file)
            #return file, False
        if file.endswith('.csv'):
            if verbose:
                print(f'Returning {file}')
            table_files.append(file)
            #return file, True
        if is_archive(file):
            archives.append(file)
        if '.txt' in file:
            text_files.append(file)
        if '.' not in file:
            extensionless_files.append(file)

    if len(table_files) > 0:
        ret = {}
        
        for f in table_files:
            basename = os.path.basename(f)
            try:
                df = read_csv(f)
            except Exception as e:
                df = pd.read_excel(f, engine='openpyxl')

            ret[basename] = df

        return ret
            
    
    if verbose:
        print('Did not find any tabular/CSV data. Trying archives:', archives)
    
    ret = None

    import editdistance
    from functools import cmp_to_key

    def dist(item):
        return min(editdistance.eval(item, 'data'), editdistance.eval(item, file_path))
    
    def compare(item1, item2):
        return dist(item1) - dist(item2)
    
    sorted(archives, key=cmp_to_key(compare))
    
    for a in archives:
        if verbose:
            print('trying this archive:', a)
        res = extract_and_get_path(a, verbose)
        if res is not None:
            return res
        else:
            if ret is None:
                ret = []
            if verbose:
                print('trying JSON')
            res = try_json_extraction(a, verbose=verbose)
            if res is not None:
                ret.append(res)

    # try any txt files as CSV file
    if verbose:
        print('trying txt files')
    delimiters = [None, ',', ';', '\t']
    backup = {}
    nasum = 1
    for t in text_files:
        for d in delimiters:
            try:
            
                df = read_csv(t, header=None, delimiter=d)

                # print('imported successfully,', df.shape)

                this_nasum = df.isna().sum().sum() / df.size
                if df.shape[1] == 1 or this_nasum > 0:
                    # print('only one column, save as backup')
                    if this_nasum < nasum:
                        backup = {os.path.basename(t): df}
                        nasum = this_nasum
                    elif abs(this_nasum - nasum) < 0.01:
                        backup[os.path.basename(t)] = df
                    else:
                        # print('actually dont save due to nans (', this_nasum, '>', nasum, ')')
                        pass
                    continue
                
                return df
            except Exception as e:
                #print(e)
                pass
    
    if verbose:
        print('trying files with no extension')
    for t in extensionless_files:
        for d in delimiters:
            try:
                df = read_csv(t, header=None, delimiter=d)

                #print('imported successfully,', df.shape)

                this_nasum = df.isna().sum().sum() / df.size
                if df.shape[1] == 1 or this_nasum > 0:
                    #print('only one column, save as backup')
                    if this_nasum < nasum:
                        backup = {os.path.basename(t): df}
                        nasum = this_nasum
                    else:
                        #print('actually dont save due to nans (', this_nasum, '>', nasum, ')')
                        pass
                    continue
                
                return df
            except Exception as e:
                pass

    # print('this is our backup', backup)
    # print('backup =?= {}', backup == {})
    
    if (not backup == {}) and (backup is not None):
        if verbose:
            print('returning backup')
        return backup
    
    return ret

def extract_archive(file_path, extract_to, verbose=False):
    """Extract various types of archive files."""
    if file_path.endswith('.zip'):
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
            return zip_ref.namelist()
    elif file_path.endswith('.tar') or file_path.endswith('.tar.gz') or file_path.endswith('.tgz'):
        tar = tarfile.open(file_path)
        tar.extractall(path=extract_to)#, filter='data')
        retlist = [t.name for t in tar.getmembers()]
        #print(retlist)
        tar.close()
        return retlist
    elif file_path.endswith('.gz'):
        if verbose:
            print('handle .gz files')
        # .gz files usually contain a single file, so extract that
        with gzip.open(file_path, 'rb') as gz_ref:
            file_content = gz_ref.read()
            output_file_path = os.path.join(extract_to, os.path.basename(file_path).replace('.gz', ''))
            with open(output_file_path, 'wb') as out_file:
                out_file.write(file_content)
            os.chmod(output_file_path, 0o755)
            return [output_file_path]
    elif file_path.endswith('.tar.Z'):
        import unlzw3
        from pathlib import Path
        uncompressed_data = unlzw3.unlzw(Path(file_path).read_bytes())
        inner_file = file_path[:-2]
        with open(inner_file, 'wb') as file:
            file.write(uncompressed_data)

        if is_archive(inner_file):
            return extract_archive(inner_file, extract_to, verbose)
        else:
            return [inner_file]
    else:
        raise ValueError("Unsupported file format:", file_path)

def is_archive(file_path):
    archive_extensions = ['.zip', '.tar', '.gz', '.bz2', '.7z', '.rar', '.z', '.tar.z']
    #print(file_path, any(file_path.lower().endswith(ext) for ext in archive_extensions))
    return any(file_path.lower().endswith(ext) for ext in archive_extensions)

def read_csv(file, header=None, delimiter=None):
    if delimiter is None:
        try:
            return pd.read_csv(file, header=header, delimiter=delimiter)
        except:
            pass
    
    largest_col_cnt = 0

    with open(file, 'r') as temp_f:
        lines = temp_f.readlines()

        for l in lines:
            col_cnt = len(l.split(delimiter)) + 1

            largest_col_cnt = max(largest_col_cnt, col_cnt)

    col_names = [i for i in range(0, largest_col_cnt)]

    return pd.read_csv(file, header=header, delimiter=delimiter, names=col_names)

def try_json_extraction(archive, name_list=None, verbose=False):
    """
    Try to import dataset as a JSON, where each file 
    """

    extract_path = os.path.join(os.getcwd(), 'extracted_files')
    
    # Extract the archive
    if name_list is None:
        name_list = extract_archive(archive, extract_path, verbose)
    
    extracted_files = [os.path.join(extract_path, file) for file in name_list]

    if verbose:
        print('Attempting CSV import...')

    from pathlib import Path

    start_folder = os.path.commonprefix(extracted_files)
    extracted_files = [s[len(start_folder):] for s in extracted_files]

    max_depth = 0
    
    for e in extracted_files:
        depth = len(Path(e).parents)

        max_depth = max(max_depth, depth)
    
    def read(file):
        try:
            with open(file, 'r') as f:
                # Read the entire content of the file
                content = f.read()
    
            return content
        except:
            #print('had to skip', file)
            return ""
    
    if max_depth <= 2:
        data = dict()

        for f in extracted_files:
            if f == '':
                continue
            f = f[1:]
            
            parts = os.path.split(f)

            if parts[0] not in data:
                data[parts[0]] = []

            data[parts[0]].append(read(os.path.join(start_folder, f)))
        
        df = pd.DataFrame.from_dict(data, orient='index')
        df = df.transpose()

        return df

    ret = {}
    # traverse root directory, and list directories as dirs and files as files
    if verbose:
        print('Fallback: returning JSON dir structure')
    start_idx = len(splitpath(start_folder))
    for root, dirs, files in os.walk(start_folder):
        path = splitpath(root)[start_idx-1:]

        curr = {}
        
        for file in files:
            curr[file] = read(os.path.join(root, file))

        currnode = ret
        for part in path[:-1]:
            currnode = currnode[part]
        currnode[path[-1]] = curr

    return ret

def splitpath(path):
    ret = re.split(r'[/\\]+', path)
    filtered_array = [item for item in ret if item]
    return filtered_array

def read_gz_as_csv(gz_path):
    # Open the .gz file
    with gzip.open(gz_path, mode='rt') as file:
        # Read the file as a CSV into a pandas DataFrame
        df = pd.read_csv(file, comment='#', sep=' ')
        return df

def special_case_download(name, verbose=False):
    if name == 'movie':
        base_url = 'https://cdn.jsdelivr.net/gh/cernoch/movies@latest/data'
        files = [
            'actors.csv',
            'casts.csv',
            'remakes.csv',
            'studios.csv',
            'synonyms.csv',
            'main.csv',
            'people.csv'
        ]
        delim=None
    elif name == 'diabetes':
        base_url = 'https://cdn.jsdelivr.net/gh/kenneth-ge/UCI-Import@latest/manually_cleaned/diabetes'
        files = [
            'diabetes_complete.tsv'
        ]
        delim='\t'
    elif name == 'reuters':
        base_url = 'https://cdn.jsdelivr.net/gh/kenneth-ge/UCI-Import@latest/manually_cleaned/reuters'
        files = [
            'reuters_hayes_test.csv',
            'reuters_hayes_train.csv',
            'reuters_lewis_test.csv',
            'reuters_lewis_train.csv',
            'reuters_apte_test.csv',
            'reuters_apte_train.csv',
        ]
        delim=None
    elif name == 'eeg':
        """ For this dataset we use fully custom code """
        clear_extract_folder(verbose)
        
        file_path = os.path.join(os.getcwd(), 'eeg+database.zip')
        if not os.path.exists(file_path):
            download_file('https://archive.ics.uci.edu/static/public/121/eeg+database.zip', file_path, verbose=verbose)
            # print(f'File downloaded and saved as: {file_path}')

        extract_path = os.path.join(os.getcwd(), 'extracted_files')

        if verbose:
            print('extracting...')
        extract_archive(file_path, extract_path, verbose)
        
        eeg_full_files = os.path.join(extract_path, 'eeg_full')

        # List only files (excluding directories)
        files = os.listdir(eeg_full_files)

        ret = dict()
        
        # Print the files
        for file in files:
            if verbose:
                print('processing:', file)
            resulting_path = os.path.join(extract_path, os.path.basename(file)[:-7])
            name_list = extract_archive(os.path.join(eeg_full_files, file), extract_path, verbose)
            extracted_files = [os.path.join(extract_path, file) for file in name_list]
            
            ret[os.path.basename(file)] = dict()
            for f in extracted_files:
                if '.gz' not in f:
                    continue
                #print(f, os.path.basename(file), os.path.basename(f))
                try:
                    ret[os.path.basename(file)][os.path.basename(f)] = read_gz_as_csv(f)
                except:
                    pass

        return ret

        
    ret = {}

    for f in files:
        if os.path.exists(f):
            ret[f] = pd.read_csv(f, on_bad_lines='skip', delimiter=delim)
        else:
            path = os.path.join(base_url, f)
            path = path.replace('\\', '/')
            if verbose:
                print('path:', path)
            ret[f] = pd.read_csv(path, on_bad_lines='skip', delimiter=delim)

    return ret

import requests
from requests.exceptions import Timeout
import time

def download_file(url, file_path, connect_timeout=10, read_timeout=99999, verbose=False):
    try:
        start_time = time.time()
        # Use a session to handle the request
        with requests.Session() as session:
            response = session.get(url, stream=True, timeout=(connect_timeout, read_timeout))
            response.raise_for_status()  # Check for HTTP errors
            
            # Write the content to a file
            with open(file_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    #print('elapsed:', time.time() - start_time)
                    if time.time() - start_time > read_timeout:
                        #print('raising exception')
                        raise Timeout()
                    if chunk:  # filter out keep-alive new chunks
                        file.write(chunk)

    except Exception as err:
        if verbose:
            print(err)
        os.remove(file_path)
        raise Exception("Download timed out or " + f"another error occurred: {err}")