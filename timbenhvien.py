import streamlit as st
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
# from gsheetsdb import connect
import gspread
# from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2 import service_account
import urllib.request as req
import requests
import bs4
import json
from geopy.distance import geodesic

import email, smtplib, ssl # to automate email
import email as mail
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import datetime as dt # to work with date, time
from bs4 import BeautifulSoup # to work with web scrapping (HTML)
from IPython.core.display import HTML # to display HTML in the notebook





    #     # Đọc data từ sheet dùng gsheetsdb
# conn = connect()
# def run_query(query):
#     rows = conn.execute(query, headers=1)
#     return rows
# sheet_url = st.secrets["public_gsheets_url"]
# rows = run_query(f'SELECT * FROM "{sheet_url}"')
# #Đọc data từ dạng query sang dạng pandas
# df = pd.DataFrame(rows.fetchall())
# st.write(pd.DataFrame(df.values, columns = ['STT', 'Điền', 'KẾT QUẢ', 2,6,7,8,9,0,1]))
    #       # Các lựa chọn

st.sidebar.image('https://raw.githubusercontent.com/Ha-Huynh-Anh/Timbenhvien_test/main/Picture/FONT_TBV.png')
st.image('https://raw.githubusercontent.com/Ha-Huynh-Anh/Timbenhvien_test/main/Picture/so_tay_bv.png')


# Dùng gspread load danh sách bệnh viện + địa chỉ + các yếu tố đặc biệt
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes= scope)
@st.cache(hash_funcs={service_account.Credentials: lambda _: None})
def get_data():
# credentials = ServiceAccountCredentials.from_json_keyfile_name('timbenhvien-830ed70dcaeb.json', scope)
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key('1ysTWh2T1rJXOuYWC7KB9g0cOgyLgFESnK0PbqPMNlsU')
    worksheet1 = sh.get_worksheet(0)
    df_1 = pd.DataFrame(worksheet1.get_all_records())
    worksheet2 = sh.get_worksheet(1)
    df_2 = pd.DataFrame(worksheet1.get_all_records())
    return df_1, df_2 

#sym_df
@st.cache
def get_sym_df(url1):
  sym_df = pd.read_csv(url1)
  sym_df = pd.DataFrame(sym_df)
  sym_df = sym_df.loc[:,('eng','viet')]
  return sym_df

#dis_df
@st.cache
def get_dis_df(url1):
  dis_df = pd.read_csv(url1)
  dis_df = pd.DataFrame(dis_df)
  dis_df = dis_df.loc[:,('id_diseases', 'eng', 'viet', 'bv_tuong_ung')]
  return dis_df

#train_df
@st.cache(allow_output_mutation=True)
def get_train_df(url1):
  train_df = pd.read_csv(url1)
  train_df = pd.DataFrame(train_df)
  train_df['vector'] = train_df.iloc[:,-133:-1].apply(lambda x: list(x), axis=1) ## sau nay nen tong quat hoa cac con so 133, 1, ...
  return train_df

@st.cache
def get_hospital_add(url1):
    hospital_add = pd.read_csv(url1)
    hospital_add = pd.DataFrame(hospital_add)
    hospital_add = hospital_add.loc[:,('id_bv', 'name', 'type', 'address', 'district','ksk_thong_thuong', 'ksk_nuoc_ngoai', 'ksk_lai_xe', 'ghi_chu','lat','lon')]
    return hospital_add

@st.cache
def get_hospital_df(url1):
    hospital_df = pd.read_csv(url1)
    hospital_df = pd.DataFrame(hospital_df)
    hospital_df = hospital_df.loc[:,('id_bv', 'name', 'khoa', 'gio_kham_bt', 'gio_kham_ng','gio_kham_dv', 'kham_dv', 'ghi_chu', 'nguoi_dien', 'link')]
    return hospital_df

#load data_chan doan benh
url_train_df = 'https://raw.githubusercontent.com/Ha-Huynh-Anh/Timbenhvien_test/main/data/train_df.csv'
url_dis_df = 'https://raw.githubusercontent.com/Ha-Huynh-Anh/Timbenhvien_test/main/data/diseases_df.csv'
url_sym_df = 'https://raw.githubusercontent.com/Ha-Huynh-Anh/Timbenhvien_test/main/data/sym_df.csv'

