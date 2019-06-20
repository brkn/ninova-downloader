import requests
import bs4
import getpass
import os
import datetime

'''Base URL'''
url = 'https://ninova.itu.edu.tr'


def login(s, username, password):

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


def sanitizePath(s):
    return s.replace('/', '').replace(':', '')


def createDir(classTag, rootFolder):

    path = '{}{}{}_({})'.format(rootFolder, 
                                os.sep,
                                sanitizePath(classTag.findPrevious('span').text),
                                sanitizePath(classTag.findNext('span').text)
                                )

    '''Try creating a new folder'''
    try:
        os.mkdir(path)

    except FileExistsError:
        '''If folder exists, create a new one'''
        print('Folder already exists "'+path+'"')
        path = path + '_duplicate'
        os.mkdir(path)

    '''Create the necessary subfolders'''
    os.mkdir(path + os.sep + 'dersDosyalari')
    os.mkdir(path + os.sep + 'sinifDosyalari')

    return path


def capturePage(session, resourceTagList, rootFolder):

    '''Iterate through tags'''
    for tag in resourceTagList:

        '''Check for the icon, if it is a folder, create the subfolder,
            and enter, then call capturePage for the subfolder page'''
        if tag.findPrevious('img')['src'] == '/images/ds/folder.png':

            subFolder = rootFolder + os.sep + sanitizePath(tag.text)
            os.mkdir(subFolder)

            soup = getPage(session, url+tag['href'])
            links = getLinks(soup, 'Dosyalari?g')

            capturePage(session, links, subFolder)

        elif tag.findPrevious('img')['src'] == '/images/ds/link.png':
            '''If the icon is a link, dont touch it'''
            continue

        else:
            '''Download the rest'''
            r = session.get(url+tag['href'])
            saveFile(r, rootFolder + os.sep + sanitizePath(tag.text))


def captureClass(session, classTag, rootFolder):

    '''Create class folder'''
    newRoot = createDir(classTag, rootFolder)

    '''GET and capture lecture files'''
    pageSoup = getPage(session, url+classTag['href']+'/DersDosyalari')
    links = getLinks(pageSoup, 'DersDosyalari?')
    path = '{}{}{}'.format(newRoot, os.sep, 'dersDosyalari')
    capturePage(session, links, path)

    '''GET and capture class files'''
    pageSoup = getPage(session, url+classTag['href']+'/SinifDosyalari')
    links = getLinks(pageSoup, 'SinifDosyalari?')
    path = '{}{}{}'.format(newRoot, os.sep, 'sinifDosyalari')
    capturePage(session, links, path)


def run():

    '''Create a session for cookie management'''
    s = requests.Session()

    '''Get creds, get rich'''
    '''Get username'''
    username = input("username: ")
    '''Get password with getpass module, cuz muh privacy'''
    password = getpass.getpass("pass: ")

    '''Log onto ITU account'''
    login(s, username, password)

    '''Get the main page and class links from ninova'''
    kampusSoup = getPage(s, url+'/Kampus1')
    classLinks = getLinks(kampusSoup, 'ErisimAgaci')

    '''Create a root folder for the dump'''
    rootFolder = './{}_{}_{}'.format('ninova',
                                    username,
                                    datetime.datetime.now().strftime('%d-%m-%y')
                                    )
    try:
        os.mkdir(rootFolder)
    except OSError:
        print('Folder already exists!')
        return

    '''Capture parsed classes'''
    for link in classLinks:
        captureClass(s, link, rootFolder)


if __name__ == "__main__":
    run()