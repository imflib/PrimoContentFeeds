# This script will generate the HTML output of Primo Searches to be embedded, for instance, in LibGuides widgets.
#
# Input:
#   - requests.csv -> search ids, query and output parameters
#   - arguments    -> comma-separated list of search ids to process (e.g. 1,3). If not present, all searches will be launched
#
# Output:
#   - HTML files (1 per search) in the output directory specified below, with the file name indicated in requests.csv

import os
import sys
import time
import requests
import re
import csv
import urllib.parse
from datetime import date
from time import sleep



### CONFIGURATION

# Primo Search API endpoint
api_gateway_url = 'SELECT_FROM_BELOW'   # e.g. 'https://api-na.hosted.exlibrisgroup.com' if your region is North America
# select your regional api_gateway_url (check https://developers.exlibrisgroup.com/primo/apis/#calling)
# North America  - https://api-na.hosted.exlibrisgroup.com
# Europe         - https://api-eu.hosted.exlibrisgroup.com
# Asia Pacific   - https://api-ap.hosted.exlibrisgroup.com
# Canada         - https://api-ca.hosted.exlibrisgroup.com
# China          - https://api-cn.hosted.exlibrisgroup.com.cn
vid = 'YOUR_VIEW_ID'      # you will find this value in the URL of a regular search in Primo
tab = 'default_tab'       # change if needed, you will find this value in the URL of a regular search in Primo
scope = 'All_resources'   # change if needed, you will find this value in the URL of a regular search in Primo
pcAvailability = 'false'  # change if needed, check options in Primo Search API documentation
api_endpoint = api_gateway_url + "/primo/v1/search?vid=" + vid + "&tab=" + tab + "&scope=" + scope + "&pcAvailability=" + pcAvailability

# Primo Search API key
apikey = 'YOUR_API_KEY'

# Primo hostname
primo_hostname = 'YOUR_PRIMO_HOSTNAME'  # e.g. 'SOMETHING.hosted.exlibrisgroup.com'

# directory where this script is located
basedir = os.path.dirname(os.path.realpath(__file__)) + os.path.sep

# path to book list requests file
requests_file_path = basedir + "requests.csv"

# directory to save output files
output_dir = basedir + "_output" + os.path.sep   # change as needed, this would normally be a directory exposed via web server

# limit book covers api call rate per minute, if needed. Set to 0 for no limit.
# for unregistered users of the Google Books API, this value should be 100 (as of Oct 2022)
max_book_cover_calls_per_min = 100

# proxy servers, if needed
proxies = {
}



### FUNCTIONS

def get_book_cover(isbns):
    # Retrieves a link to a cover image from Google Books from the list of given ISBNs, or False if not found
    # Google Books API site: https://developers.google.com/books
    
    result = False
    
    for isbn in isbns:
        
        # sanitize ISBN value (remove hyphens)
        isbn = isbn.replace('-','')
        
        url = 'https://www.googleapis.com/books/v1/volumes?q=isbn:' + isbn
        
        # allow time between calls
        sleep(pause_book_cover)
        res = requests.get(url, proxies=proxies)
        res_json=res.json()
        
        try:
            if res_json["totalItems"] > 0:
                for item in res_json["items"]:
                    result = item['volumeInfo']['imageLinks']['thumbnail']
        except KeyError:
            pass
            
            if result:
                # stop looking for covers for this book
                break
            
    return result


def get_query(q):
    # reformat query for API call
    q = q.replace("OR&query=","OR;")
    q = q.replace("AND&query=","AND;")
    return q


