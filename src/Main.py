import csv
import datetime
import copy
import multiprocessing
import glob
import logging
import os

from banei_scraper import Scraper as scr
from banei_scraper.exception import ScraperException

exec_date = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
logger = logging.getLogger(exec_date + ".log")

def write_all_result_to_csv(resource_dicpath, output_dicpath):
    is_complete_write_header = False
    all_csv_path = sorted(glob.glob(resource_dicpath + '*.csv'))
    first_filename = os.path.basename(all_csv_path[0]).replace(".csv", "")
    last_filename = os.path.basename(all_csv_path[-1]).replace(".csv", "")

    with open(output_dicpath + first_filename + ">>" + last_filename + ".csv", "w") as f1:
        writer = csv.writer(f1, delimiter=',')
        header = get_header(resource_dicpath)
        for file_path in all_csv_path:
            print("write data >> " + file_path)
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

def request_HTML(date, max_round=12):
    formatted_date = datetime.date.strftime(date, "%Y%m%d")
    for i in range(1, max_round + 1):
        # すでにスクレイピング済みならスキップする
        file_name = formatted_date.replace("/", "-") + "-" + str(i).zfill(2) + "R.csv"
        filepath = RESOURCE_DIC + file_name
        if os.path.exists(filepath):
            continue
        
        try:
            # スクレイピング開始
            result_list = scr.scrape(formatted_date, i)
        except ScraperException as e:
            logger.error(e.message)
            if e.message in 'No data in the soup':
                break
            else:
                continue
        else:
            scr.output_to_file(result_list, filepath)
            print("WRITE date: " + formatted_date + " round: " + str(i).zfill(2))

def make_date_list(start_date, end_date):
    date = copy.deepcopy(start_date)
    all_date = []
    while date != end_date:
        all_date.append(date)
        date = date + datetime.timedelta(days=1)
    return all_date

def get_header(resource_dicpath):
    """
    一番日付の古いcsvからヘッダを取得
    """
    for file_path in glob.glob(resource_dicpath + '*.csv'):
        with open(file_path, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                return row

def make_output_filename(start_date, end_date):
    formatted_start_date = datetime.date.strftime(start_date, "%Y%m%d")
    formatted_end_date = datetime.date.strftime(end_date, "%Y%m%d")
    return "banei_" + formatted_start_date + "-" + formatted_end_date + ".csv"

def init_logger(log_dicpath):
    """
    warning以上のログをファイルに落とす
    """
    logger.setLevel(logging.WARNING)

    fh = logging.FileHandler(log_dicpath + exec_date + '.log')
    logger.addHandler(fh)

    sh = logging.StreamHandler()
    logger.addHandler(sh)

def init_directories(resource_dicpath: str, output_dicpath: str, log_dicpath: str):
    os.makedirs(resource_dicpath, exist_ok=True)
    os.makedirs(output_dicpath, exist_ok=True)
    os.makedirs(log_dicpath, exist_ok=True)

if __name__ == '__main__':
    RESOURCE_DIC = "resource/"
    OUTPUT_DIC = "output/"
    LOG_DIC = "logs/"
    MULTIPROCESSING_POOL = multiprocessing.cpu_count()

    START_DATE = datetime.date(2010, 1, 1)
    END_DATE = datetime.date.today()

    # 保存ディレクトリの初期化
    init_directories(RESOURCE_DIC, OUTPUT_DIC, LOG_DIC)

    # ロガーの初期化
    init_logger(LOG_DIC)

    # 探索する日付のリストを生成
    dates = make_date_list(START_DATE, END_DATE)

    # 並列処理でリクエスト&スクレイピング
    pool = multiprocessing.Pool(MULTIPROCESSING_POOL)
    pool.map(request_HTML, dates)

    # 一つのファイルにまとめる
    output_file_path = make_output_filename(START_DATE, END_DATE)
    write_all_result_to_csv(RESOURCE_DIC, OUTPUT_DIC)

    print("DONE")
