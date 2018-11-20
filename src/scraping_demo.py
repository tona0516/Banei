import csv
import datetime
import copy
import multiprocessing
import glob
import logging
import os
import argparse

from banei_scraper import Scraper as scraper
from banei_scraper.exception import ScraperException

exec_date = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
logger = logging.getLogger(exec_date + ".log")


def write_all_result_to_csv(resource_dicpath, output_dicpath):
    all_csv_path = sorted(glob.glob(resource_dicpath + '*.csv'))
    first_filename = os.path.basename(all_csv_path[0]).replace(".csv", "")
    last_filename = os.path.basename(all_csv_path[-1]).replace(".csv", "")

    with open(output_dicpath + first_filename + ">>" + last_filename + ".csv", "w") as all_result_file:
        writer = csv.writer(all_result_file, delimiter=',')

        # ヘッダの書き込み
        header = get_header(resource_dicpath)
        writer.writerow(header)

        # 値の書き込み
        for file_path in all_csv_path:
            with open(file_path, "r") as race_result_file:
                reader = csv.reader(race_result_file)
                data = [row for i, row in enumerate(reader) if i != 0]
                [writer.writerow(row) for row in data]


def request_html(date, max_round=12):
    formatted_date = datetime.date.strftime(date, "%Y%m%d")
    for i in range(1, max_round + 1):
        # すでにスクレイピング済みならスキップする
        file_name = formatted_date.replace("/", "-") + "-" + str(i).zfill(2) + "R.csv"
        file_path = RESOURCE_DIC + file_name
        if os.path.exists(file_path):
            continue
        
        try:
            # スクレイピング開始
            result_list = scraper.scrape(formatted_date, i)
        except ScraperException as e:
            logger.error(e.message)
            if e.message in 'No data in the soup':
                break
            else:
                continue
        else:
            scraper.output_to_file(result_list, file_path)
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


def check_positive(value):
    ivalue = int(value)
    if ivalue <= 0:
         raise argparse.ArgumentTypeError("%s is an invalid positive int value" % value)
    return ivalue


def check_date(s):
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


def read_option():
    parser = argparse.ArgumentParser(description='scraping data from Rakuten keiba')
    
    parser.add_argument('-s', '--start_date', type=check_date, default=datetime.date(2010, 1, 1), help="the start date - format YYYY-MM-DD (default: " + str(datetime.date(2010, 1, 1)) + ')')
    parser.add_argument('-e', '--end_date', type=check_date, default=datetime.date.today(), help="the end date - format YYYY-MM-DD (default: " + str(datetime.date.today()) + ')')
    parser.add_argument('-p', '--process', type=check_positive, default=multiprocessing.cpu_count(), help='the number of process using scraping data (default: ' + str(multiprocessing.cpu_count()) + ')')
    parser.add_argument('-rd', '--resource_dir', type=str, default='resource/', help='the directory saved each race data (default: resource/)')
    parser.add_argument('-od', '--output_dir', type=str, default='output/', help='the directory saved all race merged data (default: output/)')
    parser.add_argument('-ld', '--log_dir', type=str, default='log/', help='the directory saved log file (default: log/)')
    
    args = parser.parse_args()

    return args


if __name__ == '__main__':
    args = read_option()

    RESOURCE_DIC = args.resource_dir
    OUTPUT_DIC = args.output_dir
    LOG_DIC = args.log_dir

    MULTIPROCESSING_POOL = args.process
    START_DATE = args.start_date
    END_DATE = args.end_date

    # 保存ディレクトリの初期化
    init_directories(RESOURCE_DIC, OUTPUT_DIC, LOG_DIC)

    # ロガーの初期化
    init_logger(LOG_DIC)

    # 探索する日付のリストを生成
    dates = make_date_list(START_DATE, END_DATE)

    # 並列処理でリクエスト&スクレイピング
    pool = multiprocessing.Pool(MULTIPROCESSING_POOL)
    pool.map(request_html, dates)

    # 一つのファイルにまとめる
    output_file_path = make_output_filename(START_DATE, END_DATE)
    write_all_result_to_csv(RESOURCE_DIC, OUTPUT_DIC)

    print("DONE")
