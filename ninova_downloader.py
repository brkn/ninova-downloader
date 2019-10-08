import requests
import bs4
import getpass
import os
import datetime
import shutil

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


def mergeFolders(root_src_dir, root_dst_dir):
    for src_dir, dirs, files in os.walk(root_src_dir):
        dst_dir = src_dir.replace(root_src_dir, root_dst_dir, 1)
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        for file_ in files:
            src_file = os.path.join(src_dir, file_)
            dst_file = os.path.join(dst_dir, file_)
            if os.path.exists(dst_file):
                os.remove(dst_file)
            shutil.copy(src_file, dst_dir)



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

    # Check if the same user already has a rootFolder
    ninova_list = os.listdir("./")
    existing_ninova = False
    overwrite = 'n'
    while not existing_ninova:
        for item in ninova_list:
            if item.find('{}_{}'.format('ninova',username)) != -1:
                existing_ninova = True
                print("The user " + username + " already has a Ninova folder")
                overwrite = input("Do you want to update the existing folder (y/n): ")
                existing_path = item
                break
        break


    rootFolder = './{}_{}_{}'.format('ninova',
                                     username,
                                     datetime.datetime.now().strftime('%d-%m-%y_%H:%M:%S')
                                     )
    '''Create a root folder for the dump'''
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

    # Once all the downloads are done, merge old ninova with the new one
    if existing_ninova and overwrite == 'y':
        mergeFolders(rootFolder, existing_path)
        print("Merging finished.")
        shutil.rmtree(rootFolder)
        os.rename(f'{existing_path}', f'{rootFolder}')

if __name__ == "__main__":
    run()
