import datetime
import pytz
import time
import json
import requests
import re
from bs4 import BeautifulSoup, NavigableString
from pprint import pprint


DATE_TIME = datetime.datetime.now(tz=pytz.timezone('America/New_York'))
DATE = DATE_TIME.date()
unique_jobs = set()
url_template = 'https://www.indeed.com/jobs?q=title%3Apayments&l=United%20States&radius=0&limit=50&fromage=60&start={}'
omitted_jobs_url = 'https://www.indeed.com/jobs?q=title%3Apayments&l=United%20States&radius=0&limit=50&fromage=60&filter=0&start={}'
main_page = 'https://indeed.com'
fields = ['Job title', 'Company name', 'City', 'State', 'Posting date']

selectors = {
    'job_block': 'a[class*="tapItem"]',     # has to be checked later
    'job_title': 'td.resultContent div:first-of-type span[title]',
    'company_name': 'td.resultContent div:nth-of-type(2) span.companyName',     # get_text() method should be checked later! DONE
    'location': 'td.resultContent div:nth-of-type(2) div.companyLocation',      # those long selectors effectiveness should be checked as well DONE
    'posting_date': 'div[class*="result-footer"] span.date'
}

detail_selectors = {
    'job_title': 'h1[class*="jobsearch-JobInfoHeader-title"]',
    'company_name': 'div.jobsearch-JobInfoHeader-subtitle div.jobsearch-InlineCompanyRating div',  # Maybe not clean
    'info_block': 'div.jobsearch-JobInfoHeader-subtitle',
    'footer_meta': 'div.jobsearch-JobMetadataFooter'
}

date_formats = []


# def ensure_left_bracket(filename):
#     with open(filename, 'r+', encoding='utf-8') as file:
#         first_line = file.readline()
#         if first_line[0] != '[':
#             file.seek(0, 0)
#             file.write('[' + first_line)
#
#
# def ensure_right_bracket(filename):
#     with open(filename, 'r+', encoding='utf-8') as file:
#         file.seek(0, 2)
#         file.seek(file.tell()-1, 0)
#         if file.read() == '\n':
#             file.write(']')


def find_no_attr(element):
    return not element.attrs


def parse_date(date_text):
    lower = date_text.lower()
    if 'today' in lower or 'just posted' in lower:
        date_string = DATE.strftime('%d.%m.%Y')
    else:
        expiration = ''
        days = date_text.split(' ')[0]
        if days[-1] == '+':
            days = days[:-1]
            expiration = '>'
        delta_t = datetime.timedelta(days=int(days))
        date_string = expiration + (DATE - delta_t).strftime('%d.%m.%Y')
    return date_string


def find_children(url):
    response = requests.get(url)
    bs = BeautifulSoup(response.text, 'lxml')
    element = bs.find('span', string='Remote')
    print(element)
    for child in element.children:
        print(child)
    return


