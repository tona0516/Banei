import csv
import datetime
import copy
import multiprocessing
import glob
import logging
import os
from banei_scraper import Scraper

RESOURCE_DIC = "resource/"
OUTPUT_DIC = "output/"
LOG_DIC = "logs/"
MULTIPROCESSING_POOL = 16
MAX_ROUND = 12

start_date = datetime.date(2012, 4, 1)
end_date = datetime.date(2018, 9, 30)

exec_date = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
logger = logging.getLogger(exec_date + ".log")

def write_all_result_to_csv(resource_dic_path, header, output_file_path):
    is_complete_write_header = False
    with open(output_file_path, "w") as f1:
        writer = csv.writer(f1, delimiter=',')
        for file_path in sorted(glob.glob(resource_dic_path + '*.csv')):
            logger.debug("write data >> " + file_path)
            with open(file_path, "r") as f2:
                reader = csv.reader(f2)
                data = []
                for row in reader:
                    data.append(row)

                if not is_complete_write_header:
                    writer.writerow(header)
                    is_complete_write_header = True

                for i in range(1, len(data)):
                    if len(header) == len(data[i]):
                        writer.writerow(data[i])
                    else:
                        logger.error("not match row count: " + str(file_path))

def request_HTML(date):
    formatted_date = datetime.date.strftime(date, "%Y%m%d")
    for i in range(1, MAX_ROUND + 1):
        # すでにスクレイピング済みならスキップする
        file_name = formatted_date.replace("/", "-") + "-" + str(i).zfill(2) + "R.csv"
        file_path = RESOURCE_DIC + file_name
        if os.path.exists(file_path):
            continue
        
        try:
            # スクレイピング開始
            scraper = Scraper(formatted_date, str(i), logger)
            # ディクショナリのリストとして取得してCSVに保存
            scraper.scrape()
        except:
            continue
        else:
            if scraper.result_list:
                scraper.write_to_csv(file_path)
                print("WRITE date: " + formatted_date + " round: " + str(i).zfill(2))
            else:
                break


def make_date_list(start_date, end_date):
    date = copy.deepcopy(start_date)
    all_date = []
    while date != end_date:
        all_date.append(date)
        date = date + datetime.timedelta(days=1)
    return all_date

def get_header():
    for file_path in glob.glob(RESOURCE_DIC + '*.csv'):
        with open(file_path, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                return row

def make_output_filename(start_date, end_date):
    formatted_start_date = datetime.date.strftime(start_date, "%Y%m%d")
    formatted_end_date = datetime.date.strftime(end_date, "%Y%m%d")
    return "banei_" + formatted_start_date + "-" + formatted_end_date + ".csv"

def init_logger():
    logger.setLevel(logging.WARNING)

    fh = logging.FileHandler(LOG_DIC + exec_date + '.log')
    logger.addHandler(fh)

    sh = logging.StreamHandler()
    logger.addHandler(sh)

def init_directories():
    os.makedirs(RESOURCE_DIC, exist_ok=True)
    os.makedirs(OUTPUT_DIC, exist_ok=True)
    os.makedirs(LOG_DIC, exist_ok=True)

if __name__ == '__main__':
    # 保存ディレクトリの初期化
    init_directories()

    # ロガーの初期化
    init_logger()

    # 探索する日付のリストを生成
    dates = make_date_list(start_date, end_date)

    # 並列処理でリクエスト&スクレイピング
    pool = multiprocessing.Pool(MULTIPROCESSING_POOL)
    pool.map(request_HTML, dates)

    # 一つのファイルにまとめる
    header = get_header()
    output_file_path = make_output_filename(start_date, end_date)
    write_all_result_to_csv(RESOURCE_DIC, header, OUTPUT_DIC + output_file_path)

    print("DONE")