sym_df = get_sym_df(url_sym_df)
dis_df = get_dis_df(url_dis_df)
train_df = get_train_df(url_train_df)
#load data ve cac benh vien
url_hospital_add = 'https://raw.githubusercontent.com/Ha-Huynh-Anh/Timbenhvien_test/main/data/hospital_add.csv'
url_hospital_df = 'https://raw.githubusercontent.com/Ha-Huynh-Anh/Timbenhvien_test/main/data/hospital_df.csv' 

hospital_add = get_hospital_add(url_hospital_add)
hospital_df = get_hospital_df(url_hospital_df)

# get coor from hospital database
def get_coor(list_hospital):
    list_coor = []
    hospital_add = get_hospital_add(url_hospital_add)
    for i in list_hospital:
        lat = hospital_add[hospital_add.id_bv == i].lat
        lat = list(lat)[0]
        lon = hospital_add[hospital_add.id_bv == i].lon
        lon = list(lon)[0]
        list_coor.append((lat,lon))
    return list_coor

# to convert an address to coordinate
def get_coor_goong(add):
    """
    add_demo = '125/61 Âu Dương Lân, Phường 2, Quận 8'
    expected_output = (10.7405538, 106.6871743)

    """
    add = req.pathname2url(add)
    add = add.replace('/','%2F')

    endpoint_coor_goong = 'https://rsapi.goong.io/Geocode?'
    api_key_goong = st.secrets["api_key_goong"]

    nav_request_coor = 'address={}&api_key={}'.format(add,api_key_goong)

    request_coor = endpoint_coor_goong + nav_request_coor
    result_coor = requests.get(request_coor)
    soup_coor = bs4.BeautifulSoup(result_coor.text,'lxml')
    coor_json=json.loads(soup_coor.text)
    # distance = site_json['rows'][0]['elements'][0]['distance']['text']
    # time_travel = site_json['rows'][0]['elements'][0]['duration']['text']
    lat = coor_json['results'][0]['geometry']['location']['lat']
    lon = coor_json['results'][0]['geometry']['location']['lng']
    coor_output = (lat,lon)
    return coor_output

# to get distance from 2 coordinate
def get_dis_coor_goong(coor1,coor2):
    """
    coor_demo1 = (10.7405538, 106.6871)
    coor_demo2 = (10.772109500000001, 106.69827839999999)
    output = ('5 km', '16 phút')
    """
    endpoint_goong = 'https://rsapi.goong.io/DistanceMatrix?'
    api_key_goong = st.secrets["api_key_goong"]
    nav_request_dis = 'origins={}%2C{}&destinations={}%2C{}&api_key={}'.format(coor1[0],coor1[1],coor2[0],coor2[1],api_key_goong)
    request_goon = endpoint_goong + nav_request_dis
    result_goon = requests.get(request_goon)
    soup_dis = bs4.BeautifulSoup(result_goon.text,'lxml')
    site_json=json.loads(soup_dis.text)
    distance = site_json['rows'][0]['elements'][0]['distance']['text']
    time_travel = site_json['rows'][0]['elements'][0]['duration']['text']
    return (distance,time_travel)

# make link google map from coor
def link_ggmap(user_coor,destination):
    """
    destination = (10.8108725, 106.69471580000001)
    output = 'https://www.google.com/maps/dir/10.816616271,106.706402793/10.8108725,106.69471580000001'
    """
    endpoint_link = 'https://www.google.com/maps/dir/'
    nav_link = '{},{}/{},{}'.format(user_coor[0],user_coor[1],destination[0],destination[1])
    url = endpoint_link+nav_link
    return url
