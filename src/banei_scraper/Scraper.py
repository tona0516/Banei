import re
import datetime
from typing import List, Dict, Tuple

from .APIClient import APIClient
from .Config import Config
from .Output import Output
from .FileType import FileType
from .exception.ScraperException import ScraperException

def scrape(race_date: str, race_round: int) -> List:
    try:
        # URLを生成
        racecard_url = Config.URL_RACECARD + race_date + "03000000" + str(race_round).zfill(2)
        odds_url = Config.URL_ODDS + race_date + "03000000" + str(race_round).zfill(2)
        record_url = Config.URL_RECORD + race_date + "03000000" + str(race_round).zfill(2)

        # 各ページをスクレイピング
        race_dict, racecard_list, prize = __scrape_racecard(racecard_url)
        odds_list = __scrape_odds(odds_url)
        record_list = __scrape_record(record_url)
        
        # 各データを統合
        result_list = __merge(race_dict, racecard_list, odds_list, record_list, prize)
    except Exception as e:
        raise ScraperException(e.args)
    else:
        return result_list

def output_to_file(result_list: List, filepath: str, filetype=FileType.CSV):
    if filetype == FileType.CSV:
        Output.output_to_csv(result_list, filepath)
        return
    
    if filetype == FileType.JSON:
        Output.output_to_json(result_list, filepath)
        return

def __scrape_racecard(url: str) -> Tuple[Dict, List, List]:
    soup = APIClient.get_soup(url)

    div = soup.find('div', class_="raceNote")
    if div is None:
        raise ScraperException('message=\"No Match class namaed raceNote\", url=\"' + url + '\"')

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
        raise ScraperException('message=\"No Match class namaed raceCard\", url=\"' + url + '\"')

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

def __scrape_odds(url: str) -> List:
    soup = APIClient.get_soup(url)

    table = soup.find('tbody', class_='single selectWrap')
    if table is None:
        raise ScraperException('message=\"No Match class namaed single selectWrap\", url=\"' + url + '\"')

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

def __scrape_record(url: str) -> List:
    soup = APIClient.get_soup(url)

    table = soup.find('tbody', class_='record')
    if table is None:
        raise ScraperException('message=\"No Match class namaed record\", url=\"' + url + '\"')

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

def __merge(race_dict: Dict, racecard_list: List, odds_list: List, record_list: List, prize: List) -> List:
    output_list = []
    for (racecard, odds, record) in zip(racecard_list, odds_list, record_list):
        merged_dict = {}
        merged_dict.update(race_dict)
        merged_dict.update(racecard)
        merged_dict.update(odds)
        merged_dict.update(record)

        merged_dict = __process_dictionary(merged_dict, prize)
        output_list.append(merged_dict)
    return output_list

def __process_dictionary(merged_dict: Dict, prize: List) -> Dict:
    """
    各カラムの値を修正する
    """
    # 賞金の計算
    merged_dict["賞金"] = __calculate_prize(merged_dict, prize)

    # 「%」を削除
    merged_dict["勝率"] = merged_dict["勝率"].replace("%", "")
    merged_dict["3着内率"] = merged_dict["3着内率"].replace("%", "")

    # 連対時馬体重の計算
    weight = merged_dict.pop("連対時馬体重")
    if "|" in weight:
        weight = weight.split("|")
        merged_dict["連対時馬体重(下限)"] = weight[0]
        merged_dict["連対時馬体重(上限)"] = weight[1]
    else:
        merged_dict["連対時馬体重(下限)"] = "-"
        merged_dict["連対時馬体重(上限)"] = "-"

    # 体重と増減差の計算
    weight_updown_text = merged_dict.pop("馬体重増減")
    if "+" in weight_updown_text:
        weight_updown = weight_updown_text.split("+")
        merged_dict["馬体重(前走)"] = weight_updown[0]
        merged_dict["体重増減差"] = weight_updown[1]
    elif "-" in weight_updown_text:
        weight_updown = weight_updown_text.split("-")
        merged_dict["馬体重(前走)"] = weight_updown[0]
        merged_dict["体重増減差"] = "-" + weight_updown[1]
    elif "±" in weight_updown_text:
        weight_updown = weight_updown_text.split("±")
        merged_dict["馬体重(前走)"] = weight_updown[0]
        merged_dict["体重増減差"] = weight_updown[1]
    else:
        merged_dict["馬体重(前走)"] = "-"
        merged_dict["体重増減差"] = "-"

    # 日付の表記の修正
    race_date = merged_dict["日付"]
    race_date_datetime = datetime.datetime.strptime(race_date, "%Y年%m月%d日")
    merged_dict["日付"] = race_date_datetime.strftime("%Y年%m月%d日")

    # 誕生日の日付を修正
    birthday = merged_dict["誕生日"]
    birthday_datetime = datetime.datetime.strptime(birthday, "%Y/%m/%d生")
    merged_dict["誕生日"] = birthday_datetime.strftime("%Y年%m月%d日")

    # 性別と年齢を別カラムに分割
    gender_age_text = merged_dict.pop("性齢")
    merged_dict["性"] = gender_age_text[0]
    merged_dict["年齢"] = gender_age_text[1:]

    # オッズの計算
    merged_dict["単勝オッズ"] = merged_dict.pop("単勝オッズ")
    odds_place = merged_dict.pop("複勝オッズ").split(" - ")
    if len(odds_place) == 2:
        merged_dict["複勝オッズ(下限)"] = odds_place[0]
        merged_dict["複勝オッズ(上限)"] = odds_place[1]
    else:
        merged_dict["複勝オッズ(下限)"] = "-"
        merged_dict["複勝オッズ(上限)"] = "-"

    return merged_dict

def __calculate_prize(merged_dict: Dict, prize: List) -> int:
    if __can_convert_to_int(merged_dict["着順"]) and int(merged_dict["着順"]) - 1 < len(prize):
        return int(prize[int(merged_dict["着順"]) - 1])
    return 0

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
