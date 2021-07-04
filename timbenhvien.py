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

st.set_page_config(
     page_title="Sotaybenhvien",
     page_icon=':gift:',
     layout="centered",
     initial_sidebar_state="expanded",
)

st.title("DỰ ÁN SỔ TAY BỆNH VIỆN")
st.sidebar.image('Picture\FONT_TBV.png')
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
  sym_df = sym_df.loc[:,('eng','viet')]
  return sym_df

#dis_df
@st.cache
def get_dis_df(url1):
  dis_df = pd.read_csv(url1)
  dis_df = dis_df.loc[:,('id_diseases', 'eng', 'viet', 'bv_tuong_ung')]
  return dis_df

#train_df
@st.cache(allow_output_mutation=True)
def get_train_df(url1):
  train_df = pd.read_csv(url1)
  train_df['vector'] = train_df.iloc[:,-133:-1].apply(lambda x: list(x), axis=1) ## sau nay nen tong quat hoa cac con so 133, 1, ...
  return train_df

@st.cache
def get_hospital_add(url1):
    hospital_add = pd.read_csv(url1)
    hospital_add = hospital_add.loc[:,('id_bv', 'name', 'type', 'address', 'district','ksk_thong_thuong', 'ksk_nuoc_ngoai', 'ksk_lai_xe', 'ghi_chu','lat','lon')]
    return hospital_add

@st.cache
def get_hospital_df(url1):
    hospital_df = pd.read_csv(url1)
    hospital_df = hospital_df.loc[:,('id_bv', 'name', 'khoa', 'gio_kham_bt', 'gio_kham_ng','gio_kham_dv', 'kham_dv', 'ghi_chu', 'nguoi_dien', 'link')]
    hospital_df[hospital_df.isna()] = 0
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
    st.markdown('**+ Địa chỉ:** '+ df_1.set_index('ID_BV').loc[input_id, 'ĐỊA CHỈ'] + ', Quận, ' + str(df_1.set_index('ID_BV').loc[input_id, 'QH']))
    st.markdown('**+ Lưu ý:** ' + df_1.set_index('ID_BV').loc[input_id,'GHI CHÚ'])
    lat = hospital_add[hospital_add.id_bv == input_id].lat
    lat = list(lat)[0]
    lon = hospital_add[hospital_add.id_bv == input_id].lon
    lon = list(lon)[0]
    bv_coor = (lat,lon)
    link1 = df_1.set_index('ID_BV').loc[input_id, 'Link website ']
    st.markdown('**+ Website của bệnh viện:** ')
    st.markdown(link1,unsafe_allow_html = True)
    st.write('**+ Bản đồ hướng dẫn:** ')
    st.markdown(link_ggmap(user_coor,bv_coor),unsafe_allow_html = True)
    st.markdown(':information_source: Từ vị trí của bạn đến bệnh viện khoảng ' + str(get_dis_coor_goong(bv_coor,user_coor)[0]) + 
    ', tốn khoảng ' + str(get_dis_coor_goong(bv_coor,user_coor)[1]))
    st.write('')
    st.write('')
    

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
    return dis_result.groupby('prognosis').max('similar').iloc[:,-1].sort_values(ascending=False)    

list_disease_eng = dis_df.eng.to_list()
list_disease_vie = dis_df.viet.to_list()
list_disease_id = dis_df.id_diseases.to_list()

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


df_1, df_2 = get_data()
st.sidebar.subheader('Bạn đang tìm bệnh viện theo tiêu chí:')
option1 = st.sidebar.radio("", ('Vui lòng lựa chọn ở các ô bên dưới',
    'Khám sức khỏe thông thường/ tổng quát', 'Khám sức khỏe cho người lái xe', 
    'Khám sức khỏe cho người nước ngoài', 'Khám sức khỏe để xuất ngoại','Cần tư vấn bệnh viện theo triệu chứng'))

check_box = st.sidebar.checkbox("Tìm các bệnh viện gần nhất")
if check_box:
    submitted = False
    with st.sidebar.form('bv_gan'):
        diachi_user = st.text_input("Địa chỉ của bạn", '10 Lê Hồng Phong, Quận 10,Hồ Chí Minh')
        submitted = st.form_submit_button("Tìm")
        if submitted:
            user_coor = get_coor_goong(diachi_user)

check_box_1 = st.sidebar.checkbox("Bạn muốn nhận email về thông tin bệnh viện bạn đang quan tâm")
if check_box_1:
    submitted_1 = False
    st.sidebar.selectbox('Bệnh viện quan tâm',list(df_1.iloc[:,1]))
    with st.sidebar.form('bv_quantam'):
        diachi_user = st.text_input("Địa chỉ của bạn", '10 Lê Hồng Phong, Quận 10,Hồ Chí Minh')
        email_user = st.text_input('Email của bạn')
        submitted_1 = st.form_submit_button("Nhận thông tin")
        if submitted_1:
            st.sidebar.markdown('### :white_check_mark: Đã gửi. Stay safe!')

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
    sym_input_eng = trans_sym(sym_input_vie)
    #convert to vector
    input_array = np.array([sym_to_vector(sym_input_eng)])
    output_disease_eng =  get_disease(train_df,input_array)
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
                st.write(df_result.loc[id_bv, :].set_index('TÊN'))
            if check_box:
                if submitted:
                    list_coor = get_coor(id_bv)
                    result_hospital = pd.DataFrame({'hospital_id':id_bv,'coor':list_coor})
                    result_hospital['geodesic'] = result_hospital.coor.apply(lambda x: geodesic(x, user_coor).km)
                    result_hospital = result_hospital.sort_values('geodesic',ascending=True)
                    top_hospital = result_hospital.iloc[0:3,:]
                    st.markdown('**Danh sách các bệnh viện gần vị trí của bạn**')
                    for input_id in list(top_hospital.loc[:,'hospital_id']):
                        print_hospital_info_txt(input_id,user_coor)

if option1 not in ['Vui lòng lựa chọn ở các ô bên dưới','Cần tư vấn bệnh viện theo triệu chứng'] :
    with st.beta_expander('Danh sách bệnh viện bạn có thể tham khảo'):
        st.dataframe(df_result.set_index('TÊN'))
    if check_box:
        if submitted:
            id_bv = list(df_result.iloc[:,0])
            list_coor = get_coor(id_bv)
            result_hospital = pd.DataFrame({'hospital_id':id_bv,'coor':list_coor})
            result_hospital['geodesic'] = result_hospital.coor.apply(lambda x: geodesic(x, user_coor).km)
            result_hospital = result_hospital.sort_values('geodesic',ascending=True)
            top_hospital = result_hospital.iloc[0:3,:]
            st.markdown('**Danh sách các bệnh viện gần vị trí của bạn**')
            for input_id in list(top_hospital.loc[:,'hospital_id']):
                with st.beta_expander():
                    print_hospital_info_txt(input_id,user_coor)