# FUNCTION LIET KE THONG TIN CUA 1 BENH VIEN
def print_hospital_info_txt(input_id,user_coor):
    st.info(df_1.set_index('ID_BV').loc[input_id, 'TÊN'])
    lat = hospital_add[hospital_add.id_bv == input_id].lat
    lat = list(lat)[0]
    lon = hospital_add[hospital_add.id_bv == input_id].lon
    lon = list(lon)[0]
    bv_coor = (lat,lon)
    link1 = df_1.set_index('ID_BV').loc[input_id, 'Link website ']
    with st.beta_expander('Thông tin cơ bản về bệnh viện'):
        st.markdown(':rainbow: **Địa chỉ:** '+ df_1.set_index('ID_BV').loc[input_id, 'ĐỊA CHỈ'] + ', Quận, ' + str(df_1.set_index('ID_BV').loc[input_id, 'QH']))
        st.markdown(':information_source: Từ vị trí của bạn đến bệnh viện khoảng ' + str(get_dis_coor_goong(bv_coor,user_coor)[0]) + 
        ', tốn khoảng ' + str(get_dis_coor_goong(bv_coor,user_coor)[1]))
        if df_1.set_index('ID_BV').loc[input_id,'GHI CHÚ'] != '':
            st.markdown(':star: **Lưu ý:** ' + df_1.set_index('ID_BV').loc[input_id,'GHI CHÚ'])
        st.markdown(':earth_africa: **Website của bệnh viện:** '+ link1, unsafe_allow_html = True)
        st.write(':world_map: ** Bản đồ hướng dẫn:** ' + link_ggmap(user_coor,bv_coor),unsafe_allow_html = True)
    st.write('')
    st.write('')

# function to save information of 1 hospital to a text file to send email:
def print_hospital_info_email(input_id):
    file_infor = open('hospital_infor.txt','w', encoding='utf-8', errors='replace')
    one_add = hospital_add[hospital_add.id_bv == input_id].values[0]
    print(f'Tên bệnh viện: {one_add[1]}',file=file_infor)
    print(f'Địa chỉ: {one_add[3]}, quận {one_add[4]}',file=file_infor)
    print('-------------Thông tin chi tiết-------------',file=file_infor)

    one_infor = hospital_df[hospital_df.id_bv == input_id].values[0]

    if one_infor[3] != 0: print(f'Thời gian khám thông thường: {one_infor[3]}',file=file_infor)
    if one_infor[4] != 0: print(f'Thời gian khám ngoài giờ: {one_infor[4]}',file=file_infor)
    if one_infor[5] != 0: print(f'Thời gian khám dịch vụ: {one_infor[5]}',file=file_infor)
    print('\n',file=file_infor)
    if one_infor[2] != 0: print(f'Các khoa khám bệnh chính: \n{one_infor[2]}',file=file_infor)
    if one_infor[6] != 0: print(f'Ghi chú: {one_infor[6]}',file=file_infor)
    print('\n',file=file_infor)
    file_infor.close()
    return open('hospital_infor.txt','r',encoding='utf-8', errors='replace').read()

# email:
def send_email(receiver_email, subject,input_id,user_coor):
    lat = hospital_add[hospital_add.id_bv == input_id].lat
    lat = list(lat)[0]
    lon = hospital_add[hospital_add.id_bv == input_id].lon
    lon = list(lon)[0]
    one_coor = (lat,lon)
    # (1) Create the email head (sender, receiver, and subject)
    sender_email = st.secrets['SENDER_EMAIL']
    password = st.secrets['PWD_EMAIL']
    email = MIMEMultipart()
    email["From"] = sender_email
    email["To"] = receiver_email
    email["Subject"] = subject

    # (2) Create Body part

    html1 = """
      <html>
      <h1><strong>Thông tin bệnh viện </strong></h1>
      <body>
      <p>Xin chào bạn! <br>
        Đây là thông tin bệnh viện bạn đang tìm kiếm:
      </p>
      </body>
      </html>
      """
    text1 = print_hospital_info_email(input_id)