def generate_html(url):
    print(" # calling Primo Search API...")
    res = requests.get(url, proxies=proxies)
    res_json=res.json()
    
    # retrieve book covers for each book
    print(" # getting book covers...")
    # array of json for each book
    docs = res_json["docs"]
    
    bookInfo = []
    titles=[]

    # get info for each book
    for doc in docs:
        # store all ISBN values
        isbns=[]
        if "isbn" in doc["pnx"]["search"]:
            for isbn in doc["pnx"]["search"]["isbn"]:
                if isbn not in isbns: isbns.append(isbn)

        cover_link = get_book_cover(isbns)
        # default to generic book cover image
        # Icon made by Freepik from www.flaticon.com
        if not cover_link: cover_link = 'https://cdn-icons-png.flaticon.com/512/85/85522.png'
        
        info={}
        title = doc["pnx"]["search"]["title"][0]
        title = re.sub("\s/","",title)
        title = re.sub("\s:",":",title)
        title = re.sub("\s\.","",title)
        if title.lower() in titles:
            continue
        else:
            titles.append(title.lower())
        info["title"] = title

        if "author" in doc["pnx"]["sort"]:
            info["author"] = " by " + doc["pnx"]["sort"]["author"][0]
        else:
            info["author"]=""
            
        if "creationdate" in doc["pnx"]["display"]:
            info["year"]=doc["pnx"]["display"]["creationdate"][0]
        else:
            info["year"]=""
            
        info["imgURL"] = cover_link
        
        if "directlink" in doc["delivery"]["availabilityLinks"]:
            info["catURL"] = doc["delivery"]["availabilityLinksUrl"][0]
            
        elif "detailsGetit1" in doc["delivery"]["availabilityLinks"]:
            docID = doc["pnx"]["control"]["recordid"][0]
            info["catURL"] = "https://" + primo_hostname + "/primo-explore/fulldisplay?vid=" + vid + "&docid=" + docID + "&context=" + doc["context"]
        
        bookInfo.append(info)
     
    html = '''<!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <style>

    body {
        margin: 0;
    }

    body, table {
        font-family: Arial,Helvetica,Verdana;
        font-size: 12px;
    }

    td {
        vertical-align: top;
        padding-bottom: 15px;
    }

    a {
        color: #337ab7;
        text-decoration: none;
    }
    a:focus, a:hover {
        color: #23527c;
        text-decoration: underline;
    }

    td.resource-thumbnail {
      width: 25%;
    }

    td.resource-description {
      padding-left: 5px;
      
    }
    </style>
    </head>

    <body>
    <table width=100%">
    <tbody>'''


    for book in bookInfo:
        html+='''<tr>
                <td width="15%" align="right" style="padding-right:10px;padding-bottom:10px;vertical-align:top;">
                    <a href="'''+book["catURL"]+'''" target="_blank"><img src="'''+book["imgURL"]+'''" style="width:100%"></a>
                </td>
                <td align="left" style="vertical-align:top" style="padding-left:10px">	
                        <a href="'''+book["catURL"]+'''" target="_blank"><p style="font-size: 15px;"><b>'''+book["title"]+'''</b></a>'''+book["author"]+'''</p>
                    <p>Publication Year: '''+book["year"]+'''</p>
                </td>
            </tr>'''

    html+="</tbody></table></body></html>"  
    
    return html



### MAIN

# get comma-separated (no spaces) list of request ids to generate
if len(sys.argv) >= 2:
    list_ids = sys.argv[1].strip().split(',')
else:
    list_ids = False

# ensure we have required directories
for directory in [output_dir]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# get current year in YYYY format
current_year = date.today().year

# set waiting time between calls for book covers
pause_book_cover = 0
if max_book_cover_calls_per_min and max_book_cover_calls_per_min > 0:
    pause_book_cover = 60 / max_book_cover_calls_per_min

# read book list requests into a dictionary with first row as keys
with open(requests_file_path) as file:
    list_requests = [{k: v for k, v in row.items()}
        for row in csv.DictReader(file, skipinitialspace=True)]

# for each request, append booklist URL and API query URL to dictionary
API_URLS={}

for r in list_requests:
    if not list_ids or (list_ids and r['id'] in list_ids):
        html_path = r['file_name']
        q = get_query(r['query'])
        mfacets = urllib.parse.quote(r['facets'])
        from_year = r['from_YYYY']
        
        # if from_year has a value
        if from_year:
            # add separator to mfacets if it had content
            if len(mfacets)>0: mfacets += urllib.parse.quote('|,|')
            # add creation date filter to mfacets
            mfacets += urllib.parse.quote('facet_searchcreationdate,include,[' + str(from_year) + '+TO+' + str(current_year) + ']')
        
        sort_value = r['sort']
        
        limit = str(int(r['results_limit'])).strip()
        if not limit.isnumeric():
            limit = ''

        URL = api_endpoint + "&q=" + q + "&multiFacets=" + mfacets + "&limit=" + limit + "&sort=" + sort_value + "&apikey=" + apikey
        
        API_URLS[html_path]=URL
        
    
# for each booklist, create html based on API results
for listURL, query in API_URLS.items():
    
    start_time = time.time()
    
    print( '\n ### updating: ' + listURL)
    html = generate_html(query)
    
    print(" # writing HTML output...")
    html_file= open(output_dir + listURL, "w", encoding='utf8')
    html_file.write(html)
    html_file.close()
    
    exec_time = time.time() - start_time
    print(f" # time elapsed: {exec_time:.02f} secs.")

print("DONE.")
