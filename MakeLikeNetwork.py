import re
import bs4
import requests
import json
import multiprocessing as mp
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import datetime
import time
import pickle
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException,TimeoutException
import networkx as nx
import multiprocessing as mp

NUM_PAGES = 500
def get_json_on_page(page_number=1):
    # We'll derive everything else from the
    # Json returned from this function.
    # 100 requests per second allowed
    time.sleep(1/100)
    url = "https://us.forums.blizzard.com/en/wow/c/pvp/arenas/21/l/latest.json?ascending=false&order=default&page="+str(page_number)
    try:
        r = requests.get(url)
        data = r.json()
    except Exception:
        return {}

    return data

def get_topic_url(urlbase,topic):
    return urlbase + topic['slug'] + '/' + str(topic['id'])

scrollElementIntoMiddle = "var viewPortHeight = Math.max(document.documentElement.clientHeight, window.innerHeight || 0);"\
                                            + "var elementTop = arguments[0].getBoundingClientRect().top;"\
                                            + "window.scrollBy(0, elementTop-(viewPortHeight/2));"

def update_like_graph(post_data):
    time.sleep(14/100)
    driver = webdriver.Chrome()
    LikeG = nx.DiGraph()
    run_number,(url,post_count) = post_data
    print("Starting run number " + str(run_number))
    driver.get(url)
    driver.execute_script("window.scrollTo(0,0);")
    for i in range(1,post_count):
        try:
            wait_element = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//article[@id='post_"+str(i)+"']")))
            driver.execute_script(scrollElementIntoMiddle,wait_element)
            try:
                poster = driver.find_element_by_xpath("//article[@id='post_"+str(i)+"']//a[contains(@class,'main-avatar')]").get_attribute('data-user-card')
                element = driver.find_element_by_xpath("//article[@id='post_"+str(i)+"']//button[contains(@class,'like-count')]")
                driver.execute_script(scrollElementIntoMiddle,element)
                element.click()
                who_liked = WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.XPATH,"//article[@id='post_"+str(i)+"']//div[contains(@class,'who-liked')]//a")))
                for fan in who_liked:
                    fanname = fan.get_attribute('data-user-card')
                    if LikeG.has_edge(fanname,poster):
                        LikeG.edges[(fanname,poster)]['weight'] += 1
                    else:
                        LikeG.add_edge(fan.get_attribute('data-user-card'),poster,weight=1)

            except (TimeoutException,NoSuchElementException) as e:
                pass
        except TimeoutException as h:
            driver.quit()
            return LikeG
    driver.quit()
    return LikeG

def combine_graphs(graphL):
    to_ret = nx.DiGraph()
    for graph in graphL:
        for edge in graph.edges:
            if to_ret.has_edge(*edge):
                to_ret.edges[edge]['weight'] += graph.edges[edge]['weight']
            else:
                to_ret.add_edge(*edge,weight= graph.edges[edge]['weight'])
    return to_ret

if __name__ == "__main__":
    

    try:
        with open('json10k.p','rb') as f:
            jsonL = pickle.load(f)
    except Exception as e:
        print("Couldn't load from file, building json list...")
        #jsonL = [get_json_on_page(page) for page in range(1,NUM_PAGES+1)]

    topics = sum([js['topic_list']['topics'] for js in jsonL],[])
    urlbase = "https://us.forums.blizzard.com/en/wow/t/"
    topic_urls = [(get_topic_url(urlbase,topic),topic['posts_count']) for topic in topics]

    NUM_PROCS = 2
    pool = mp.Pool(NUM_PROCS)
    graphL = pool.map(update_like_graph,enumerate(topic_urls))
    pool.close()
    pool.join()

    G = combine_graphs(graphL)
    print("Writing to file...")
    nx.write_graphml(G,"ArenaLikeG.graphml")
    print("Done.")