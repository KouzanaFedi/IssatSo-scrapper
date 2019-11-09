import requests
from requests.exceptions import HTTPError
from bs4 import BeautifulSoup as Bs
import json
import re
from datetime import datetime

from parallel import ConcurrentPipeline
from concurrent.futures.thread import ThreadPoolExecutor
from concurrent.futures import as_completed


from functools import partial
from timeit import default_timer as timer

link = 'http://www.issatso.rnu.tn/fo/emplois/emploi_groupe.php'


def init():

    try:
        print("[+] Requesting...")
        print(f'{link}')
        response = requests.get(link)
        response.raise_for_status()
        print("[+] Requesting succeded")

        # making the soup
        soup = Bs(response.content, "html.parser")
        print("[+] Html parsing succeded")

        # scraping token
        jeton = soup.select_one('#jeton').get('value')

        # getting the cookie
        cookie = response.cookies.get_dict()

        return soup, jeton, cookie

    except HTTPError as err:

        print(f'HTTP error occured : {err}')
        print('[-] Requesting failed.')

    except Exception as err:

        print(f'Other error occured : {err}')
        print('[-] Requesting failed.')


def scrapGroups(soup):
    if soup:
        print("[+] Scraping groups")
        groupsList = [(group.text, group.get('value'))
                      for group in soup.select('option')]
        return groupsList
    else:
        print("Soup is empty")



def requestEmploi(jeton, cookie, group, id):
    try:

        print(f'[+] Setup to request {group} emploi...')
        data = {}
        data["jeton"] = jeton
        data["id"] = id

        print("[+] Requesting emploi...")
        currentTime = timer()

        response = requests.post(link, cookies=cookie, data=data)

        elapsed = timer() - currentTime
        response.raise_for_status()
        print("[+] Requesting succeded " + str(elapsed))
        return Bs(response.content, "html.parser")
    except HTTPError as err:

        print(f'HTTP error occured : {err}')
        print('[-] Requesting failed.')

    except Exception as err:

        print(f'Other error occured : {err}')
        print('[-] Requesting failed.')


def scrapEmploi(group,toScrap):
    res = {}

    htmlParsed = toScrap.select("div#dvContainer tbody tr")
    index = 0
    theads = ["Séance",
              "Deb",
              "Fin",
              "Matière",
              "Enseignant",
              "Type",
              "Salle",
              "Régime"]

    jours = [
        "1-Lundi",
        "2-Mardi",
        "3-Mercredi",
        "4-Jeudi",
        "5-Vendredi",
        "6-Samedi", ]
    jour = ""
    seance = {}
    sousGroup = ""
    inSeance = False
    start = True
    for row in htmlParsed:
        soupRow = Bs(str(row), "html.parser").select('center')
        for clmn in soupRow:
            if index > 7:
                index = 0
                inSeance = False
                res[sousGroup][jour].append(seance)
                seance = {}
            if clmn.text:
                if clmn.text == "10-Tous les Jours-PFE":
                    start = False
                elif re.search(r"-0[1-9]-[1-2]$", clmn.text):
                    if f'{group}-1' not in res:
                        sousGroup = f'{group}-1'
                        res[sousGroup] = {}
                    else:
                        sousGroup = f'{group}-2'
                        res[sousGroup] = {}
                elif clmn.text in jours:
                    start = True
                    jour = clmn.text
                    res[sousGroup][jour] = []
                elif start:
                    inSeance = True
                    if index == 1 or index == 2:
                        index += 1
                        pass
                    else:
                        seance[theads[index]] = clmn.text
                        index += 1
            elif inSeance:
                seance[theads[index]] = clmn.text
                index += 1

    return res


def groupClass(group):
    components = group.split('-')
    matchIndex = -1
    for component in components:
        if re.search(r"A[1-3]", component):
            matchIndex = components.index(component)
    if matchIndex == -1:
        return f'{group}'
    else:
        return f'{"-".join(str(e) for e in components[:matchIndex+1])}'


def main():
    current_time =timer()

    tokens = []
    token_number = 50
    tokensPipeline = ConcurrentPipeline(30)

    for _ in range(0,token_number):
        tokensPipeline.addToQueue(partial(init))
    
    tokens = tokensPipeline.result(asDic=False)
    groups = scrapGroups(tokens[0][0])

    dic = {}
    dic["schedules"] = {}
    jsonContent = ""

    pipeline = ConcurrentPipeline(50,50)

    it = 0
    for group in groups:
        it = (it+1) % token_number
        pipeline.addToQueue(
            partial(requestEmploi,tokens[it][1],tokens[it][2], group[0], group[1]),
            partial(scrapEmploi,group[0]))
    
    data = pipeline.result()
    for group in groups:
        classe = groupClass(group[0])
        if classe not in dic["schedules"]:
            dic["schedules"][classe] = {}
        matching = [s for s in data.keys() if group[0] in s]
        dic["schedules"][classe][group[0]]= {}
        temp = {}
        for m in matching:
            temp[m] = data[m]
        dic["schedules"][classe][group[0]] = temp

    dic["updateTime"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    jsonContent = json.dumps(dic, ensure_ascii=False)
    file = open('./test.json', 'w')
    file.write(jsonContent)
    file.close()
    
    elapsed =timer() - current_time
    print(str(elapsed))

if __name__ == "__main__":
    main()
