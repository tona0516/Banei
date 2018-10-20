import re
import datetime
import csv

from .APIClient import APIClient
from .Config import Config
from .exception import APIClientException
from .exception import ParseException

def scrape(race_date, race_round):
    # URLを生成
    racecard_url: str = Config.URL_RACECARD + race_date + "03000000" + str(race_round).zfill(2)
    odds_url: str = Config.URL_ODDS + race_date + "03000000" + str(race_round).zfill(2)
    record_url: str = Config.URL_RECORD + race_date + "03000000" + str(race_round).zfill(2)

    # 各ページをスクレイピング
    race_dict, racecard_list, prize = __scrape_racecard(racecard_url)
    odds_list = __scrape_odds(odds_url)
    record_list = __scrape_record(record_url)
    
    # 各データを統合
    result_list = __merge(race_dict, racecard_list, odds_list, record_list, prize)
    
    return result_list

def __scrape_racecard(url):
    soup = APIClient.get_soup(url)

    div = soup.find('div', class_="raceNote")
    if div is None:
        raise ParseException('message=\"No Match class namaed raceNote\", url=\"' + url + '\"')

    race_dict = {
        "レース名": div.find("h2").text,
        "日付": div.find("ul", class_="trackState").find("li").text,
        "ラウンド": soup.find("div", class_="placeNumber").find("span", class_="num").text,
        "天候": div.find("ul", class_="trackState trackMainState").find_all("dd")[0].text,
        "馬場": div.find("ul", class_="trackState trackMainState").find_all("dd")[1].text.replace("%", "")
    }

    prize = __process_prize_text(div.find("dl", class_="prizeMoney").find("ol").text)

    table = soup.find('tbody', class_='raceCard')
    if table is None:
        raise ParseException('message=\"No Match class namaed raceCard\", url=\"' + url + '\"')

    tr = table.find_all('tr', class_=re.compile("^box"))

    racecard_list = []
    for _tr in tr:
        rows = [
            __extract_number(_tr),
            __extract_name(_tr),
            __extract_profile(_tr),
            __extract_weight(_tr),
            __extract_weight_distance(_tr)
        ]

        # カンマ区切りで繋がっているのでリストに整形し直す
        item = __adjust_comma(",".join(rows))
        result_list = __adjust_list(item.split(","))

        result_dic = {}
        for (result, label) in zip(result_list, Config.LABELS_RACECARD):
            if label == "オッズ":
                continue
            result_dic[label] = result
        racecard_list.append(result_dic)

    return race_dict, racecard_list, prize

def __scrape_odds(url):
    soup = APIClient.get_soup(url)

    table = soup.find('tbody', class_='single selectWrap')
    if table is None:
        raise ParseException('message=\"No Match class namaed single selectWrap\", url=\"' + url + '\"')

    tr = table.find_all('tr', class_=re.compile("^box"))

    odds_list = []
    for _tr in tr:
        rows = [
            __extract_number(_tr),
            __extract_win(_tr),
            __extract_place(_tr)
        ]

        # カンマ区切りで繋がっているのでリストに整形し直す
        item = __adjust_comma(",".join(rows))
        result_list = __adjust_list(item.split(","))

        result_dic = {}
        for (result, label) in zip(result_list, Config.LABELS_ODDS):
            result_dic[label] = result
        odds_list.append(result_dic)

    return odds_list

def __scrape_record(url):
    soup = APIClient.get_soup(url)

    table = soup.find('tbody', class_='record')
    if table is None:
        raise ParseException('message=\"No Match class namaed record\", url=\"' + url + '\"')

    tr = table.find_all('tr', class_=re.compile("^box"))
    
    odds_list = []
    for _tr in tr:
        rows = [
            __extract_number(_tr),
            __extract_order(_tr),
            __extract_time(_tr)
        ]

        # カンマ区切りで繋がっているのでリストに整形し直す
        item = __adjust_comma(",".join(rows))
        result_list = __adjust_list(item.split(","))

        result_dic = {}
        for (result, label) in zip(result_list, Config.LABELS_RECORD):
            result_dic[label] = result
        odds_list.append(result_dic)

    return odds_list

def __merge(race_dict, racecard_list, odds_list, record_list, prize):
    output_list = []
    for (racecard, odds, record) in zip(racecard_list, odds_list, record_list):
        dict = {}
        dict.update(race_dict)
        dict.update(racecard)
        dict.update(odds)
        dict.update(record)

        # 賞金の計算
        if __can_convert_to_int(dict["着順"]) and int(dict["着順"]) - 1 < len(prize):
            dict["賞金"] = prize[int(dict["着順"]) - 1]
        else:
            dict["賞金"] = "0"
        dict = __process_dictionary(dict)
        output_list.append(dict)
    return output_list

# def write_to_csv(file_path):
#     if result_list:
#         with open(file_path, "w") as f:
#             header = result_list[0].keys()
#             writer = csv.DictWriter(f, fieldnames=header, delimiter=',')
#             writer.writeheader()
#             for row in result_list:
#                 writer.writerow(row)
#             logger.debug("outputted file >> " + file_path)
#     else:
#         logger.debug("no result >> " + file_path)

#     return self

