import sys, threading, signal
import urllib.request
import traceback
import time
import os
import sendgrid
from sendgrid.helpers.mail import *
from urllib.request import urlopen
from urllib.parse import urlparse
from urllib.parse import quote
from bs4 import BeautifulSoup
from queue import Queue, Empty

#sendgrid settings
to_email= Email(os.environ.get('SENDGRID_RECIPIENT'))
sg = sendgrid.SendGridAPIClient(os.environ.get('SENDGRID_KEY'))
from_email = Email("python-spider@noreply")

#constants
interval_between_requests = 1

#variables
broken = {}
visited = set()
queue = Queue()


def send_email(host, broken):
    body = '\n\n'.join(f'{k}  =  {v["err"]} --> parent:  {v["parent_url"]}' for (k,v) in broken.items())
    subject = str(len(broken)) + " broken links at " + host
    mail = Mail(from_email, subject, to_email,  Content("text/plain", body))
    response = sg.client.mail.send.post(request_body=mail.get())
    
    if response.status_code != 202:
        return 'An error occurred: {}'.format(response.body), response.status_code

def maybe_enqueue(href, parent_url):
    parsed_uri = urlparse(href)
    if not parsed_uri.scheme =='javascript': 
        if parsed_uri.hostname == None or parsed_uri.hostname==host:
            if (parsed_uri.hostname==None): href =  host + ('/' if not href.startswith('/') else '') +  href
            href = "http://" + href if parsed_uri.scheme == '' else href
            if href not in visited: 
                queue.put((href, parent_url))


def enqueue_hrefs(url, queue):
    req = urllib.request.Request(url,  headers={'User-Agent' : "Magic Browser"})         
    content = urlopen( req, timeout=5).read()
    for link in BeautifulSoup(content,  features='html.parser').findAll('a', href=True):          
        href = link['href'].rstrip('/')
        if not href.startswith("mailto"): 
            maybe_enqueue(href, url)
          

if __name__ == '__main__':

    host= sys.argv[1].rstrip('/')
    queue.put(('http://'+host, ''))
    
    while not queue.empty():       
        time.sleep(interval_between_requests)
        dequed = queue.get_nowait()
        url = dequed[0]
        if url in visited: 
            continue
        print ("visiting: " + url)
        visited.add(url)
        try:
            enqueue_hrefs(url, queue)

        except urllib.error.HTTPError as err:
            print ("broken link: " + url  + " " + str(err.code))
            broken[url] = {'err':str(err.code), 'parent_url' : dequed[1]}

        except Exception as e:
            broken[url] = str(e)
            broken[url] = {'err':str(e), 'parent_url' :dequed[1]}
            print (traceback.format_exc())
    
    print ("broken urls: " + str(len(broken)) +" out of " + str(len(visited)))
    if len(broken)>0:
        send_email(host, broken)
    