#     text1 = 'infor of the hospital'
    html2 = """
    <html>

    Email được gửi vào lúc at <b>{}</b><br>
    </html>
    """.format(dt.datetime.now().isoformat())
    link4 = """
    <html>
    Link <a href={}>bản đồ</a> chỉ đường.
    <br>
    </html>
    """.format(link_ggmap(user_coor,one_coor))
    text5 = '--- Hết. ----'

    # Combine parts
    part1 = MIMEText(html1, 'html')
    part2 = MIMEText(text1, 'plain')
    part3 = MIMEText(link4, 'html')
    part4 = MIMEText(html2, 'html')
    part5 = MIMEText(text5, 'plain')

    email.attach(part1)
    email.attach(part2)
    email.attach(part3)
    email.attach(part4)
    email.attach(part5)

    # (3) Create SMTP session for sending the mail
    session = smtplib.SMTP('smtp.gmail.com', 587) #use gmail with port
    session.starttls() #enable security
    session.login(sender_email, password) #login with mail_id and password
    text = email.as_string()
    session.sendmail(sender_email, receiver_email, text)

# function to translate sym vie - eng:
def trans_sym(list_sym):
    """
    translate sym from list vie to list eng
    input: ['Yếu mệt','Da nổi mẩn']
    output: ['lethargy', 'nodal_skin_eruptions']
    """
    list_eng = []
    for i in list_sym:
        if i in list(sym_df.viet):
            index = list(sym_df.viet).index(i)
            list_eng.append(list(sym_df.eng)[index])
    return list_eng
# sym_to_vector(sym_input_eng)
# convert to array format
def sym_to_vector(list_input_sym):
    #  to convert sym to vector
    sym_input_vector = []    
    for i in list(sym_df.eng): 
        if i in list_input_sym:
            sym_input_vector.append(1)
        else:
            sym_input_vector.append(0)
    return sym_input_vector
# convert all into list
def get_disease(train_df, input_array):
    
    # cal similarity
    train_df['similar'] = train_df.vector.apply(lambda x: cosine_similarity(input_array,np.array([x]))[0][0])

    # disease result
    dis_result = train_df[train_df['similar'] > 0]
    dis_result = pd.DataFrame(dis_result)
    return dis_result.groupby('prognosis').max('similar').iloc[:,-1].sort_values(ascending=False)    

dis_df = pd.DataFrame(dis_df)
list_disease_eng = list(dis_df.eng)
list_disease_vie = list(dis_df.viet)
list_disease_id = list(dis_df.id_diseases)

# convert disease to vie
def disease_to_vie(dis_eng):
    if dis_eng in list_disease_eng:
        index = list_disease_eng.index(dis_eng)
        return list_disease_vie[index]
def disease_to_id(dis_eng):
    if dis_eng in list_disease_eng:
        index = list_disease_eng.index(dis_eng)
        return list_disease_id[index]
#Lay ID benh vien tuong ung voi ID benh
def get_hopital_list(dis_id):
    bv_id = dis_df[dis_df.id_diseases == dis_id].bv_tuong_ung
    bv_id = list(bv_id)[0]
    bv_id = bv_id.split(sep = ';')
    return bv_id

st.sidebar.subheader('Nhập địa chỉ để nhận được đề xuất bệnh viện **gần nhất**')
diachi_user = st.sidebar.text_input("*******")
if len(diachi_user) > 0:     
    user_coor = get_coor_goong(diachi_user)
else: user_coor = ()

df_1, df_2 = get_data()
st.sidebar.subheader('Bạn đang tìm bệnh viện theo tiêu chí:')
option1 = st.sidebar.radio("", ('Cần tư vấn bệnh viện theo triệu chứng',
    'Khám sức khỏe thông thường/ tổng quát', 'Khám sức khỏe cho người lái xe', 
    'Khám sức khỏe cho người nước ngoài', 'Khám sức khỏe để xuất ngoại'))




check_box_1 = st.sidebar.checkbox("Bạn muốn nhận email về thông tin bệnh viện bạn đang quan tâm")
if check_box_1:
    submitted_1 = False
    ten_bv = st.sidebar.selectbox('Bệnh viện quan tâm',list(df_1.iloc[:,1]))
    id_bv_1 = df_1.set_index('TÊN').loc[ten_bv, 'ID_BV']
    with st.sidebar.form('bv_quantam'):
        email_user = st.text_input('Email của bạn')
        submitted_1 = st.form_submit_button("Nhận thông tin")
        if submitted_1 and len(diachi_user) > 0 and len(email_user)>0:
            sub_ject = 'Sổ tay bệnh viện gửi bạn'
            send_email(email_user,sub_ject, id_bv_1, user_coor)
            st.sidebar.markdown('### :white_check_mark: Đã gửi. Stay safe!')
        else: st.sidebar.markdown(':zap: Vui lòng điền đầy đủ thông tin địa chỉ và email')
