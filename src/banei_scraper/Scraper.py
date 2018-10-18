import re
import datetime
import csv

from .APIClient import APIClient
from .Config import Config
from .exception import APIClientException
from .exception import ParseException

class Scraper:
    def __init__(self, race_date: str, race_round: str, logger):
        self.race_date: str = race_date
        self.race_no: str = race_round
        self.racecard_url: str = Config.URL_RACECARD + race_date + "03000000" + race_round.zfill(2)
        self.odds_url: str = Config.URL_ODDS + race_date + "03000000" + race_round.zfill(2)
        self.record_url: str = Config.URL_RECORD + race_date + "03000000" + race_round.zfill(2)

        self.logger = logger
        self.result_list = []

    def scrape(self):
        try:
            race_dict, racecard_list, prize = self.__scrape_racecard(self.racecard_url)
            odds_list = self.__scrape_odds(self.odds_url)
            record_list = self.__scrape_record(self.record_url)
        except ParseException as e:
            self.logger.warning(e.message)
            raise
        except APIClientException:
            raise
        else:
            self.result_list = self.__integrate(race_dict, racecard_list, odds_list, record_list, prize)
            return self

    def __integrate(self, race_dict, racecard_list, odds_list, record_list, prize):
        output_list = []
        for (racecard, odds, record) in zip(racecard_list, odds_list, record_list):
            dict = {}
            dict.update(race_dict)
            dict.update(racecard)
            dict.update(odds)
            dict.update(record)
            if self.__can_convert_to_int(dict["着順"]) and int(dict["着順"]) - 1 < len(prize):
                dict["賞金"] = prize[int(dict["着順"]) - 1]
            else:
                dict["賞金"] = "0"
            dict = self.__process_dictionary(dict)
            output_list.append(dict)
        return output_list

    def write_to_csv(self, file_path):
        if self.result_list:
            with open(file_path, "w") as f:
                header = self.result_list[0].keys()
                writer = csv.DictWriter(f, fieldnames=header, delimiter=',')
                writer.writeheader()
                for row in self.result_list:
                    writer.writerow(row)
                self.logger.debug("outputted file >> " + file_path)
        else:
            self.logger.debug("no result >> " + file_path)

        return self

    def __process_dictionary(self, dict):
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

    def __scrape_racecard(self, url):
        soup = APIClient.get_soup(url)

        # par race note
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

        prize = self.__process_prize_text(div.find("dl", class_="prizeMoney").find("ol").text)

        # parse candidate data
        table = soup.find('tbody', class_='raceCard')
        if table is None:
            raise ParseException('message=\"No Match class namaed raceCard\", url=\"' + url + '\"')

        tr = table.find_all('tr', class_=re.compile("^box"))

        candidate_list = []
        for _tr in tr:
            rows = []
            rows.append(self.__extract_number(_tr))
            rows.append(self.__extract_name(_tr))
            rows.append(self.__extract_profile(_tr))
            rows.append(self.__extract_weight(_tr))
            rows.append(self.__extract_weight_distance(_tr))
            item = self.__adjust_comma(",".join(rows))
            result_list = self.__adjust_list(item.split(","))
            result_dic = {}
            for (result, label) in zip(result_list, Config.LABELS_RACECARD):
                if label == "オッズ":
                    continue
                result_dic[label] = result
            candidate_list.append(result_dic)
        return race_dict, candidate_list, prize

    def __scrape_odds(self, url):
        soup = APIClient.get_soup(url)

        table = soup.find('tbody', class_='single selectWrap')
        if table is None:
            raise ParseException('message=\"No Match class namaed single selectWrap\", url=\"' + url + '\"')

        tr = table.find_all('tr', class_=re.compile("^box"))

        odds_list = []
        for _tr in tr:
            rows = []
            rows.append(self.__extract_number(_tr))
            rows.append(self.__extract_win(_tr))
            rows.append(self.__extract_place(_tr))
            item = self.__adjust_comma(",".join(rows))
            result_list = self.__adjust_list(item.split(","))
            result_dic = {}
            for (result, label) in zip(result_list, Config.LABELS_ODDS):
                result_dic[label] = result
            odds_list.append(result_dic)
        return odds_list

    def __scrape_record(self, url):
        soup = APIClient.get_soup(url)

        table = soup.find('tbody', class_='record')
        if table is None:
            raise ParseException('message=\"No Match class namaed record\", url=\"' + url + '\"')
        tr = table.find_all('tr', class_=re.compile("^box"))
        odds_list = []
        for _tr in tr:
            rows = []
            rows.append(self.__extract_number(_tr))
            rows.append(self.__extract_order(_tr))
            rows.append(self.__extract_time(_tr))
            item = self.__adjust_comma(",".join(rows))
            result_list = self.__adjust_list(item.split(","))
            result_dic = {}
            for (result, label) in zip(result_list, Config.LABELS_RECORD):
                result_dic[label] = result
            odds_list.append(result_dic)
        return odds_list
        

    def __process_prize_text(self, text):
        prize_list = []
        prizes = text.split("\n")
        for prize in prizes:
            if len(prize) > 0:
                prize_list.append(re.sub(".着", "", prize).replace(",", "").replace("円", ""))
        return prize_list

    def __extract_number(self, html):
        if html.find('td', class_=Config.CLASS_NUMBER) is None:
            return "-"
        text = html.find('td', class_=Config.CLASS_NUMBER).text
        text = self.__newline_to_comma(text)
        text = self.__remove_brackets(text)
        return text

    def __extract_name(self, html):
        if html.find('td', class_=Config.CLASS_NAME) is None:
            return "-"
        text = html.find('td', class_=Config.CLASS_NAME).text
        text = self.__newline_to_comma(text)
        text = self.__remove_brackets(text)
        return text

    def __extract_profile(self, html):
        if html.find('td', class_=Config.CLASS_PROFILE) is None:
            return "-"
        text = html.find('td', class_=Config.CLASS_PROFILE).text
        text = self.__newline_to_comma(text)
        text = self.__remove_brackets(text)
        return text

    def __extract_weight(self, html):
        if html.find('td', class_=Config.CLASS_WEIGHT) is None:
            return "-"
        text = html.find('td', class_=Config.CLASS_WEIGHT).text
        text = self.__newline_to_comma(text)
        text = self.__remove_brackets(text)
        return text

    def __extract_weight_distance(self, html):
        if html.find('td', class_=Config.CLASS_WEIGHT_DISTANCE) is None:
            return "-"
        text = html.find('td', class_=Config.CLASS_WEIGHT_DISTANCE).text
        text = self.__newline_to_comma(text)
        text = self.__remove_brackets(text)
        return text

    def __extract_win(self, html):
        if html.find('td', class_=Config.CLASS_ODDS_WIN) is None:
            return "-"
        text = html.find('td', class_=Config.CLASS_ODDS_WIN).text
        text = self.__newline_to_comma(text)
        text = self.__remove_brackets(text)
        return text

    def __extract_place(self, html):
        if html.find('td', class_=Config.CLASS_ODDS_PLACE) is None:
            return "-"
        text = html.find('td', class_=Config.CLASS_ODDS_PLACE).text
        text = self.__newline_to_comma(text)
        text = self.__remove_brackets(text)
        return text

    def __extract_order(self, html):
        if html.find('td', class_=Config.CLASS_ORDER) is None:
            return "-"
        text = html.find('td', class_=Config.CLASS_ORDER).text
        text = self.__newline_to_comma(text)
        text = self.__remove_brackets(text)
        return text

    def __extract_time(self, html):
        if html.find('td', class_=Config.CLASS_TIME) is None:
            return "-"
        text = html.find('td', class_=Config.CLASS_TIME).text
        text = self.__newline_to_comma(text)
        text = self.__remove_brackets(text)
        return text

    def __newline_to_comma(self, text):
        return text.replace("<br>", ",").replace("\n", ",")

    def __adjust_comma(self, text):
        return re.sub(",{2,}", ",", text)

    def __adjust_list(self, list):
        output_list = []
        for item in list:
            if len(item) > 0:
                output_list.append(item)
        return output_list


    def __find_item_by_word(self, array, word):
        for item in array:
            if word in item:
                return item
        return ""

    def __can_convert_to_int(self, text):
        try:
            int(text)
            return True
        except ValueError:
            return False

    def __remove(self, text, array):
        for item in array:
            text.replace(item, "")

    def __remove_brackets(self, text):
        return text.replace("(", "").replace(")", "").replace("（", "").replace("）", "").replace("【", "").replace("】", "")
