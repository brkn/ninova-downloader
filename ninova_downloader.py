import requests
import bs4
import getpass
import os


def login(s):

    '''Get username'''
    username = input("username: ")
    '''Get password with getpass module, cuz muh privacy'''
    password = getpass.getpass("pass: ")

    '''Try to get main page of ninova'''
    r = s.get('http://ninova.itu.edu.tr/kampus')

    '''Parse the returned page with bs4'''
    forms = bs4.BeautifulSoup(r.text, 'html.parser').findAll('input')

    '''Fill POST data'''
    data = {}
    for form in forms:
        if 'value' in form.attrs:
            data[form['name']] = form['value']
        else:
            data[form['name']] = ""
    data['__EVENTTARGET'] = ''
    data['__EVENTARGUMENT'] = ''
    data['ctl00$ContentPlaceHolder1$tbUserName'] = username,
    data['ctl00$ContentPlaceHolder1$tbPassword'] = password,

    '''Login and return'''
    return s.post(r.url, data=data)


def getPage(session, url):

    '''GET the url'''
    kampusPage = session.get(url)
    print(kampusPage.url)

    '''Return parsed data'''
    return bs4.BeautifulSoup(kampusPage.text, 'html.parser')


def getLinks(soup, filterString):

    '''Fill the list with relevant links'''
    tags = []
    for line in soup.find_all('a'):
        '''Only links with filterString in them'''
        if filterString in str(line):
            tags.append(line)

    '''Return the list of tags'''
    return tags


def saveFile(r, name):

    '''Save the content of response to file "name"'''
    f = open(name, 'wb')
    f.write(r.content)
    f.close()


def mkdir(classTag):

    '''Get cwd'''
    root = os.getcwd()

    name = classTag.findPrevious('span').text

    '''Try creating a new folder'''
    try:
        os.mkdir(name)

    except FileExistsError:
        '''If folder exists, create a new one'''
        print('Folder already exists "'+name+'"')
        name = name+' (dup)'
        os.mkdir(name)

    os.chdir(name)

    '''Create the necessary subfolders'''
    os.mkdir('dersDosyalari')
    os.mkdir('sinifDosyalari')

    '''Go back'''
    os.chdir(root)

    return name


def capturePage(session, resourceTagList):

    '''Iterate through tags'''
    for tag in resourceTagList:

        '''Check for the icon, if it is a folder, create the subfolder,
            and enter, then call capturePage for the subfolder page'''
        if tag.findPrevious('img')['src'] == '/images/ds/folder.png':

            '''Get root directory'''
            root = os.getcwd()

            os.mkdir(tag.text)
            os.chdir(tag.text)

            soup = getPage(session, url+tag['href'])
            links = getLinks(soup, 'Dosyalari?g')

            capturePage(session, links)

            '''Go back when done'''
            os.chdir(root)

        elif tag.findPrevious('img')['src'] == '/images/ds/link.png':
            '''If the icon is a link, dont touch it'''
            continue

        else:
            '''Download the rest'''
            r = session.get(url+tag['href'])
            f = open(tag.text, 'wb')
            f.write(r.content)
            f.close()


def captureClass(session, classTag):

    '''Get root directory'''
    root = os.getcwd()

    '''Create class folder'''
    name = mkdir(link)
    os.chdir(name)

    '''GET and capture lecture files'''
    pageSoup = getPage(s, url+link['href']+'/DersDosyalari')
    links = getLinks(pageSoup, 'DersDosyalari?')
    os.chdir('dersDosyalari')
    capturePage(session, links)
    os.chdir('..')

    '''GET and capture class files'''
    pageSoup = getPage(s, url+link['href']+'/SinifDosyalari')
    links = getLinks(pageSoup, 'SinifDosyalari?')
    os.chdir('sinifDosyalari')
    capturePage(session, links)

    '''Go back to root when done'''
    os.chdir(root)


'''Base URL'''
url = 'http://ninova.itu.edu.tr'

'''Create a session for cookie management'''
s = requests.Session()

'''Login to ITU account'''
login(s)

'''Get the main page and class links from ninova'''
kampusSoup = getPage(s, url+'/Kampus1')
classLinks = getLinks(kampusSoup, 'ErisimAgaci')

'''Capture parsed classes'''
for link in classLinks:
    captureClass(s, link)