if option1 == 'Khám sức khỏe thông thường/ tổng quát':
    df_result = df_1[df_1.iloc[:,5] == 'x'].iloc[:,[0,1,3,4,8,9]]
elif option1 == 'Khám sức khỏe cho người lái xe':
    df_result = df_1[df_1.iloc[:,7] == 'x'].iloc[:,[0,1,3,4,8,9]]
elif option1 == 'Khám sức khỏe cho người nước ngoài':
    df_result = df_1[df_1.iloc[:,8].str.contains('Thực hiện')].iloc[:,[0,1,3,4,8,9]]
elif option1 == 'Khám sức khỏe để xuất ngoại':
    df_result = df_1[df_1.iloc[:,6] == 'x'].iloc[:,[0,1,3,4,8,9]]
elif option1 == 'Cần tư vấn bệnh viện theo triệu chứng':
    sym_input_vie = st.multiselect('Các triệu chứng của bạn', sym_df.viet.values)
    # translate vie into eng
    # test lại bằng streamlit 0.80.0
    sym_input_eng = trans_sym(sym_input_vie)
    #convert to vector
    input_array = np.array([sym_to_vector(sym_input_eng)])
    output_disease_eng =  get_disease(train_df,input_array)
    output_disease_eng = pd.DataFrame(output_disease_eng)
    output_disease_eng = output_disease_eng.reset_index()
    # create table
    output_disease_eng['viet'] = output_disease_eng.prognosis.apply(lambda x: disease_to_vie(x))
    output_disease_eng['id'] = output_disease_eng.prognosis.apply(lambda x: disease_to_id(x))
    if len(sym_input_vie) > 0:
        st.markdown(':hospital: Bạn có thể cần được khám về ')
    for i in output_disease_eng.index:
        see_hospital = st.checkbox(output_disease_eng.iloc[i,2])
        if see_hospital:
            id_bv = get_hopital_list(output_disease_eng.iloc[i,3])
            df_result = df_1.iloc[:, [0,1,3,4,9,8]].set_index('ID_BV')
            with st.beta_expander('Danh sách bệnh viện bạn có thể tham khảo'):
                st.write(df_result.loc[id_bv, ['TÊN','ĐỊA CHỈ','QH']].set_index('TÊN'))
            if len(user_coor) > 0:
                list_coor = get_coor(id_bv)
                result_hospital = pd.DataFrame({'hospital_id':id_bv,'coor':list_coor})
                result_hospital['geodesic'] = result_hospital.coor.apply(lambda x: geodesic(x, user_coor).km)
                result_hospital = result_hospital.sort_values('geodesic',ascending=True)
                top_hospital = result_hospital.iloc[0:3,:]
                st.markdown('**Các bệnh viện gần vị trí của bạn**')
                for input_id in list(top_hospital.loc[:,'hospital_id']):
                    print_hospital_info_txt(input_id,user_coor)

if option1 not in ['Cần tư vấn bệnh viện theo triệu chứng'] :
    with st.beta_expander('Danh sách bệnh viện bạn có thể tham khảo'):
        st.dataframe(df_result.loc[:,['TÊN','ĐỊA CHỈ','QH']].set_index('TÊN'))
    if len(user_coor) > 0:
        id_bv = list(df_result.iloc[:,0])
        list_coor = get_coor(id_bv)
        result_hospital = pd.DataFrame({'hospital_id':id_bv,'coor':list_coor})
        result_hospital['geodesic'] = result_hospital.coor.apply(lambda x: geodesic(x, user_coor).km)
        result_hospital = result_hospital.sort_values('geodesic',ascending=True)
        top_hospital = result_hospital.iloc[0:3,:]
        st.markdown('**Danh sách các bệnh viện gần vị trí của bạn**')
        for input_id in list(top_hospital.loc[:,'hospital_id']):
            print_hospital_info_txt(input_id,user_coor)