def parse_jobs(response):
    jobs_bs = BeautifulSoup(response.text, 'lxml')
    jobs = jobs_bs.select(selectors['job_block'])
    for job in jobs:
        temp = dict.fromkeys(fields, '')
        location = job.select_one(selectors['location'])
        loc_text = location.get_text()
        if 'location' in loc_text:
            # print(f'Link element: {location.select_one("a.more_loc")["href"]}')
            more_loc_url = main_page + location.select_one('a.more_loc')['href']
            time.sleep(1)
            more_loc_response = requests.get(more_loc_url)
            print('Request sent, going recursive')
            if more_loc_response.status_code == requests.codes.ok:
                parse_jobs(more_loc_response)
        else:
            job_title = job.select_one(selectors['job_title']).get_text(strip=True)
            posting_date = job.select_one(selectors['posting_date']).get_text(strip=True)
            if '...' in job_title or 'active' in posting_date.lower():
                time.sleep(1)
                job_view_response = requests.get(main_page + job['href'])
                print('Request sent, going to parse detailed job')
                if job_view_response.status_code == requests.codes.ok:
                    parse_detailed_job(job_view_response)   # check later
            else:
                if 'payments' in job_title.lower():
                    company_name = job.select_one(selectors['company_name']).get_text(strip=True)
                    if '...' in company_name or '...' in loc_text:
                        job_view_response = requests.get(main_page + job['href'])
                        print('Request sent, going to parse detailed job')
                        if job_view_response.status_code == requests.codes.ok:
                            parse_detailed_job(job_view_response)
                    else:
                        temp['Job title'] = job_title
                        temp['Company name'] = company_name
                        remote = ''
                        for element in location:
                            elem_text = element.get_text(strip=True)
                            # print(elem_text)
                            if all((isinstance(element, NavigableString), len(element) > 1, not re.search('^[0-9]{5}$', element.get_text()))):
                                if ',' in elem_text:
                                    comma_index = elem_text.find(',')
                                    temp['City'] = elem_text[:comma_index]
                                    if elem_text[comma_index+1] == ' ':
                                        temp['State'] = elem_text[comma_index+2:]
                                    else:
                                        temp['State'] = elem_text[comma_index+1:]
                                else:
                                    temp['State'] = elem_text
                            if 'remote' in elem_text.lower():
                                remote = elem_text
                        if remote:
                            temp['State'] = temp['State'] + ', ' + remote if temp['State'] else remote
                    temp['Posting date'] = parse_date(posting_date)
                    print(f"Job title: {temp['Job title']}, Job State:{temp['State']}, parsed as usual, job link: {main_page+job['href']}")
                    print(temp['Posting date'])
                    unique_jobs.add(tuple(temp.values()))


def parse_detailed_job(response):
    job_view_bs = BeautifulSoup(response.text, 'lxml')
    temp = dict.fromkeys(fields, '')
    job_title = job_view_bs.select_one(detail_selectors['job_title']).get_text(strip=True)
    if 'payments' not in job_title.lower():
        return
    temp['Job title'] = job_title
    info_block = job_view_bs.select_one(detail_selectors['info_block'])
    remote = ''
    for element in info_block:
        elem_text = element.get_text()
        if 'remote' in elem_text.lower():
            remote = elem_text.strip()
        elif element.get('class') and 'jobsearch-InlineCompanyRating' in element['class']:
            company_name = element.select_one('div:first-of-type').get_text(strip=True)
            temp['Company name'] = company_name
        elif element.name == 'div':
            if ',' in element.get_text(strip=True):
                comma_index = elem_text.strip().find(',')
                temp['City'] = elem_text[:comma_index]
                if elem_text[comma_index+1] == ' ':
                    temp['State'] = elem_text[comma_index+2:comma_index+4]
                else:
                    temp['State'] = elem_text[comma_index+1:comma_index+3]
            else:
                temp['State'] = elem_text.strip()
    if remote:
        temp['State'] = temp['State'] + ', ' + remote if temp['State'] else remote
    footer = job_view_bs.select_one(detail_selectors['footer_meta'])
    date_text = footer.find(find_no_attr).get_text(strip=True)
    temp['Posting date'] = parse_date(date_text)
    # pprint(temp)
    print(f"Job title: {temp['Job title']}, Job State:{temp['State']}, result of detailed parsing")
    unique_jobs.add(tuple(temp.values()))


def main():
    for i in range(0, 50, 950):
        response = requests.get(url_template.format(i))
        print('Request sent')
        parse_jobs(response)
        time.sleep(2)
    print(unique_jobs)
    print(f'Jobs without listing similar ones: {len(unique_jobs)}')
    time.sleep(10)
    for i in range(0, 50, 950):
        response = requests.get(omitted_jobs_url.format(i))
        print('Request sent')
        parse_jobs(response)
        time.sleep(2)
    print(f'Jobs including similar ones: {len(unique_jobs)}')
    results = []
    for values_pack in unique_jobs:
        temp = dict(zip(fields, values_pack))
        results.append(temp)
    with open('jobs.json', 'w', encoding='utf-8') as file:
        json.dump(results, file)


if __name__ == '__main__':
    main()
