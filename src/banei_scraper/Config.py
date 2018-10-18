class Config:
    # スクレイピング対象
    URL_BASE = 'https://keiba.rakuten.co.jp/'
    URL_RACECARD = URL_BASE + 'race_card/list/RACEID/'
    URL_ODDS = URL_BASE + 'odds/tanfuku/RACEID/'
    URL_RECORD = URL_BASE + 'race_performance/list/RACEID/'

    # HTMLのクラス
    CLASS_NUMBER = 'number'
    CLASS_NAME = 'name'
    CLASS_PROFILE = 'profile'
    CLASS_WEIGHT = 'weight'
    CLASS_WEIGHT_DISTANCE = 'weightDistance'
    CLASS_ODDS_WIN = 'oddsWin'
    CLASS_ODDS_PLACE = 'oddsPlace'
    CLASS_ORDER = 'order'
    CLASS_TIME = 'time'

    # 各データのラベル
    LABELS_RACECARD= [
        "馬番",
        "父馬",
        "馬名",
        "母馬",
        "母父馬",
        "オッズ",
        "誕生日",
        "馬主名",
        "生産牧場",
        "性齢",
        "毛色",
        "負担重量",
        "騎手名",
        "所属",
        "勝率",
        "3着内率",
        "調教師名",
        "連対時馬体重",
        "馬体重増減"
    ]
    LABELS_ODDS = [
        "馬番",
        "単勝オッズ",
        "複勝オッズ"
    ]
    LABELS_RECORD= [
        "馬番",
        "着順",
        "タイム"
    ]