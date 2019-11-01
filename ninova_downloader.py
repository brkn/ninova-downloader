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


# Authentication error raised when wrong login credentials are given
class AuthError(Exception):
    pass


def getPage(session, url):
    '''GET the url'''
    kampusPage = session.get(url)   # Code duplication for some reason
    kampusPage = session.get(url)
    unsuccessfullURLext = "ogrenci.default.aspx"
    if kampusPage.url.find(unsuccessfullURLext) != -1:
        raise AuthError
    print("Current site: ", kampusPage.url)

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
        print('Folder already exists "' + path + '"')
        path = path + '_duplicate'
        os.mkdir(path)

    '''Create the necessary subfolders'''
    os.mkdir(path + os.sep + 'dersDosyalari')
    os.mkdir(path + os.sep + 'sinifDosyalari')
    os.mkdir(path + os.sep + 'odevKaynakDosyalari')

    return path


def capturePage(session, resourceTagList, rootFolder):
    '''Iterate through tags'''
    for tag in resourceTagList:

        '''Check for the icon, if it is a folder, create the subfolder,
            and enter, then call capturePage for the subfolder page'''
        if tag.findPrevious('img')['src'] == '/images/ds/folder.png':

            subFolder = rootFolder + os.sep + sanitizePath(tag.text)
            os.mkdir(subFolder)

            soup = getPage(session, url + tag['href'])
            links = getLinks(soup, 'Dosyalari?g')

            capturePage(session, links, subFolder)

        elif tag.findPrevious('img')['src'] == '/images/ds/link.png':
            '''If the icon is a link, dont touch it'''
            continue

        else:
            '''Download the rest'''
            r = session.get(url + tag['href'])
            saveFile(r, rootFolder + os.sep + sanitizePath(tag.text))


def tabularForm(nestedTableList):
    tableList = list(nestedTableList)
    maxCharacters = 50
    
    #if type of the item is a string, recursion should end.
    if isinstance(tableList[0], str):
        for counter, line in enumerate(tableList):
            if len(line) > maxCharacters:
                tableList.insert(counter + 1, line[maxCharacters:])
                tableList[counter] = line[:maxCharacters]
    else:
        #recurse for each item in list
        for counter, subList in enumerate(tableList):
            tableList[counter] = tabularForm(subList)
            
        #make sure right column and left column have equal amount of items
        #so that it is easy to concatenate them
        maxLength = 0
        for subList in tableList:
            maxLength = max(maxLength, len(subList))
        for subList in tableList:
            subList += [''] * (maxLength - len(subList))
            
    return tableList


def captureHomeworkDesc(soup, path, name):
    output = name + '\n-----------\n'

    #get due date from the soup
    dueDate = soup.find(string="Teslim Bitişi").find_next().get_text().strip()
    output += "Due date: " + dueDate + '\n-----------\nHomework Description:\n'

    #get homework description from the soup in a list form
    hwDesc = soup.find(string="Ödev Açıklaması").find_next().get_text().split('\n')
    hwDesc = list(filter(None, hwDesc))
    if hwDesc == []:
        hwDesc = ["No homework description given."]
        
    #add homework description to the output
    for line in tabularForm(hwDesc):
        output += line + '\n'
    output += '-----------\nRequested Files:\n'

    #get requested files section, in a list of rows of the table
    requestedFiles = soup.find(string="İstenen Dosyalar").find_next().find_all("tr")
    
    if len(requestedFiles) == 1:
        #if there's no files requested
        output += "You are not required to submit any files for the homework.\nFor more information, please contact the course instructor.\n"
        
    else:
        #drop header row of the table and seperate rows in the columns
        requestedFiles = requestedFiles[1:]
        table = []
        for row in requestedFiles:
            leftColumn = row.find_all("td")[0].get_text().strip().split('\n')
            leftColumn = [cell.strip() for cell in leftColumn]
            rightColumn = row.find_all("td")[1].get_text().strip().split('\n')
            rightColumn = [cell.strip() for cell in rightColumn]
            table.append([leftColumn, rightColumn])
            
        #format the table before joining to output
        table = tabularForm(table)
        
        #add requested files section to the output
        output += '{:^105}\n'.format('-'*80)
        for row in table:
            for counter in range(len(row[0])):
                output += '{:51} | {:51}\n'.format(row[0][counter].strip(), row[1][counter].strip())
            output += '{:^105}\n'.format('-'*80)
        
    outFile = open(path + os.sep + "homeworkDescription.txt", "w")
    outFile.write(output)
    outFile.close()


def captureClass(session, classTag, rootFolder):
    '''Create class folder'''
    newRoot = createDir(classTag, rootFolder)

    '''GET and capture lecture files'''
    pageSoup = getPage(session, url + classTag['href'] + '/DersDosyalari')
    links = getLinks(pageSoup, 'DersDosyalari?')
    path = '{}{}{}'.format(newRoot, os.sep, 'dersDosyalari')
    capturePage(session, links, path)

    '''GET and capture class files'''
    pageSoup = getPage(session, url + classTag['href'] + '/SinifDosyalari')
    links = getLinks(pageSoup, 'SinifDosyalari?')
    path = '{}{}{}'.format(newRoot, os.sep, 'sinifDosyalari')
    capturePage(session, links, path)

    '''GET and capture homework files'''
    parentSoup = getPage(session, url + classTag['href'] + '/Odevler')
    parentLinks = getLinks(parentSoup, 'Ödevi Görüntüle')
    homeworkIds = [link['href'].split('/')[-1] for link in parentLinks]
    #iterate over homework pages by id
    for id in homeworkIds:
        pageSoup = getPage(session, url + classTag['href'] + '/Odev/' + id)
        links = getLinks(pageSoup, id + '?')
        homeworkName = pageSoup.select('#ctl00_pnlHeader > h1')[0].string.strip()
        path = '{}{}{}{}{}'.format(newRoot, os.sep, 'odevKaynakDosyalari', os.sep, id + '_' + sanitizePath(homeworkName))
        os.mkdir(path)
        captureHomeworkDesc(pageSoup, path, homeworkName)
        capturePage(session, links, path)

def run():
    '''Create a session for cookie management'''
    s = requests.Session()

    '''Get the main page and class links from ninova'''
    # Check if the user entered their correct credentials
    loginSuccess = False
    while not loginSuccess:
        '''Get creds, get rich'''
        '''Get username'''
        username = input("Username: ")
        '''Get password with getpass module'''
        password = getpass.getpass("Pass: ")

        '''Log onto ITU account'''
        login(s, username, password)
        try:
            kampusSoup = getPage(s, url + '/Kampus1')
            loginSuccess = True
        except AuthError:
            print("There was an error logging in, please try again.")
            continue

    print("Login successful!\nDownloading...")
    classLinks = getLinks(kampusSoup, 'ErisimAgaci')

    '''Create a root folder for the dump'''
    rootFolder = './{}_{}_{}'.format('ninova',
                                     username,
                                     datetime.datetime.now().strftime('%d-%m-%y_%H:%M:%S')
                                     )
    try:
        os.mkdir(rootFolder)
    except OSError:
        rootFolder = rootFolder + '_duplicate'
        # How can one manage starting a code twice in a sec but errors can happen so we need to handle
        print('Duplicate folder created.')
        os.mkdir(rootFolder)
        return

    '''Capture parsed classes'''
    for link in classLinks:
        captureClass(s, link, rootFolder)


if __name__ == "__main__":
    run()
