import requests
from bs4 import BeautifulSoup
from bs4.element import Comment
import re
import validators
import time
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from TopicExtraction import predictCategory


#Inspired by https://stackoverflow.com/questions/1936466/beautifulsoup-grab-visible-webpage-text
def tag_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
        return False
    if isinstance(element, Comment):
        return False
    return True

def stringExtract(soup):
    soup = BeautifulSoup(soup, 'html.parser')
    texts = soup.findAll(text=True)
    visibleText = filter(tag_visible, texts)
    allText = []

    for t in visibleText:
        t = str(t.strip())
        t = re.split(r'([(|\]])+(|\. )+' ,t)

        for text in t:
            text = re.sub(r'[\)|\]]', '',text)
            if len(text)>0:
                allText.append(text)
    return allText


#Iteratively depth checks surrounding elements to a particular element (Button)
def depthCheckHTML(soup,word,buttonClassIds):
    if not isinstance(soup,str):
        soup = str(soup)
    if not isinstance(word,str):
        word = str(word)

    checkLevel = 0
    newRowCount = 0
    stoppingCond = False
    soupLength = len(soup)

    while not stoppingCond :
        #print("***CHECK LEVEL ",checkLevel, "***")

        if checkLevel == 0:
            startIndex = soup.find(word)
            endIndex = startIndex+len(word)

        rowCount = newRowCount
        deepSoup = soup[startIndex:endIndex+1]

        interiorTagCount = 0
        foundStart = False
        foundEnd = False


        while foundStart == False:
            startIndex = startIndex -1
            if startIndex<1:
                return soup,deepSoup
            if soup[startIndex] == "<":
                if soup[startIndex+1] == "/":
                    interiorTagCount+=2
                if interiorTagCount ==0:
                    foundStart = True
                interiorTagCount -=1
            elif soup[startIndex] == ">":
                if soup[startIndex-1] == "/":
                    interiorTagCount += 1

        interiorTagCount = 0

        while foundEnd == False:
            endIndex = endIndex +1
            if endIndex >= soupLength:
                return soup, deepSoup
            if soup[endIndex] == ">":
                if interiorTagCount ==0:
                    foundEnd = True
                interiorTagCount-=1
            elif soup[endIndex] == "<":
                if soup[endIndex+1] != "/":
                    interiorTagCount += 1


        eventHTML = BeautifulSoup(soup[startIndex:endIndex+1], 'html.parser')
        buttonsInSoup = eventHTML.find_all('button')

        newRowCount = eventHTML.prettify().count('\n')+1
        #print("newRow = ",newRowCount," oldRow = ",rowCount)


        #If the number of rows is increasing by more than 10 this turn and it isn't the first turn then stop the depth search
        if (newRowCount-rowCount)>10 and rowCount!=0:
            stoppingCond = True
            #print("STOP DEPTH-SEARCH: Row Increase Too Large")
            return soup,deepSoup

        #If there are more than one button then compare the button classes with those of our buttonClassIds to see if we are including
        #repeats of the same button.
        elif len(buttonsInSoup)!=1:
            buttonsInSoup.pop() #The first element is always the target button, so this is removed for this check

            for buttons in buttonsInSoup:
                classInSoup = " ".join(buttons['class'])
                for classInList in buttonClassIds:
                    if classInSoup == classInList:
                        stoppingCond = True
                        #print("STOP DEPTH-SEARCH: Too Many Buttons")
                        return soup,deepSoup

        checkLevel+=1
    return soup,deepSoup


#Returns the number of events and prints these events out topic by topic
def extractEvent(baseUrl,URL,soup):
    soup = str(soup)
    soup = BeautifulSoup(soup, 'html.parser')

    buttonMentions = soup.find_all('button',{"class":True})
    buttonClassIds = []
    buttonCount=0
    eventCount=0
    topicCount=0

    for button in buttonMentions:
        buttonCount+=1
        #print("\nBUTTON MENTION ",buttonCount)
        buttonClassIds.append(" ".join(button['class']))

        depthCheckResults = depthCheckHTML(soup,button,buttonClassIds)
        soup = depthCheckResults[0]
        deepSoup = depthCheckResults[1]

        soupStrExtract = stringExtract(soup)
        deepSoupStrExtract = stringExtract(deepSoup)

        if len(soupStrExtract) >0 and len(deepSoupStrExtract)>0:
            topics = predictCategory(deepSoupStrExtract,soupStrExtract)
            if topics>2:
                eventCount+=1
                topicCount +=topics


    return eventCount , topicCount
