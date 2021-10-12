import requests
import time
import re
import json
from bs4 import BeautifulSoup
from pprint import pprint


def parse_physical_location(loc, temp):
    if ', ' in loc:
        comma_pos = loc.index(',')
        temp['City'] = loc[:comma_pos]
        temp['State'] = loc[comma_pos+2:comma_pos+4]
        left_bracket = loc.find('[')
        right_bracket = loc.find(']')
        if left_bracket != -1 and right_bracket != -1:
            temp['City'] = temp['City'] + ' ' + loc[left_bracket:right_bracket+1]
    else:
        temp['State'] = loc


url_template = 'https://www.indeed.com/jobs?q=payments&l=United%20States&fromage=60&filter=0&start={}'
fields = ['Job title', 'Company name', 'City', 'State', 'Posting date']
selectors = {
    'job_block': '.job_seen_beacon',
    'Job title': '.resultContent div:first-of-type h2 > span',
    'Company name': '.resultContent div:nth-of-type(2) span:first-of-type',
    'Location': '.resultContent div:nth-of-type(2) div',
    'State': '',
    'Posting date': 'table:nth-of-type(2) span.date',
}

# jobs_info = []


def ensure_left_bracket(filename):
    with open(filename, 'r+', encoding='utf-8') as file:
        first_line = file.readline()
        if not first_line or first_line[0] != '[':
            file.seek(0, 0)
            file.write('[' + first_line)


def ensure_right_bracket(filename):
    with open(filename, 'r+', encoding='utf-8') as file:
        file.seek(0, 2)
        file.seek(file.tell()-2, 0)
        if file.read(1) != ']':
            file.seek(file.tell()-1, 0)
            file.write(']')


def remove_right_bracket(filename):
    with open(filename, 'r+', encoding='utf-8') as file:
        file.seek(0, 2)
        file.seek(file.tell() - 2, 0)
        if file.read(1) == ']':
            file.seek(file.tell() - 1, 0)
            file.write(',\n')


def count_lines(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        return len(file.readlines())


try:
    with open('results.json', 'r', encoding='utf-8'):
        pass
except FileNotFoundError:
    print('Results file has not been found. Creating new one.')
    with open('results.json', 'w', encoding='utf-8') as file:
        pass


# time.sleep(10)

lines = count_lines('results.json')
job_index = lines % 10
start_from = lines - job_index
ensure_left_bracket('results.json')
if lines:
    remove_right_bracket('results.json')
    print(f'{lines} lines were preprocessed already. Starting from {lines+1}' if lines < 1000 else
          f'{lines} lines are already scraped. Job is completed')


for i in range(start_from, 1000, 10):
    response = requests.get(url_template.format(i))
    bs = BeautifulSoup(response.text, 'lxml')
    jobs = bs.select(selectors['job_block'])
    if job_index:
        jobs = jobs[job_index:]
    for job in jobs:
        temp = dict.fromkeys(fields, '')
        location = job.select_one(selectors['Location']).get_text()
        if '•' in location:
            loc_parts = location.split('•')
            parse_physical_location(loc_parts[0], temp)
            temp['State'] += '/' + loc_parts[-1]
        else:
            if 'remote' in location.lower():
                temp['State'] = location
            else:
                parse_physical_location(location, temp)
        temp['Company name'] = job.select_one(selectors['Company name']).get_text()
        temp['Posting date'] = job.select_one(selectors['Posting date']).get_text()
        temp['Job title'] = job.select_one(selectors['Job title']).get_text()
        pprint(temp)
        # print(location)
        # print()
        with open('results.json', 'a', encoding='utf-8') as file:
            json.dump(temp, file)
            file.write(',\n')

    print(f'{i-start_from+10}/{1000-start_from}')
    time.sleep(2)

ensure_right_bracket('results.json')