def __process_dictionary(dict):
    dict["勝率"] = dict["勝率"].replace("%", "")
    dict["3着内率"] = dict["3着内率"].replace("%", "")

    weight = dict.pop("連対時馬体重")
    if "|" in weight:
        weight = weight.split("|")
        dict["連対時馬体重(下限)"] = weight[0]
        dict["連対時馬体重(上限)"] = weight[1]
    else:
        dict["連対時馬体重(下限)"] = "-"
        dict["連対時馬体重(上限)"] = "-"

    weight_updown_text = dict.pop("馬体重増減")
    if "+" in weight_updown_text:
        weight_updown = weight_updown_text.split("+")
        dict["馬体重(前走)"] = weight_updown[0]
        dict["体重増減差"] = weight_updown[1]
    elif "-" in weight_updown_text:
        weight_updown = weight_updown_text.split("-")
        dict["馬体重(前走)"] = weight_updown[0]
        dict["体重増減差"] = "-" + weight_updown[1]
    elif "±" in weight_updown_text:
        weight_updown = weight_updown_text.split("±")
        dict["馬体重(前走)"] = weight_updown[0]
        dict["体重増減差"] = weight_updown[1]
    else:
        dict["馬体重(前走)"] = "-"
        dict["体重増減差"] = "-"

    race_date = dict["日付"]
    race_date_datetime = datetime.datetime.strptime(race_date, "%Y年%m月%d日")
    dict["日付"] = race_date_datetime.strftime("%Y年%m月%d日")

    birthday = dict["誕生日"]
    birthday_datetime = datetime.datetime.strptime(birthday, "%Y/%m/%d生")
    dict["誕生日"] = birthday_datetime.strftime("%Y年%m月%d日")

    gender_age_text = dict.pop("性齢")
    dict["性"] = gender_age_text[0]
    dict["年齢"] = gender_age_text[1:]

    dict["単勝オッズ"] = dict.pop("単勝オッズ")
    odds_place = dict.pop("複勝オッズ").split(" - ")
    if len(odds_place) == 2:
        dict["複勝オッズ(下限)"] = odds_place[0]
        dict["複勝オッズ(上限)"] = odds_place[1]
    else:
        dict["複勝オッズ(下限)"] = "-"
        dict["複勝オッズ(上限)"] = "-"

    return dict


def __process_prize_text(text):
    prize_list = []
    prizes = text.split("\n")
    for prize in prizes:
        if len(prize) > 0:
            prize_list.append(re.sub(".着", "", prize).replace(",", "").replace("円", ""))
    return prize_list

def __extract_number(html):
    if html.find('td', class_=Config.CLASS_NUMBER) is None:
        return "-"
    text = html.find('td', class_=Config.CLASS_NUMBER).text
    text = __newline_to_comma(text)
    text = __remove_brackets(text)
    return text

def __extract_name(html):
    if html.find('td', class_=Config.CLASS_NAME) is None:
        return "-"
    text = html.find('td', class_=Config.CLASS_NAME).text
    text = __newline_to_comma(text)
    text = __remove_brackets(text)
    return text

def __extract_profile(html):
    if html.find('td', class_=Config.CLASS_PROFILE) is None:
        return "-"
    text = html.find('td', class_=Config.CLASS_PROFILE).text
    text = __newline_to_comma(text)
    text = __remove_brackets(text)
    return text

def __extract_weight(html):
    if html.find('td', class_=Config.CLASS_WEIGHT) is None:
        return "-"
    text = html.find('td', class_=Config.CLASS_WEIGHT).text
    text = __newline_to_comma(text)
    text = __remove_brackets(text)
    return text

def __extract_weight_distance(html):
    if html.find('td', class_=Config.CLASS_WEIGHT_DISTANCE) is None:
        return "-"
    text = html.find('td', class_=Config.CLASS_WEIGHT_DISTANCE).text
    text = __newline_to_comma(text)
    text = __remove_brackets(text)
    return text

def __extract_win(html):
    if html.find('td', class_=Config.CLASS_ODDS_WIN) is None:
        return "-"
    text = html.find('td', class_=Config.CLASS_ODDS_WIN).text
    text = __newline_to_comma(text)
    text = __remove_brackets(text)
    return text

def __extract_place(html):
    if html.find('td', class_=Config.CLASS_ODDS_PLACE) is None:
        return "-"
    text = html.find('td', class_=Config.CLASS_ODDS_PLACE).text
    text = __newline_to_comma(text)
    text = __remove_brackets(text)
    return text

def __extract_order(html):
    if html.find('td', class_=Config.CLASS_ORDER) is None:
        return "-"
    text = html.find('td', class_=Config.CLASS_ORDER).text
    text = __newline_to_comma(text)
    text = __remove_brackets(text)
    return text

def __extract_time(html):
    if html.find('td', class_=Config.CLASS_TIME) is None:
        return "-"
    text = html.find('td', class_=Config.CLASS_TIME).text
    text = __newline_to_comma(text)
    text = __remove_brackets(text)
    return text

def __newline_to_comma(text):
    return text.replace("<br>", ",").replace("\n", ",")

def __adjust_comma(text):
    return re.sub(",{2,}", ",", text)

def __adjust_list(list):
    output_list = []
    for item in list:
        if len(item) > 0:
            output_list.append(item)
    return output_list

def __find_item_by_word(array, word):
    for item in array:
        if word in item:
            return item
    return ""

def __can_convert_to_int(text):
    try:
        int(text)
        return True
    except ValueError:
        return False

def __remove(text, array):
    for item in array:
        text.replace(item, "")

def __remove_brackets(text):
    return text.replace("(", "").replace(")", "").replace("（", "").replace("）", "").replace("【", "").replace("】", "")
