import re
import datetime
from typing import List, Dict, Tuple

from .APIClient import APIClient
from .Config import Config
from .Output import Output
from .FileType import FileType
from .ScrapeUtil import ScrapeUtil
from .exception.ScraperException import ScraperException


def scrape(race_date: str, race_round: int) -> List:
    # URLを生成
    racecard_url = Config.URL_RACECARD + race_date + "03000000" + str(race_round).zfill(2)
    odds_url = Config.URL_ODDS + race_date + "03000000" + str(race_round).zfill(2)
    record_url = Config.URL_RECORD + race_date + "03000000" + str(race_round).zfill(2)

    # 各ページをスクレイピング
    race_dict, racecard_list, prizes = __scrape_racecard(racecard_url)
    odds_list = __scrape_odds(odds_url)
    record_list = __scrape_record(record_url)

    # 各データを統合
    result_list = __merge(race_dict, racecard_list, odds_list, record_list, prizes)

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

    race_name = div.find("h2").text
    race_date = div.find("ul", class_="trackState").find("li").text
    race_round = soup.find("div", class_="placeNumber").find("span", class_="num").text
    try:
        race_weather = div.find("ul", class_="trackState trackMainState").find_all("dd")[0].text
        race_condition = div.find("ul", class_="trackState trackMainState").find_all("dd")[1].text.replace("%", "")
    except IndexError:
        race_weather = '-'
        race_condition = '-'
    race_dict = {
        "レース名": race_name,
        "日付": race_date,
        "ラウンド": race_round,
        "天候": race_weather,
        "馬場": race_condition,
    }

    prizes = __extract_prizes(div.find("dl", class_="prizeMoney").find("ol").text)

    table = soup.find('tbody', class_='raceCard')
    if table is None:
        raise ScraperException('message=\"No Match class namaed raceCard\", url=\"' + url + '\"')

    tr_list = table.find_all('tr', class_=re.compile("^box"))

    racecard_list = []
    for tr in tr_list:
        rows = [
            ScrapeUtil.extract_inner_text(tr, Config.CLASS_NUMBER),
            ScrapeUtil.extract_inner_text(tr, Config.CLASS_NAME),
            ScrapeUtil.extract_inner_text(tr, Config.CLASS_PROFILE),
            ScrapeUtil.extract_inner_text(tr, Config.CLASS_WEIGHT),
            ScrapeUtil.extract_inner_text(tr, Config.CLASS_WEIGHT_DISTANCE),
        ]

        # 要素内がカンマ区切りで繋がっているのでリストに整形し直す
        result_list = ScrapeUtil.comma_to_list(rows)

        result_dic = {}
        for (result, label) in zip(result_list, Config.LABELS_RACECARD):
            if label == "オッズ":
                continue
            result_dic[label] = result
        racecard_list.append(result_dic)

    return race_dict, racecard_list, prizes


def __scrape_odds(url: str) -> List:
    soup = APIClient.get_soup(url)

    table = soup.find('tbody', class_='single selectWrap')
    if table is None:
        raise ScraperException('message=\"No Match class namaed single selectWrap\", url=\"' + url + '\"')

    tr_list = table.find_all('tr', class_=re.compile("^box"))

    odds_list = []
    for tr in tr_list:
        rows = [
            ScrapeUtil.extract_inner_text(tr, Config.CLASS_NUMBER),
            ScrapeUtil.extract_inner_text(tr, Config.CLASS_ODDS_WIN),
            ScrapeUtil.extract_inner_text(tr, Config.CLASS_ODDS_PLACE),
        ]

        # 要素内がカンマ区切りで繋がっているのでリストに整形し直す
        result_list = ScrapeUtil.comma_to_list(rows)

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

    tr_list = table.find_all('tr', class_=re.compile("^box"))
    
    odds_list = []
    for tr in tr_list:
        rows = [
            ScrapeUtil.extract_inner_text(tr, Config.CLASS_NUMBER),
            ScrapeUtil.extract_inner_text(tr, Config.CLASS_ORDER),
            ScrapeUtil.extract_inner_text(tr, Config.CLASS_TIME),
        ]

        # 要素内がカンマ区切りで繋がっているのでリストに整形し直す
        result_list = ScrapeUtil.comma_to_list(rows)

        result_dic = {}
        for (result, label) in zip(result_list, Config.LABELS_RECORD):
            result_dic[label] = result
        odds_list.append(result_dic)

    return odds_list


def __merge(race_dict: Dict, racecard_list: List, odds_list: List, record_list: List, prizes: List) -> List:
    output_list = []
    for (racecard, odds, record) in zip(racecard_list, odds_list, record_list):
        merged_dict = {}
        merged_dict.update(race_dict)
        merged_dict.update(racecard)
        merged_dict.update(odds)
        merged_dict.update(record)
        merged_dict["賞金"] =  __get_prize(merged_dict["着順"], prizes)

        merged_dict = __fix(merged_dict)
        output_list.append(merged_dict)
    return output_list


def __fix(merged_dict: Dict) -> Dict:
    """
    各カラムの値を修正する
    """
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
    try:
        birthday_datetime = datetime.datetime.strptime(birthday, "%Y/%m/%d生")
    except ValueError:
        merged_dict["誕生日"] = '-'
    else:
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


def __get_prize(order: str, prizes: List) -> int:
    try:
        prize_index = int(order) - 1
        if 0 <= prize_index < len(prizes):
            prize = int(prizes[prize_index])
        else:
            return 0
    except ValueError:
        return 0
    else:
        return prize


def __extract_prizes(text: str) -> List:
    return re.sub('[0-9]+着', '', text).replace('円', '').replace(',', '').split("\n")
