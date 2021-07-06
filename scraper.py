import time
import argparse

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait


TOTAL_PAGE_NUM = 14320
NUM_PER_PAGE = 100
URL = 'https://utas.adm.u-tokyo.ac.jp/campusweb/campusportal.do'

options = Options()
options.add_argument('--headless')


def get_class_data(target_page, from_, to_, ID, PASS):
    driver = webdriver.Chrome('/usr/local/bin/chromedriver', options=options)
    driver.implicitly_wait(30)

    driver.get(URL)

    ## UTASのログインボタン
    driver.find_element_by_xpath('//*[@id="wf_PTW0000011_20120827233559-form"]/p/button').click()

    ## UTokyoアカウントでログイン
    driver.find_element_by_id('userNameInput').send_keys(ID)
    driver.find_element_by_id('passwordInput').send_keys(PASS)
    driver.find_element_by_id('submitButton').click()
    time.sleep(1)
    ## syllabusへ移動
    driver.find_element_by_id('tab-sy').click()

    ## frameの切り替え
    time.sleep(2)
    iframe = driver.find_element_by_id('main-frame-if')
    driver.switch_to.frame(iframe)
    ## 検索ボタンで1ページ目へ
    driver.find_element_by_xpath('//*[@id="jikanwariFreewordForm"]/p[5]/input[1]').click()

    df = pd.DataFrame()

    page_num = 1
    while True:
        if target_page == page_num:
            print(f'page: {page_num:3d} ... ', end='')
            profile_columns = [elem.text for elem in driver.find_element_by_xpath(f'/html/body/table/thead').find_element_by_tag_name('tr').find_elements_by_tag_name('th')]

            for row_num in range(1, NUM_PER_PAGE+1):
                if from_ <= row_num <= to_:
                    print("+", end='')

                    ## 基本情報を取得
                    df_profile = pd.DataFrame(
                        [[elem.text for elem in driver.find_element_by_xpath(f'/html/body/table/tbody/tr[{row_num}]').find_elements_by_tag_name('td')]], 
                        columns=profile_columns, 
                        index=[100*(page_num-1)+row_num]
                    )

                    ## 各授業の詳細ボタンをclick
                    driver.find_element_by_xpath(f'/html/body/table/tbody/tr[{row_num}]/td[13]/input').click()
                    # もしその授業に詳細のページがあるなら、windowの切り替え + 各授業の詳細情報を取得する
                    if len(driver.window_handles) > 1:
                        ## ページを移動
                        driver.switch_to.window(driver.window_handles[1])
                        ## 「詳細情報」のタブに移動
                        driver.find_element_by_xpath('//*[@id="tabs"]/ul/li[2]/a').click()
                        
                        ## 表を取得
                        columns = [elem.find_element_by_tag_name('th').text for elem in driver.find_element_by_id('tabs-2').find_elements_by_tag_name('tr')]
                        values = [elem.find_element_by_tag_name('td').text for elem in driver.find_element_by_id('tabs-2').find_elements_by_tag_name('tr')]
                        df_detail = pd.DataFrame([values], columns=columns, index=[100*(page_num-1)+row_num])
                        ## 空白列、カラム名の重複を削除
                        df_detail = df_detail[df_detail != ''].dropna(axis=1)
                        df_detail = df_detail.loc[:,~df_detail.columns.duplicated()]
                        ## 結合
                        df_row = pd.concat([df_profile, df_detail], axis=1, join='outer')
                        df = pd.concat([df, df_row], join='outer')
                        time.sleep(0.5)

                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                        ## 2ページ目以降はiframe切り替えが不要
                        if page_num == 1:
                            driver.switch_to.frame(iframe)
                    # 詳細ページがない場合は基本情報だけ取得する
                    else:
                        df = pd.concat([df, df_profile], join='outer')

                else:
                    print("=", end='')

            print()
            ## whileから抜けて終了
            break

        else:
            ## 次のページへのリンクを取得
            links = [(elem.get_attribute('href'), elem.text) for elem in driver.find_elements_by_tag_name("a")]
            is_last_page = (links[-1][1] != '次へ >>')
            if is_last_page:
                print("Reached to the last page...")
                break
            
            ### 次のページに飛ぶ
            # 一番遠くまで飛ぶ(9ページ先)
            if target_page - page_num > 9:
                driver.get(links[-2][0])
                assert links[-2][1] == str(page_num + 9)
                page_num += 9
            # 直接飛ぶ
            else:
                for link, p in links:
                    if p == str(target_page):
                        page_num = target_page
                        driver.get(link)
            time.sleep(1)

    driver.close()
    return df


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", hlep='UTokyo Account ID')
    parser.add_argument("--from", default=1, dtype=int, help='Which page do you start scraping from...?')
    args = parser.parse_args()

    ID = args.id
    PASS = input("UTokyo Account password: ")

    for p in range(args.default, (TOTAL_PAGE_NUM//100)+1):
        df1 = get_class_data(p,  1, 33, ID, PASS)
        df2 = get_class_data(p, 34, 66, ID, PASS)
        df3 = get_class_data(p, 67, 100, ID, PASS)
        df = pd.concat([df1, df2, df3], join='outer')
        df.to_csv(f'syllabus/{p}.csv')