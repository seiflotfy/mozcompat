#!/usr/bin/env python
import sys
import time
import os
import pika
import subprocess
import urllib2
import json

RWCY_URL = "http://arewecompatibleyet.com/data/masterbugtable.js"
RWCY_PREFIX =\
    """/* This file is generated by preproc/buildlists.py - do not edit */
var masterBugTable ="""

BASEPATH = os.path.abspath(os.path.dirname(os.path.abspath(__file__)))
BROWSER_CMD = BASEPATH + "/xvfb-run.sh -w 0 python " + BASEPATH + "/browser.py %s"

browsers = {}
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
channel.queue_declare(queue='mozcompat')
channel.basic_qos(prefetch_count=1)

i = 0

def callback(channel, method, properties, body):
    global i
    i += 1
    print "RECEIVED", i, body
    if not body in browsers:
        browsers[body] = subprocess.Popen(BROWSER_CMD % (body), shell=True)
        time.sleep(1)
    while not is_clean():
        time.sleep(1)


def is_clean():
    values = [(key, value) for key, value in browsers.items()]
    for key, value in values:
        if value.poll() is not None:
            del browsers[key]
    return len(browsers) < 5


if len(sys.argv) == 2 and sys.argv[1] == "listen":
    channel.basic_consume(callback, queue='mozcompat', no_ack=True)
    channel.start_consuming()

elif len(sys.argv) == 2 and sys.argv[1] == "rwcy":
    response = urllib2.urlopen(RWCY_URL)
    js_str = response.read()[len(RWCY_PREFIX):].strip()
    js = json.loads(js_str)
    for key in js["hostIndex"].keys():
        if key[-1] == ".":
            continue
        url = "http://%s" % key
        channel.basic_publish(exchange='', routing_key='mozcompat', body=url)

elif len(sys.argv) == 3:
    if sys.argv[1] == "push":
        channel.basic_publish(exchange='', routing_key='mozcompat',
                              body=sys.argv[2])
    elif sys.argv[1] == "pushall":
        f = open(sys.argv[2], "r")
        sites = f.readlines()
        for site in sites:
            channel.basic_publish(exchange='', routing_key='mozcompat',
                                  body=site)

else:
    print "WRONG BLA BLA"
